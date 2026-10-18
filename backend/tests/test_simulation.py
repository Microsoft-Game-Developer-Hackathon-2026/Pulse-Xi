from fastapi.testclient import TestClient

from app.analytics import metrics_at, state_at, tactics_at
from app.agents import audit_model_packet
from app.evidence import insights_for, overlays_for, verify
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
    pressure = next(event for event in events if event.event_type == EventType.pressure)
    assert state_at(match, events, pressure.match_second).possession_team_id != pressure.team_id


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


def test_idempotent_out_of_order_ingest(tmp_path, monkeypatch):
    monkeypatch.setenv("PULSE_IMPORT_TOKEN", "test-import-token-at-least-32-characters")
    monkeypatch.setenv("PULSE_DB_PATH", str(tmp_path / "matches.sqlite"))
    match, events = generate("custom", 809)
    match = match.model_copy(update={"match_id": "imported-fixture"})
    sample = [e.model_copy(update={"match_id": match.match_id, "event_id": f"import-{i}"})
              for i, e in enumerate(events[:8])]
    client = TestClient(app)
    payload = {"match": match.model_dump(mode="json"),
               "events": [e.model_dump(mode="json", by_alias=True) for e in reversed(sample)]}
    response = client.post("/api/matches/ingest", headers={"Authorization": "Bearer test-import-token-at-least-32-characters"}, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["inserted"] == 8
    assert client.post("/api/matches/ingest", headers={"Authorization": "Bearer test-import-token-at-least-32-characters"}, json=payload).json()["inserted"] == 0
    stored_events = client.get("/api/matches/imported-fixture/events").json()
    assert [e["match_second"] for e in stored_events] == sorted(e["match_second"] for e in stored_events)
    assert [e["sequence"] for e in stored_events] == list(range(1, 9))
    payload["events"][0]["outcome"] = "corrupted"
    assert client.post("/api/matches/ingest", headers={"Authorization": "Bearer test-import-token-at-least-32-characters"}, json=payload).status_code == 409
    from app.storage import imported_match
    recovered = imported_match(match.match_id)
    assert recovered is not None
    assert len(recovered[1]) == 8
    assert recovered[1][0].sequence == 1
    assert client.get("/api/matches").json()[-1]["match_id"] == match.match_id


def test_prooftrail_overlay_and_localized_recap():
    match, events = generate("comeback")
    insights = insights_for(match, events)
    overlays = overlays_for(match, events)
    assert len(insights) == len(overlays) >= 5
    assert sum(item.category == "goal" for item in insights) == 5
    assert any(item.category == "momentum_shift" for item in insights)
    assert all(verify(insight, match, events) for insight in insights)
    assert all(cue.trigger_match_second == insight.match_second and
               cue.supporting_event_ids == insight.supporting_event_ids
               for cue, insight in zip(overlays, insights))
    assert all(cue.end_match_second <= next_cue.start_match_second for cue, next_cue in zip(overlays, overlays[1:]))
    bad = insights[0].model_copy(update={"supporting_event_ids": ["missing"]})
    assert not verify(bad, match, events)
    client = TestClient(app)
    match_id = match.match_id
    assert sum(item["category"] == "goal" for item in client.get(f"/api/matches/{match_id}/insights?at_second=3500").json()) == 2
    packet = client.post(f"/api/insights/{insights[0].insight_id}/explain").json()
    assert len(packet["source_events"]) == 2
    assert client.get(f"/api/matches/{match_id}/overlays").json()[0]["trigger_match_second"] == 1000
    cue = client.get(f"/api/matches/{match_id}/overlays/{overlays[0].cue_id}").json()
    assert cue["schema_version"] == "1.0"
    assert cue["start_match_second"] == 1000 and cue["end_match_second"] == 1012
    assert client.get(f"/api/matches/{match_id}/overlays/not-a-cue").status_code == 404
    casual = client.post(f"/api/matches/{match_id}/recap?locale=es&persona=casual").json()
    analyst = client.post(f"/api/matches/{match_id}/recap?locale=es&persona=analyst").json()
    assert casual["provider"] == "verified_rule_based_templates"
    assert casual["moments"][0]["text"] != analyst["moments"][0]["text"]
    assert casual["moments"][0]["supporting_event_ids"] == insights[0].supporting_event_ids


def test_tactics_and_evidence_rejects_future_or_wrong_team():
    match, events = generate("comeback")
    at_zero = tactics_at(match, events, 0)
    assert at_zero["computed_from_event_count"] == 1
    assert at_zero["teams"][match.home.team_id]["shots"] == []
    full = tactics_at(match, events, 5400)
    assert full["teams"][match.home.team_id]["passes_completed"] <= full["teams"][match.home.team_id]["passes_attempted"]
    assert full["momentum_windows"]
    client = TestClient(app)
    assert client.get(f"/api/matches/{match.match_id}/tactics?at_second=0").json() == at_zero
    assert client.get(f"/api/matches/{match.match_id}/tactics?at_second=6000").status_code == 422
    insights = insights_for(match, events)
    assert all(verify(item, match, events) for item in insights)
    tactical = next(item for item in insights if item.category == "momentum_shift")
    other_team = match.away.team_id if tactical.team_id == match.home.team_id else match.home.team_id
    assert not verify(tactical.model_copy(update={"team_id": other_team}), match, events)
    assert not verify(tactical.model_copy(update={"supporting_event_ids": tactical.supporting_event_ids[:-1]}), match, events)
    assert not verify(tactical.model_copy(update={"match_second": tactical.match_second - 1}), match, events)
    assert not verify(tactical.model_copy(update={"explanation": tactical.explanation + " The team had 99 shots."}), match, events)
    assert not verify(tactical.model_copy(update={"factual_claims": [tactical.factual_claims[0].model_copy(update={"value": 999}), tactical.factual_claims[1]]}), match, events)
    assert all(item.match_second <= 3500 for item in insights_for(match, events, 3500))


def test_personalized_recap_at_replay_clock():
    match, events = generate("comeback")
    client = TestClient(app)
    base = f"/api/matches/{match.match_id}/recap"
    early = client.post(f"{base}?at_second=500&locale=es").json()
    assert early["moments"] == []
    assert "0–0" in early["lead"]
    team = client.post(f"{base}?persona=favorite_team&favorite_team_id={match.away.team_id}&at_second=3500").json()
    assert len(team["moments"]) == 2
    assert all(moment["match_second"] <= 3500 for moment in team["moments"])
    player = client.post(f"{base}?persona=favorite_player&favorite_player_id={match.home.players[0].player_id}&at_second=3500").json()
    assert "completed passes" in player["lead"]
    assert player["moments"] == []
    assert client.post(f"{base}?persona=favorite_team&favorite_team_id=fictional").status_code == 422


def test_agent_auditor_and_unconfigured_guard():
    match, events = generate("late-winner")
    insight = insights_for(match, events)[0]
    valid = {"headline": "A goal changes the match", "commentary": "A clear finish reshapes the scoreline.",
             "event_ids": insight.supporting_event_ids}
    assert audit_model_packet(valid, insight, match, events)
    assert not audit_model_packet({**valid, "commentary": "The striker ran 35 km/h."}, insight, match, events)
    assert not audit_model_packet({**valid, "event_ids": ["invented-event"]}, insight, match, events)
    client = TestClient(app)
    response = client.post(f"/api/insights/{insight.insight_id}/agent-run")
    assert response.status_code == 503
    assert client.get("/api/agent-traces").json() == []
