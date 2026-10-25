import { useEffect, useState } from 'react'
import type { Cue, Insight, Recap } from './types'

type FanState = { status: 'loading' } | { status: 'ready'; text: string; ids: string[] } | { status: 'absent' } | { status: 'unavailable'; reason: string }

/** One verified moment, three framings. Every lens is drawn from the same insight_id and
 * its supporting event IDs; the consistency line is computed from the returned IDs, not asserted. */
export function ThreeStories({ insight, cues, locale, clock }: { insight: Insight; cues: Cue[]; locale: string; clock: (second: number) => string }) {
  const [fan, setFan] = useState<FanState>({ status: 'loading' })
  useEffect(() => {
    const controller = new AbortController()
    setFan({ status: 'loading' })
    const params = new URLSearchParams({ locale, persona: 'casual', at_second: String(Math.floor(insight.match_second)) })
    fetch(`/api/matches/${encodeURIComponent(insight.match_id)}/recap?${params}`, { method: 'POST', signal: controller.signal })
      .then(async response => {
        if (response.status === 429) return setFan({ status: 'unavailable', reason: 'Fan recap is rate limited; retry shortly.' })
        if (!response.ok) return setFan({ status: 'unavailable', reason: 'Fan recap is unavailable for this moment.' })
        const recap = await response.json() as Recap
        if (controller.signal.aborted) return
        const moment = recap.moments.find(item => item.insight_id === insight.insight_id)
        setFan(moment ? { status: 'ready', text: moment.text, ids: moment.supporting_event_ids } : { status: 'absent' })
      })
      .catch(() => { if (!controller.signal.aborted) setFan({ status: 'unavailable', reason: 'Fan recap request failed.' }) })
    return () => controller.abort()
  }, [insight.insight_id, insight.match_id, insight.match_second, locale])

  const cue = cues.find(item => item.match_id === insight.match_id && item.insight_id === insight.insight_id)
  const source = new Set(insight.supporting_event_ids)
  const within = (ids: string[]) => ids.every(id => source.has(id))
  const checks: { lens: string; ok: boolean }[] = []
  if (fan.status === 'ready') checks.push({ lens: 'Fan', ok: within(fan.ids) })
  if (cue) checks.push({ lens: 'Director', ok: within(cue.supporting_event_ids) })
  const consistent = checks.every(item => item.ok)

  return <section className="three-stories" aria-label="One moment, three stories" data-testid="three-stories">
    <h3>ONE MOMENT · THREE STORIES</h3>
    <div className="story-grid">
      <article data-lens="analyst"><small>TACTICAL ANALYST</small><p>{insight.explanation}</p>
        <small>{insight.factual_claims.length} computed {insight.factual_claims.length === 1 ? 'claim' : 'claims'} · window {clock(insight.evidence_window[0])}–{clock(insight.evidence_window[1])}{insight.comparison_window ? ` vs ${clock(insight.comparison_window[0])}–${clock(insight.comparison_window[1])}` : ''}</small>
        <small>{insight.uncertainty}</small></article>
      <article data-lens="fan"><small>FAN LENS · CASUAL</small>
        {fan.status === 'loading' && <p role="status">Loading the fan framing…</p>}
        {fan.status === 'ready' && <p>{fan.text}</p>}
        {fan.status === 'absent' && <p>This moment is not among the recap highlights at its own clock, so no fan framing is shown.</p>}
        {fan.status === 'unavailable' && <p role="status">{fan.reason}</p>}
        <small>Rule-based recap · {fan.status === 'ready' ? `${fan.ids.length} source events` : 'no claims shown'}</small></article>
      <article data-lens="director"><small>BROADCAST DIRECTOR</small>
        {cue ? <><p>{cue.text}</p><small>On air {clock(cue.start_match_second)}–{clock(cue.end_match_second)} · {cue.show_duration_seconds}s · {cue.visual_template}</small>
          <small className="cue-status">PROPOSED · rule-based cue · not producer-approved (approval happens in Director Studio)</small></> : <p>No broadcast cue was generated for this moment.</p>}</article>
    </div>
    <p className={consistent ? 'story-check ok' : 'story-check warn'} role="status">{consistent
      ? `✓ Every lens cites only this moment's ${source.size} verified source events.`
      : `⚠ ${checks.filter(item => !item.ok).map(item => item.lens).join(', ')} cites an event outside this moment's source set.`}</p>
  </section>
}
