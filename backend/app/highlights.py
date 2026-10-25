"""Event-derived highlight manifest.

A manifest is a deterministic, evidence-linked storyboard for a short highlight reel. Every clip
comes from a verified rule-based insight and cites real event IDs; nothing is invented and no
match footage or external asset is involved. Rendering is a separate step (see
frontend/scripts/render-highlights.mjs).
"""
from __future__ import annotations

import hashlib
import json

from .analytics import state_at
from .evidence import insights_for
from .models import Match, MatchEvent

SCHEMA = "highlight-manifest/1"
FPS = 30
WIDTH, HEIGHT = 1280, 720
INTRO_SECONDS = 3.0
CLIP_SECONDS = 6.0
OUTRO_SECONDS = 3.0
CONTEXT_BEFORE, CONTEXT_AFTER = 15, 10  # replay seconds shown around the key event


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def highlights_for(match: Match, events: list[MatchEvent], at_second: int = 5400, limit: int = 6) -> dict:
    """Select goals first, then the highest-priority momentum shifts, shown in match order."""
    by_id = {event.event_id: event for event in events}
    insights = insights_for(match, events, at_second)
    goals = [item for item in insights if item.category == "goal"]
    others = sorted((item for item in insights if item.category != "goal"),
                    key=lambda item: (-item.priority, item.match_second, item.insight_id))
    chosen = (goals + others)[:limit]
    clips = []
    for position, insight in enumerate(sorted(chosen, key=lambda item: (item.match_second, item.insight_id)), start=1):
        before = state_at(match, events, max(0, insight.match_second - 1)).score
        after = state_at(match, events, insight.match_second).score
        sources = []
        for event_id in insight.supporting_event_ids:
            event = by_id[event_id]
            sources.append({"event_id": event.event_id, "sequence": event.sequence, "match_second": event.match_second,
                            "type": event.event_type.value, "team_id": event.team_id, "outcome": event.outcome,
                            "start": event.start.model_dump() if event.start else None,
                            "end": event.end.model_dump() if event.end else None})
        clips.append({
            "clip_id": f"clip-{position}-{insight.insight_id}", "insight_id": insight.insight_id,
            "category": insight.category, "match_second": insight.match_second, "team_id": insight.team_id,
            "replay_window": [max(0, insight.match_second - CONTEXT_BEFORE),
                              min(match.duration_seconds, insight.match_second + CONTEXT_AFTER)],
            "title": insight.title, "caption": insight.explanation, "uncertainty": insight.uncertainty,
            "score_before": {"home": before.home, "away": before.away},
            "score_after": {"home": after.home, "away": after.away},
            "verification_status": insight.verification_status,
            "source_events": sources, "duration_seconds": CLIP_SECONDS,
        })
    body = {
        "schema_version": SCHEMA, "match_id": match.match_id, "title": match.title, "seed": match.seed,
        "home": {"team_id": match.home.team_id, "name": match.home.name, "color": match.home.color},
        "away": {"team_id": match.away.team_id, "name": match.away.name, "color": match.away.color},
        "at_second": at_second,
        "video": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "intro_seconds": INTRO_SECONDS,
                  "outro_seconds": OUTRO_SECONDS,
                  "total_seconds": INTRO_SECONDS + OUTRO_SECONDS + CLIP_SECONDS * len(clips)},
        "clips": clips,
        "provenance": {"source": "synthetic-generator", "selection": "goals first, then highest-priority verified momentum shifts",
                       "footage": "none; graphics are drawn from event data", "external_assets": []},
    }
    return {**body, "manifest_sha256": hashlib.sha256(_canonical(body)).hexdigest()}
