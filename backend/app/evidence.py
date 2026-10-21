"""Deterministic evidence packets and rule-based verification."""
from .analytics import event_metric, events_at, state_at, window_events
from .models import EventType, FactualClaim, Insight, Match, MatchEvent, OverlayCue


def verify(insight: Insight, match: Match, events: list[MatchEvent]) -> bool:
    if insight.match_id != match.match_id or insight.team_id not in (None, match.home.team_id, match.away.team_id):
        return False
    if not (0 <= insight.evidence_window[0] <= insight.evidence_window[1] <= insight.match_second):
        return False
    indexed = {event.event_id: event for event in events}
    if any(event_id not in indexed for event_id in insight.supporting_event_ids):
        return False
    if any(not (insight.evidence_window[0] <= indexed[event_id].match_second <= insight.evidence_window[1])
           for event_id in insight.supporting_event_ids):
        return False
    if insight.team_id and any(indexed[event_id].team_id != insight.team_id for event_id in insight.supporting_event_ids):
        return False
    for claim in insight.factual_claims:
        if claim.at_second > insight.match_second or claim.window_start > claim.at_second:
            return False
        if claim.metric.startswith("score_"):
            if claim.team_id is not None:
                return False
            value = getattr(state_at(match, events, claim.at_second).score, claim.metric.removeprefix("score_"))
        else:
            if claim.team_id not in (match.home.team_id, match.away.team_id):
                return False
            value = event_metric(events, claim.team_id, claim.metric, claim.window_start, claim.at_second)
        if value != claim.value:
            return False
    if insight.category == "goal" and not any(indexed[event_id].event_type == EventType.goal for event_id in insight.supporting_event_ids):
        return False
    if insight.category != "goal" and insight.team_id is None:
        return False
    if insight.category == "goal":
        team = match.home if insight.team_id == match.home.team_id else match.away
        goals = [indexed[event_id] for event_id in insight.supporting_event_ids if indexed[event_id].event_type == EventType.goal]
        if (len(goals) != 1 or goals[0].team_id != insight.team_id or
            len(insight.factual_claims) != 2 or
            [claim.metric for claim in insight.factual_claims] != ["score_home", "score_away"]):
            return False
        home, away = (claim.value for claim in insight.factual_claims)
        if insight.title != f"{team.name} score" or insight.explanation != (
            f"{team.name} score at {insight.match_second // 60}' to make it {home}–{away}."
        ):
            return False
    if insight.category == "momentum_shift":
        start, end = insight.evidence_window
        contributors = {e.event_id for e in window_events(events, start - 1, end)
                        if e.team_id == insight.team_id and
                        (e.event_type in (EventType.shot, EventType.recovery) or
                         e.event_type in (EventType.pass_, EventType.carry) and e.outcome == "complete"
                         and e.start and e.end and e.start.x < 66.7 <= e.end.x)}
        if set(insight.supporting_event_ids) != contributors:
            return False
        if insight.comparison_window is None or len(insight.factual_claims) != 2:
            return False
        before, after = insight.factual_claims
        if (before.metric != "momentum_points" or after.metric != "momentum_points" or
            before.team_id != insight.team_id or after.team_id != insight.team_id or
            before.window_start != insight.comparison_window[0] - 1 or
            before.at_second != insight.comparison_window[1] or
            after.window_start != start - 1 or after.at_second != end or
            after.value - before.value < 6):
            return False
        team = match.home if insight.team_id == match.home.team_id else match.away
        if (insight.title != f"{team.name} attacking activity rises" or
            insight.explanation != f"{team.name}'s event activity index rose from {before.value} to {after.value} in consecutive five-minute windows. This is a descriptive event proxy, not a scoring probability."):
            return False
    return True


