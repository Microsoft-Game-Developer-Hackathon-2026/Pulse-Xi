import { useState } from 'react'
import type { Event, Match, Tactics } from './types'

const time = (value: number) => `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`

export function TacticalLab({ match, tactics, seen, seek }: { match: Match; tactics: Tactics | null; seen: Event[]; seek: (second: number) => void }) {
  const [teamId, setTeamId] = useState(match.home.team_id)
  const chosenId = teamId === match.away.team_id ? teamId : match.home.team_id
  const team = chosenId === match.home.team_id ? match.home : match.away
  const data = tactics?.teams[chosenId]
  const passes = seen.filter(event => event.team_id === chosenId && event.type === 'pass' && event.start && event.end)
  const windows = tactics?.momentum_windows ?? []
  const maxPoint = Math.max(1, ...windows.flatMap(window => [window.home_points, window.away_points]))
  return <section className="tactical-lab panel" aria-label="Tactical analysis">
    <div className="panel-title"><span>TACTICAL LAB / OBSERVED EVENTS</span><small>{tactics?.computed_from_event_count ?? 0} EVENTS AT REPLAY CLOCK</small></div>
    <div className="tactical-controls"><label>TEAM <select value={chosenId} onChange={event => setTeamId(event.target.value)}><option value={match.home.team_id}>{match.home.name}</option><option value={match.away.team_id}>{match.away.name}</option></select></label><span>POSITION AND DISTANCE USE NORMALIZED PITCH UNITS</span></div>
    <div className="tactical-layout">
      <div className="tactical-chart"><h3>ATTACKING ACTIVITY / FIVE-MINUTE WINDOWS</h3><div className="momentum-bars">{windows.map(window => <button key={window.end_second} title={`${time(window.start_second)}–${time(window.end_second)}: ${match.home.name} ${window.home_points}, ${match.away.name} ${window.away_points}`} onClick={() => seek(window.end_second)}><i style={{height: `${window.home_points / maxPoint * 100}%`}}/><b style={{height: `${window.away_points / maxPoint * 100}%`}}/></button>)}</div><div className="chart-legend"><span style={{color: match.home.color}}>■ {match.home.name}</span><span style={{color: match.away.color}}>■ {match.away.name}</span></div><p>{tactics?.momentum_definition ?? 'Loading event-derived activity index…'}</p></div>
      <div className="tactical-chart"><h3>PASS AND SHOT MAP / {team.name.toUpperCase()}</h3><svg className="analysis-pitch" viewBox="0 0 100 100" role="img" aria-label="Pass and shot positions on a normalized pitch"><rect x="1" y="1" width="98" height="98" fill="#103b37" stroke="#7ea9a0" strokeWidth=".5"/><path d="M50 1V99 M1 25H18V75H1 M99 25H82V75H99" stroke="#7ea9a0" strokeWidth=".5" fill="none"/>{passes.map(event => <line key={event.event_id} x1={event.start!.x} y1={event.start!.y} x2={event.end!.x} y2={event.end!.y} stroke={event.outcome === 'complete' ? team.color : '#ba7770'} strokeOpacity=".45" strokeWidth=".6"/>)}{data?.shots.filter(shot => shot.x !== null && shot.y !== null).map(shot => <circle key={shot.event_id} cx={shot.x!} cy={shot.y!} r="1.8" fill={shot.outcome === 'goal' ? '#ffcf6c' : '#f1f7ed'} stroke="#182a2c" strokeWidth=".6" onClick={() => seek(shot.match_second)} style={{cursor:'pointer'}}><title>{`${shot.outcome} at ${time(shot.match_second)}`}</title></circle>)}</svg><p>{data?.passes_completed ?? 0}/{data?.passes_attempted ?? 0} passes completed · {data?.shots.length ?? 0} shots. Select a shot to seek.</p></div>
      <div className="tactical-chart"><h3>PLAYER CONTRIBUTIONS / {team.name.toUpperCase()}</h3><div className="player-table" role="table" aria-label="Player contributions"><div role="row" className="player-head"><span>PLAYER</span><span>PASS</span><span>SHOT</span><span>REC</span><span>PRESS</span></div>{data?.players.slice().sort((a,b) => b.passes_completed - a.passes_completed).map(player => <div role="row" key={player.player_id}><span>{player.name}</span><span>{player.passes_completed}/{player.passes_attempted}</span><span>{player.shots}</span><span>{player.recoveries}</span><span>{player.pressures}</span></div>)}</div><p>{data?.possession_sequences.length ?? 0} recorded possession sequences · {data?.forward_passes ?? 0} forward pass attempts · {data?.pass_distance_normalized_units ?? 0} normalized units of observed pass distance.</p></div>
    </div>
  </section>
}
