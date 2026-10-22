"""SQLite storage for imported synthetic matches. Generated fixtures remain seed-based."""
import os
import json
import sqlite3
from uuid import uuid4
from contextlib import contextmanager
from pathlib import Path
from time import monotonic, sleep

from .models import EventType, Match, MatchEvent


def database_path() -> Path:
    return Path(os.getenv("PULSE_DB_PATH", str(Path(__file__).resolve().parents[1] / "data" / "pulse_xi.sqlite")))


def enable_wal(connection: sqlite3.Connection) -> None:
    """Journal-mode promotion can return BUSY without SQLite's busy timeout."""
    deadline = monotonic() + 10
    while True:
        try:
            if connection.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
                connection.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as error:
            if (getattr(error, "sqlite_errorcode", 0) & 255) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                raise
            if monotonic() >= deadline:
                raise
            sleep(0.02)


@contextmanager
def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        enable_wal(connection)
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            # Recheck under the SQLite writer lock: another request/process may
            # have completed migration after our first read. executescript would
            # implicitly commit, so keep every DDL statement in this transaction.
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                connection.execute("CREATE TABLE matches (match_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
                connection.execute("""CREATE TABLE events (
                    match_id TEXT NOT NULL REFERENCES matches(match_id),
                    event_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                    match_second INTEGER NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY (match_id, event_id), UNIQUE (match_id, sequence))""")
                connection.execute("CREATE INDEX events_clock ON events(match_id, match_second, sequence)")
                connection.execute("PRAGMA user_version=1")
                version = 1
            connection.commit()
        if version == 1:
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 1:
                connection.execute("CREATE TABLE IF NOT EXISTS package_metadata (match_id TEXT PRIMARY KEY REFERENCES matches(match_id), provenance TEXT NOT NULL)")
                connection.execute("""CREATE TABLE match_lifecycle (
                    match_id TEXT PRIMARY KEY REFERENCES matches(match_id), generation TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK(revision > 0), archived INTEGER NOT NULL CHECK(archived IN (0,1)))""")
                connection.execute("CREATE TABLE deleted_matches (match_id TEXT PRIMARY KEY, deletion_id TEXT NOT NULL, deleted_at TEXT NOT NULL)")
                for (match_id,) in connection.execute("SELECT match_id FROM matches").fetchall():
                    connection.execute("INSERT INTO match_lifecycle VALUES (?,?,1,0)", (match_id, uuid4().hex))
                connection.execute("PRAGMA user_version=2")
                version = 2
            connection.commit()
        if version not in (2, 3):
            raise RuntimeError(f"unsupported PULSE XI database version {version}")
        with connection:
            yield connection
    finally:
        connection.close()


def imported_matches() -> list[Match]:
    with connect() as db:
        return [Match.model_validate_json(row[0]) for row in db.execute("SELECT m.payload FROM matches m LEFT JOIN match_lifecycle l USING(match_id) WHERE COALESCE(l.archived,0)=0 ORDER BY m.match_id")]


def imported_snapshot(match_id: str) -> tuple[Match, list[MatchEvent], dict | None] | None:
    with connect() as db:
        db.execute("BEGIN")
        row = db.execute("SELECT payload FROM matches WHERE match_id=?", (match_id,)).fetchone()
        if row is None:
            return None
        events = [MatchEvent.model_validate_json(item[0]) for item in db.execute(
            "SELECT payload FROM events WHERE match_id=? ORDER BY sequence", (match_id,))]
        provenance = db.execute('SELECT provenance FROM package_metadata WHERE match_id=?',(match_id,)).fetchone()
    return Match.model_validate_json(row[0]), events, json.loads(provenance[0]) if provenance else None


def imported_match(match_id: str) -> tuple[Match, list[MatchEvent]] | None:
    snapshot = imported_snapshot(match_id)
    return snapshot[:2] if snapshot else None


class StorageConflict(ValueError):
    pass


def inspect_imported(match_id: str) -> tuple[Match, list[MatchEvent]] | None:
    """No-write lookup for import previews, including before a database exists."""
    path = database_path().resolve()
    if not path.is_file():
        return None
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)
    try:
        db.execute("BEGIN")
        row = db.execute("SELECT payload FROM matches WHERE match_id=?", (match_id,)).fetchone()
        if row is None:
            return None
        events = [MatchEvent.model_validate_json(e[0]) for e in db.execute(
            "SELECT payload FROM events WHERE match_id=? ORDER BY sequence", (match_id,))]
        return Match.model_validate_json(row[0]), events
    finally:
        db.close()


def package_provenance(match_id: str) -> dict | None:
    path = database_path().resolve()
    if not path.is_file():
        return None
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)
    try:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='package_metadata'").fetchone():
            return None
        row = db.execute("SELECT provenance FROM package_metadata WHERE match_id=?", (match_id,)).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        db.close()