def insights_for(match: Match, events: list[MatchEvent], at_second: int = 5400) -> list[Insight]:
    insights: list[Insight] = []
    for event in events:
        if event.event_type != EventType.goal or event.match_second > at_second:
            continue
        side = "home" if event.team_id == match.home.team_id else "away"
        team = match.home if side == "home" else match.away
        state = state_at(match, events, event.match_second)
        shot = next((e for e in reversed([prior for prior in events if prior.sequence < event.sequence])
                     if e.event_type == EventType.shot and e.team_id == event.team_id
                     and e.match_second == event.match_second), None)
        references = [shot.event_id, event.event_id] if shot else [event.event_id]
        claim = [FactualClaim(metric="score_home", value=state.score.home, at_second=event.match_second),
                 FactualClaim(metric="score_away", value=state.score.away, at_second=event.match_second)]
        insight = Insight(insight_id=f"{match.match_id}-insight-{event.sequence}", match_id=match.match_id,
                          category="goal", match_second=event.match_second, team_id=team.team_id, title=f"{team.name} score",
                          explanation=f"{team.name} score at {event.match_second // 60}' to make it {state.score.home}–{state.score.away}.",
                          factual_claims=claim, supporting_event_ids=references,
                          derived_metric_ids=[f"score:{event.match_second}"],
                          evidence_window=(event.match_second, event.match_second),
                          uncertainty="Score and event timing are exact within this synthetic event stream; no causal claim is made.",
                          priority=90, verification_status="verified_rule_based")
        if verify(insight, match, events):
            insights.append(insight)
    # A swing is reported only when the team gains at least six descriptive activity
    # points compared with its immediately preceding, equally sized five-minute window.
    for end in range(600, min(at_second, 5400) + 1, 300):
        for team in (match.home, match.away):
            current_start, previous_start = end - 300, end - 600
            current = event_metric(events, team.team_id, "momentum_points", current_start, end)
            previous = event_metric(events, team.team_id, "momentum_points", previous_start, current_start)
            if current - previous < 6:
                continue
            supporting = [e.event_id for e in window_events(events, current_start, end)
                          if e.team_id == team.team_id and (e.event_type in (EventType.shot, EventType.recovery)
                          or e.event_type in (EventType.pass_, EventType.carry) and e.outcome == "complete"
                          and e.start and e.end and e.start.x < 66.7 <= e.end.x)]
            if not supporting:
                continue
            insight = Insight(insight_id=f"{match.match_id}-momentum-{team.team_id}-{end}", match_id=match.match_id,
                              category="momentum_shift", match_second=end, team_id=team.team_id,
                              title=f"{team.name} attacking activity rises",
                              explanation=f"{team.name}'s event activity index rose from {previous} to {current} in consecutive five-minute windows. This is a descriptive event proxy, not a scoring probability.",
                              factual_claims=[FactualClaim(metric="momentum_points", team_id=team.team_id,
                                                           value=previous, window_start=previous_start, at_second=current_start),
                                              FactualClaim(metric="momentum_points", team_id=team.team_id,
                                                           value=current, window_start=current_start, at_second=end)],
                              supporting_event_ids=supporting, derived_metric_ids=["momentum_points:v1"],
                              evidence_window=(current_start + 1, end), comparison_window=(previous_start + 1, current_start),
                              uncertainty="Activity index uses event counts only; pressure and tracking movement are not inferred.",
                              priority=55, verification_status="verified_rule_based")
            if verify(insight, match, events):
                insights.append(insight)
    return sorted(insights, key=lambda item: (item.match_second, -item.priority, item.insight_id))


def overlays_for(match: Match, events: list[MatchEvent], at_second: int = 5400) -> list[OverlayCue]:
    cues = []
    for insight in insights_for(match, events, at_second):
        if insight.category == "goal":
            metrics = {claim.metric: claim.value for claim in insight.factual_claims}
        else:
            metrics = {"momentum_previous": insight.factual_claims[0].value,
                       "momentum_current": insight.factual_claims[1].value}
        start = max(insight.match_second, cues[-1].end_match_second if cues else 0)
        if start >= match.duration_seconds:
            continue
        end = min(match.duration_seconds, start + 12)
        cues.append(OverlayCue(cue_id=f"cue-{insight.insight_id}", match_id=match.match_id,
                               trigger_match_second=insight.match_second, start_match_second=start,
                               end_match_second=end, show_duration_seconds=end - start,
                               priority=insight.priority, overlay_type="goal" if insight.category == "goal" else "insight", text=insight.title.upper(),
                               visual_template="score_lower_third" if insight.category == "goal" else "tactical_lower_third",
                               metrics=metrics, supporting_event_ids=insight.supporting_event_ids,
                               insight_id=insight.insight_id))
    return cues


