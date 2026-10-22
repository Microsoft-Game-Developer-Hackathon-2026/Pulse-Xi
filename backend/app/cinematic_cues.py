"""Offline, read-only cinematic cue export from existing synthetic fixtures."""
from typing import Any

from .models import EventType, Match, MatchEvent
from .simulator import FIXTURES


def export_goal_cues(fixture: str) -> dict[str, Any]:
    """Return a deterministic, data-only shot list; never creates match state."""
    if fixture not in FIXTURES:
        raise ValueError("unknown built-in synthetic fixture")

    # Import the exact generator used by the API. No second simulation is made.
    from .simulator import generate

    match, events = generate(fixture)
    return build_goal_cues(match, events, fixture)


def build_goal_cues(match: Match, events: list[MatchEvent], fixture: str) -> dict[str, Any]:
    if fixture not in FIXTURES or match.synthetic is not True or match.event_source != "synthetic-generator":
        raise ValueError("synthetic fixture provenance is required")
    if match.seed != FIXTURES[fixture][0] or match.match_id != f"{fixture}-{match.seed}":
        raise ValueError("match identity does not match the built-in fixture")
    if not events:
        raise ValueError("fixture events are required")

    event_ids: set[str] = set()
    team_ids = {match.home.team_id, match.away.team_id}
    previous_sequence = 0
    previous_second = -1
    cues: list[dict[str, Any]] = []
    for event in events:
        if event.match_id != match.match_id or event.source_type != "synthetic-generator":
            raise ValueError("event match/provenance does not match the fixture")
        if not isinstance(event.event_type, EventType):
            raise ValueError("unsupported event type")
        if (not event.event_id or event.event_id in event_ids
                or event.sequence <= previous_sequence or event.match_second < previous_second):
            raise ValueError("event IDs and ordering must be unique and monotonic")
        event_ids.add(event.event_id)
        previous_sequence = event.sequence
        previous_second = event.match_second

        if event.event_type != EventType.goal:
            continue
        if event.team_id not in team_ids:
            raise ValueError("goal cue requires a known synthetic team")
        team = match.home if event.team_id == match.home.team_id else match.away
        cues.append({
            "cue_id": f"goal:{event.event_id}",
            "match_second": event.match_second,
            "source_event_id": event.event_id,
            "event_sequence": event.sequence,
            "team_id": event.team_id,
            "team_label": team.name,
            "shot_id": "synthetic_goal_wide_v1",
            "insight_refs": [],
        })

    if not cues:
        raise ValueError("fixture contains no supported goal cues")
    return {
        "schema_version": "pulse-cinematic-cues/1",
        "source": {
            "match_id": match.match_id,
            "seed": match.seed,
            "match_schema_version": match.schema_version,
            "event_schema_version": "1.0",
            "synthetic": True,
            "fixture": fixture,
            "provenance": match.event_source,
        },
        "scene": {
            "template_version": "synthetic-goal-beat/1",
            "required_assets": [{
                "asset_id": "neutral-procedural-primitive-set",
                "license_basis": "new project-authored geometry; rights confirmation pending issue #23",
                "release_status": "pending-human-review",
            }],
        },
        "cues": cues,
    }
