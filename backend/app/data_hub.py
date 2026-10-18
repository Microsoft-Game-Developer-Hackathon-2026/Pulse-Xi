"""Portable recorded-event packages. No simulation or engine snapshots."""
import json
import os
import re
import secrets
import hashlib
from collections import Counter
from datetime import datetime, timezone
from typing import Literal

from fastapi import Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import Match, MatchEvent, Player, Point, Team
from .storage import StorageConflict, inspect_imported

MAX_BYTES = 2_000_000
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$")


def require_import_token(authorization: str | None = Header(default=None)) -> None:
    token = os.getenv("PULSE_IMPORT_TOKEN", "")
    if len(token) < 32:
        raise HTTPException(503, "Imports disabled: configure PULSE_IMPORT_TOKEN with at least 32 characters on the server")
    supplied = (authorization or "").removeprefix("Bearer ")
    if not (authorization or "").startswith("Bearer ") or not secrets.compare_digest(supplied.encode(), token.encode()):
        raise HTTPException(403, "Import authorization required")


class PackagePlayer(Player):
    model_config = ConfigDict(extra="forbid", strict=True)
    role: str = Field(min_length=1, max_length=80)


class PackageTeam(Team):
    model_config = ConfigDict(extra="forbid", strict=True)
    players: list[PackagePlayer] = Field(min_length=1, max_length=40)


class PackageMatch(Match):
    model_config = ConfigDict(extra="forbid", strict=True)
    home: PackageTeam
    away: PackageTeam
    duration_seconds: int = Field(default=5400, ge=1, le=5400)


class PackagePoint(Point):
    model_config = ConfigDict(extra="forbid", strict=True)


class PackageEvent(MatchEvent):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    start: PackagePoint | None = None
    end: PackagePoint | None = None
    sequence: int = Field(ge=1, le=100_000_000, strict=True)
    match_second: int = Field(ge=0, le=5400, strict=True)
    generated_at_utc: datetime
    outcome: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def timestamp_metadata(self):
        if self.generated_at_utc.utcoffset() is None:
            raise ValueError("generated_at_utc requires an explicit timezone")
        if self.possession_id is not None and not ID.fullmatch(self.possession_id):
            raise ValueError("invalid possession identifier")
        if len(self.qualifiers) > 64 or any(len(k) > 80 or isinstance(v, str) and len(v) > 1000 for k, v in self.qualifiers.items()):
            raise ValueError("qualifiers exceed 64 entries, 80-character keys or 1,000-character values")
        return self


class PackageIntegrity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    algorithm: Literal["sha256"]
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def package_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode('utf-8')).hexdigest()


class MatchPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["pulse-xi-match-package/1", "pulse-xi-match-package/2"]
    match: PackageMatch
    events: list[PackageEvent] = Field(max_length=1000)
    provenance: dict[Literal["source", "exported_at", "application_revision"], str | None] = Field(default_factory=dict)
    integrity: PackageIntegrity | None = None

    @model_validator(mode="after")
    def references(self):
        match = self.match
        if any(value is not None and len(value) > 500 for value in self.provenance.values()):
            raise ValueError("provenance fields must be at most 500 characters")
        identifiers = [match.match_id, match.home.team_id, match.away.team_id]
        players = [p.player_id for t in (match.home, match.away) for p in t.players]
        if any(not ID.fullmatch(value) for value in identifiers + players):
            raise ValueError("match/team/player IDs must be 1..160 safe identifier characters")
        if match.home.team_id == match.away.team_id or len(set(players)) != len(players):
            raise ValueError("teams and player identities must be distinct")
        for text in [match.title, match.home.name, match.away.name] + [p.name for t in (match.home, match.away) for p in t.players]:
            if not text.strip() or len(text) > 200:
                raise ValueError("names and title must contain 1..200 characters")
        for team in (match.home, match.away):
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", team.color):
                raise ValueError("team color must be a six-digit hex color")
        validate_events(match, self.events)
        if self.schema_version == 'pulse-xi-match-package/2' and not self.integrity:
            raise ValueError('version 2 packages require SHA-256 integrity metadata')
        if self.integrity:
            value = self.model_dump(mode='json', by_alias=True, exclude={'integrity'})
            value['events'].sort(key=lambda e: e['sequence'])
            if not secrets.compare_digest(self.integrity.content_sha256, package_digest(value)):
                raise ValueError('package checksum mismatch; source data or provenance was altered')
        return self


