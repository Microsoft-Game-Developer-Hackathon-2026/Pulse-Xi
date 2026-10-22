import { useEffect, useState, type CSSProperties } from 'react'
import type { ControlChaos, ControlMetric, ControlTurningPoint, Event, Match } from './types'

const clock = (second: number) => `${Math.floor(second / 60)}:${String(second % 60).padStart(2, '0')}`
const labels: Record<string, string> = {
  observed_possession_sequences: 'Observed possession IDs',
  pass_attempts: 'Pass attempts',
  completed_passes: 'Completed passes',
  pass_completion_ratio: 'Pass completion',
  forward_progression: 'Forward progression',
  final_third_entries: 'Final-third entries',
  eligible_completed_events: 'Eligible completed passes/carries',
  coordinate_coverage_percent: 'Coordinate coverage',
  pressure_events: 'Recorded pressure',
  recoveries: 'Recoveries',
  turnovers: 'Turnovers',
  rapid_transitions: 'Observed rapid transitions',
  shots: 'Shots',
  final_third_entry_points: 'Entry points',
  shot_points: 'Shot points',
  recovery_points: 'Recovery points',
  activity_index: 'Activity index',
}
const categories = [
  ['retention', 'RETENTION'],
  ['progression', 'PROGRESSION'],
  ['disruption', 'DISRUPTION'],
  ['attacking_activity', 'ATTACKING ACTIVITY'],
] as const

function display(metric: ControlMetric) {
  if (metric.value === null) return 'Unavailable'
  return `${metric.value}${metric.unit === 'percent' ? '%' : ''}`
}

function coverage(metric: ControlMetric) {
  if (metric.located_event_count !== null && metric.eligible_event_count > 0) {
    return `${metric.located_event_count}/${metric.eligible_event_count} located · ${metric.missing_coordinate_count ?? 0} missing coords`
  }
  if (metric.missing_identifier_count !== null) {
    return `${metric.eligible_event_count} on-ball events · ${metric.missing_identifier_count} without possession ID`
  }
  if (metric.unknown_chain_count !== null) return `${metric.unknown_chain_count} unknown possession chains`
  return `${metric.eligible_event_count} supporting/eligible events`
}

