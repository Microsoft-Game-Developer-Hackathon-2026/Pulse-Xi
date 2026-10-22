import { useEffect, useRef, useState } from 'react'
import type { Match } from '../../types'
import type { DifficultyPage, PassDifficulty, PlayerDifficultySummary } from './types'
import './passes.css'

const clock = (second: number) => `${Math.floor(second / 60)}:${String(second % 60).padStart(2, '0')}`
const number = (value: number | null) => value === null ? 'Unavailable' : value.toFixed(2)

async function read<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal })
  if (!response.ok) throw new Error(`Pass analysis unavailable (${response.status}).`)
  return response.json() as Promise<T>
}

export function PassInspector({ match, atSecond, teamId, seek, dataSecond = atSecond, selectedEventId, selectPass, apiBase, load = read }: {
  match: Match; atSecond: number; teamId: string; seek: (second: number) => void; dataSecond?: number
  apiBase?: string; load?: <T>(path: string, signal: AbortSignal) => Promise<T>
  selectedEventId?: string; selectPass?: (eventId: string, second: number) => void
}) {
  const base = apiBase ?? `/api/matches/${encodeURIComponent(match.match_id)}`
  const cutoff = Math.floor(Math.min(dataSecond, atSecond))
  const [result, setResult] = useState<{ key: string; base: string; cutoff: number; items: PassDifficulty[] } | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [filter, setFilter] = useState('all')
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const evidenceRequest = useRef<AbortController | null>(null)
  useEffect(() => () => evidenceRequest.current?.abort(), [base, cutoff, load])
  const key = `${match.match_id}:${cutoff}`
  useEffect(() => {
    if (selectedEventId) { setSelectedId(selectedEventId); setFilter('all') }
  }, [selectedEventId])
  useEffect(() => {
    const controller = new AbortController()
    setError('')
    const timer = window.setTimeout(async () => {
      try {
        const items: PassDifficulty[] = []
        let cursor = 0
        do {
          const page = await load<DifficultyPage>(`${base}/pass-difficulty?at_second=${cutoff}&cursor=${cursor}&limit=200`, controller.signal)
          items.push(...page.items)
          cursor = page.next_cursor ?? 0
        } while (cursor && !controller.signal.aborted)
        if (!controller.signal.aborted) setResult({ key, base, cutoff, items })
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Pass analysis unavailable.')
      }
    }, 140)
    return () => { controller.abort(); window.clearTimeout(timer) }
  }, [match.match_id, cutoff, key, retry, base, load])
  // v1 geometry scores cannot change between passes. Cache by visible pass
  // boundary, never by a future cutoff, to avoid request churn during playback.
  const loaded = result && (result.key === key || !apiBase && result.base === base && result.cutoff <= cutoff)
  const all = loaded ? result.items.filter(item => item.team_id === teamId) : []
  const passes = all.filter(item => filter === 'all' || item.score !== null && item.score >= 70 &&
    (filter === 'high-complete' ? item.outcome === 'complete' : item.outcome === 'incomplete'))
  const selected = passes.find(item => item.event_id === selectedId) ?? passes.at(-1)
  const team = teamId === match.home.team_id ? match.home : match.away
  const playerName = (id: string | null) => team.players.find(player => player.player_id === id)?.name ?? 'Unknown recipient'

  return <section className="pass-workbench" aria-label="Pass difficulty analysis">
    <div className="pass-heading"><div><span className="section-index">PASS INTELLIGENCE</span><h3>Every pass, explained.</h3></div><span className="pass-badge">EVENT-DERIVED HEURISTIC</span></div>
    <p className="pass-intro">Explore distance and forward progression. Scores describe this synthetic formula; they are not pass-failure probabilities.</p>
    <div className="pass-filters"><label>PASS FILTER <select value={filter} onChange={event => { setFilter(event.target.value); setSelectedId('') }}><option value="all">All recorded passes</option><option value="high-complete">High difficulty · completed</option><option value="high-failed">High difficulty · not completed</option></select></label><span>{loaded ? `${passes.length} ELIGIBLE EVENTS · ${clock(result?.cutoff ?? 0)}${result?.cutoff !== cutoff ? " / UPDATING" : ""}` : 'UPDATING AT REPLAY CLOCK'}</span></div>
    <div className="pass-reading" tabIndex={0} aria-label="Pass analysis details">
    {error ? <div role="alert" className="pass-empty">{error} <button onClick={() => setRetry(value => value + 1)}>Retry pass analysis</button></div> : !loaded ? <p className="pass-empty" role="status">Loading pass analysis…</p> : !selected ? <p className="pass-empty">{filter === 'all' ? 'No passes recorded for this team at the selected time.' : 'No passes meet this filter. High difficulty starts at 70/100; the current fixtures may contain none.'}</p> : <>
      <label className="pass-select">SELECT PASS <select value={selected.event_id} onChange={event => { setSelectedId(event.target.value); const pass = passes.find(item => item.event_id === event.target.value); if (pass) selectPass?.(pass.event_id, pass.match_second) }}>{passes.map(pass => <option key={pass.event_id} value={pass.event_id}>{clock(pass.match_second)} · {playerName(pass.player_id)} · {pass.outcome ?? 'unknown outcome'} · {pass.score ?? 'unavailable'}/100</option>)}</select></label>
      <div className="pass-inspection" data-testid="pass-inspector" data-event-id={selected.event_id}>
        <div className="pass-detail">
          <div className="pass-route"><strong>{playerName(selected.player_id)}</strong><span>→</span><strong>{playerName(selected.recipient_id)}</strong></div>
          <p>{clock(selected.match_second)} · {selected.outcome ?? 'Unknown outcome'} · {team.name}</p>
          <svg viewBox="0 0 100 65" role="img" aria-label="Selected pass path in normalized pitch coordinates" className="pass-pitch"><rect x="1" y="1" width="98" height="63" rx="1" fill="#103b37" stroke="#719b90" strokeWidth=".4"/><path d="M50 1V64 M1 18H16V47H1 M99 18H84V47H99" fill="none" stroke="#719b90" strokeWidth=".4"/><circle cx="50" cy="32.5" r="9" fill="none" stroke="#719b90" strokeWidth=".4"/>{selected.start && selected.end && <><path d={`M${1 + selected.start.x * .98} ${1 + selected.start.y * .63} L${1 + selected.end.x * .98} ${1 + selected.end.y * .63}`} stroke={team.color} strokeWidth="1"/><circle cx={1 + selected.start.x * .98} cy={1 + selected.start.y * .63} r="1.5" fill={team.color}/><circle cx={1 + selected.end.x * .98} cy={1 + selected.end.y * .63} r="1.5" fill="white"/></>}</svg>
          <small>Start {selected.start ? `(${number(selected.start.x)}, ${number(selected.start.y)})` : 'unknown'} → End {selected.end ? `(${number(selected.end.x)}, ${number(selected.end.y)})` : 'unknown'} · normalized units</small>
        </div>
        <div className="pass-scorecard"><span className="pass-score-label">{selected.difficulty_band.toUpperCase()} HEURISTIC DIFFICULTY</span><div className="pass-score"><strong>{selected.score ?? '—'}</strong><span>/ 100</span></div>{selected.score !== null && <meter min="0" max="100" value={selected.score} aria-label="Heuristic pass difficulty"/>}<p>{selected.unavailable_reason ?? 'Calculated from this pass’s recorded geometry. Outcome does not change its score.'}</p>{selected.factors.map(factor => <div className="pass-factor" key={factor.factor_id}><span>{factor.factor_id.replaceAll('_', ' ')}<small>{factor.available ? `${number(factor.raw_value)} ${factor.units}` : 'Unavailable · excluded'}</small></span><strong>{factor.available ? `+${number(factor.contribution_points)}` : '—'}</strong></div>)}</div>
      </div>
      <details className="pass-method" key={selected.event_id}><summary>Inspect calculation and source evidence</summary><p>{selected.formula_version} · {selected.verification_status.replaceAll('_', ' ')}</p><p>100 × [(55/85) × min(distance/100, 1) + (30/85) × min(forward progression/60, 1)]. Round the final sum half up. Low &lt;35; moderate 35–69; high ≥70.</p><p>{selected.factors.find(factor => factor.factor_id === 'pressure_context')?.unavailable_reason} Passing lanes and defender proximity are excluded.</p><p>Source event: <button className="pass-source" onClick={() => selectPass ? selectPass(selected.event_id, selected.match_second) : seek(selected.match_second)}>{selected.event_id} · seek to {clock(selected.match_second)}</button></p>{apiBase ? <button onClick={() => { evidenceRequest.current?.abort(); const controller = new AbortController(); evidenceRequest.current = controller; void load<unknown>(`${base}/passes/${encodeURIComponent(selected.event_id)}/difficulty/evidence?at_second=${cutoff}`, controller.signal).then(value => { if (controller.signal.aborted) return; const blob = new Blob([JSON.stringify(value, null, 2)], {type:'application/json'}); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = 'runtime-pass-evidence.json'; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 2000) }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Evidence unavailable.') }) }}>Download authenticated pass evidence</button> : <a href={`/api/matches/${encodeURIComponent(match.match_id)}/passes/${encodeURIComponent(selected.event_id)}/difficulty/evidence?at_second=${cutoff}`} target="_blank" rel="noreferrer">Open versioned evidence JSON ↗</a>}</details>
    </>}
    </div>
  </section>
}

export function PassPlayerSummary({ matchId, playerId, atSecond }: { matchId: string; playerId: string; atSecond: number }) {
  const cutoff = Math.floor(atSecond)
  const key = `${matchId}:${cutoff}`
  const [result, setResult] = useState<{ key: string; players: PlayerDifficultySummary[] } | null>(null)
  const [errorKey, setErrorKey] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    setErrorKey('')
    const timer = window.setTimeout(() => {
      read<{ players: PlayerDifficultySummary[] }>(`/api/matches/${encodeURIComponent(matchId)}/pass-difficulty/players?at_second=${cutoff}`, controller.signal)
        .then(value => { if (!controller.signal.aborted) setResult({ key, players: value.players }) })
        .catch(() => { if (!controller.signal.aborted) { setResult(null); setErrorKey(key) } })
    }, 180)
    return () => { controller.abort(); window.clearTimeout(timer) }
  }, [matchId, cutoff, key])
  const value = result?.key === key ? result.players.find(item => item.player_id === playerId) : undefined
  return <div className="pass-player-summary"><strong>PASS DIFFICULTY / PLAYER LENS</strong><p>{errorKey === key ? 'Pass summary unavailable. Try seeking again or reloading.' : value ? `${value.sample_count} rated passes · mean ${number(value.mean_score)} · median ${number(value.median_score)} · ${value.unavailable_count} unavailable` : 'No rated pass summary available at this replay time.'}</p><small>Descriptive heuristic, with sample count. No player ranking or calibrated performance claim.</small></div>
}
