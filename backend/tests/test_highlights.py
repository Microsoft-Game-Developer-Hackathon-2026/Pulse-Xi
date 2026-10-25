from fastapi.testclient import TestClient

from app.highlights import highlights_for
from app.main import app
from app.models import EventType
from app.simulator import FIXTURES, generate

client = TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000))
MATCH = "comeback-1107"


def _match(name="comeback"):
    return generate(name)


def test_manifest_is_deterministic_and_hash_covers_content():
    match, events = _match()
    first, second = highlights_for(match, events), highlights_for(match, events)
    assert first == second and len(first["manifest_sha256"]) == 64
    changed = highlights_for(match, events, limit=2)
    assert changed["manifest_sha256"] != first["manifest_sha256"]


def test_every_goal_is_a_clip_and_score_matches_independent_count():
    match, events = _match()
    manifest = highlights_for(match, events)
    goals = [event for event in events if event.event_type == EventType.goal]
    goal_clips = [clip for clip in manifest["clips"] if clip["category"] == "goal"]
    assert [clip["match_second"] for clip in goal_clips] == [goal.match_second for goal in goals]
    for clip, goal in zip(goal_clips, goals):
        home = sum(1 for e in events if e.event_type == EventType.goal and e.team_id == match.home.team_id and e.sequence <= goal.sequence)
        away = sum(1 for e in events if e.event_type == EventType.goal and e.team_id == match.away.team_id and e.sequence <= goal.sequence)
        assert clip["score_after"] == {"home": home, "away": away}
        scoring = "home" if goal.team_id == match.home.team_id else "away"
        other = "away" if scoring == "home" else "home"
        assert clip["score_before"][scoring] == clip["score_after"][scoring] - 1
        assert clip["score_before"][other] == clip["score_after"][other]


def test_clips_cite_real_events_never_from_the_future_and_in_match_order():
    match, events = _match("late-winner")
    by_id = {event.event_id: event for event in events}
    manifest = highlights_for(match, events)
    seconds = [clip["match_second"] for clip in manifest["clips"]]
    assert seconds == sorted(seconds)
    for clip in manifest["clips"]:
        assert clip["verification_status"] == "verified_rule_based" and clip["source_events"]
        for source in clip["source_events"]:
            real = by_id[source["event_id"]]
            assert (source["match_second"], source["type"], source["sequence"]) == (real.match_second, real.event_type.value, real.sequence)
            assert source["match_second"] <= clip["match_second"]
        low, high = clip["replay_window"]
        assert 0 <= low <= clip["match_second"] <= high <= match.duration_seconds


def test_cutoff_excludes_later_clips_and_limit_is_bounded():
    match, events = _match()
    full = highlights_for(match, events)
    early = highlights_for(match, events, at_second=2000)
    assert all(clip["match_second"] <= 2000 for clip in early["clips"]) and len(early["clips"]) < len(full["clips"])
    assert len(highlights_for(match, events, limit=1)["clips"]) == 1
    assert full["video"]["total_seconds"] == 6.0 + 6.0 * len(full["clips"])


def test_provenance_states_no_footage_and_no_external_assets():
    match, events = _match()
    provenance = highlights_for(match, events)["provenance"]
    assert provenance["external_assets"] == [] and "none" in provenance["footage"]


def test_http_endpoint_matches_module_and_validates_input():
    response = client.get(f"/api/matches/{MATCH}/highlights")
    assert response.status_code == 200
    match, events = generate("comeback")
    assert response.json() == highlights_for(match, events)
    assert client.get(f"/api/matches/{MATCH}/highlights?limit=0").status_code == 422
    assert client.get(f"/api/matches/{MATCH}/highlights?limit=99").status_code == 422
    assert client.get(f"/api/matches/{MATCH}/highlights?at_second=9999").status_code == 422
    assert client.get("/api/matches/does-not-exist/highlights").status_code == 404
