import { useEffect, useState } from 'react'
import type { Event, Match, Tactics } from './types'
import { PassInspector } from './features/passes/PassInspector'

const time = (value: number) => `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`

export function TacticalLab({ match, tactics, seen, seek, atSecond, selectedEvent, selectPass }: { match: Match; tactics: Tactics | null; seen: Event[]; seek: (second: number) => void; atSecond: number; selectedEvent?: Event; selectPass?: (eventId: string, second: number) => void }) {
  const [teamId, setTeamId] = useState(match.home.team_id)
  useEffect(() => {
    if (selectedEvent?.type === 'pass' && selectedEvent.team_id) setTeamId(selectedEvent.team_id)
  }, [selectedEvent?.event_id, selectedEvent?.team_id, selectedEvent?.type])
  const chosenId = teamId === match.away.team_id ? teamId : match.home.team_id
  const team = chosenId === match.home.team_id ? match.home : match.away
  const data = tactics?.teams[chosenId]
  const passes = seen.filter(event => event.team_id === chosenId && event.type === 'pass' && event.start && event.end)
  const observed = new Map<string, { x: number; y: number; count: number }>()
  const addPosition = (playerId: string | null, x: number, y: number) => {
    if (!playerId) return
    const prior = observed.get(playerId) ?? { x: 0, y: 0, count: 0 }
    observed.set(playerId, { x: prior.x + x, y: prior.y + y, count: prior.count + 1 })
  }
  passes.filter(event => event.outcome === 'complete').forEach(event => {
    addPosition(event.actor_id, event.start!.x, event.start!.y)
    addPosition(event.recipient_id, event.end!.x, event.end!.y)
  })
  const position = (playerId: string) => {
    const value = observed.get(playerId)
    return value ? { x: value.x / value.count, y: value.y / value.count } : null
  }
  const pressureBins = Array.from({ length: 25 }, () => 0)
  data?.pressure_events.forEach(event => {
    if (event.x === null || event.y === null) return
    const column = Math.min(4, Math.floor(event.x / 20))
    const row = Math.min(4, Math.floor(event.y / 20))
    pressureBins[row * 5 + column] += 1
  })
  const maxPressure = Math.max(1, ...pressureBins)
  const windows = tactics?.momentum_windows ?? []
  const maxPoint = Math.max(1, ...windows.flatMap(window => [window.home_points, window.away_points]))
  return <section className="tactical-lab panel" aria-label="Tactical analysis">
    <div className="panel-title"><span>TACTICAL LAB / OBSERVED EVENTS</span><small>{tactics?.computed_from_event_count ?? 0} EVENTS / {tactics ? `THROUGH ${time(tactics.at_second)}` : "SYNCHRONIZING"}</small></div>
    <div className="tactical-controls"><label>TEAM <select value={chosenId} onChange={event => setTeamId(event.target.value)}><option value={match.home.team_id}>{match.home.name}</option><option value={match.away.team_id}>{match.away.name}</option></select></label><span>POSITION AND DISTANCE USE NORMALIZED PITCH UNITS</span></div>
    <div className="tactical-layout">
      <div className="tactical-chart"><h3>ATTACKING ACTIVITY / FIVE-MINUTE WINDOWS</h3><div className="momentum-bars">{windows.map(window => <button key={window.end_second} title={`${time(window.start_second)}–${time(window.end_second)}: ${match.home.name} ${window.home_points}, ${match.away.name} ${window.away_points}`} onClick={() => seek(window.end_second)}><i style={{height: `${window.home_points / maxPoint * 100}%`}}/><b style={{height: `${window.away_points / maxPoint * 100}%`}}/></button>)}</div><div className="chart-legend"><span style={{color: match.home.color}}>■ {match.home.name}</span><span style={{color: match.away.color}}>■ {match.away.name}</span></div><p>{tactics?.momentum_definition ?? 'Loading event-derived activity index…'}</p></div>
      <div className="tactical-chart"><h3>PASS AND SHOT MAP / {team.name.toUpperCase()}</h3><svg className="analysis-pitch" viewBox="0 0 100 100" role="group" aria-label="Pass and shot positions on a normalized pitch"><rect x="1" y="1" width="98" height="98" fill="#103b37" stroke="#7ea9a0" strokeWidth=".5"/><path d="M50 1V99 M1 25H18V75H1 M99 25H82V75H99" stroke="#7ea9a0" strokeWidth=".5" fill="none"/>{passes.map(event => <g key={event.event_id} role="button" tabIndex={0} aria-label={`Inspect pass ${event.event_id} at ${time(event.match_second)}`} aria-pressed={selectedEvent?.event_id === event.event_id} onClick={() => selectPass?.(event.event_id, event.match_second)} onKeyDown={key => { if (key.key === 'Enter' || key.key === ' ') { key.preventDefault(); selectPass?.(event.event_id, event.match_second) } }}><line x1={event.start!.x} y1={event.start!.y} x2={event.end!.x} y2={event.end!.y} stroke="transparent" strokeWidth="3"/><line x1={event.start!.x} y1={event.start!.y} x2={event.end!.x} y2={event.end!.y} stroke={event.outcome === 'complete' ? team.color : '#ba7770'} strokeOpacity={selectedEvent?.event_id === event.event_id ? 1 : .45} strokeWidth={selectedEvent?.event_id === event.event_id ? 1.2 : .6}/></g>)}{data?.shots.filter(shot => shot.x !== null && shot.y !== null).map(shot => <circle key={shot.event_id} cx={shot.x!} cy={shot.y!} r="1.8" fill={shot.outcome === 'goal' ? '#ffcf6c' : '#f1f7ed'} stroke="#182a2c" strokeWidth=".6" role="button" tabIndex={0} aria-label={`Seek shot ${shot.event_id} at ${time(shot.match_second)}`} onKeyDown={key => { if (key.key === 'Enter' || key.key === ' ') { key.preventDefault(); seek(shot.match_second) } }} onClick={() => seek(shot.match_second)} style={{cursor:'pointer'}}><title>{`${shot.outcome} at ${time(shot.match_second)}`}</title></circle>)}</svg><p>{data?.passes_completed ?? 0}/{data?.passes_attempted ?? 0} passes completed · {data?.shots.length ?? 0} shots. Select a pass to inspect, or a shot to seek. Keyboard: Tab, then Enter or Space.</p></div>
      <div className="tactical-chart"><h3>PLAYER CONTRIBUTIONS / {team.name.toUpperCase()}</h3><div className="player-table" role="table" aria-label="Player contributions"><div role="row" className="player-head"><span>PLAYER</span><span>PASS</span><span>SHOT</span><span>REC</span><span>PRESS</span></div>{data?.players.slice().sort((a,b) => b.passes_completed - a.passes_completed).map(player => <div role="row" key={player.player_id}><span>{player.name}</span><span>{player.passes_completed}/{player.passes_attempted}</span><span>{player.shots}</span><span>{player.recoveries}</span><span>{player.pressures}</span></div>)}</div><p>{data?.possession_sequences.length ?? 0} recorded possession sequences · {data?.forward_passes ?? 0} forward pass attempts · {data?.pass_distance_normalized_units ?? 0} normalized units of observed pass distance.</p></div>
      <div className="tactical-chart"><h3>OBSERVED PASSING NETWORK / {team.name.toUpperCase()}</h3><svg className="analysis-pitch" viewBox="0 0 100 100" role="img" aria-label="Player passing links positioned by observed pass locations"><rect x="1" y="1" width="98" height="98" fill="#103b37" stroke="#7ea9a0" strokeWidth=".5"/><path d="M50 1V99" stroke="#7ea9a0" strokeWidth=".5"/>{data?.passing_network.map(link => { const from = position(link.from_player_id); const to = position(link.to_player_id); return from && to ? <line key={`${link.from_player_id}-${link.to_player_id}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={team.color} strokeOpacity=".7" strokeWidth={Math.min(2.5, .35 + link.completed_passes * .35)}><title>{`${link.completed_passes} completed passes`}</title></line> : null })}{Array.from(observed.entries()).map(([id]) => { const at = position(id)!; return <g key={id}><circle cx={at.x} cy={at.y} r="2.4" fill="#f3f8ee" stroke={team.color} strokeWidth=".7"/><text x={at.x + 2.8} y={at.y - 2.8} fill="#e8f5ed" fontSize="3">{team.players.find(player => player.player_id === id)?.shirt_number}</text></g> })}</svg><p>Links count completed observed passes. Player positions average recorded pass origins and receipt points; no tracking coordinates are implied.</p></div>
      <div className="tactical-chart"><h3>PRESSURE EVENT DENSITY / {team.name.toUpperCase()}</h3><svg className="analysis-pitch" viewBox="0 0 100 100" role="img" aria-label="Five by five count grid of recorded pressure events"><rect x="1" y="1" width="98" height="98" fill="#103b37" stroke="#7ea9a0" strokeWidth=".5"/>{pressureBins.map((count, index) => <g key={index}><rect x={(index % 5) * 20 + 1} y={Math.floor(index / 5) * 20 + 1} width="18" height="18" fill={team.color} fillOpacity={count ? .15 + .75 * count / maxPressure : 0} stroke="#8db0a2" strokeOpacity=".25" strokeWidth=".3"/><title>{`${count} recorded pressure events`}</title></g>)}</svg><p>{data?.pressure_events.length ?? 0} explicit pressure events. Color shows event counts per normalized 20 × 20 grid cell.</p></div>
    </div>
    <PassInspector match={match} atSecond={atSecond} dataSecond={seen.filter(event => event.type === 'pass').at(-1)?.match_second ?? 0} teamId={chosenId} seek={seek} selectedEventId={selectedEvent?.type === 'pass' ? selectedEvent.event_id : undefined} selectPass={selectPass}/>
  </section>
}
