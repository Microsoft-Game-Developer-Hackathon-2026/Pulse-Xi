"""PULSE XI local API. A match stream is a deterministic replay of synthetic events."""
import asyncio
import os
import secrets
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analytics import metrics_at, state_at, tactics_at
from .agents import TRACES, configured, run_specialists
from .evidence import insights_for, overlays_for, recap_for
from .models import Match, MatchEvent
from .pass_difficulty import (
    PassDifficulty, PassDifficultyEvidence, PassDifficultyPage, PlayerDifficultyResponse,
    player_summary, score_pass, verify_pass_difficulty,
)
from .simulator import FIXTURES, generate
from .storage import StorageConflict, imported_match, imported_matches, ingest

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
@lru_cache(maxsize=24)
def stored(fixture: str, seed: int | None = None) -> tuple[Match, list[MatchEvent]]:
    return generate(fixture, seed)


def get_match(match_id: str) -> tuple[Match, list[MatchEvent]]:
    imported = imported_match(match_id)
    if imported:
        return imported
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
    return {"status": "ok", "simulation": "synthetic",
            "narrative_provider": "configured_not_verified" if configured() else "not_configured"}


@app.get("/api/matches")
def list_matches():
    return [stored(name)[0] for name in FIXTURES] + imported_matches()


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
    try:
        return ingest(match, request.events)
    except StorageConflict as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


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


@app.get("/api/matches/{match_id}/tactics")
def match_tactics(match_id: str, at_second: int = Query(5400, ge=0, le=5400)):
    match, events = get_match(match_id)
    return tactics_at(match, events, at_second)


@app.get("/api/matches/{match_id}/passes/{event_id}/difficulty", response_model=PassDifficulty)
def pass_difficulty(match_id: str, event_id: str, at_second: int = Query(5400, ge=0, le=5400)):
    match, events = get_match(match_id)
    if at_second > match.duration_seconds:
        raise HTTPException(422, "replay cutoff exceeds match duration")
    event = next((e for e in events if e.event_id == event_id and e.match_second <= at_second), None)
    if event is None:
        raise HTTPException(404, "visible pass not found")
    try:
        return score_pass(match, event, at_second)
    except ValueError as error:
        raise HTTPException(404, "visible pass not found") from error


@app.get("/api/matches/{match_id}/passes/{event_id}/difficulty/evidence", response_model=PassDifficultyEvidence)
def pass_difficulty_evidence(match_id: str, event_id: str, at_second: int = Query(5400, ge=0, le=5400)):
    packet = pass_difficulty(match_id, event_id, at_second)
    match, events = get_match(match_id)
    return {"claim": packet, "verified": verify_pass_difficulty(packet, match, events),
            "source_events": [e for e in events if e.event_id in packet.supporting_event_ids]}


@app.get("/api/matches/{match_id}/pass-difficulty", response_model=PassDifficultyPage)
def pass_difficulties(match_id: str, at_second: int = Query(5400, ge=0, le=5400),
                      cursor: int = Query(0, ge=0), limit: int = Query(200, ge=1, le=200)):
    match, events = get_match(match_id)
    if at_second > match.duration_seconds:
        raise HTTPException(422, "replay cutoff exceeds match duration")
    visible = [e for e in events if e.event_type.value == "pass" and e.match_second <= at_second]
    page = [e for e in visible if e.sequence > cursor][:limit]
    more = bool(page and any(e.sequence > page[-1].sequence for e in visible))
    return PassDifficultyPage(match_id=match_id, at_second=at_second,
                              items=score_pass_stream(match, page, at_second),
                              next_cursor=page[-1].sequence if more else None,
                              total_visible_passes=len(visible))


@app.get("/api/matches/{match_id}/pass-difficulty/players", response_model=PlayerDifficultyResponse)
def pass_difficulty_players(match_id: str, at_second: int = Query(5400, ge=0, le=5400)):
    match, events = get_match(match_id)
    if at_second > match.duration_seconds:
        raise HTTPException(422, "replay cutoff exceeds match duration")
    items = score_pass_stream(match, [e for e in events
             if e.event_type.value == "pass" and e.match_second <= at_second], at_second)
    return {"match_id": match_id, "at_second": at_second, "players": player_summary(items)}


