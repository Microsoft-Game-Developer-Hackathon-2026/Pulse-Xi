"""Pure replay and metrics; all values are derived from events at a clock position."""
from collections import Counter
from math import hypot

from .models import EventType, Match, MatchEvent, MatchMetrics, MatchState, Score, TeamMetrics


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
