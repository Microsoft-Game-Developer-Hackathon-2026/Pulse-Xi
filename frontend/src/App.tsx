import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowRight, ChevronLeft, ChevronRight, CirclePause, CirclePlay, Radio, RotateCcw, Wifi } from 'lucide-react'
import type { Event, Match, Metrics } from './types'

const important = new Set(['goal', 'shot', 'turnover', 'recovery', 'halftime', 'fulltime', 'kickoff'])
const clock = (seconds: number) => `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${Math.floor(seconds % 60).toString().padStart(2, '0')}`

async function api<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) throw new Error(`API request failed (${response.status})`)
  return response.json() as Promise<T>
}

function Pitch({ event, match }: { event?: Event; match: Match }) {
  const color = event?.team_id === match.home.team_id ? match.home.color : match.away.color
  return <div className="pitch-wrap">
    <div className="pitch-topline"><span>SPATIAL EVENT VIEW</span><span>ATTACKING DIRECTION <ArrowRight size={13}/></span></div>
    <svg className="pitch" viewBox="0 0 1000 600" role="img" aria-label={event ? `Pitch position of ${event.type} at ${clock(event.match_second)}` : 'Football pitch awaiting first event'}>
      <defs><pattern id="grass" width="200" height="600" patternUnits="userSpaceOnUse"><rect width="100" height="600" fill="#103b37"/><rect x="100" width="100" height="600" fill="#123f3a"/></pattern><radialGradient id="spot"><stop stopColor={color} stopOpacity=".8"/><stop offset="1" stopColor={color} stopOpacity="0"/></radialGradient></defs>
      <rect width="1000" height="600" fill="url(#grass)"/><rect x="40" y="40" width="920" height="520" fill="none" stroke="#b0d6c7" strokeOpacity=".7" strokeWidth="2"/>
      <path d="M500 40V560 M40 190H190V410H40 M960 190H810V410H960 M40 245H98V355H40 M960 245H902V355H960" fill="none" stroke="#b0d6c7" strokeOpacity=".6" strokeWidth="2"/>
      <circle cx="500" cy="300" r="74" fill="none" stroke="#b0d6c7" strokeOpacity=".6" strokeWidth="2"/><circle cx="500" cy="300" r="4" fill="#b0d6c7"/>
      {event?.start && <><circle cx={40 + event.start.x * 9.2} cy={40 + event.start.y * 5.2} r="72" fill="url(#spot)"/>
        {event.end && <path d={`M${40 + event.start.x * 9.2} ${40 + event.start.y * 5.2} L${40 + event.end.x * 9.2} ${40 + event.end.y * 5.2}`} stroke={color} strokeWidth="4" strokeDasharray="9 7" opacity=".85"/>}
        <circle cx={40 + event.start.x * 9.2} cy={40 + event.start.y * 5.2} r="12" fill={color} stroke="white" strokeWidth="3"/>
        {event.end && <circle cx={40 + event.end.x * 9.2} cy={40 + event.end.y * 5.2} r="6" fill={color}/>}
      </>}
    </svg>
    <div className="pitch-caption"><span className="live-dot"/> {event ? `${event.type.toUpperCase()} · ${event.outcome ?? 'EVENT'} · ${event.event_id}` : 'KICKOFF READY'}<span>GENERATED COORDINATES · SYNTHETIC</span></div>
  </div>
}

