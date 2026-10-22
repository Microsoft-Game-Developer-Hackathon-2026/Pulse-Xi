import { useCallback, useEffect, useState } from 'react'
import type { Event, Match, Metrics, Insight } from '../../types'
import { PassInspector } from '../passes/PassInspector'
import { ObserverSwitch } from '../observer/ObserverSwitch'
import { AnalysisTools } from '../sandbox/AnalysisTools'
import type { View } from './api'
import { root } from './api'

type Analysis = { schema_version: 'runtime-analysis/1' | 'runtime-native-analysis/1'; session_id: string; scenario_id: string; revision: number;
  authoritative_tick: number; at_second: number; match: Match; events: Event[]; metrics: Metrics; insights: Insight[];
  clock?: {duration_seconds: number; halftime_tick: number; current_period: number; inspection_period: number}; unavailable?: Record<string,string>;
  event_counts_by_team?: Record<string,Record<string,number>> }

/** Read-only consumers of the engine-owned v1 event projection, never a clock. */
export function RuntimeAnalysis({ token, view, cutoff, sequence, select }: {
  token: string; view: View; cutoff: number; sequence?: number; select: (sequence: number, tick?: number) => void
}) {
  const [open, setOpen] = useState(false)
  const [result, setResult] = useState<{ key: string; credential: string; data: Analysis } | null>(null)
  const [error, setError] = useState(''), [retry, setRetry] = useState(0)
  const [panel, setPanel] = useState<'bookmarks' | 'exports'>('bookmarks')
  const base = `${root}/sessions/${encodeURIComponent(view.session_id)}`
  const key = `${view.session_id}:${view.revision}:${cutoff}`
  const native = view.state.scenario.config.duration_seconds !== 5400
  const load = useCallback(async <T,>(path: string, signal: AbortSignal): Promise<T> => {
    const url = new URL(path, location.origin)
    if (native) url.searchParams.set('projection', 'native')
    const response = await fetch(url, { headers: {Authorization: `Bearer ${token}`}, signal })
    if (!response.ok) throw Error(`Recorded runtime analysis unavailable (${response.status}). Reconnect or refresh the authoritative state.`)
    return response.json() as Promise<T>
  }, [token, native])
  const exportData = useCallback((params: URLSearchParams, signal: AbortSignal) => {
    if (native) params.set('projection', 'native')
    return fetch(`${base}/analysis-export?${params}`, { headers: {Authorization: `Bearer ${token}`}, signal })
  }, [base, token, native])
  useEffect(() => {
    if (!open) return
    const controller = new AbortController(); setError('')
    void load<Analysis>(`${base}/analysis?at_second=${cutoff}`, controller.signal).then(data => {
      if (data.session_id !== view.session_id || data.at_second !== cutoff || data.revision < view.revision) throw Error('Analysis response does not match the requested runtime boundary.')
      if (!controller.signal.aborted) setResult({key, credential: token, data})
    }).catch(reason => { if (!controller.signal.aborted) setError(String(reason.message)) })
    return () => controller.abort()
  }, [open, base, cutoff, key, load, retry, token, view.session_id, view.revision])
  // Keep controls mounted across revision refreshes so drafts and camera choices
  // survive. Hide the old boundary until refreshed; never reuse another owner.
  const data = result?.credential === token && result.data.session_id === view.session_id ? result.data : null
  const current = result?.key === key && Boolean(data) && !error
  const selected = data?.events.find(e => e.sequence === sequence)
  return <details className="panel runtime-analysis" onToggle={e => setOpen(e.currentTarget.open)}>
    <summary>Recorded-event analysis, bookmarks and 3D</summary>
    <p>Read-only analysis follows the committed inspection cutoff. It never advances or rewinds the engine. Coordinates use each team's attacking frame, not continuous tracking.</p>
    {open && <>
      {error ? <p role="alert">{error} <button onClick={() => setRetry(n => n + 1)}>Retry runtime analysis</button></p> : !current && <p role="status">Loading committed recorded-event analysis...</p>}
      {data && <div hidden={!current}>
        <p>Runtime <code>{data.session_id}</code> / revision {data.revision} / inspection {data.at_second}s.</p>
        {data.clock && <p role="status">Native duration {data.clock.duration_seconds}s / halftime {data.clock.halftime_tick}s / inspection period {data.clock.inspection_period}. Authoritative period {data.clock.current_period}. Time is not rescaled.</p>}
        {data.clock && selected && <p>Source sequence {selected.sequence} / native tick {selected.match_second} / recorded period {selected.period}.</p>}
        {data.unavailable && <details><summary>Native analysis availability</summary><ul>{Object.entries(data.unavailable).map(([name,reason]) => <li key={name}>{reason}</li>)}</ul></details>}
        <div className="runtime-table-wrap"><table><caption>Recorded-event statistics through inspection cutoff</caption><thead><tr><th>Team</th><th>Passes</th><th>Shots</th><th>Goals</th><th>Recoveries</th>{data.event_counts_by_team && <><th>Carries</th><th>Turnovers</th></>}</tr></thead><tbody>{(['home','away'] as const).map(side => <tr key={side}><th>{data.match[side].name}</th><td>{data.metrics[side].passes}</td><td>{data.metrics[side].shots}</td><td>{data.metrics[side].goals}</td><td>{data.metrics[side].recoveries}</td>{data.event_counts_by_team && <><td>{data.event_counts_by_team[data.match[side].team_id]?.carry ?? 0}</td><td>{data.metrics[side].turnovers}</td></>}</tr>)}</tbody></table></div>
        <ObserverSwitch apiBase={base} load={load} match={data.match} event={selected} atSecond={cutoff} scope={{match_id: data.match.match_id, scenario_id: data.scenario_id, branch_id: data.session_id}}>
          <svg viewBox="0 0 100 64" role="img" aria-label="Analysis recorded event pitch"><rect x="1" y="1" width="98" height="62" fill="#103b37" stroke="#a7d7c4"/><path d="M50 1V63 M1 18H17V46H1 M99 18H83V46H99" fill="none" stroke="#a7d7c4"/><circle cx="50" cy="32" r="10" fill="none" stroke="#a7d7c4"/>{selected?.start && <><circle cx={1+selected.start.x*.98} cy={1+selected.start.y*.62} r="1.5" fill="white"/>{selected.end && <path d={`M${1+selected.start.x*.98} ${1+selected.start.y*.62} L${1+selected.end.x*.98} ${1+selected.end.y*.62}`} stroke="#66e5df" fill="none"/>}</>}</svg>
        </ObserverSwitch>
        <PassInspector match={data.match} atSecond={cutoff} teamId={selected?.team_id ?? data.match.home.team_id}
          selectedEventId={selected?.event_id} apiBase={base} load={load}
          seek={tick => select(selected?.sequence ?? 1, tick)}
          selectPass={id => { const event = data.events.find(e => e.event_id === id); if (event) select(event.sequence) }}/>
        <details><summary>ProofTrail / verified recorded-event claims ({data.insights.length})</summary>{!data.insights.length && <p>{data.unavailable?.legacy_insight_templates ?? 'No existing rule-based insight qualifies at this cutoff.'}</p>}{data.insights.map(insight => <article key={insight.insight_id}><h4>{insight.title}</h4><p>{insight.explanation}</p><p>{insight.verification_status} / {insight.uncertainty}</p><ul>{insight.supporting_event_ids.map(id => { const event = data.events.find(e => e.event_id === id); return <li key={id}><button disabled={!event} onClick={() => { if (event) select(event.sequence) }}>{id}</button></li> })}</ul></article>)}</details>
        <AnalysisTools match={data.match} events={data.events} selected={selected} second={cutoff}
          filters={{team:'all',kind:'all'}} panel={panel} setPanel={setPanel} runtimeExport={exportData}
          select={event => select(event.sequence, event.match_second)}/>
      </div>}
    </>}
  </details>
}
