import pytest

from app.cinematic_cues import build_goal_cues, export_goal_cues
from app.models import EventType
from app.simulator import generate


def test_builtin_goal_cue_export_is_deterministic_and_references_source_events():
    first = export_goal_cues("comeback")
    second = export_goal_cues("comeback")
    assert first == second
    assert first["source"] == {
        "match_id": "comeback-1107", "seed": 1107, "match_schema_version": "1.0",
        "event_schema_version": "1.0", "synthetic": True, "fixture": "comeback",
        "provenance": "synthetic-generator",
    }
    match, events = generate("comeback")
    by_id = {event.event_id: event for event in events}
    assert len(first["cues"]) == 5
    assert all(cue["shot_id"] == "synthetic_goal_wide_v1" for cue in first["cues"])
    assert all(cue["source_event_id"] in by_id for cue in first["cues"])
    assert all(by_id[cue["source_event_id"]].event_type == EventType.goal for cue in first["cues"])
    assert [cue["event_sequence"] for cue in first["cues"]] == sorted(
        cue["event_sequence"] for cue in first["cues"])
    assert first["scene"]["required_assets"][0]["release_status"] == "pending-human-review"


def test_cue_export_rejects_unknown_fixture_and_missing_provenance():
    with pytest.raises(ValueError, match="unknown built-in"):
        export_goal_cues("untrusted-import")
    match, events = generate("comeback")
    unproven = events[0].model_copy(update={"source_type": "imported"})
    with pytest.raises(ValueError, match="provenance"):
        build_goal_cues(match, [unproven, *events[1:]], "comeback")


@pytest.mark.parametrize("damage", ["duplicate_id", "unordered_sequence", "wrong_match", "unsupported_type"])
def test_cue_export_rejects_malformed_event_stream(damage):
    match, original = generate("comeback")
    events = list(original)
    if damage == "duplicate_id":
        events[1] = events[1].model_copy(update={"event_id": events[0].event_id})
    elif damage == "unordered_sequence":
        events[1] = events[1].model_copy(update={"sequence": events[0].sequence})
    elif damage == "wrong_match":
        events[1] = events[1].model_copy(update={"match_id": "other-match"})
    else:
        goal_index = next(i for i, event in enumerate(events) if event.event_type == EventType.goal)
        events[goal_index] = events[goal_index].model_copy(update={"event_type": "tracking"})
    with pytest.raises(ValueError):
        build_goal_cues(match, events, "comeback")
