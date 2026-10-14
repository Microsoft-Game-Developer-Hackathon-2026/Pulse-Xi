"""Pure replay and metrics; all values are derived from events at a clock position."""
from collections import Counter

from .models import EventType, Match, MatchEvent, MatchMetrics, MatchState, Score, TeamMetrics


def events_at(events: list[MatchEvent], second: int) -> list[MatchEvent]:
    return [event for event in events if event.match_second <= second]


def state_at(match: Match, events: list[MatchEvent], second: int) -> MatchState:
    seen = events_at(events, second)
    goals = Counter(event.team_id for event in seen if event.event_type == EventType.goal)
    possession = next((e.team_id for e in reversed(seen) if e.possession_id and e.team_id), None)
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
