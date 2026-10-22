"""Deterministic, replay-bounded Fan Lens metric alerts."""
from pydantic import BaseModel, ConfigDict, Field

from .models import EventType, Match, MatchEvent

FORMULA_VERSION = "fan-lens-windows/1"
WINDOW_SECONDS = 300

METRICS = {
    "pressure_events": {"label": "Recorded pressure events", "unit": "events", "thresholds": {"few": 2, "some": 4, "many": 6}},
    "completed_passes": {"label": "Completed passes", "unit": "passes", "thresholds": {"few": 8, "some": 15, "many": 25}},
    "recoveries": {"label": "Ball recoveries", "unit": "recoveries", "thresholds": {"few": 2, "some": 4, "many": 6}},
    "shots": {"label": "Shots", "unit": "shots", "thresholds": {"few": 1, "some": 2, "many": 3}},
    "final_third_entries": {"label": "Completed final-third entries", "unit": "entries", "thresholds": {"few": 2, "some": 4, "many": 6}},
    "forward_progression": {"label": "Completed forward progression", "unit": "normalized pitch units", "thresholds": {"few": 10, "some": 20, "many": 35}},
}


class FanLensResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "fan-lens/1"
    formula_version: str = FORMULA_VERSION
    match_id: str
    at_second: int = Field(ge=0, le=5400)
    metric_id: str
    metric: dict
    threshold_id: str
    threshold_value: int
    team_id: str | None = None
    player_id: str | None = None
    alerts: list[dict]
    value: int | float
    event_count: int
    unavailable_reason: str | None = None
    supported_locales: list[str] = ["en", "es", "hi"]


def fan_lens_at(match: Match, events: list[MatchEvent], *, at_second: int, metric_id: str,
                threshold_id: str, team_id: str | None = None, player_id: str | None = None) -> FanLensResponse:
    if metric_id not in METRICS:
        raise ValueError("unknown metric")
    definition = METRICS[metric_id]
    if threshold_id not in definition["thresholds"]:
        raise ValueError("unknown threshold")
    teams = {match.home.team_id, match.away.team_id}
    players = {player.player_id for team in (match.home, match.away) for player in team.players}
    if team_id is not None and team_id not in teams:
        raise ValueError("unknown team")
    if player_id is not None and player_id not in players:
        raise ValueError("unknown player")
    if player_id is not None:
        player_team = next(team.team_id for team in (match.home, match.away) if any(p.player_id == player_id for p in team.players))
        if team_id is not None and team_id != player_team:
            raise ValueError("player does not belong to selected team")
        team_id = player_team

    eligible = [e for e in events if e.match_second <= at_second and (team_id is None or e.team_id == team_id)
                and (player_id is None or e.actor_id == player_id)]
    def amount(event: MatchEvent) -> float:
        if metric_id == "pressure_events": return float(event.event_type == EventType.pressure)
        if metric_id == "completed_passes": return float(event.event_type == EventType.pass_ and event.outcome == "complete")
        if metric_id == "recoveries": return float(event.event_type == EventType.recovery)
        if metric_id == "shots": return float(event.event_type == EventType.shot)
        if metric_id == "final_third_entries":
            return float(event.event_type in (EventType.pass_, EventType.carry) and event.outcome == "complete"
                         and event.start is not None and event.end is not None and event.start.x < 66.7 <= event.end.x)
        if metric_id == "forward_progression":
            return max(0.0, event.end.x - event.start.x) if event.event_type in (EventType.pass_, EventType.carry) \
                and event.outcome == "complete" and event.start is not None and event.end is not None else 0.0
        return 0.0

    threshold = definition["thresholds"][threshold_id]
    value = sum(amount(e) for e in eligible)
    by_window: dict[int, list[MatchEvent]] = {}
    for event in eligible:
        if amount(event) > 0 and event.match_second > 0:
            # A boundary event belongs to the interval ending at that tick.
            by_window.setdefault((event.match_second - 1) // WINDOW_SECONDS, []).append(event)
    alerts = []
    for index, sources in sorted(by_window.items()):
        start, end = index * WINDOW_SECONDS, (index + 1) * WINDOW_SECONDS
        if end <= at_second and sum(amount(e) for e in sources) >= threshold:
            observed = sum(amount(e) for e in sources)
            ids = sorted(e.event_id for e in sources)
            alerts.append({"alert_id": f"{match.match_id}:{metric_id}:{team_id or 'all'}:{player_id or 'all'}:{index}",
                           "match_id": match.match_id, "branch_id": None, "metric_id": metric_id,
                           "team_id": team_id, "player_id": player_id, "at_second": end,
                           "window_start": start, "window_end": end, "threshold": threshold,
                           "observed_value": observed, "unit": definition["unit"],
                           "supporting_event_ids": ids, "verification_status": "verified_rule_based",
                           "formula_version": FORMULA_VERSION})
    return FanLensResponse(match_id=match.match_id, at_second=at_second, metric_id=metric_id,
                           metric={**definition, "formula_version": FORMULA_VERSION}, threshold_id=threshold_id,
                           threshold_value=threshold, team_id=team_id, player_id=player_id, alerts=alerts,
                           value=value, event_count=sum(amount(e) > 0 for e in eligible),
                           unavailable_reason="No eligible recorded events at this replay time." if not any(amount(e) > 0 for e in eligible) else None)
