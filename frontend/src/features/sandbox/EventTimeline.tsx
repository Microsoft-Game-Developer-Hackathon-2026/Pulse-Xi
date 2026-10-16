import { useState } from 'react'
import type { Event, Match } from '../../types'

const clock = (second: number) => `${Math.floor(second / 60)}:${String(second % 60).padStart(2, '0')}`

export function EventTimeline({ match, seen, atSecond, selectedId, select }: {
  match: Match; seen: Event[]; atSecond: number; selectedId?: string; select: (event: Event) => void
}) {
  const [team, setTeam] = useState('all')
  const [kind, setKind] = useState('all')
  const [limit, setLimit] = useState(50)
  const filtered = seen.filter(event => (team === 'all' || event.team_id === team) && (kind === 'all' || event.type === kind)).slice().reverse()
  const teams = [match.home, match.away]
  return <section className="sandbox-timeline panel" aria-label="Sandbox event timeline">
    <div className="panel-title"><span>EVENT EXPLORER / REPLAY BOUNDARY</span><small>{seen.length} VISIBLE · CURSOR {seen.at(-1)?.sequence ?? 0} · {clock(Math.floor(atSecond))}</small></div>
    <div className="sandbox-timeline-filters"><label>EVENT TEAM <select value={team} onChange={event => { setTeam(event.target.value); setLimit(50) }}><option value="all">Both teams and officials</option>{teams.map(item => <option key={item.team_id} value={item.team_id}>{item.name}</option>)}</select></label><label>EVENT TYPE <select value={kind} onChange={event => { setKind(event.target.value); setLimit(50) }}><option value="all">All event types</option>{['pass', 'carry', 'shot', 'goal', 'pressure', 'recovery', 'turnover', 'interception', 'tackle'].map(type => <option key={type} value={type}>{type}</option>)}</select></label><span>Only events at or before the replay clock are shown.</span></div>
    <ol className="sandbox-event-list" aria-label="Recorded replay events">{filtered.slice(0, limit).map(event => {
      const eventTeam = teams.find(item => item.team_id === event.team_id)
      const player = eventTeam?.players.find(item => item.player_id === event.actor_id)
      return <li key={event.event_id}><button aria-pressed={selectedId === event.event_id} onClick={() => select(event)}><time>{clock(event.match_second)}</time><i style={{ background: eventTeam?.color ?? '#8ca6a4' }}/><span><strong>{event.type.toUpperCase()} <small>{event.outcome ?? 'recorded'}</small></strong><span>{player?.name ?? eventTeam?.name ?? 'Match official'}</span></span><code>{event.event_id}</code><span aria-hidden="true">↗</span></button></li>
    })}</ol>
    {!filtered.length && <p className="sandbox-timeline-empty">No matching events at this replay time. Change a filter or advance the replay.</p>}
    {filtered.length > limit && <button className="sandbox-more" onClick={() => setLimit(value => value + 50)}>Show 50 more recorded events</button>}
    <p className="sandbox-timeline-note">Positions are recorded synthetic event points. Continuous actor movement is not available in this fixture stream.</p>
  </section>
}
