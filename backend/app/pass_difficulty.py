"""Versioned descriptive pass heuristic and independent evidence reconstruction.

v1 deliberately excludes pressure: event coordinates use each team's attacking
frame and the legacy stream does not declare pressure coverage or a frame transform.
"""
from math import floor, hypot
from statistics import mean, median
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .models import EventType, Match, MatchEvent, Point

FORMULA_VERSION = "synthetic-pass-difficulty/1.0"
PRESSURE_REASON = "Pressure coverage and a shared opponent coordinate frame are unavailable."


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class DifficultyFactor(StrictModel):
    factor_id: Literal["distance", "progression", "pressure_context"]
    available: bool
    raw_value: float | None
    normalized_value: float | None
    effective_weight: float
    contribution_points: float | None
    units: str
    supporting_event_ids: list[str]
    unavailable_reason: str | None = None


class PassDifficulty(StrictModel):
    match_id: str
    event_id: str
    match_second: int
    at_second: int
    team_id: str
    player_id: str
    recipient_id: str | None
    start: Point | None
    end: Point | None
    outcome: str | None
    score: int | None = Field(ge=0, le=100)
    scale: Literal["0–100"] = "0–100"
    heuristic_label: str = "Heuristic synthetic pass difficulty; not a failure probability."
    difficulty_band: Literal["low", "moderate", "high", "unavailable"]
    formula_version: Literal["synthetic-pass-difficulty/1.0"] = FORMULA_VERSION
    factors: list[DifficultyFactor]
    excluded_factors: list[str] = ["passing_lane", "defender_proximity"]
    unavailable_reason: str | None
    supporting_event_ids: list[str]
    verification_status: Literal["verified_rule_based"] = "verified_rule_based"


class PassDifficultyPage(StrictModel):
    match_id: str
    at_second: int
    items: list[PassDifficulty]
    next_cursor: int | None
    total_visible_passes: int


class PassDifficultyEvidence(StrictModel):
    claim: PassDifficulty
    verified: bool
    source_events: list[MatchEvent]


class PlayerDifficultySummary(StrictModel):
    player_id: str
    sample_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    mean_score: float | None = Field(ge=0, le=100)
    median_score: float | None = Field(ge=0, le=100)


class PlayerDifficultyResponse(StrictModel):
    match_id: str
    at_second: int
    players: list[PlayerDifficultySummary]


def score_pass(match: Match, event: MatchEvent, at_second: int) -> PassDifficulty:
    """Compute from the pass alone; later events can never alter this version."""
    if not 0 <= at_second <= match.duration_seconds:
        raise ValueError("invalid replay cutoff")
    if (event.match_id != match.match_id or event.event_type != EventType.pass_
            or event.match_second > at_second):
        raise ValueError("visible pass not found")
    team = next((t for t in (match.home, match.away) if t.team_id == event.team_id), None)
    players = {p.player_id for p in team.players} if team else set()
    if event.actor_id not in players or event.recipient_id is not None and event.recipient_id not in players:
        raise ValueError("pass has invalid team or player attribution")
    located = event.start is not None and event.end is not None
    distance = hypot(event.end.x - event.start.x, event.end.y - event.start.y) if located else None
    progression = max(0.0, event.end.x - event.start.x) if located else None
    factors = []
    weighted = 0.0
    for key, value, cap, weight in (("distance", distance, 100.0, 55 / 85),
                                    ("progression", progression, 60.0, 30 / 85)):
        normalized = min(value / cap, 1.0) if value is not None else None
        points = 100 * weight * normalized if normalized is not None else None
        weighted += points or 0
        factors.append(DifficultyFactor(
            factor_id=key, available=located, raw_value=value, normalized_value=normalized,
            effective_weight=weight, contribution_points=points, units="normalized pitch units",
            supporting_event_ids=[event.event_id],
            unavailable_reason=None if located else "Pass start and end coordinates are required."))
    factors.append(DifficultyFactor(
        factor_id="pressure_context", available=False, raw_value=None, normalized_value=None,
        effective_weight=0, contribution_points=None, units="recorded context",
        supporting_event_ids=[], unavailable_reason=PRESSURE_REASON))
    # Half-up rounding, applied once to the unrounded sum. Never use outcome.
    score = min(100, max(0, floor(weighted + 0.5))) if located else None
    band = "unavailable" if score is None else "high" if score >= 70 else "moderate" if score >= 35 else "low"
    return PassDifficulty(
        match_id=match.match_id, event_id=event.event_id, match_second=event.match_second,
        at_second=at_second, team_id=event.team_id, player_id=event.actor_id,
        recipient_id=event.recipient_id, start=event.start, end=event.end, outcome=event.outcome,
        score=score, difficulty_band=band, factors=factors,
        unavailable_reason=None if located else "Pass start and end coordinates are required.",
        supporting_event_ids=[event.event_id])


def verify_pass_difficulty(packet: PassDifficulty, match: Match, events: list[MatchEvent]) -> bool:
    """Rebuild every field from authoritative source data; reject altered claims."""
    matches = [e for e in events if e.event_id == packet.event_id]
    if len(matches) != 1:
        return False
    try:
        PassDifficulty.model_validate(packet.model_dump())
        expected = score_pass(match, matches[0], packet.at_second)
    except (ValueError, ValidationError):
        return False
    return packet.model_dump_json() == expected.model_dump_json()


def player_summary(items: list[PassDifficulty]) -> list[PlayerDifficultySummary]:
    """Descriptive summaries retain sample counts and unavailable counts."""
    players = sorted({item.player_id for item in items})
    result = []
    for player_id in players:
        own = [item for item in items if item.player_id == player_id]
        scores = [item.score for item in own if item.score is not None]
        result.append(PlayerDifficultySummary(
            player_id=player_id, sample_count=len(scores), unavailable_count=len(own) - len(scores),
            mean_score=round(mean(scores), 2) if scores else None,
            median_score=median(scores) if scores else None))
    return result
