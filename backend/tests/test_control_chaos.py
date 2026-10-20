from hashlib import sha256

import pytest
from fastapi.testclient import TestClient

from app.analytics import control_chaos_at
from app.evidence import verify_control_turning_point
from app.main import app
from app.models import EventType, MatchEvent, Point
from app.simulator import generate


@pytest.fixture
def fixture_data():
    return generate("comeback")


def make_event(match, template, event_id, second, sequence, team_id, event_type,
               outcome=None, start=None, end=None, possession_id=None):
    return template.model_copy(update={
        "event_id": event_id,
        "match_id": match.match_id,
        "sequence": sequence,
        "match_second": second,
        "period": 1 if second <= 2700 else 2,
        "team_id": team_id,
        "actor_id": None,
        "recipient_id": None,
        "event_type": event_type,
        "outcome": outcome,
        "start": Point(**start) if start else None,
        "end": Point(**end) if end else None,
        "possession_id": possession_id,
    })


def test_equal_windows_boundary_seconds_and_deterministic_hash(fixture_data):
    match, fixture_events = fixture_data
    template = fixture_events[0]
    home = match.home.team_id
    events = [
        make_event(match, template, f"boundary-{second}", second, index + 1, home,
                   EventType.pass_, "complete", {"x": 10, "y": 20}, {"x": 20, "y": 20},
                   f"p-{second}")
        for index, second in enumerate([600, 300, 301, 599, 601])
    ]

    packet = control_chaos_at(match, events, 600, 300)
    current = packet.teams[home].retention["completed_passes"]
    assert packet.window.model_dump() == {"start_second": 300, "end_second": 600}
    assert packet.previous_window.model_dump() == {"start_second": 0, "end_second": 300}
    assert current.value == 3
    assert current.supporting_event_ids == ["boundary-301", "boundary-599", "boundary-600"]
    assert packet.teams[home].retention["completed_passes"].denominator == 3
    assert packet.teams[home].progression["forward_progression"].value == 30
    again = control_chaos_at(match, events, 600, 300)
    assert sha256(packet.model_dump_json().encode()).hexdigest() == sha256(
        again.model_dump_json().encode()
    ).hexdigest()
    assert all(event_id != "boundary-601" for event_id in current.supporting_event_ids)


@pytest.mark.parametrize("window", [300, 600, 900])
def test_all_supported_windows_are_equal_and_clock_bounded(fixture_data, window):
    match, fixture_events = fixture_data
    packet = control_chaos_at(match, fixture_events, window * 2, window)
    assert packet.window.model_dump() == {"start_second": window, "end_second": window * 2}
    assert packet.previous_window.model_dump() == {"start_second": 0, "end_second": window}
    assert all(
        event.match_second <= packet.at_second
        for team in packet.teams.values()
        for category in (team.retention, team.progression, team.disruption, team.attacking_activity)
        for metric in category.values()
        for event_id in metric.supporting_event_ids
        for event in fixture_events if event.event_id == event_id
    )


def test_partial_halftime_match_edges_and_api_validation(fixture_data):
    match, fixture_events = fixture_data
    client = TestClient(app)
    url = f"/api/matches/{match.match_id}/control-chaos"
    partial = client.get(url, params={"at_second": 299, "window_seconds": 300}).json()
    assert partial["window"] == {"start_second": 0, "end_second": 299}
    assert partial["previous_window"] is None
    assert partial["deltas"] is None
    assert "rhythm change unavailable" in partial["unavailable_reasons"][0]

    halftime = client.get(url, params={"at_second": 2700, "window_seconds": 300}).json()
    assert halftime["window"] == {"start_second": 2400, "end_second": 2700}
    assert halftime["previous_window"] == {"start_second": 2100, "end_second": 2400}
    at_start = control_chaos_at(match, [], 0, 900)
    assert at_start.window.model_dump() == {"start_second": 0, "end_second": 0}
    end_event = make_event(
        match, fixture_events[0], "match-end", match.duration_seconds, 1,
        match.home.team_id, EventType.shot,
    )
    at_end = control_chaos_at(match, [end_event], match.duration_seconds, 900)
    assert at_end.at_second == match.duration_seconds
    assert at_end.teams[match.home.team_id].attacking_activity["shots"].supporting_event_ids == ["match-end"]
    with pytest.raises(ValueError, match="cutoff"):
        control_chaos_at(match, [], match.duration_seconds + 1, 300)

    assert client.get("/api/matches/missing/control-chaos").status_code == 404
    assert client.get(url, params={"at_second": 6000}).status_code == 422
    assert client.get(url, params={"window_seconds": 301}).status_code == 422


