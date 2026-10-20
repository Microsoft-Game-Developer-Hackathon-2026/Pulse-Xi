"""Pure replay and metrics; all values are derived from events at a clock position."""
from bisect import bisect_right
from collections import Counter
from math import hypot

from .models import (
    ControlChaosResponse, ControlInterpretation, ControlMetric, ControlMetricDelta,
    ControlTeamComponents, ControlTurningPoint, EventType, Match, MatchEvent,
    MatchMetrics, MatchState, Score, TeamMetrics,
)

MAX_CONTROL_CHAOS_EVENTS = 20_000
ON_BALL_TYPES = {EventType.pass_, EventType.carry, EventType.shot, EventType.goal, EventType.clearance}


def events_at(events: list[MatchEvent], second: int) -> list[MatchEvent]:
    return [event for event in events if event.match_second <= second]


def state_at(match: Match, events: list[MatchEvent], second: int) -> MatchState:
    seen = events_at(events, second)
    goals = Counter(event.team_id for event in seen if event.event_type == EventType.goal)
    possession = next((e.team_id for e in reversed(seen) if e.possession_id and e.team_id
                       and e.event_type != EventType.pressure), None)
    phase = "pre_match" if not seen else "first_half" if second < 2700 else "halftime" if second == 2700 else "second_half"
    if seen and seen[-1].event_type == EventType.fulltime:
        phase = "fulltime"
    return MatchState(match_id=match.match_id, at_second=second,
                      score=Score(home=goals[match.home.team_id], away=goals[match.away.team_id]),
                      phase=phase, possession_team_id=possession,
                      last_event_id=seen[-1].event_id if seen else None, event_count=len(seen))


def metrics_at(match: Match, events: list[MatchEvent], second: int) -> MatchMetrics:
    seen = events_at(events, second)

    def team_metrics(team_id: str) -> TeamMetrics:
        team_events = [event for event in seen if event.team_id == team_id]
        count = Counter(event.event_type for event in team_events)
        passes = [e for e in team_events if e.event_type == EventType.pass_]
        completed = sum(e.outcome == "complete" for e in passes)
        entries = sum(e.event_type in (EventType.pass_, EventType.carry) and e.outcome == "complete"
                      and e.start is not None and e.end is not None and e.start.x < 66.7 <= e.end.x
                      for e in team_events)
        return TeamMetrics(team_id=team_id, goals=count[EventType.goal], shots=count[EventType.shot],
                           passes=len(passes), completed_passes=completed,
                           pass_completion_pct=round(100 * completed / len(passes), 1) if passes else 0,
                           final_third_entries=entries, recoveries=count[EventType.recovery],
                           turnovers=count[EventType.turnover], pressure_events=count[EventType.pressure])

    return MatchMetrics(match_id=match.match_id, at_second=second,
                        home=team_metrics(match.home.team_id), away=team_metrics(match.away.team_id),
                        computed_from_event_count=len(seen))


def window_events(events: list[MatchEvent], start: int, end: int) -> list[MatchEvent]:
    """Inclusive end, exclusive start. Start=-1 includes kickoff at zero."""
    return [e for e in events if start < e.match_second <= end]


def _control_component(
    value: int | float | None,
    numerator: int | float,
    unit: str,
    supporting: list[MatchEvent],
    *,
    denominator: int | None = None,
    eligible: int | None = None,
    located: int | None = None,
    missing_coordinates: int | None = None,
    missing_identifiers: int | None = None,
    unknown_chains: int | None = None,
    unavailable_reason: str | None = None,
) -> ControlMetric:
    return ControlMetric(
        value=value, numerator=numerator, denominator=denominator, unit=unit,
        eligible_event_count=len(supporting) if eligible is None else eligible,
        located_event_count=located, missing_coordinate_count=missing_coordinates,
        missing_identifier_count=missing_identifiers, unknown_chain_count=unknown_chains,
        supporting_event_ids=[event.event_id for event in supporting],
        unavailable_reason=unavailable_reason,
    )