export function ControlChaosPanel({ match, atSecond, events, selectEvent }: {
  match: Match
  atSecond: number
  events: Event[]
  selectEvent: (event: Event) => void
}) {
  const [windowSeconds, setWindowSeconds] = useState<300 | 600 | 900>(300)
  const [data, setData] = useState<ControlChaos | null>(null)
  const [selected, setSelected] = useState<ControlTurningPoint | null>(null)
  const [error, setError] = useState('')
  const second = Math.floor(atSecond)

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({
        at_second: String(second),
        window_seconds: String(windowSeconds),
      })
      fetch(`/api/matches/${encodeURIComponent(match.match_id)}/control-chaos?${params}`, { signal: controller.signal })
        .then(response => {
          if (!response.ok) throw new Error(`Control vs Chaos request failed (${response.status})`)
          return response.json() as Promise<ControlChaos>
        })
        .then(value => {
          if (!controller.signal.aborted) {
            setData(value)
            setError('')
            setSelected(current => value.interpretation.turning_points.find(
              point => point.evidence_id === current?.evidence_id,
            ) ?? null)
          }
        })
        .catch(reason => {
          if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Control vs Chaos request failed')
        })
    }, 160)
    return () => { controller.abort(); window.clearTimeout(timer) }
  }, [match.match_id, second, windowSeconds])

  const visible = data?.match_id === match.match_id && data.at_second === second
    && data.window.start_second === Math.max(0, second - windowSeconds)
    && data.formula_version === 'control-chaos-formulas/1' ? data : null
  const activityDelta = (teamId: string) => visible?.deltas?.[teamId]?.['attacking_activity.activity_index']
  const maxActivity = Math.max(1, ...[match.home.team_id, match.away.team_id].flatMap(teamId => {
    const delta = activityDelta(teamId)
    return [delta?.current ?? 0, delta?.previous ?? 0]
  }))
  const selectedTeam = selected
    ? selected.team_id === match.home.team_id ? match.home : match.away
    : null
  const sourceEvents = selected && visible
    ? [...new Set([...selected.previous_event_ids, ...selected.current_event_ids])]
      .map(id => events.find(event => event.event_id === id && event.match_second <= second))
      .filter((event): event is Event => Boolean(event))
      .sort((a, b) => a.match_second - b.match_second || a.sequence - b.sequence || a.event_id.localeCompare(b.event_id))
    : []
  const selectedInputs = selected && visible
    ? visible.deltas?.[selected.team_id]
    : undefined

  return <section className="control-chaos panel" aria-label="Control vs Chaos analysis">
    <div className="panel-title">
      <span>CONTROL VS CHAOS / EVENT-DERIVED RHYTHM</span>
      <small>{visible ? `${visible.formula_version} · THROUGH ${clock(second)}` : 'SYNCING TO REPLAY'}</small>
    </div>
    <div className="control-toolbar">
      <label>WINDOW
        <select aria-label="Control vs Chaos window" value={windowSeconds}
          onChange={event => setWindowSeconds(Number(event.target.value) as 300 | 600 | 900)}>
          <option value={300}>5 minutes</option><option value={600}>10 minutes</option><option value={900}>15 minutes</option>
        </select>
      </label>
      <span>{visible ? `CURRENT ${clock(visible.window.start_second)}–${clock(visible.window.end_second)}` : 'CURRENT WINDOW LOADING'}</span>
      <span>{visible?.previous_window
        ? `PREVIOUS ${clock(visible.previous_window.start_second)}–${clock(visible.previous_window.end_second)}`
        : 'PREVIOUS WINDOW UNAVAILABLE · NEED TWO COMPLETE WINDOWS'}</span>
    </div>
    {error && <p className="control-error" role="alert">{error}</p>}
    {!visible && !error && <p className="control-empty" role="status">Calculating event windows at the selected replay time…</p>}
    {visible && <>
      <div className="control-definitions">
        <p>Observed possession IDs are not possession time. Progression is completed, located horizontal movement in normalized pitch units. Pressure, recoveries, turnovers, shots and activity points stay separate.</p>
        <details>
          <summary>Definitions, coverage and turning-point rule</summary>
          <ul>
            <li>Pass completion = completed passes / pass attempts. Distinct supplied possession IDs count observed on-ball sequences only; no duration or possession share is estimated.</li>
            <li>Progression = sum of positive end.x − start.x for completed located passes/carries. Entries cross from x &lt; 66.7 to x ≥ 66.7. Missing coordinates reduce coverage; they are not imputed.</li>
            <li>Rapid transitions require a recovery or opponent turnover followed within 30 match seconds by the same team's completed located entry or shot with the same non-empty possession ID. Unknown possession links remain unavailable.</li>
            <li>Activity index = 2 × completed final-third entries + 3 × shots + recoveries. A turning point needs at least 3 current-window contributing events, a rise of at least 6 points, and at least 50% growth over a non-zero prior value (or a rise from zero).</li>
          </ul>
        </details>
      </div>
      <div className="control-team-grid">
        {[match.home, match.away].map(team => {
          const components = visible.teams[team.team_id]
          return <article className="control-team" key={team.team_id} style={{ '--team-color': team.color } as CSSProperties}>
            <h3><i/> {team.name}</h3>
            {categories.map(([category, title]) => <section className="control-category" key={category}>
              <h4>{title}</h4>
              {Object.entries(components[category]).map(([name, metric]) => {
                const delta = visible.deltas?.[team.team_id]?.[`${category}.${name}`]
                return <div className="control-metric" key={name}>
                  <span>{labels[name] ?? name.replaceAll('_', ' ')}</span>
                  <strong>{display(metric)} <small>{metric.unit}</small></strong>
                  {visible.previous_window && delta?.difference !== null && delta?.difference !== undefined
                    ? <small className="control-delta">Δ {delta.difference > 0 ? '+' : ''}{delta.difference}{delta.rate_difference_per_300_seconds !== null
                      ? ` · ${delta.rate_difference_per_300_seconds > 0 ? '+' : ''}${delta.rate_difference_per_300_seconds}/300s`
                      : ' pp'}</small>
                    : <small className="control-delta">{visible.previous_window
                      ? `CHANGE UNAVAILABLE${delta?.unavailable_reason ? ` · ${delta.unavailable_reason}` : ''}`
                      : 'CHANGE UNAVAILABLE · PARTIAL HISTORY'}</small>}
                  <small className={metric.unavailable_reason ? 'control-coverage unavailable' : 'control-coverage'}>
                    {metric.unavailable_reason ? metric.unavailable_reason : coverage(metric)}
                  </small>
                </div>
              })}
            </section>)}
          </article>
        })}
      </div>
      <section className="control-rhythm" aria-label="Attacking activity rhythm timeline">
        <h3>RHYTHM TIMELINE / DESCRIPTIVE ACTIVITY INDEX</h3>
        {[match.home, match.away].map(team => {
          const delta = activityDelta(team.team_id)
          return <div className="rhythm-row" key={team.team_id}>
            <span style={{ color: team.color }}>{team.name}</span>
            <div className="rhythm-track" aria-label={`${team.name} activity index`} style={{ '--team-color': team.color } as CSSProperties}>
              <i style={{ width: `${(delta?.previous ?? 0) / maxActivity * 100}%` }}/>
              <b style={{ width: `${(delta?.current ?? 0) / maxActivity * 100}%` }}/>
            </div>
            <small>{delta?.previous ?? '—'} → {delta?.current ?? visible.teams[team.team_id].attacking_activity.activity_index.value}</small>
          </div>
        })}
        <p>{visible.previous_window
          ? 'Bars compare equal-duration windows: previous (muted) → current (team color). Select a verified rule-based turning point below for its inputs and sources.'
          : 'Only current-window counts are available; rhythm change is withheld until a previous equal-duration window exists.'}</p>
      </section>
      <div className="control-interpretation">
        {(() => {
          const home = visible.teams[match.home.team_id]
          const away = visible.teams[match.away.team_id]
          const homeCount = home.retention.observed_possession_sequences.value ?? 0
          const awayCount = away.retention.observed_possession_sequences.value ?? 0
          const higherSequenceTeam = homeCount > awayCount ? match.home : awayCount > homeCount ? match.away : null
          const higherTeamData = higherSequenceTeam?.team_id === match.home.team_id ? home : away
          const lowerTeamData = higherSequenceTeam?.team_id === match.home.team_id ? away : home
          const fewerPressures = higherSequenceTeam
            && (higherTeamData.disruption.pressure_events.value ?? 0) < (lowerTeamData.disruption.pressure_events.value ?? 0)
          const fewerRecoveries = higherSequenceTeam
            && (higherTeamData.disruption.recoveries.value ?? 0) < (lowerTeamData.disruption.recoveries.value ?? 0)
          const contrast = higherSequenceTeam && fewerPressures && fewerRecoveries
            ? `More observed possession IDs for ${higherSequenceTeam.name} coincide with fewer recorded pressures and recoveries in this window.`
            : `Observed possession IDs: ${homeCount} vs ${awayCount}; recorded pressures: ${home.disruption.pressure_events.value} vs ${away.disruption.pressure_events.value}; recoveries: ${home.disruption.recoveries.value} vs ${away.disruption.recoveries.value}.`
          return <p>{contrast} This is a descriptive event contrast, not possession duration, complete match control, superiority or a causal explanation. Turnovers and attacking activity remain separate.</p>
        })()}
      </div>
      <div className="control-turning-points">
        <h3>VERIFIED RHYTHM TURNING POINTS</h3>
        {visible.interpretation.turning_points.length
          ? visible.interpretation.turning_points.map(point => <button key={point.evidence_id}
            aria-pressed={selected?.evidence_id === point.evidence_id}
            onClick={() => setSelected(point)}>
            {match.home.team_id === point.team_id ? match.home.name : match.away.name}: activity index {point.previous_value} → {point.current_value} (+{point.difference})
          </button>)
          : <p>{visible.previous_window
            ? 'No turning point met the published sample and change thresholds in these windows.'
            : 'No turning-point detection: two complete windows are not yet available.'}</p>}
      </div>
      {selected && selectedTeam && <section className="control-proof" aria-label="ProofTrail Control vs Chaos evidence">
        <div className="control-proof-head">
          <div><span>PROOFTRAIL / {selected.evidence_id}</span><small>VERIFIED RULE-BASED · {selectedTeam.name}</small></div>
          <button aria-label="Close turning point proof" onClick={() => setSelected(null)}>×</button>
        </div>
        <p>{selected.rule}</p>
        <div className="control-proof-windows">
          <div><b>PREVIOUS {visible.previous_window && `${clock(visible.previous_window.start_second)}–${clock(visible.previous_window.end_second)}`}</b>
            <span>2 × {selectedInputs?.['attacking_activity.final_third_entries']?.previous ?? '—'} entries = {selectedInputs?.['attacking_activity.final_third_entry_points']?.previous ?? '—'} points</span>
            <span>3 × {selectedInputs?.['attacking_activity.shots']?.previous ?? '—'} shots = {selectedInputs?.['attacking_activity.shot_points']?.previous ?? '—'} points</span>
            <span>{selectedInputs?.['disruption.recoveries']?.previous ?? '—'} recoveries = {selectedInputs?.['attacking_activity.recovery_points']?.previous ?? '—'} points</span>
            <strong>= {selected.previous_value}</strong></div>
          <div><b>CURRENT {clock(visible.window.start_second)}–{clock(visible.window.end_second)}</b>
            <span>2 × {selectedInputs?.['attacking_activity.final_third_entries']?.current ?? '—'} entries = {selectedInputs?.['attacking_activity.final_third_entry_points']?.current ?? '—'} points</span>
            <span>3 × {selectedInputs?.['attacking_activity.shots']?.current ?? '—'} shots = {selectedInputs?.['attacking_activity.shot_points']?.current ?? '—'} points</span>
            <span>{selectedInputs?.['disruption.recoveries']?.current ?? '—'} recoveries = {selectedInputs?.['attacking_activity.recovery_points']?.current ?? '—'} points</span>
            <strong>= {selected.current_value}</strong></div>
        </div>
        <h4>SOURCE EVENTS · SELECT TO SEEK</h4>
        <div className="control-source-list">{sourceEvents.length
          ? sourceEvents.map(event => <button key={event.event_id} onClick={() => selectEvent(event)}>
            {clock(event.match_second)} · {event.type.toUpperCase()} · {event.event_id}
          </button>)
          : <p>No cited events are visible at this replay cutoff.</p>}</div>
        <small className="control-proof-note">Points = 2 × completed final-third entries + 3 × shots + recoveries. Association only; not a causal claim or calibrated tactical score.</small>
      </section>}
    </>}
  </section>
}