def test_missing_coordinates_and_possession_are_unavailable(fixture_data):
    match, fixture_events = fixture_data
    template = fixture_events[0]
    home = match.home.team_id
    events = [
        make_event(match, template, "unlocated-pass", 100, 1, home, EventType.pass_,
                   "complete", possession_id=None),
        make_event(match, template, "unknown-recovery", 110, 2, home, EventType.recovery),
    ]
    team = control_chaos_at(match, events, 200, 300).teams[home]
    possession = team.retention["observed_possession_sequences"]
    assert possession.value == 0 and possession.eligible_event_count == 1
    assert possession.missing_identifier_count == 1
    assert team.progression["forward_progression"].value is None
    assert team.progression["final_third_entries"].value is None
    assert team.progression["coordinate_coverage_percent"].value == 0
    assert team.progression["forward_progression"].missing_coordinate_count == 1
    rapid = team.disruption["rapid_transitions"]
    assert rapid.value is None
    assert rapid.unknown_chain_count == 1
    assert "1 transition trigger(s) have no possession ID" in rapid.unavailable_reason


def test_rapid_transition_requires_same_possession_and_30_second_bound(fixture_data):
    match, fixture_events = fixture_data
    template = fixture_events[0]
    home, away = match.home.team_id, match.away.team_id
    events = [
        make_event(match, template, "rec-1", 100, 1, home, EventType.recovery, possession_id="p1"),
        make_event(match, template, "entry-1", 130, 2, home, EventType.carry, "complete",
                   {"x": 60, "y": 30}, {"x": 70, "y": 30}, "p1"),
        make_event(match, template, "rec-2", 200, 3, home, EventType.recovery, possession_id="p2"),
        make_event(match, template, "shot-2", 231, 4, home, EventType.shot, possession_id="p2"),
        make_event(match, template, "opp-turnover", 300, 5, away, EventType.turnover, possession_id="p3"),
        make_event(match, template, "shot-3", 330, 6, home, EventType.shot, possession_id="p3"),
        make_event(match, template, "rec-4", 350, 7, home, EventType.recovery, possession_id="p4"),
        make_event(match, template, "shot-too-late", 381, 8, home, EventType.shot, possession_id="p4"),
        make_event(match, template, "rec-5", 400, 9, home, EventType.recovery, possession_id="p5"),
        make_event(match, template, "wrong-possession-shot", 410, 10, home, EventType.shot, possession_id="other"),
    ]
    result = control_chaos_at(match, events, 500, 600).teams[home].disruption["rapid_transitions"]
    assert result.value == 3
    assert set(result.supporting_event_ids) == {
        "rec-1", "entry-1", "rec-2", "shot-2", "opp-turnover", "shot-3",
    }


def test_turning_point_verifier_recomputes_claims_and_rejects_tampering(fixture_data):
    match, fixture_events = fixture_data
    template = fixture_events[0]
    home = match.home.team_id
    events = [
        make_event(match, template, f"shot-{second}", second, index + 1, home, EventType.shot)
        for index, second in enumerate([301, 302, 303])
    ]
    packet = control_chaos_at(match, events, 600, 300)
    assert len(packet.interpretation.turning_points) == 1
    claim = packet.interpretation.turning_points[0]
    assert claim.previous_value == 0 and claim.current_value == 9
    assert verify_control_turning_point(claim, match, events, 600, 300)
    assert not verify_control_turning_point(
        claim.model_copy(update={"current_value": claim.current_value + 1}), match, events, 600, 300,
    )
    assert not verify_control_turning_point(
        claim.model_copy(update={"team_id": match.away.team_id}), match, events, 600, 300,
    )
    assert not verify_control_turning_point(
        claim.model_copy(update={"current_event_ids": ["fabricated"]}), match, events, 600, 300,
    )
    assert not verify_control_turning_point(
        claim.model_copy(update={"current_event_ids": []}), match, events, 600, 300,
    )
    future = make_event(match, fixture_events[0], "future-shot", 601, 4, home, EventType.shot)
    assert not verify_control_turning_point(
        claim.model_copy(update={"current_event_ids": [*claim.current_event_ids, future.event_id]}),
        match, [*events, future], 600, 300,
    )


def test_turning_point_relative_threshold_is_enforced(fixture_data):
    match, fixture_events = fixture_data
    template = fixture_events[0]
    home = match.home.team_id
    previous = [
        make_event(match, template, f"previous-{second}", second, index + 1, home, EventType.shot)
        for index, second in enumerate(range(100, 106))
    ]
    current = [
        make_event(match, template, f"current-{second}", second, index + 7, home, EventType.shot)
        for index, second in enumerate(range(301, 309))
    ]
    packet = control_chaos_at(match, [*previous, *current], 600, 300)
    assert packet.teams[home].attacking_activity["activity_index"].value == 24
    assert packet.deltas[home]["attacking_activity.activity_index"].difference == 6
    assert not packet.interpretation.turning_points

    ninth_shot = make_event(match, template, "current-309", 309, 15, home, EventType.shot)
    exact = control_chaos_at(match, [*previous, *current, ninth_shot], 600, 300)
    point = exact.interpretation.turning_points[0]
    assert (point.previous_value, point.current_value, point.difference) == (18, 27, 9)