def validate_events(match: Match, events: list[MatchEvent]) -> None:
    members = {t.team_id: {p.player_id for p in t.players} for t in (match.home, match.away)}
    ids: set[str] = set()
    sequences: set[int] = set()
    locations = {id(event): index for index, event in enumerate(events)}
    ordered = sorted(events, key=lambda e: e.sequence)
    previous_time = -1
    for index, event in enumerate(ordered):
        prefix = f"events[{locations[id(event)]}] ({event.event_id})"
        if not ID.fullmatch(event.event_id) or event.event_id in ids or event.sequence in sequences:
            raise ValueError(f"{prefix}: invalid or duplicate event ID/sequence")
        ids.add(event.event_id)
        sequences.add(event.sequence)
        if event.match_id != match.match_id:
            raise ValueError(f"{prefix}: wrong match identity")
        if event.match_second < previous_time or event.match_second > match.duration_seconds:
            raise ValueError(f"{prefix}: timestamp/order exceeds match boundaries")
        previous_time = event.match_second
        if event.event_type == "fulltime" and index != len(ordered) - 1:
            raise ValueError(f"{prefix}: events after fulltime")
        if event.team_id is None:
            if event.actor_id is not None or event.recipient_id is not None:
                raise ValueError(f"{prefix}: player reference requires a team")
        elif event.team_id not in members or any(p is not None and p not in members[event.team_id] for p in (event.actor_id, event.recipient_id)):
            raise ValueError(f"{prefix}: unknown team or player reference")
        if not all(isinstance(v, (str, int, float, bool)) for v in event.qualifiers.values()):
            raise ValueError(f"{prefix}: unsupported qualifier")


def quality(match: Match, events: list[MatchEvent]) -> dict:
    passes = [e for e in events if e.event_type == "pass"]
    missing_start = sum(e.start is None for e in events)
    ordered = sorted(events, key=lambda e: e.sequence)
    return {"event_count": len(events), "event_types": dict(sorted(Counter(e.event_type.value for e in events).items())),
            "duplicate_event_ids": len(events) - len({e.event_id for e in events}),
            "sequence_consistent": len({e.sequence for e in events}) == len(events) and all(a.match_second <= b.match_second for a, b in zip(ordered, ordered[1:])),
            "first_second": min((e.match_second for e in events), default=None),
            "last_second": max((e.match_second for e in events), default=None),
            "missing_start": missing_start, "missing_end": sum(e.end is None for e in events),
            "missing_actor": sum(e.actor_id is None for e in events),
            "missing_recipient_on_passes": sum(e.recipient_id is None for e in passes),
            "pass_count": len(passes), "passes_with_coordinates": sum(e.start is not None and e.end is not None for e in passes),
            "limitations": ["Synthetic recorded events, not continuous tracking.",
                            "Pressure coverage is not established by a count of pressure events.",
                            "Missing optional fields are unavailable, never inferred."]}


def package_conflict(package: MatchPackage) -> str:
    prior = inspect_imported(package.match.match_id)
    if prior is None:
        return "new"
    match, events = prior
    if match.model_dump(mode="json") != package.match.model_dump(mode="json"):
        raise StorageConflict("match metadata conflicts with stored match")
    expected = [e.model_dump(mode="json", by_alias=True) for e in sorted(package.events, key=lambda e: e.sequence)]
    if [e.model_dump(mode="json", by_alias=True) for e in events] != expected:
        raise StorageConflict("complete package conflicts with stored events; choose a new match ID or restore the original package")
    return "identical"


def package_bytes(match: Match, events: list[MatchEvent], provenance: dict | None = None) -> bytes:
    if len(events) > 1000:
        raise HTTPException(413, "Complete package exceeds the 1,000-event import limit; no data was truncated")
    value = {"schema_version": "pulse-xi-match-package/2", "match": match.model_dump(mode="json"),
             "events": [e.model_dump(mode="json", by_alias=True) for e in sorted(events, key=lambda e: e.sequence)],
             "provenance": {"source": (provenance or {}).get("source", "Pulse-Xi recorded match export"),
                            "application_revision": (provenance or {}).get("application_revision"),
                            "exported_at": datetime.now(timezone.utc).isoformat()}}
    value['integrity'] = {'algorithm':'sha256', 'content_sha256':package_digest(value)}
    result = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(result) > MAX_BYTES:
        raise HTTPException(413, "Complete package exceeds the 2 MB import limit; no data was truncated")
    # Never offer a download that this installation cannot import losslessly.
    MatchPackage.model_validate_json(result)
    return result
