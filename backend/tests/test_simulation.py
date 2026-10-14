from fastapi.testclient import TestClient

from app.analytics import metrics_at, state_at
from app.main import app
from app.models import EventType, MatchEvent
from app.simulator import FIXTURES, generate


def test_reproducible_and_match_invariants():
    for fixture in FIXTURES:
        match, events = generate(fixture)
        again = generate(fixture)[1]
        assert [e.model_dump() for e in events] == [e.model_dump() for e in again]
        assert [e.sequence for e in events] == list(range(1, len(events) + 1))
        assert [e.match_second for e in events] == sorted(e.match_second for e in events)
        assert events[-1].event_type == EventType.fulltime
        assert len({e.event_id for e in events}) == len(events)
        members = {team.team_id: {p.player_id for p in team.players} for team in [match.home, match.away]}
        for event in events:
            if event.team_id:
                assert event.actor_id in members[event.team_id]
                assert event.recipient_id is None or event.recipient_id in members[event.team_id]
            assert MatchEvent.model_validate_json(event.model_dump_json(by_alias=True)) == event


def test_golden_scores_and_metrics():
    expected = {"comeback": (3, 2), "high-press": (2, 1), "late-winner": (2, 1)}
    for fixture, (home, away) in expected.items():
        match, events = generate(fixture)
        state = state_at(match, events, 5400)
        metrics = metrics_at(match, events, 5400)
        assert (state.score.home, state.score.away) == (home, away)
        assert (metrics.home.goals, metrics.away.goals) == (home, away)
        assert state.phase == "fulltime"
        assert metrics.home.completed_passes <= metrics.home.passes
        assert metrics.away.completed_passes <= metrics.away.passes
    match, events = generate("comeback")
    assert state_at(match, events, 3500).score.away == 2
    assert state_at(match, events, 3500).score.home == 0


def test_api_and_websocket():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    matches = client.get("/api/matches").json()
    assert len(matches) == 3
    match_id = matches[0]["match_id"]
    events = client.get(f"/api/matches/{match_id}/events?limit=5").json()
    assert len(events) == 5
    assert client.get(f"/api/matches/{match_id}/events?cursor=5&limit=1").json()[0]["sequence"] == 6
    assert client.get(f"/api/matches/{match_id}/state?at_second=5400").json()["score"] == {"home": 3, "away": 2}
    assert client.get(f"/api/matches/{match_id}/metrics?at_second=5400").json()["home"]["goals"] == 3
    assert client.get("/api/matches/does-not-exist").status_code == 404
    assert client.get(f"/api/matches/{match_id}/state?at_second=6000").status_code == 422
    with client.websocket_connect(f"/ws/matches/{match_id}?cursor=1") as socket:
        assert socket.receive_json()["kind"] == "snapshot"
        event = socket.receive_json()
        assert event["kind"] == "event" and event["sequence"] == 2


def test_idempotent_out_of_order_ingest():
    match, events = generate("custom", 809)
    match = match.model_copy(update={"match_id": "imported-fixture"})
    sample = [e.model_copy(update={"match_id": match.match_id, "event_id": f"import-{i}"})
              for i, e in enumerate(events[:8])]
    client = TestClient(app)
    payload = {"match": match.model_dump(mode="json"),
               "events": [e.model_dump(mode="json", by_alias=True) for e in reversed(sample)]}
    response = client.post("/api/matches/ingest", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["inserted"] == 8
    assert client.post("/api/matches/ingest", json=payload).json()["inserted"] == 0
    stored_events = client.get("/api/matches/imported-fixture/events").json()
    assert [e["match_second"] for e in stored_events] == sorted(e["match_second"] for e in stored_events)
    assert [e["sequence"] for e in stored_events] == list(range(1, 9))
    payload["events"][0]["outcome"] = "corrupted"
    assert client.post("/api/matches/ingest", json=payload).status_code == 409
