"""PULSE XI local API. A match stream is a deterministic replay of synthetic events."""
import asyncio
from functools import lru_cache
from pathlib import Path
from threading import RLock

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analytics import metrics_at, state_at
from .models import EventType, Match, MatchEvent
from .simulator import FIXTURES, generate

app = FastAPI(title="PULSE XI API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def index():
    if (DIST / "index.html").is_file():
        return FileResponse(DIST / "index.html")
    return {"message": "Frontend not built; run scripts/build-local.ps1"}
ingested: dict[str, tuple[Match, list[MatchEvent]]] = {}
ingest_lock = RLock()


@lru_cache(maxsize=24)
def stored(fixture: str, seed: int | None = None) -> tuple[Match, list[MatchEvent]]:
    return generate(fixture, seed)


def get_match(match_id: str) -> tuple[Match, list[MatchEvent]]:
    with ingest_lock:
        if match_id in ingested:
            return ingested[match_id]
    for fixture, (seed, _, _) in FIXTURES.items():
        if match_id == f"{fixture}-{seed}":
            return stored(fixture)
    if match_id.startswith("custom-"):
        try:
            return stored("custom", int(match_id.split("-", 1)[1]))
        except ValueError:
            pass
    raise HTTPException(404, "match not found")


class GenerateRequest(BaseModel):
    seed: int = Field(ge=0, le=2_147_483_647)


class IngestRequest(BaseModel):
    match: Match
    events: list[MatchEvent] = Field(min_length=1, max_length=1000)


@app.get("/health")
def health():
    return {"status": "ok", "simulation": "synthetic", "narrative_provider": "not_configured"}


@app.get("/api/matches")
def list_matches():
    with ingest_lock:
        return [stored(name)[0] for name in FIXTURES] + [match for match, _ in ingested.values()]


@app.post("/api/matches/generate", response_model=Match)
def create_match(request: GenerateRequest):
    return stored("custom", request.seed)[0]


@app.post("/api/matches/ingest")
def ingest_match(request: IngestRequest):
    """Idempotent, out-of-order tolerant ingestion of compatible synthetic events."""
    match = request.match
    if match.match_id.startswith("custom-") or any(match.match_id == f"{name}-{seed}" for name, (seed, _, _) in FIXTURES.items()):
        raise HTTPException(409, "reserved generated match ID")
    members = {team.team_id: {player.player_id for player in team.players} for team in (match.home, match.away)}
    for event in request.events:
        if event.match_id != match.match_id:
            raise HTTPException(422, f"event {event.event_id} belongs to another match")
        if event.team_id is not None and event.team_id not in members:
            raise HTTPException(422, f"unknown team in {event.event_id}")
        if event.team_id is not None and (event.actor_id not in members[event.team_id] or
                                          event.recipient_id is not None and event.recipient_id not in members[event.team_id]):
            raise HTTPException(422, f"unknown player in {event.event_id}")
        if event.team_id is None and (event.actor_id is not None or event.recipient_id is not None):
            raise HTTPException(422, f"teamless event has player in {event.event_id}")
    with ingest_lock:
        previous = ingested.get(match.match_id)
        if previous and previous[0] != match:
            raise HTTPException(409, "match metadata conflict")
        by_id = {event.event_id: event for event in previous[1]} if previous else {}
        inserted = 0
        for event in request.events:
            existing = by_id.get(event.event_id)
            if existing:
                if existing.model_copy(update={"sequence": event.sequence}) != event:
                    raise HTTPException(409, f"event ID conflict: {event.event_id}")
            else:
                by_id[event.event_id] = event
                inserted += 1
        ordered = sorted(by_id.values(), key=lambda event: (event.match_second, event.event_id))
        fulltime = [index for index, event in enumerate(ordered) if event.event_type == EventType.fulltime]
        if fulltime and (len(fulltime) != 1 or fulltime[0] != len(ordered) - 1):
            raise HTTPException(422, "events occur after fulltime")
        normalized = [event.model_copy(update={"sequence": index + 1}) for index, event in enumerate(ordered)]
        ingested[match.match_id] = (match, normalized)
    return {"match_id": match.match_id, "inserted": inserted, "total": len(normalized),
            "last_sequence": len(normalized)}


@app.get("/api/matches/{match_id}", response_model=Match)
def match_detail(match_id: str):
    return get_match(match_id)[0]


@app.get("/api/matches/{match_id}/events", response_model=list[MatchEvent])
def match_events(match_id: str, cursor: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=1000)):
    _, events = get_match(match_id)
    return [event for event in events if event.sequence > cursor][:limit]


@app.get("/api/matches/{match_id}/state")
def match_state(match_id: str, at_second: int = Query(5400, ge=0, le=5400)):
    match, events = get_match(match_id)
    return state_at(match, events, at_second)


@app.get("/api/matches/{match_id}/metrics")
def match_metrics(match_id: str, at_second: int = Query(5400, ge=0, le=5400)):
    match, events = get_match(match_id)
    return metrics_at(match, events, at_second)


@app.websocket("/ws/matches/{match_id}")
async def stream_match(websocket: WebSocket, match_id: str, cursor: int = 0):
    try:
        match, events = get_match(match_id)
    except HTTPException:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    await websocket.send_json({"kind": "snapshot", "match": match.model_dump(mode="json"),
                               "state": state_at(match, events, 0).model_dump(mode="json"), "cursor": cursor})
    try:
        for event in events:
            if event.sequence <= cursor:
                continue
            await websocket.send_json({"kind": "event", "sequence": event.sequence,
                                       "event": event.model_dump(mode="json", by_alias=True)})
            await asyncio.sleep(0.015)
        await websocket.send_json({"kind": "complete", "cursor": events[-1].sequence})
    except WebSocketDisconnect:
        pass