export default function App() {
  const [matches, setMatches] = useState<Match[]>([])
  const [matchId, setMatchId] = useState(localStorage.getItem('pulse-xi-match') || '')
  const [events, setEvents] = useState<Event[]>([])
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [second, setSecond] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [error, setError] = useState('')

  useEffect(() => { api<Match[]>('/api/matches').then(items => { setMatches(items); if (!items.some(m => m.match_id === matchId)) setMatchId(items[0]?.match_id || '') }).catch(e => setError(e.message)) }, [])
  useEffect(() => {
    if (!matchId) return
    localStorage.setItem('pulse-xi-match', matchId)
    setEvents([]); setSecond(0); setPlaying(false); setMetrics(null)
    api<Event[]>(`/api/matches/${matchId}/events?limit=1000`).then(setEvents).catch(e => setError(e.message))
  }, [matchId])
  useEffect(() => {
    if (!matchId) return
    const timer = window.setTimeout(() => api<Metrics>(`/api/matches/${matchId}/metrics?at_second=${Math.floor(second)}`).then(setMetrics).catch(e => setError(e.message)), 120)
    return () => window.clearTimeout(timer)
  }, [matchId, second])
  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => setSecond(current => { const next = Math.min(5400, current + speed * 6); if (next === 5400) setPlaying(false); return next }), 200)
    return () => window.clearInterval(timer)
  }, [playing, speed])

  const match = matches.find(m => m.match_id === matchId)
  const seen = useMemo(() => events.filter(e => e.match_second <= second), [events, second])
  const current = [...seen].reverse().find(e => e.start)
  const highlights = events.filter(e => e.type === 'goal')
  const feed = [...seen].reverse().filter(e => important.has(e.type)).slice(0, 7)
  const homeGoals = seen.filter(e => e.type === 'goal' && e.team_id === match?.home.team_id).length
  const awayGoals = seen.filter(e => e.type === 'goal' && e.team_id === match?.away.team_id).length
  const step = (direction: number) => {
    const list = direction > 0 ? events.filter(e => e.match_second > second) : events.filter(e => e.match_second < second)
    const target = direction > 0 ? list[0] : list.at(-1)
    if (target) setSecond(target.match_second)
    setPlaying(false)
  }

  return <div className="app-shell">
    <aside className="rail"><div className="rail-brand">P<span>XI</span></div><div className="rail-rule"/><div className="rail-item active" title="Command center"><Activity size={21}/></div><div className="rail-item" title="Live replay"><Radio size={21}/></div><div className="rail-end">01<br/><small>CORE</small></div></aside>
    <main className="main">
      <header className="header"><div className="brand"><div className="eyebrow">FOOTBALL INTELLIGENCE OPERATING SYSTEM</div><h1>PULSE <em>XI</em><span className="brand-slash">/</span><small>COMMAND CENTER</small></h1></div><div className="header-right"><span className="synthetic-tag">SYNTHETIC SIMULATION</span><span className="status"><Wifi size={16}/> LOCAL ENGINE</span></div></header>
      {error && <div className="error" role="alert">{error}. Start the FastAPI backend on port 8000, then reload.</div>}
      {!match ? <div className="loading">Connecting to match engine…</div> : <>
        <div className="topbar"><div><span className="section-index">01 / LIVE MATCH INTELLIGENCE</span><h2>{match.title}</h2></div><label className="match-select">SELECT MATCH <select value={matchId} onChange={e => setMatchId(e.target.value)}>{matches.map(m => <option key={m.match_id} value={m.match_id}>{m.title}</option>)}</select></label></div>
        <section className="scoreboard"><div className="team home"><span className="team-mark" style={{background: match.home.color}}>HC</span><div><span className="team-label">HOME</span><strong>{match.home.name}</strong></div></div><div className="score-center"><div className="match-phase"><span className="live-dot"/> {second >= 5400 ? 'FULL TIME' : second === 0 ? 'READY TO REPLAY' : 'REPLAY IN PROGRESS'}</div><div className="score"><span>{homeGoals}</span><b>:</b><span>{awayGoals}</span></div><div className="match-clock">{clock(second)} <span>/ 90:00</span></div></div><div className="team away"><div><span className="team-label">AWAY</span><strong>{match.away.name}</strong></div><span className="team-mark" style={{background: match.away.color}}>NU</span></div></section>
        <div className="content-grid"><div className="primary-column"><Pitch event={current} match={match}/>
          <section className="transport panel"><div className="transport-heading"><span>TIME MACHINE</span><span>SIM CLOCK · 30 MATCH SECONDS / REAL SECOND AT 1×</span></div><input aria-label="Seek match time" type="range" min="0" max="5400" step="1" value={second} onChange={e => { setSecond(Number(e.target.value)); setPlaying(false) }}/><div className="transport-bottom"><div className="buttons"><button aria-label="Restart" onClick={() => { setSecond(0); setPlaying(false) }}><RotateCcw size={18}/></button><button aria-label="Previous event" onClick={() => step(-1)}><ChevronLeft size={20}/></button><button className="play" aria-label={playing ? 'Pause' : 'Play'} onClick={() => setPlaying(!playing)}>{playing ? <CirclePause size={27}/> : <CirclePlay size={27}/>}</button><button aria-label="Next event" onClick={() => step(1)}><ChevronRight size={20}/></button></div><div className="speed">SPEED {[.5, 1, 2, 4].map(value => <button key={value} className={speed === value ? 'selected' : ''} onClick={() => setSpeed(value)}>{value}×</button>)}</div></div></section>
          <section className="moments panel"><div className="panel-title"><span>CRITICAL MOMENTS</span><small>SELECT TO SEEK</small></div><div className="moment-list">{highlights.map((e, i) => <button className={second >= e.match_second && second < (highlights[i + 1]?.match_second ?? 5401) ? 'moment current' : 'moment'} key={e.event_id} onClick={() => { setSecond(e.match_second); setPlaying(false) }}><span className="moment-time">{Math.floor(e.match_second / 60)}′</span><span className="moment-dot" style={{background: e.team_id === match.home.team_id ? match.home.color : match.away.color}}/><span>GOAL · {e.team_id === match.home.team_id ? match.home.name : match.away.name}</span><ArrowRight size={16}/></button>)}</div></section>
        </div><div className="secondary-column"><section className="metrics panel"><div className="panel-title"><span>MATCH SIGNALS</span><small>COMPUTED FROM {metrics?.computed_from_event_count ?? 0} EVENTS</small></div>{[['Shots', metrics?.home.shots, metrics?.away.shots], ['Completed passes', metrics?.home.completed_passes, metrics?.away.completed_passes], ['Pass accuracy', metrics?.home.pass_completion_pct, metrics?.away.pass_completion_pct, '%'], ['Final-third entries', metrics?.home.final_third_entries, metrics?.away.final_third_entries], ['Recoveries', metrics?.home.recoveries, metrics?.away.recoveries], ['Pressure events', metrics?.home.pressure_events, metrics?.away.pressure_events]].map(([label, a, b, suffix]) => <div className="metric-row" key={String(label)}><span>{a ?? '—'}{suffix ?? ''}</span><div><label>{label}</label><div className="metric-bars"><i style={{width: `${((Number(a) || 0) / Math.max(1, Number(a) + Number(b))) * 100}%`}}/><b style={{width: `${((Number(b) || 0) / Math.max(1, Number(a) + Number(b))) * 100}%`}}/></div></div><span>{b ?? '—'}{suffix ?? ''}</span></div>)}</section>
          <section className="feed panel"><div className="panel-title"><span>EVENT WIRE</span><small><span className="live-dot"/> SEQUENCED FEED</small></div><div className="feed-list">{feed.length ? feed.map(e => <button key={e.event_id} className="feed-item" onClick={() => { setSecond(e.match_second); setPlaying(false) }}><span className="feed-time">{clock(e.match_second)}</span><span className={`feed-symbol ${e.type}`}>{e.type === 'goal' ? '●' : '◇'}</span><span><strong>{e.type.toUpperCase()}</strong><small>{e.team_id === match.home.team_id ? match.home.name : e.team_id === match.away.team_id ? match.away.name : 'Match official'} · {e.outcome}</small></span></button>) : <div className="empty">Press play or seek to inspect the event stream.</div>}</div></section></div></div>
        <footer><span>POWERED BY DETERMINISTIC SYNTHETIC EVENTS</span><span>MODEL INFERENCE: NOT CONFIGURED · RULE-BASED ENGINE</span><span>SCHEMA v1.0</span></footer>
      </>}
    </main>
  </div>
}
