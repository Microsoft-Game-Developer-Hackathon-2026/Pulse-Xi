"""Deterministic, replay-bounded Fan Lens metric alerts."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import EventType, Match, MatchEvent

FORMULA_VERSION = "fan-lens-windows/1"
WINDOW_SECONDS = 300

METRICS = {
    "pressure_events": {"label": "Recorded pressure events", "unit": "events", "eligible_rule": "Recorded pressure event", "thresholds": {"few": 2, "some": 4, "many": 6}},
    "completed_passes": {"label": "Completed passes", "unit": "passes", "eligible_rule": "Pass with outcome complete", "thresholds": {"few": 8, "some": 15, "many": 25}},
    "recoveries": {"label": "Ball recoveries", "unit": "recoveries", "eligible_rule": "Recorded recovery event", "thresholds": {"few": 2, "some": 4, "many": 6}},
    "shots": {"label": "Shots", "unit": "shots", "eligible_rule": "Recorded shot event", "thresholds": {"few": 1, "some": 2, "many": 3}},
    "final_third_entries": {"label": "Completed final-third entries", "unit": "entries", "eligible_rule": "Completed pass/carry; located points required for a crossing", "thresholds": {"few": 2, "some": 4, "many": 6}},
    "forward_progression": {"label": "Completed forward progression", "unit": "normalized pitch units", "eligible_rule": "Completed located pass/carry; positive end.x - start.x only", "thresholds": {"few": 10, "some": 20, "many": 35}},
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
    coverage: dict
    unavailable_reason: Literal["no_eligible_events", "missing_coordinates"] | None = None
    supported_locales: list[str] = Field(default_factory=lambda: ["en", "es", "hi"])


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

    scoped = [e for e in events if e.match_second <= at_second and (team_id is None or e.team_id == team_id)
              and (player_id is None or e.actor_id == player_id)]
    spatial = metric_id in {"final_third_entries", "forward_progression"}
    def is_eligible(event: MatchEvent) -> bool:
        if metric_id == "pressure_events": return event.event_type == EventType.pressure
        if metric_id == "completed_passes": return event.event_type == EventType.pass_ and event.outcome == "complete"
        if metric_id == "recoveries": return event.event_type == EventType.recovery
        if metric_id == "shots": return event.event_type == EventType.shot
        return event.event_type in (EventType.pass_, EventType.carry) and event.outcome == "complete"

    eligible = [event for event in scoped if is_eligible(event)]
    located = [event for event in eligible if event.start is not None and event.end is not None] if spatial else []
    missing_coordinates = len(eligible) - len(located) if spatial else 0
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
        if event.match_second > 0:
            # A boundary event belongs to the interval ending at that tick.
            by_window.setdefault((event.match_second - 1) // WINDOW_SECONDS, []).append(event)
    alerts = []
    for index, sources in sorted(by_window.items()):
        start, end = index * WINDOW_SECONDS, (index + 1) * WINDOW_SECONDS
        contributing = [event for event in sources if amount(event) > 0]
        if end <= at_second and sum(amount(e) for e in sources) >= threshold and contributing:
            observed = sum(amount(e) for e in sources)
            ids = sorted(e.event_id for e in contributing)
            window_located = sum(event.start is not None and event.end is not None for event in sources) if spatial else None
            alerts.append({"alert_id": f"{match.match_id}:{metric_id}:{team_id or 'all'}:{player_id or 'all'}:{index}",
                           "match_id": match.match_id, "branch_id": None, "metric_id": metric_id,
                           "team_id": team_id, "player_id": player_id, "at_second": end,
                           "window_start": start, "window_end": end, "threshold": threshold,
                           "observed_value": observed, "unit": definition["unit"],
                           "supporting_event_ids": ids,
                           "coverage": {"eligible_event_count": len(sources), "located_event_count": window_located,
                                        "missing_coordinate_count": len(sources) - window_located if spatial else 0},
                           "verification_status": "verified_rule_based",
                           "formula_version": FORMULA_VERSION})
    return FanLensResponse(match_id=match.match_id, at_second=at_second, metric_id=metric_id,
                           metric={**definition, "formula_version": FORMULA_VERSION}, threshold_id=threshold_id,
                           threshold_value=threshold, team_id=team_id, player_id=player_id, alerts=alerts,
                           value=value, event_count=sum(amount(e) > 0 for e in eligible),
                           coverage={"eligible_event_count": len(eligible), "located_event_count": len(located) if spatial else None,
                                     "missing_coordinate_count": missing_coordinates},
                           unavailable_reason="no_eligible_events" if not eligible else
                           "missing_coordinates" if spatial and not located else None)