def recap_for(match: Match, events: list[MatchEvent], locale: str = "en", persona: str = "casual",
              at_second: int = 5400, favorite_team_id: str | None = None,
              favorite_player_id: str | None = None) -> dict:
    """Limited template localization; no translation model is implied."""
    if locale not in {"en", "es", "hi"} or persona not in {"casual", "analyst", "broadcaster", "favorite_team", "favorite_player"}:
        raise ValueError("unsupported locale or persona")
    if favorite_team_id and favorite_team_id not in (match.home.team_id, match.away.team_id):
        raise ValueError("unknown favorite team")
    players = {player.player_id: player for team in (match.home, match.away) for player in team.players}
    if favorite_player_id and favorite_player_id not in players:
        raise ValueError("unknown favorite player")
    insights = [insight for insight in insights_for(match, events, at_second) if insight.category == "goal"]
    if persona == "favorite_team":
        favorite_team_id = favorite_team_id or match.home.team_id
        insights = [item for item in insights if item.team_id == favorite_team_id]
    if persona == "favorite_player":
        favorite_player_id = favorite_player_id or match.home.players[0].player_id
        insights = [item for item in insights if any(e.event_id in item.supporting_event_ids and e.actor_id == favorite_player_id
                                                    and e.event_type == EventType.goal for e in events)]
    final = state_at(match, events, at_second).score
    lead = {
        "en": f"{match.home.name} {final.home}–{final.away} {match.away.name}. Every goal below links to synthetic event evidence.",
        "es": f"{match.home.name} {final.home}–{final.away} {match.away.name}. Cada gol enlaza con eventos sintéticos.",
        "hi": f"{match.home.name} {final.home}–{final.away} {match.away.name}। हर गोल का सिंथेटिक इवेंट प्रमाण उपलब्ध है।",
    }[locale]
    if persona == "favorite_team":
        team = match.home if favorite_team_id == match.home.team_id else match.away
        lead = {"en": f"{team.name} focus: {len(insights)} verified goals by {at_second // 60}' in this synthetic replay.",
                "es": f"Enfoque en {team.name}: {len(insights)} goles verificados hasta el minuto {at_second // 60}.",
                "hi": f"{team.name} पर ध्यान: {at_second // 60}वें मिनट तक {len(insights)} सत्यापित गोल।"}[locale]
    if persona == "favorite_player":
        own = [e for e in events_at(events, at_second) if e.actor_id == favorite_player_id]
        completed = sum(e.event_type == EventType.pass_ and e.outcome == "complete" for e in own)
        shots = sum(e.event_type == EventType.shot for e in own)
        name = players[favorite_player_id].name
        lead = {"en": f"{name} focus: {completed} completed passes and {shots} shots by {at_second // 60}' in this synthetic replay.",
                "es": f"Enfoque en {name}: {completed} pases completados y {shots} tiros hasta el minuto {at_second // 60}.",
                "hi": f"{name} पर ध्यान: {at_second // 60}वें मिनट तक {completed} सफल पास और {shots} शॉट।"}[locale]
    verbs = {"en": "scored", "es": "marcó", "hi": "ने गोल किया"}
    moments = []
    for insight in insights:
        goal = next(event for event in events if event.event_id == insight.supporting_event_ids[-1])
        team = match.home if goal.team_id == match.home.team_id else match.away
        score = {claim.metric: claim.value for claim in insight.factual_claims}
        if persona == "analyst":
            text = {
                "en": f"{team.name} scored · {goal.match_second // 60}' · {score['score_home']}–{score['score_away']} · {len(insight.supporting_event_ids)} source events",
                "es": f"{team.name} marcó · {goal.match_second // 60}' · {score['score_home']}–{score['score_away']} · {len(insight.supporting_event_ids)} eventos de origen",
                "hi": f"{team.name} ने गोल किया · {goal.match_second // 60}' · {score['score_home']}–{score['score_away']} · {len(insight.supporting_event_ids)} स्रोत इवेंट",
            }[locale]
        elif persona == "broadcaster":
            text = {
                "en": f"{goal.match_second // 60}' | {team.name.upper()} SCORED | {score['score_home']}–{score['score_away']}",
                "es": f"{goal.match_second // 60}' | {team.name.upper()} MARCÓ | {score['score_home']}–{score['score_away']}",
                "hi": f"{goal.match_second // 60}' | {team.name.upper()} ने गोल किया | {score['score_home']}–{score['score_away']}",
            }[locale]
        else:
            text = {
                "en": f"{team.name} scored at {goal.match_second // 60}'! {score['score_home']}–{score['score_away']}",
                "es": f"¡{team.name} marcó en el minuto {goal.match_second // 60}! {score['score_home']}–{score['score_away']}",
                "hi": f"{goal.match_second // 60}वें मिनट में {team.name} ने गोल किया! {score['score_home']}–{score['score_away']}",
            }[locale]
        moments.append({"text": text, "insight_id": insight.insight_id,
                        "supporting_event_ids": insight.supporting_event_ids, "match_second": insight.match_second})
    return {"match_id": match.match_id, "locale": locale, "persona": persona,
            "at_second": at_second, "favorite_team_id": favorite_team_id, "favorite_player_id": favorite_player_id,
            "provider": "verified_rule_based_templates", "localization_scope": "goal recaps only",
            "lead": lead, "moments": moments, "synthetic": True}
