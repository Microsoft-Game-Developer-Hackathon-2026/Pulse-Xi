"""Authorized, revisioned editorial drafts over deterministic overlay cues."""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .evidence import overlays_for
from .models import Match, MatchEvent, OverlayCue
from .storage import connect


class CueEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    cue_id: str = Field(min_length=1, max_length=160)
    order: int = Field(ge=0, le=99)
    start_match_second: int = Field(ge=0, le=5400)
    show_duration_seconds: int = Field(ge=1, le=60)
    priority: int = Field(ge=0, le=100)
    visual_template: Literal["score_lower_third", "tactical_lower_third"]
    safe_area: Literal["lower_third", "top_left", "top_right"] = "lower_third"
    transition: Literal["fade", "slide", "wipe"] = "fade"


class DraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=0)
    cues: list[CueEdit] = Field(max_length=100)


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=1)


def _ensure_tables(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS director_studio_state (
        match_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, cues_json TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS director_studio_approvals (
        match_id TEXT NOT NULL, revision INTEGER NOT NULL, snapshot_json TEXT NOT NULL,
        approved_at TEXT NOT NULL, PRIMARY KEY(match_id, revision))""")
    db.execute("""CREATE TABLE IF NOT EXISTS director_studio_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT, match_id TEXT NOT NULL, revision INTEGER NOT NULL,
        action TEXT NOT NULL, at_utc TEXT NOT NULL)""")


def _sources(match: Match, events: list[MatchEvent]) -> dict[str, OverlayCue]:
    return {cue.cue_id: cue for cue in overlays_for(match, events, match.duration_seconds)}


def _materialize(match: Match, sources: dict[str, OverlayCue], edits: list[CueEdit]) -> list[dict]:
    if len({item.cue_id for item in edits}) != len(edits) or len({item.order for item in edits}) != len(edits):
        raise ValueError("cue IDs and order values must be unique")
    ordered = sorted(edits, key=lambda item: item.order)
    previous_end = -1
    rows = []
    for edit in ordered:
        source = sources.get(edit.cue_id)
        if source is None:
            raise ValueError("cue is not a current verified overlay")
        if edit.visual_template != source.visual_template:
            raise ValueError("template must match the verified cue category")
        end = edit.start_match_second + edit.show_duration_seconds
        if edit.start_match_second < source.trigger_match_second or end > match.duration_seconds:
            raise ValueError("cue timing must follow its source event and stay within the match")
        if edit.start_match_second < previous_end:
            raise ValueError("cue schedule overlaps; move or reorder the conflicting cue")
        previous_end = end
        rows.append({**source.model_dump(mode="json"), "order": edit.order,
                     "start_match_second": edit.start_match_second,
                     "end_match_second": end,
                     "show_duration_seconds": edit.show_duration_seconds,
                     "priority": edit.priority, "visual_template": edit.visual_template,
                     "safe_area": edit.safe_area, "transition": edit.transition})
    return rows


def _default_edits(sources: dict[str, OverlayCue]) -> list[CueEdit]:
    return [CueEdit(cue_id=cue.cue_id, order=index, start_match_second=cue.start_match_second,
                    show_duration_seconds=cue.show_duration_seconds, priority=cue.priority,
                    visual_template=cue.visual_template)
            for index, cue in enumerate(sorted(sources.values(), key=lambda cue: (cue.start_match_second, cue.cue_id)))]


def read_studio(match: Match, events: list[MatchEvent]) -> dict:
    sources = _sources(match, events)
    with connect() as db:
        _ensure_tables(db)
        row = db.execute("SELECT revision,cues_json FROM director_studio_state WHERE match_id=?", (match.match_id,)).fetchone()
        approved = db.execute("SELECT MAX(revision) FROM director_studio_approvals WHERE match_id=?", (match.match_id,)).fetchone()[0]
        audit = db.execute("SELECT revision,action,at_utc FROM director_studio_audit WHERE match_id=? ORDER BY id DESC LIMIT 50", (match.match_id,)).fetchall()
    revision = row[0] if row else 0
    edits = [CueEdit.model_validate(item) for item in json.loads(row[1])] if row else _default_edits(sources)
    return {"schema_version": "director-studio/1", "match_id": match.match_id, "revision": revision,
            "approved_revision": approved, "status": "draft" if approved != revision else "approved",
            "cues": _materialize(match, sources, edits),
            "audit_history": [{"revision": item[0], "action": item[1], "at_utc": item[2]} for item in audit]}


def save_studio(match: Match, events: list[MatchEvent], update: DraftUpdate) -> dict:
    sources = _sources(match, events)
    _materialize(match, sources, update.cues)
    serialized = json.dumps([item.model_dump(mode="json") for item in update.cues], sort_keys=True, separators=(",", ":"))
    with connect() as db:
        _ensure_tables(db)
        db.execute("BEGIN IMMEDIATE")
        current = db.execute("SELECT revision FROM director_studio_state WHERE match_id=?", (match.match_id,)).fetchone()
        revision = current[0] if current else 0
        if revision != update.expected_revision:
            raise RuntimeError("studio draft changed; reload the current revision")
        new_revision = revision + 1
        db.execute("INSERT INTO director_studio_state VALUES (?,?,?) ON CONFLICT(match_id) DO UPDATE SET revision=excluded.revision,cues_json=excluded.cues_json",
                   (match.match_id, new_revision, serialized))
        db.execute("INSERT INTO director_studio_audit(match_id,revision,action,at_utc) VALUES (?,?,?,?)",
                   (match.match_id, new_revision, "draft_saved", datetime.now(timezone.utc).isoformat()))
    return read_studio(match, events)


def approve_studio(match: Match, events: list[MatchEvent], request: ApprovalRequest) -> dict:
    with connect() as db:
        _ensure_tables(db)
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT revision,cues_json FROM director_studio_state WHERE match_id=?", (match.match_id,)).fetchone()
        if row is None or row[0] != request.expected_revision:
            raise RuntimeError("studio draft changed; reload the current revision")
        edits = [CueEdit.model_validate(item) for item in json.loads(row[1])]
        snapshot = _materialize(match, _sources(match, events), edits)
        serialized = json.dumps({"schema_version": "director-studio-export/1", "match_id": match.match_id,
                                 "revision": row[0], "cues": snapshot}, sort_keys=True, separators=(",", ":"))
        now = datetime.now(timezone.utc).isoformat()
        existing = db.execute("SELECT approved_at FROM director_studio_approvals WHERE match_id=? AND revision=?", (match.match_id, row[0])).fetchone()
        if existing:
            now = existing[0]
        else:
            db.execute("INSERT INTO director_studio_approvals VALUES (?,?,?,?)",
                       (match.match_id, row[0], serialized, now))
            db.execute("INSERT INTO director_studio_audit(match_id,revision,action,at_utc) VALUES (?,?,?,?)",
                       (match.match_id, row[0], "approved", now))
    return {"match_id": match.match_id, "revision": request.expected_revision,
            "status": "approved", "approved_at": now}


def export_studio(match_id: str, revision: int | None = None) -> dict:
    with connect() as db:
        _ensure_tables(db)
        if revision is None:
            row = db.execute("SELECT snapshot_json FROM director_studio_approvals WHERE match_id=? ORDER BY revision DESC LIMIT 1", (match_id,)).fetchone()
        else:
            row = db.execute("SELECT snapshot_json FROM director_studio_approvals WHERE match_id=? AND revision=?", (match_id, revision)).fetchone()
    if row is None:
        raise KeyError("no approved studio revision exists")
    return json.loads(row[0])
