"""SQLite storage for imported synthetic matches. Generated fixtures remain seed-based."""
import os
import sqlite3
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
        if version != 1:
            raise RuntimeError(f"unsupported PULSE XI database version {version}")
        with connection:
            yield connection
    finally:
        connection.close()


def imported_matches() -> list[Match]:
    with connect() as db:
        return [Match.model_validate_json(row[0]) for row in db.execute("SELECT payload FROM matches ORDER BY match_id")]


def imported_match(match_id: str) -> tuple[Match, list[MatchEvent]] | None:
    with connect() as db:
        row = db.execute("SELECT payload FROM matches WHERE match_id=?", (match_id,)).fetchone()
        if row is None:
            return None
        events = [MatchEvent.model_validate_json(item[0]) for item in db.execute(
            "SELECT payload FROM events WHERE match_id=? ORDER BY sequence", (match_id,))]
    return Match.model_validate_json(row[0]), events


class StorageConflict(ValueError):
    pass


def ingest(match: Match, incoming: list[MatchEvent]) -> dict:
    """Merge atomically; exact duplicate IDs are no-ops and clocks define replay order."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        prior = db.execute("SELECT payload FROM matches WHERE match_id=?", (match.match_id,)).fetchone()
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
        fulltime = [index for index, event in enumerate(ordered) if event.event_type == EventType.fulltime]
        if fulltime and (len(fulltime) != 1 or fulltime[0] != len(ordered) - 1):
            raise ValueError("events occur after fulltime")
        db.execute("INSERT OR IGNORE INTO matches(match_id, payload) VALUES(?, ?)",
                   (match.match_id, match.model_dump_json()))
        db.execute("DELETE FROM events WHERE match_id=?", (match.match_id,))
        for sequence, event in enumerate(ordered, 1):
            normalized = event.model_copy(update={"sequence": sequence})
            db.execute("INSERT INTO events(match_id, event_id, sequence, match_second, payload) VALUES(?,?,?,?,?)",
                       (match.match_id, event.event_id, sequence, event.match_second,
                        normalized.model_dump_json(by_alias=True)))
    return {"match_id": match.match_id, "inserted": inserted, "total": len(ordered),
            "last_sequence": len(ordered)}
