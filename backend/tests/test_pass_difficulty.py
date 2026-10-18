from math import hypot

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models import EventType, Point
from app.pass_difficulty import FORMULA_VERSION, score_pass, verify_pass_difficulty
from app.simulator import FIXTURES, generate


@pytest.fixture
def source():
    match, events = generate("comeback")
    event = next(e for e in events if e.event_type == EventType.pass_)
    return match, event, events


@pytest.mark.parametrize("start,end,expected", [
    ((0, 0), (0, 0), 0), ((0, 0), (100, 0), 100),
    ((100, 0), (0, 0), 65), ((0, 0), (0, 100), 65),
    ((0, 0), (100, 100), 100), ((50, 50), (60, 50), 12),
])
def test_formula_boundaries_and_outcome_independence(source, start, end, expected):
    match, event, _ = source
    event = event.model_copy(update={"start": Point(x=start[0], y=start[1]),
                                     "end": Point(x=end[0], y=end[1])})
    complete = score_pass(match, event.model_copy(update={"outcome": "complete"}), 5400)
    failed = score_pass(match, event.model_copy(update={"outcome": "incomplete"}), 5400)
    assert complete.score == failed.score == expected
    assert complete.formula_version == FORMULA_VERSION
    assert complete.factors[0].raw_value == hypot(end[0] - start[0], end[1] - start[1])
    assert sum(f.effective_weight for f in complete.factors) == pytest.approx(1)
    assert complete.factors == failed.factors


@pytest.mark.parametrize("field", ["start", "end"])
def test_missing_coordinates_are_unavailable(source, field):
    match, event, _ = source
    event = event.model_copy(update={field: None, "recipient_id": None})
    packet = score_pass(match, event, 5400)
    assert packet.score is None and packet.difficulty_band == "unavailable"
    assert packet.unavailable_reason
    assert packet.recipient_id is None
    assert not packet.factors[0].available
    assert verify_pass_difficulty(packet, match, [event])


def test_recompute_rejects_tampered_claims_and_future_events(source):
    match, event, events = source
    packet = score_pass(match, event, event.match_second)
    assert verify_pass_difficulty(packet, match, events)
    assert not verify_pass_difficulty(packet.model_copy(update={"score": 99}), match, events)
    assert not verify_pass_difficulty(packet.model_copy(update={"event_id": "fake"}), match, events)
    assert not verify_pass_difficulty(packet.model_copy(update={"team_id": match.away.team_id}), match, events)
    assert not verify_pass_difficulty(packet.model_copy(update={"supporting_event_ids": ["fake"]}), match, events)
    factor = packet.factors[0].model_copy(update={"raw_value": 999})
    assert not verify_pass_difficulty(packet.model_copy(update={"factors": [factor, *packet.factors[1:]]}), match, events)
    assert not verify_pass_difficulty(packet.model_copy(update={"at_second": event.match_second - 1}), match, events)
    assert not verify_pass_difficulty(packet, match, [event, event])
    with pytest.raises(ValueError):
        score_pass(match, event.model_copy(update={"actor_id": "fake"}), 5400)
    with pytest.raises(ValidationError):
        Point(x=float("nan"), y=50)


def test_pressure_is_explicitly_unavailable_and_never_changes_history(source):
    match, event, events = source
    packet = score_pass(match, event, event.match_second)
    later = score_pass(match, event, 5400)
    assert packet.score == later.score
    assert packet.factors == later.factors
    pressure = packet.factors[2]
    assert not pressure.available and pressure.raw_value is None
    assert pressure.effective_weight == 0 and pressure.supporting_event_ids == []
    assert "shared opponent coordinate frame" in pressure.unavailable_reason
    # Even a fabricated nearby pressure event cannot supply an unsupported factor.
    contextual = event.model_copy(update={"event_id": "pressure", "event_type": EventType.pressure})
    assert verify_pass_difficulty(packet, match, [*events, contextual])


def test_fixture_reproducibility_and_api_pagination(source):
    client = TestClient(app)
    match, event, events = source
    for fixture in FIXTURES:
        m, stream = generate(fixture)
        packets = [score_pass(m, e, 5400) for e in stream if e.event_type == EventType.pass_]
        assert all(verify_pass_difficulty(p, m, stream) for p in packets)
        assert packets == [score_pass(m, e, 5400) for e in generate(fixture)[1] if e.event_type == EventType.pass_]
    base = f"/api/matches/{match.match_id}"
    url = f"{base}/passes/{event.event_id}/difficulty"
    assert client.get(f"{url}?at_second={event.match_second - 1}").status_code == 404
    assert client.get(f"{url}?at_second={event.match_second}").json()["score"] == score_pass(match, event, event.match_second).score
    evidence = client.get(f"{url}/evidence?at_second={event.match_second}").json()
    assert evidence["verified"] is True
    assert [e["event_id"] for e in evidence["source_events"]] == [event.event_id]
    assert client.get(f"{base}/passes/{events[0].event_id}/difficulty").status_code == 404
    assert client.get(f"{url}?at_second=5401").status_code == 422
    first = client.get(f"{base}/pass-difficulty?limit=1").json()
    second = client.get(f"{base}/pass-difficulty?limit=1&cursor={first['next_cursor']}").json()
    assert first["items"][0]["event_id"] != second["items"][0]["event_id"]
    assert client.get(f"{base}/pass-difficulty?at_second=0").json()["items"] == []
    assert client.get(f"{base}/pass-difficulty?limit=201").status_code == 422
    summary = client.get(f"{base}/pass-difficulty/players").json()
    assert sum(p["sample_count"] for p in summary["players"]) == first["total_visible_passes"]
    assert client.get("/api/matches/unknown/pass-difficulty").status_code == 404


def test_unattributed_imported_pass_is_a_validation_error_not_a_server_crash(source, tmp_path, monkeypatch):
    monkeypatch.setenv("PULSE_IMPORT_TOKEN", "test-import-token-at-least-32-characters")
    monkeypatch.setenv("PULSE_DB_PATH", str(tmp_path / "passes.sqlite"))
    match, event, _ = source
    match = match.model_copy(update={"match_id": "audit-unattributed-pass"})
    event = event.model_copy(update={"match_id": match.match_id, "team_id": None,
                                     "actor_id": None, "recipient_id": None})
    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/api/matches/ingest", headers={"Authorization": "Bearer test-import-token-at-least-32-characters"}, json={"match": match.model_dump(mode="json"),
        "events": [event.model_dump(mode="json", by_alias=True)]}).status_code == 200
    for route in ["pass-difficulty", "pass-difficulty/players"]:
        response = client.get(f"/api/matches/{match.match_id}/{route}")
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == "pass stream contains invalid team or player attribution"