def score_pass_stream(match: Match, events: list[MatchEvent], at_second: int) -> list[PassDifficulty]:
    """Incomplete attribution is valid in the generic event schema, not a score input."""
    try:
        return [score_pass(match, event, at_second) for event in events]
    except ValueError as error:
        # Do not silently drop records or present a partial player summary as complete.
        raise HTTPException(422, "pass stream contains invalid team or player attribution") from error


@app.get("/api/matches/{match_id}/insights")
def match_insights(match_id: str, at_second: int = Query(5400, ge=0, le=5400)):
    match, events = get_match(match_id)
    return insights_for(match, events, at_second)


@app.get("/api/matches/{match_id}/insights/{insight_id}/evidence")
def match_insight_evidence(match_id: str, insight_id: str, at_second: int = Query(5400, ge=0, le=5400)):
    """Read evidence from the selected replay, including reproducible custom seeds."""
    match, events = get_match(match_id)
    if at_second > match.duration_seconds:
        raise HTTPException(422, "replay cutoff exceeds match duration")
    insight = next((item for item in insights_for(match, events, at_second)
                    if item.insight_id == insight_id), None)
    if insight is None:
        raise HTTPException(404, "visible insight not found")
    source_ids = set(insight.supporting_event_ids)
    return {"insight": insight, "source_events": [event for event in events if event.event_id in source_ids],
            "verification": "deterministic claim check passed"}


@app.get("/api/matches/{match_id}/overlays")
def match_overlays(match_id: str, at_second: int = Query(5400, ge=0, le=5400)):
    match, events = get_match(match_id)
    return overlays_for(match, events, at_second)


@app.get("/api/matches/{match_id}/overlays/{cue_id}")
def match_overlay(match_id: str, cue_id: str):
    match, events = get_match(match_id)
    cue = next((item for item in overlays_for(match, events) if item.cue_id == cue_id), None)
    if cue is None:
        raise HTTPException(404, "cue not found")
    return cue


@app.post("/api/matches/{match_id}/recap")
def match_recap(match_id: str, locale: str = Query("en"), persona: str = Query("casual"),
                at_second: int = Query(5400, ge=0, le=5400),
                favorite_team_id: str | None = Query(None), favorite_player_id: str | None = Query(None)):
    match, events = get_match(match_id)
    try:
        return recap_for(match, events, locale, persona, at_second, favorite_team_id, favorite_player_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.post("/api/insights/{insight_id}/explain")
def explain_insight(insight_id: str):
    for match, events in [stored(name) for name in FIXTURES] + [imported_match(item.match_id) for item in imported_matches()]:
        insight = next((item for item in insights_for(match, events) if item.insight_id == insight_id), None)
        if insight:
            source_ids = set(insight.supporting_event_ids)
            return {"insight": insight, "source_events": [e for e in events if e.event_id in source_ids],
                    "verification": "deterministic claim check passed"}
    raise HTTPException(404, "insight not found")


@app.get("/api/agent-traces")
def agent_traces(x_admin_token: str | None = Header(default=None)):
    expected = os.getenv("PULSE_FOUNDRY_ADMIN_TOKEN", "")
    if expected and (not x_admin_token or not secrets.compare_digest(expected, x_admin_token)):
        raise HTTPException(403, "admin token required")
    return TRACES


@app.post("/api/insights/{insight_id}/agent-run")
async def agent_run(insight_id: str, x_admin_token: str | None = Header(default=None)):
    if not configured():
        raise HTTPException(503, "Foundry workflow is not configured; verified rule-based narratives remain available")
    expected = os.getenv("PULSE_FOUNDRY_ADMIN_TOKEN", "")
    if not expected or not x_admin_token or not secrets.compare_digest(expected, x_admin_token):
        raise HTTPException(403, "admin token required")
    for match, events in [stored(name) for name in FIXTURES] + [imported_match(item.match_id) for item in imported_matches()]:
        insight = next((item for item in insights_for(match, events) if item.insight_id == insight_id), None)
        if insight:
            try:
                return await run_specialists(match, events, insight)
            except (ImportError, ModuleNotFoundError) as error:
                raise HTTPException(503, "optional Agent Framework dependency is not installed") from error
            except Exception as error:
                raise HTTPException(502, f"Foundry workflow failed: {type(error).__name__}") from error
    raise HTTPException(404, "insight not found")


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
