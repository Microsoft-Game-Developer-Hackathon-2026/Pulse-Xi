"""Deterministic evidence packets and rule-based verification."""
from .analytics import state_at
from .models import EventType, FactualClaim, Insight, Match, MatchEvent, OverlayCue


def verify(insight: Insight, match: Match, events: list[MatchEvent]) -> bool:
    indexed = {event.event_id: event for event in events}
    if any(event_id not in indexed for event_id in insight.supporting_event_ids):
        return False
    if any(not (insight.evidence_window[0] <= indexed[event_id].match_second <= insight.evidence_window[1])
           for event_id in insight.supporting_event_ids):
        return False
    for claim in insight.factual_claims:
        if claim.metric.startswith("score_"):
            value = getattr(state_at(match, events, claim.at_second).score, claim.metric.removeprefix("score_"))
        else:
            kind = EventType.pressure if claim.metric == "pressure_events" else EventType.recovery
            value = sum(e.event_type == kind and e.team_id == claim.team_id
                        and insight.evidence_window[0] <= e.match_second <= claim.at_second for e in events)
        if value != claim.value:
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
        shot = next((e for e in reversed(events[:event.sequence - 1])
                     if e.event_type == EventType.shot and e.team_id == event.team_id
                     and e.match_second == event.match_second), None)
        references = [shot.event_id, event.event_id] if shot else [event.event_id]
        claim = [FactualClaim(metric="score_home", value=state.score.home, at_second=event.match_second),
                 FactualClaim(metric="score_away", value=state.score.away, at_second=event.match_second)]
        insight = Insight(insight_id=f"{match.match_id}-insight-{event.sequence}", match_id=match.match_id,
                          category="goal", match_second=event.match_second, title=f"{team.name} score",
                          explanation=f"{team.name} score at {event.match_second // 60}' to make it {state.score.home}–{state.score.away}.",
                          factual_claims=claim, supporting_event_ids=references,
                          derived_metric_ids=[f"score:{event.match_second}"],
                          evidence_window=(event.match_second, event.match_second),
                          uncertainty="Score and event timing are exact within this synthetic event stream; no causal claim is made.",
                          priority=90, verification_status="verified_rule_based")
        if verify(insight, match, events):
            insights.append(insight)
    return insights


def overlays_for(match: Match, events: list[MatchEvent], at_second: int = 5400) -> list[OverlayCue]:
    cues = []
    for insight in insights_for(match, events, at_second):
        score = {claim.metric: claim.value for claim in insight.factual_claims}
        cues.append(OverlayCue(cue_id=f"cue-{insight.insight_id}", match_id=match.match_id,
                               trigger_match_second=insight.match_second, show_duration_seconds=12,
                               priority=insight.priority, overlay_type="goal", text=insight.title.upper(),
                               metrics=score, supporting_event_ids=insight.supporting_event_ids,
                               insight_id=insight.insight_id))
    return cues


def recap_for(match: Match, events: list[MatchEvent], locale: str = "en", persona: str = "casual") -> dict:
    """Limited template localization; no translation model is implied."""
    if locale not in {"en", "es", "hi"} or persona not in {"casual", "analyst", "broadcaster"}:
        raise ValueError("unsupported locale or persona")
    insights = insights_for(match, events)
    final = state_at(match, events, 5400).score
    lead = {
        "en": f"{match.home.name} {final.home}–{final.away} {match.away.name}. Every goal below links to synthetic event evidence.",
        "es": f"{match.home.name} {final.home}–{final.away} {match.away.name}. Cada gol enlaza con eventos sintéticos.",
        "hi": f"{match.home.name} {final.home}–{final.away} {match.away.name}। हर गोल का सिंथेटिक इवेंट प्रमाण उपलब्ध है।",
    }[locale]
    verbs = {"en": "scored", "es": "marcó", "hi": "ने गोल किया"}
    moments = []
    for insight in insights:
        goal = next(event for event in events if event.event_id == insight.supporting_event_ids[-1])
        team = match.home if goal.team_id == match.home.team_id else match.away
        score = {claim.metric: claim.value for claim in insight.factual_claims}
        if persona == "analyst":
            text = f"{team.name} {verbs[locale]} · {goal.match_second // 60}' · {score['score_home']}–{score['score_away']} · {len(insight.supporting_event_ids)} source events"
        elif persona == "broadcaster":
            text = f"{goal.match_second // 60}' | {team.name.upper()} {verbs[locale].upper()} | {score['score_home']}–{score['score_away']}"
        else:
            text = {
                "en": f"{team.name} scored at {goal.match_second // 60}'! {score['score_home']}–{score['score_away']}",
                "es": f"¡{team.name} marcó en el minuto {goal.match_second // 60}! {score['score_home']}–{score['score_away']}",
                "hi": f"{goal.match_second // 60}वें मिनट में {team.name} ने गोल किया! {score['score_home']}–{score['score_away']}",
            }[locale]
        moments.append({"text": text, "insight_id": insight.insight_id,
                        "supporting_event_ids": insight.supporting_event_ids, "match_second": insight.match_second})
    return {"match_id": match.match_id, "locale": locale, "persona": persona,
            "provider": "verified_rule_based_templates", "localization_scope": "goal recaps only",
            "lead": lead, "moments": moments, "synthetic": True}