def _control_team(team_id: str, other_team_id: str, events: list[MatchEvent]) -> ControlTeamComponents:
    own = [event for event in events if event.team_id == team_id]
    on_ball = [event for event in own if event.event_type in ON_BALL_TYPES]
    possession_events: dict[str, list[MatchEvent]] = {}
    for event in on_ball:
        if event.possession_id:
            possession_events.setdefault(event.possession_id, []).append(event)

    passes = [event for event in own if event.event_type == EventType.pass_]
    completed_passes = [event for event in passes if event.outcome == "complete"]
    pass_completion = 100 * len(completed_passes) / len(passes) if passes else None

    eligible_progression = [
        event for event in own
        if event.event_type in (EventType.pass_, EventType.carry) and event.outcome == "complete"
    ]
    located_progression = [event for event in eligible_progression if event.start and event.end]
    missing_progression = [event for event in eligible_progression if not (event.start and event.end)]
    progression = sum(max(0.0, event.end.x - event.start.x) for event in located_progression)
    entries = [
        event for event in located_progression
        if event.start.x < 66.7 <= event.end.x
    ]

    pressures = [event for event in own if event.event_type == EventType.pressure]
    recoveries = [event for event in own if event.event_type == EventType.recovery]
    turnovers = [event for event in own if event.event_type == EventType.turnover]
    shots = [event for event in own if event.event_type == EventType.shot]

    transition_triggers = [
        event for event in events
        if event.event_type == EventType.recovery and event.team_id == team_id
        or event.event_type == EventType.turnover and event.team_id == other_team_id
    ]
    known_triggers = [event for event in transition_triggers if event.possession_id]
    unknown_triggers = [event for event in transition_triggers if not event.possession_id]
    transition_target_keys: dict[tuple[str, str], list[tuple[int, int, str]]] = {}
    transition_targets: dict[tuple[str, str], list[MatchEvent]] = {}
    for event in events:
        is_target = (
            event.event_type == EventType.shot
            or event.event_type in (EventType.pass_, EventType.carry)
            and event.outcome == "complete" and event.start and event.end
            and event.start.x < 66.7 <= event.end.x
        )
        if is_target and event.team_id and event.possession_id:
            key = (event.team_id, event.possession_id)
            transition_target_keys.setdefault(key, []).append(
                (event.match_second, event.sequence, event.event_id)
            )
            transition_targets.setdefault(key, []).append(event)
    transition_pairs: list[tuple[MatchEvent, MatchEvent]] = []
    for trigger in known_triggers:
        key = (team_id, trigger.possession_id)
        candidates = transition_targets.get(key, [])
        trigger_key = (trigger.match_second, trigger.sequence, trigger.event_id)
        index = bisect_right(transition_target_keys.get(key, []), trigger_key)
        target = candidates[index] if index < len(candidates) else None
        if target and target.match_second <= trigger.match_second + 30:
            transition_pairs.append((trigger, target))
    transition_ids = {
        event.event_id for pair in transition_pairs for event in pair
    }
    transition_support = [
        event for event in events if event.event_id in transition_ids
    ]

    activity_events = sorted(
        {event.event_id: event for event in (*entries, *shots, *recoveries)}.values(),
        key=lambda event: (event.match_second, event.sequence, event.event_id),
    )
    entry_points = 2 * len(entries)
    shot_points = 3 * len(shots)
    recovery_points = len(recoveries)
    activity_index = entry_points + shot_points + recovery_points
    transition_unavailable = (
        f"{len(unknown_triggers)} transition trigger(s) have no possession ID; total is unknown"
        if unknown_triggers else None
    )

    return ControlTeamComponents(
        team_id=team_id,
        retention={
            "observed_possession_sequences": _control_component(
                len(possession_events), len(possession_events), "observed possession IDs",
                [event for group in possession_events.values() for event in group],
                eligible=len(on_ball),
                missing_identifiers=len(on_ball) - sum(
                    len(group) for group in possession_events.values()
                ),
            ),
            "pass_attempts": _control_component(len(passes), len(passes), "passes", passes),
            "completed_passes": _control_component(
                len(completed_passes), len(completed_passes), "passes", completed_passes,
                denominator=len(passes),
            ),
            "pass_completion_ratio": _control_component(
                round(pass_completion, 2) if pass_completion is not None else None,
                len(completed_passes), "percent", passes, denominator=len(passes),
                unavailable_reason="no pass attempts in this window" if not passes else None,
            ),
        },
        progression={
            "forward_progression": _control_component(
                round(progression, 2) if located_progression else None,
                round(progression, 2), "normalized pitch x units",
                located_progression, eligible=len(eligible_progression),
                located=len(located_progression), missing_coordinates=len(missing_progression),
                unavailable_reason="no located completed pass/carry events"
                if not located_progression else None,
            ),
            "final_third_entries": _control_component(
                len(entries) if located_progression else None,
                len(entries), "entries", entries, denominator=len(eligible_progression),
                eligible=len(eligible_progression), located=len(located_progression),
                missing_coordinates=len(missing_progression),
                unavailable_reason="no located completed pass/carry events"
                if not located_progression else None,
            ),
            "eligible_completed_events": _control_component(
                len(eligible_progression), len(eligible_progression), "events",
                eligible_progression, located=len(located_progression),
                missing_coordinates=len(missing_progression),
            ),
            "coordinate_coverage_percent": _control_component(
                round(100 * len(located_progression) / len(eligible_progression), 2)
                if eligible_progression else None,
                len(located_progression), "percent", eligible_progression,
                denominator=len(eligible_progression), eligible=len(eligible_progression),
                located=len(located_progression), missing_coordinates=len(missing_progression),
                unavailable_reason="no completed pass/carry events to assess"
                if not eligible_progression else None,
            ),
        },
        disruption={
            "pressure_events": _control_component(len(pressures), len(pressures), "events", pressures),
            "recoveries": _control_component(len(recoveries), len(recoveries), "events", recoveries),
            "turnovers": _control_component(len(turnovers), len(turnovers), "events", turnovers),
            "rapid_transitions": _control_component(
                len(transition_pairs) if not unknown_triggers else None,
                len(transition_pairs), "observed transitions", transition_support,
                denominator=len(transition_triggers),
                eligible=len(transition_triggers), unknown_chains=len(unknown_triggers),
                unavailable_reason=transition_unavailable,
            ),
        },
        attacking_activity={
            "shots": _control_component(len(shots), len(shots), "shots", shots),
            "final_third_entries": _control_component(
                len(entries), len(entries), "observed entries", entries,
                denominator=len(eligible_progression),
                eligible=len(eligible_progression), located=len(located_progression),
                missing_coordinates=len(missing_progression),
            ),
            "final_third_entry_points": _control_component(
                entry_points, entry_points, "activity points", entries,
                eligible=len(eligible_progression), located=len(located_progression),
                missing_coordinates=len(missing_progression),
            ),
            "shot_points": _control_component(shot_points, shot_points, "activity points", shots),
            "recovery_points": _control_component(
                recovery_points, recovery_points, "activity points", recoveries,
            ),
            "activity_index": _control_component(
                activity_index, activity_index, "descriptive activity points", activity_events,
            ),
        },
    )