def ingest_package(match: Match, events: list[MatchEvent], provenance: dict | None = None, recovery_id: str | None = None) -> dict:
    """Immutable complete dataset; concurrent duplicates are no-ops, not appends."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        tombstone = db.execute("SELECT deletion_id FROM deleted_matches WHERE match_id=?", (match.match_id,)).fetchone()
        if (tombstone and tombstone[0] != recovery_id) or (recovery_id and not tombstone):
            raise StorageConflict("match was deleted or recovery is stale; preview the package and explicitly recover it")
        # Additive metadata only; existing matches/events and their schema remain intact.
        db.execute("CREATE TABLE IF NOT EXISTS package_metadata (match_id TEXT PRIMARY KEY REFERENCES matches(match_id), provenance TEXT NOT NULL)")
        prior = db.execute("SELECT payload FROM matches WHERE match_id=?", (match.match_id,)).fetchone()
        if prior:
            existing = [MatchEvent.model_validate_json(e[0]) for e in db.execute(
                "SELECT payload FROM events WHERE match_id=? ORDER BY sequence", (match.match_id,))]
            if Match.model_validate_json(prior[0]).model_dump() != match.model_dump() or [e.model_dump() for e in existing] != [e.model_dump() for e in events]:
                raise StorageConflict("complete package conflicts with stored match or events")
            db.execute("INSERT OR IGNORE INTO package_metadata VALUES (?, ?)", (match.match_id, json.dumps(provenance or {})))
            return {"match_id": match.match_id, "inserted": 0, "total": len(existing)}
        if db.execute("SELECT COUNT(*) FROM matches").fetchone()[0] >= 100:
            raise StorageConflict("local library limit of 100 imported matches reached")
        db.execute("INSERT INTO matches VALUES (?, ?)", (match.match_id, match.model_dump_json()))
        for event in events:
            db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)", (match.match_id, event.event_id, event.sequence,
                       event.match_second, event.model_dump_json(by_alias=True)))
        db.execute("INSERT INTO package_metadata VALUES (?, ?)", (match.match_id, json.dumps(provenance or {})))
        db.execute("INSERT INTO match_lifecycle VALUES (?,?,1,0)", (match.match_id, uuid4().hex))
        if tombstone:
            db.execute("DELETE FROM deleted_matches WHERE match_id=?", (match.match_id,))
    return {"match_id": match.match_id, "inserted": len(events), "total": len(events)}


def ingest(match: Match, incoming: list[MatchEvent]) -> dict:
    """Merge atomically; exact duplicate IDs are no-ops and clocks define replay order."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM deleted_matches WHERE match_id=?", (match.match_id,)).fetchone():
            raise StorageConflict("deleted match requires explicit package recovery")
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='package_metadata'").fetchone() and db.execute(
                "SELECT 1 FROM package_metadata WHERE match_id=?", (match.match_id,)).fetchone():
            raise StorageConflict("complete package is immutable; use the package import endpoint for identical reimports")
        prior = db.execute("SELECT payload FROM matches WHERE match_id=?", (match.match_id,)).fetchone()
        if not prior and db.execute("SELECT COUNT(*) FROM matches").fetchone()[0] >= 100:
            raise StorageConflict("local library limit of 100 imported matches reached")
        if prior and Match.model_validate_json(prior[0]) != match:
            raise StorageConflict("match metadata conflict")
        prior_events = [MatchEvent.model_validate_json(row[0]) for row in db.execute(
            "SELECT payload FROM events WHERE match_id=?", (match.match_id,))]
        by_id = {event.event_id: event for event in prior_events}
        inserted = 0
        for event in incoming:
            existing = by_id.get(event.event_id)
            if existing:
                if existing.model_copy(update={"sequence": event.sequence}) != event:
                    raise StorageConflict(f"event ID conflict: {event.event_id}")
            else:
                by_id[event.event_id] = event
                inserted += 1
        ordered = sorted(by_id.values(), key=lambda event: (event.match_second, event.event_id))
        if len(ordered) > 1000:
            raise ValueError("stored match exceeds the 1,000-event limit")
        if len(match.model_dump_json().encode()) + sum(len(e.model_dump_json(by_alias=True).encode()) for e in ordered) > 2_000_000:
            raise ValueError("stored match exceeds the 2 MB data limit")
        fulltime = [index for index, event in enumerate(ordered) if event.event_type == EventType.fulltime]
        if fulltime and (len(fulltime) != 1 or fulltime[0] != len(ordered) - 1):
            raise ValueError("events occur after fulltime")
        db.execute("INSERT OR IGNORE INTO matches(match_id, payload) VALUES(?, ?)",
                   (match.match_id, match.model_dump_json()))
        db.execute("INSERT OR IGNORE INTO match_lifecycle VALUES (?,?,1,0)", (match.match_id, uuid4().hex))
        if prior and inserted:
            db.execute("UPDATE match_lifecycle SET revision=revision+1 WHERE match_id=?", (match.match_id,))
        db.execute("DELETE FROM events WHERE match_id=?", (match.match_id,))
        for sequence, event in enumerate(ordered, 1):
            normalized = event.model_copy(update={"sequence": sequence})
            db.execute("INSERT INTO events(match_id, event_id, sequence, match_second, payload) VALUES(?,?,?,?,?)",
                       (match.match_id, event.event_id, sequence, event.match_second,
                        normalized.model_dump_json(by_alias=True)))
    return {"match_id": match.match_id, "inserted": inserted, "total": len(ordered),
            "last_sequence": len(ordered)}