def _delta(current: ControlMetric, previous: ControlMetric, duration: int) -> ControlMetricDelta:
    current_value = current.value
    previous_value = previous.value
    difference = current_value - previous_value if current_value is not None and previous_value is not None else None
    is_count = current.unit not in {"percent"}
    factor = 300 / duration
    return ControlMetricDelta(
        current=current_value, previous=previous_value, difference=difference,
        current_rate_per_300_seconds=round(current_value * factor, 3) if is_count and current_value is not None else None,
        previous_rate_per_300_seconds=round(previous_value * factor, 3) if is_count and previous_value is not None else None,
        rate_difference_per_300_seconds=round(difference * factor, 3) if is_count and difference is not None else None,
        unit=current.unit,
        unavailable_reason=(
            current.unavailable_reason if current_value is None
            else previous.unavailable_reason if previous_value is None else None
        ),
    )


def control_chaos_at(
    match: Match, events: list[MatchEvent], at_second: int, window_seconds: int,
) -> ControlChaosResponse:
    """Compare two equal-length event windows ending at the selected replay clock."""
    if window_seconds not in (300, 600, 900):
        raise ValueError("window must be 300, 600, or 900 seconds")
    if not 0 <= at_second <= match.duration_seconds:
        raise ValueError("replay cutoff exceeds match duration")
    if len(events) > MAX_CONTROL_CHAOS_EVENTS:
        raise ValueError("event stream exceeds the control-chaos calculation limit")

    end = min(at_second, match.duration_seconds)
    current_start = max(0, end - window_seconds)
    visible = sorted(
        (event for event in events if event.match_id == match.match_id and event.match_second <= end),
        key=lambda event: (event.match_second, event.sequence, event.event_id),
    )
    if len({event.event_id for event in visible}) != len(visible):
        raise ValueError("event IDs must be unique within the visible match clock")
    current_events = [event for event in visible if current_start < event.match_second <= end]
    current = {
        team.team_id: _control_team(
            team.team_id,
            match.away.team_id if team.team_id == match.home.team_id else match.home.team_id,
            current_events,
        )
        for team in (match.home, match.away)
    }

    previous_window = None
    previous = None
    deltas = None
    if end >= window_seconds * 2:
        previous_start = end - window_seconds * 2
        previous_end = end - window_seconds
        previous_window = {"start_second": previous_start, "end_second": previous_end}
        previous_events = [
            event for event in visible if previous_start < event.match_second <= previous_end
        ]
        previous = {
            team.team_id: _control_team(
                team.team_id,
                match.away.team_id if team.team_id == match.home.team_id else match.home.team_id,
                previous_events,
            )
            for team in (match.home, match.away)
        }
        deltas = {}
        for team in (match.home, match.away):
            team_deltas: dict[str, ControlMetricDelta] = {}
            for category in ("retention", "progression", "disruption", "attacking_activity"):
                for metric_name, current_metric in getattr(current[team.team_id], category).items():
                    old_metric = getattr(previous[team.team_id], category)[metric_name]
                    team_deltas[f"{category}.{metric_name}"] = _delta(
                        current_metric, old_metric, window_seconds,
                    )
            deltas[team.team_id] = team_deltas

    turning_points: list[ControlTurningPoint] = []
    if previous is not None:
        rule = (
            "At least 3 activity-contributing events in the current complete window, "
            "and the activity index rises by at least 6 points and at least 50% versus "
            "a non-zero previous index (or rises from zero). Descriptive association only; not causal."
        )
        for team in (match.home, match.away):
            current_metric = current[team.team_id].attacking_activity["activity_index"]
            previous_metric = previous[team.team_id].attacking_activity["activity_index"]
            current_value = int(current_metric.value or 0)
            previous_value = int(previous_metric.value or 0)
            difference = current_value - previous_value
            enough_events = current_metric.eligible_event_count >= 3
            relative_threshold = previous_value == 0 or difference >= 0.5 * previous_value
            if enough_events and difference >= 6 and relative_threshold:
                turning_points.append(ControlTurningPoint(
                    evidence_id=(
                        f"{match.match_id}-control-chaos-{window_seconds}-{end}-{team.team_id}"
                    ),
                    team_id=team.team_id,
                    previous_value=previous_value,
                    current_value=current_value,
                    difference=difference,
                    rule=rule,
                    previous_event_ids=previous_metric.supporting_event_ids,
                    current_event_ids=current_metric.supporting_event_ids,
                    verification_status="verified_rule_based",
                ))

    unavailable_reasons = []
    if previous is None:
        unavailable_reasons.append(
            "rhythm change unavailable until two complete equal-duration windows are present"
        )
    for team in (match.home, match.away):
        for category in ("retention", "progression", "disruption", "attacking_activity"):
            for name, metric in getattr(current[team.team_id], category).items():
                if metric.unavailable_reason:
                    unavailable_reasons.append(
                        f"{team.team_id}.{category}.{name}: {metric.unavailable_reason}"
                    )
                delta = deltas.get(team.team_id, {}).get(f"{category}.{name}") if deltas else None
                if delta and delta.unavailable_reason:
                    unavailable_reasons.append(
                        f"{team.team_id}.{category}.{name} rhythm change: {delta.unavailable_reason}"
                    )

    return ControlChaosResponse(
        match_id=match.match_id, at_second=end,
        window={"start_second": current_start, "end_second": end},
        previous_window=previous_window,
        units={
            "progression": "normalized 0-100 pitch x units; not metres",
            "possession_sequences": "distinct observed possession IDs; not time share",
            "pass_completion_ratio": "percent",
            "activity_index": "2 x final-third entries + 3 x shots + recoveries",
            "rate": "per 300 match seconds",
        },
        teams=current, deltas=deltas,
        interpretation=ControlInterpretation(
            status="verified_rule_based" if previous is not None else "unavailable",
            language_limit="Event association only; no causal or superiority claim.",
            turning_points=turning_points,
        ),
        unavailable_reasons=unavailable_reasons,
    )


def event_metric(events: list[MatchEvent], team_id: str, metric: str, start: int, end: int) -> int:
    subset = [e for e in window_events(events, start, end) if e.team_id == team_id]
    if metric == "pressure_events":
        return sum(e.event_type == EventType.pressure for e in subset)
    if metric == "recoveries":
        return sum(e.event_type == EventType.recovery for e in subset)
    if metric == "completed_passes":
        return sum(e.event_type == EventType.pass_ and e.outcome == "complete" for e in subset)
    if metric == "final_third_entries":
        return sum(e.event_type in (EventType.pass_, EventType.carry) and e.outcome == "complete"
                   and e.start is not None and e.end is not None and e.start.x < 66.7 <= e.end.x
                   for e in subset)
    if metric == "shots":
        return sum(e.event_type == EventType.shot for e in subset)
    if metric == "momentum_points":
        # Descriptive activity index; intentionally not a goal probability.
        return (event_metric(events, team_id, "final_third_entries", start, end) * 2
                + event_metric(events, team_id, "shots", start, end) * 3
                + event_metric(events, team_id, "recoveries", start, end))
    raise ValueError(f"unsupported metric: {metric}")


def tactics_at(match: Match, events: list[MatchEvent], second: int) -> dict:
    """Observed event summaries at a replay clock; distances use normalized pitch units."""
    seen = events_at(events, second)
    teams = {}
    for team in (match.home, match.away):
        team_events = [e for e in seen if e.team_id == team.team_id]
        passes = [e for e in team_events if e.event_type == EventType.pass_]
        located = [e for e in passes if e.start and e.end]
        completed = [e for e in passes if e.outcome == "complete"]
        links = Counter((e.actor_id, e.recipient_id) for e in completed if e.actor_id and e.recipient_id)
        sequences: dict[str, list[MatchEvent]] = {}
        for e in team_events:
            if e.possession_id and e.event_type != EventType.pressure:
                sequences.setdefault(e.possession_id, []).append(e)
        players = []
        for player in team.players:
            own = [e for e in team_events if e.actor_id == player.player_id]
            if own:
                players.append({"player_id": player.player_id, "name": player.name,
                                "passes_attempted": sum(e.event_type == EventType.pass_ for e in own),
                                "passes_completed": sum(e.event_type == EventType.pass_ and e.outcome == "complete" for e in own),
                                "shots": sum(e.event_type == EventType.shot for e in own),
                                "recoveries": sum(e.event_type == EventType.recovery for e in own),
                                "pressures": sum(e.event_type == EventType.pressure for e in own)})
        teams[team.team_id] = {
            "passes_attempted": len(passes), "passes_completed": len(completed),
            "pass_distance_normalized_units": round(sum(hypot(e.end.x-e.start.x, e.end.y-e.start.y) for e in located), 1),
            "forward_passes": sum(e.end.x > e.start.x for e in located),
            "forward_progression_normalized_units": round(sum(max(0, e.end.x-e.start.x) for e in located), 1),
            "possession_sequences": [{"possession_id": key, "start_second": value[0].match_second,
                                      "end_second": value[-1].match_second, "event_count": len(value)}
                                     for key, value in sequences.items()],
            "passing_network": [{"from_player_id": a, "to_player_id": b, "completed_passes": count}
                                for (a, b), count in sorted(links.items())],
            "shots": [{"event_id": e.event_id, "match_second": e.match_second,
                       "x": e.start.x if e.start else None, "y": e.start.y if e.start else None,
                       "outcome": e.outcome} for e in team_events if e.event_type == EventType.shot],
            "players": players,
            "pressure_events": [{"event_id": e.event_id, "match_second": e.match_second,
                                 "x": e.start.x if e.start else None, "y": e.start.y if e.start else None}
                                for e in team_events if e.event_type == EventType.pressure],
        }
    windows = []
    for end in range(300, min(5400, second) + 300, 300):
        end = min(end, second)
        if windows and windows[-1]["end_second"] == end:
            break
        start = max(-1, end - 300)
        windows.append({"start_second": start, "end_second": end,
                        "home_points": event_metric(seen, match.home.team_id, "momentum_points", start, end),
                        "away_points": event_metric(seen, match.away.team_id, "momentum_points", start, end)})
    return {"match_id": match.match_id, "at_second": second, "computed_from_event_count": len(seen),
            "units": "normalized pitch coordinates (0-100), not metres",
            "momentum_definition": "2 × completed final-third entries + 3 × shots + recoveries per 300-second window; descriptive proxy",
            "teams": teams, "momentum_windows": windows}
