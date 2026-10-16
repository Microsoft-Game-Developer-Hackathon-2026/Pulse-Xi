import { useEffect, useMemo, useRef, useState } from 'react'
import { Activity, ArrowRight, ChevronLeft, ChevronRight, CirclePause, CirclePlay, Radio, RotateCcw, Wifi } from 'lucide-react'
import type { Cue, Event, Insight, Match, Metrics, Recap, Tactics } from './types'
import { TacticalLab } from './TacticalLab'
import { PassPlayerSummary } from './features/passes/PassInspector'
import { SandboxSetup } from './features/sandbox/SandboxSetup'
import { EventTimeline } from './features/sandbox/EventTimeline'
import { ObserverSwitch } from './features/observer/ObserverSwitch'
import { readReplayEvents } from './features/sandbox/replayApi'

const important = new Set(['goal', 'shot', 'turnover', 'recovery', 'halftime', 'fulltime', 'kickoff'])
const clock = (seconds: number) => `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${Math.floor(seconds % 60).toString().padStart(2, '0')}`

async function api<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal })
  if (!response.ok) throw new Error(`API request failed (${response.status})`)
  return response.json() as Promise<T>
}

function Pitch({ event, match, cue }: { event?: Event; match: Match; cue?: Cue }) {
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
    {cue && <div className="broadcast-cue" role="status"><small>DIRECTOR CUE · {clock(cue.start_match_second)}</small><strong>{cue.text}</strong><span>{cue.overlay_type === 'goal' ? `${cue.metrics.score_home} — ${cue.metrics.score_away}` : `${cue.metrics.momentum_previous} → ${cue.metrics.momentum_current} ACTIVITY POINTS`} <i>PROOF {cue.supporting_event_ids.length} EVENTS</i></span></div>}
    <div className="pitch-caption"><span className="live-dot"/> {event ? `${event.type.toUpperCase()} · ${event.outcome ?? 'EVENT'} · ${event.event_id}` : 'KICKOFF READY'}<span>GENERATED COORDINATES · SYNTHETIC</span></div>
  </div>
}

export default function App() {
  const [matches, setMatches] = useState<Match[]>([])
  const [matchId, setMatchId] = useState('')
  const [events, setEvents] = useState<Event[]>([])
  const [metricResponse, setMetrics] = useState<Metrics | null>(null)
  const [tacticResponse, setTactics] = useState<Tactics | null>(null)
  const [insights, setInsights] = useState<Insight[]>([])
  const [cueResponse, setCues] = useState<Cue[]>([])
  const [proofResponse, setProof] = useState<{ insight: Insight; source_events: Event[] } | null>(null)
  const [recapResponse, setRecap] = useState<Recap | null>(null)
  const [persona, setPersona] = useState('casual')
  const [locale, setLocale] = useState('en')
  const [favoriteTeamId, setFavoriteTeamId] = useState('')
  const [favoritePlayerId, setFavoritePlayerId] = useState('')
  const [second, setSecond] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [showOverlays, setShowOverlays] = useState(true)
  const [error, setError] = useState('')
  const [workspace, setWorkspace] = useState(window.location.hash === '#/sandbox' ? 'sandbox' : 'command')
  const [selectedEventId, setSelectedEventId] = useState('')
  const [connectionAttempt, setConnectionAttempt] = useState(0)
  const priorMatch = useRef('')
  const proofDrawer = useRef<HTMLElement>(null)
  const proofRequest = useRef<AbortController | null>(null)

  useEffect(() => () => proofRequest.current?.abort(), [matchId])

  useEffect(() => {
    const change = () => setWorkspace(window.location.hash === '#/sandbox' ? 'sandbox' : 'command')
    window.addEventListener('hashchange', change)
    return () => window.removeEventListener('hashchange', change)
  }, [])
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const items = await api<Match[]>('/api/matches', controller.signal)
        let saved: string | null = null
        try { saved = localStorage.getItem('pulse-xi-match') } catch { /* Storage is optional. */ }
        if (saved?.startsWith('custom-') && !items.some(item => item.match_id === saved)) {
          try { items.push(await api<Match>(`/api/matches/${encodeURIComponent(saved)}`, controller.signal)) }
          catch { /* An invalid saved replay falls back to an available fixture. */ }
        }
        if (!controller.signal.aborted) {
          setMatches(items)
          setMatchId(items.find(item => item.match_id === saved)?.match_id || items[0]?.match_id || '')
        }
      } catch (reason) { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Match loading failed') }
    }
    void load()
    return () => controller.abort()
  }, [connectionAttempt])
  useEffect(() => {
    if (!matchId) return
    const controller = new AbortController()
    try { localStorage.setItem('pulse-xi-match', matchId) } catch { /* Replay still works without browser storage. */ }
    setError('')
    if (priorMatch.current !== matchId) {
      setEvents([]); setSecond(0); setPlaying(false); setMetrics(null); setTactics(null); setProof(null); setRecap(null); setFavoriteTeamId(''); setFavoritePlayerId(''); setInsights([]); setCues([]); setSelectedEventId('')
      priorMatch.current = matchId
    }
    const failed = (reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Match loading failed') }
    readReplayEvents(matchId, controller.signal).then(value => { if (!controller.signal.aborted) setEvents(value) }).catch(failed)
    api<Insight[]>(`/api/matches/${matchId}/insights`, controller.signal).then(value => { if (!controller.signal.aborted) setInsights(value) }).catch(failed)
    api<Cue[]>(`/api/matches/${matchId}/overlays`, controller.signal).then(value => { if (!controller.signal.aborted) setCues(value) }).catch(failed)
    return () => controller.abort()
  }, [matchId, connectionAttempt])
  useEffect(() => {
    if (!matchId) return
    let active = true
    setRecap(null)
    const params = new URLSearchParams({ locale, persona, at_second: String(Math.floor(second)) })
    if (favoriteTeamId) params.set('favorite_team_id', favoriteTeamId)
    if (favoritePlayerId) params.set('favorite_player_id', favoritePlayerId)
    const timer = window.setTimeout(() => {
      fetch(`/api/matches/${matchId}/recap?${params}`, { method: 'POST' })
        .then(response => { if (!response.ok) throw new Error('Recap request failed'); return response.json() as Promise<Recap> })
        .then(value => { if (active) setRecap(value) }).catch(e => { if (active) setError(e.message) })
    }, 220)
    return () => { active = false; window.clearTimeout(timer) }
  }, [matchId, locale, persona, second, favoriteTeamId, favoritePlayerId, connectionAttempt])
  useEffect(() => {
    if (!matchId) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => api<Metrics>(`/api/matches/${matchId}/metrics?at_second=${Math.floor(second)}`, controller.signal).then(value => { if (!controller.signal.aborted) setMetrics(value) }).catch(e => { if (!controller.signal.aborted) setError(e.message) }), 120)
    return () => { controller.abort(); window.clearTimeout(timer) }
  }, [matchId, second, connectionAttempt])
  useEffect(() => {
    if (!matchId) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => api<Tactics>(`/api/matches/${matchId}/tactics?at_second=${Math.floor(second)}`, controller.signal).then(value => { if (!controller.signal.aborted) setTactics(value) }).catch(e => { if (!controller.signal.aborted) setError(e.message) }), 180)
    return () => { controller.abort(); window.clearTimeout(timer) }
  }, [matchId, second, connectionAttempt])
  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => setSecond(current => { const next = Math.min(5400, current + speed * 6); if (next === 5400) setPlaying(false); return next }), 200)
    return () => window.clearInterval(timer)
  }, [playing, speed])

  const match = matches.find(m => m.match_id === matchId)
  const metrics = metricResponse?.match_id === matchId && metricResponse.at_second === Math.floor(second) ? metricResponse : null
  const tactics = tacticResponse?.match_id === matchId && tacticResponse.at_second === Math.floor(second) ? tacticResponse : null
  const recap = recapResponse?.match_id === matchId && recapResponse.at_second === Math.floor(second) ? recapResponse : null
  const cues = cueResponse.filter(cue => cue.match_id === matchId && (workspace !== 'sandbox' || cue.trigger_match_second <= second))
  const proof = proofResponse?.insight.match_id === matchId && proofResponse.insight.match_second <= second ? proofResponse : null
  useEffect(() => {
    if (!proof) return
    const opener = document.activeElement as HTMLElement | null
    const drawer = proofDrawer.current
    const focusable = () => Array.from(drawer?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input, select, summary, [tabindex="0"]') ?? [])
    focusable()[0]?.focus()
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { proofRequest.current?.abort(); setProof(null) }
      if (event.key === 'Tab') {
        const items = focusable(); const first = items[0]; const last = items.at(-1)
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
      }
    }
    document.addEventListener('keydown', keydown)
    return () => { document.removeEventListener('keydown', keydown); if (opener?.isConnected) opener.focus() }
  }, [proof?.insight.insight_id])
  const seen = useMemo(() => events.filter(e => e.match_id === matchId && e.match_second <= second), [events, matchId, second])
  const current = seen.find(event => event.event_id === selectedEventId && event.match_second === second) ?? [...seen].reverse().find(e => e.start)
  const highlights = events.filter(e => e.match_id === matchId && e.type === 'goal' && (workspace !== 'sandbox' || e.match_second <= second))
  const feed = [...seen].reverse().filter(e => important.has(e.type)).slice(0, 7)
  const activeCue = showOverlays ? cues.find(cue => second >= cue.start_match_second && second < cue.end_match_second) : undefined
  const visibleInsights = insights.filter(insight => insight.match_id === matchId && insight.match_second <= second).slice(-3).reverse()
  const homeGoals = seen.filter(e => e.type === 'goal' && e.team_id === match?.home.team_id).length
  const awayGoals = seen.filter(e => e.type === 'goal' && e.team_id === match?.away.team_id).length
  const step = (direction: number) => {
    const selectedIndex = events.findIndex(event => event.event_id === selectedEventId && event.match_second === second)
    const target = selectedIndex >= 0 ? events[selectedIndex + direction] : direction > 0
      ? events.find(event => event.match_second > second)
      : events.filter(event => event.match_second < second).at(-1)
    if (target) { setSecond(target.match_second); setSelectedEventId(target.event_id) }
    setPlaying(false)
  }
  const openProof = (insightId: string) => {
    proofRequest.current?.abort()
    const controller = new AbortController(); proofRequest.current = controller
    fetch(`/api/insights/${encodeURIComponent(insightId)}/explain`, { method: 'POST', signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('Proof request failed'); return response.json() as Promise<{ insight: Insight; source_events: Event[] }> })
      .then(value => { if (!controller.signal.aborted) setProof(value) }).catch(e => { if (!controller.signal.aborted) setError(e.message) })
  }
  const generated = (value: Match) => {
    setMatches(items => items.some(item => item.match_id === value.match_id) ? items : [...items, value])
    setMatchId(value.match_id); setSecond(0); setPlaying(false); setProof(null); setSelectedEventId('')
  }

  return <div className="app-shell">
    <aside className="rail"><div className="rail-brand">P<span>XI</span></div><div className="rail-rule"/><div className="rail-item active" title="Command center"><Activity size={21}/></div><div className="rail-item" title="Live replay"><Radio size={21}/></div><div className="rail-end">01<br/><small>CORE</small></div></aside>
    <main className="main">
      <header className="header"><div className="brand"><div className="eyebrow">FOOTBALL INTELLIGENCE OPERATING SYSTEM</div><h1>PULSE <em>XI</em><span className="brand-slash">/</span><small>{workspace === 'sandbox' ? 'SANDBOX LAB' : 'COMMAND CENTER'}</small></h1></div><div className="header-right"><span className="synthetic-tag">SYNTHETIC SIMULATION</span><span className="status"><Wifi size={16}/> LOCAL ENGINE</span></div></header>
      <nav className="workspace-nav" aria-label="Workspace"><a href="#/" aria-current={workspace === 'command' ? 'page' : undefined}>MATCH INTELLIGENCE</a><a href="#/sandbox" aria-current={workspace === 'sandbox' ? 'page' : undefined}>SANDBOX LAB</a></nav>
      {error && <div className="error" role="alert">{error}. <button onClick={() => { setPlaying(false); setError(''); setConnectionAttempt(value => value + 1) }}>Retry connection</button></div>}
      {!match ? <div className="loading">Connecting to match engine…</div> : <>
        {workspace === 'sandbox' && <SandboxSetup match={match} onGenerated={generated}/>}
        <div className="topbar"><div><span className="section-index">01 / LIVE MATCH INTELLIGENCE</span><h2>{match.title}</h2></div><label className="match-select">SELECT MATCH <select value={matchId} onChange={e => setMatchId(e.target.value)}>{matches.map(m => <option key={m.match_id} value={m.match_id}>{m.title}</option>)}</select></label></div>
        <section className="scoreboard"><div className="team home"><span className="team-mark" style={{background: match.home.color}}>HC</span><div><span className="team-label">HOME</span><strong>{match.home.name}</strong></div></div><div className="score-center"><div className="match-phase"><span className="live-dot"/> {second >= 5400 ? 'FULL TIME' : second === 0 ? 'READY TO REPLAY' : 'REPLAY IN PROGRESS'}</div><div className="score"><span>{homeGoals}</span><b>:</b><span>{awayGoals}</span></div><div className="match-clock">{clock(second)} <span>/ 90:00</span></div></div><div className="team away"><div><span className="team-label">AWAY</span><strong>{match.away.name}</strong></div><span className="team-mark" style={{background: match.away.color}}>NU</span></div></section>
        <div className="content-grid"><div className="primary-column">{workspace === 'sandbox' ? <ObserverSwitch match={match} event={current} atSecond={second}><Pitch event={current} match={match} cue={activeCue}/></ObserverSwitch> : <Pitch event={current} match={match} cue={activeCue}/>}
          <section className="transport panel"><div className="transport-heading"><span>TIME MACHINE</span><span>SIM CLOCK · 30 MATCH SECONDS / REAL SECOND AT 1×</span></div><input aria-label="Seek match time" type="range" min="0" max="5400" step="1" value={second} onChange={e => { setSecond(Number(e.target.value)); setPlaying(false) }}/><div className="transport-bottom"><div className="buttons"><button aria-label="Restart" onClick={() => { setSecond(0); setPlaying(false) }}><RotateCcw size={18}/></button><button aria-label="Previous event" onClick={() => step(-1)}><ChevronLeft size={20}/></button><button className="play" aria-label={playing ? 'Pause' : 'Play'} onClick={() => setPlaying(!playing)}>{playing ? <CirclePause size={27}/> : <CirclePlay size={27}/>}</button><button aria-label="Next event" onClick={() => step(1)}><ChevronRight size={20}/></button></div><div className="speed">SPEED {[.5, 1, 2, 4].map(value => <button key={value} className={speed === value ? 'selected' : ''} onClick={() => setSpeed(value)}>{value}×</button>)}</div></div></section>
          <section className="moments panel"><div className="panel-title"><span>CRITICAL MOMENTS</span><small>SELECT TO SEEK</small></div><div className="moment-list">{!highlights.length && <p className="empty">No goal events at this replay time.</p>}{highlights.map((e, i) => <button className={second >= e.match_second && second < (highlights[i + 1]?.match_second ?? 5401) ? 'moment current' : 'moment'} key={e.event_id} onClick={() => { setSecond(e.match_second); setPlaying(false) }}><span className="moment-time">{Math.floor(e.match_second / 60)}′</span><span className="moment-dot" style={{background: e.team_id === match.home.team_id ? match.home.color : match.away.color}}/><span>GOAL · {e.team_id === match.home.team_id ? match.home.name : match.away.name}</span><ArrowRight size={16}/></button>)}</div></section>
        </div><div className="secondary-column"><section className="metrics panel"><div className="panel-title"><span>MATCH SIGNALS</span><small>COMPUTED FROM {metrics?.computed_from_event_count ?? 0} EVENTS</small></div>{[['Shots', metrics?.home.shots, metrics?.away.shots], ['Completed passes', metrics?.home.completed_passes, metrics?.away.completed_passes], ['Pass accuracy', metrics?.home.pass_completion_pct, metrics?.away.pass_completion_pct, '%'], ['Final-third entries', metrics?.home.final_third_entries, metrics?.away.final_third_entries], ['Recoveries', metrics?.home.recoveries, metrics?.away.recoveries], ['Pressure events', metrics?.home.pressure_events, metrics?.away.pressure_events]].map(([label, a, b, suffix]) => <div className="metric-row" key={String(label)}><span>{a ?? '—'}{suffix ?? ''}</span><div><label>{label}</label><div className="metric-bars"><i style={{width: `${((Number(a) || 0) / Math.max(1, Number(a) + Number(b))) * 100}%`}}/><b style={{width: `${((Number(b) || 0) / Math.max(1, Number(a) + Number(b))) * 100}%`}}/></div></div><span>{b ?? '—'}{suffix ?? ''}</span></div>)}</section>
          <section className="feed panel"><div className="panel-title"><span>EVENT WIRE</span><small><span className="live-dot"/> SEQUENCED FEED</small></div><div className="feed-list">{feed.length ? feed.map(e => <button key={e.event_id} className="feed-item" onClick={() => { setSecond(e.match_second); setPlaying(false) }}><span className="feed-time">{clock(e.match_second)}</span><span className={`feed-symbol ${e.type}`}>{e.type === 'goal' ? '●' : '◇'}</span><span><strong>{e.type.toUpperCase()}</strong><small>{e.team_id === match.home.team_id ? match.home.name : e.team_id === match.away.team_id ? match.away.name : 'Match official'} · {e.outcome}</small></span></button>) : <div className="empty">Press play or seek to inspect the event stream.</div>}</div></section></div></div>
        {workspace === 'sandbox' && <EventTimeline match={match} seen={seen} atSecond={second} selectedId={current?.event_id} select={event => { setSecond(event.match_second); setPlaying(false); setProof(null); setSelectedEventId(event.event_id) }}/>}
        <TacticalLab match={match} tactics={tactics} seen={seen} selectedEvent={current} selectPass={(eventId, time) => { setSelectedEventId(eventId); setSecond(time); setPlaying(false) }} atSecond={second} seek={value => { setSecond(value); setPlaying(false) }}/>
        {persona === 'favorite_player' && <PassPlayerSummary matchId={matchId} playerId={favoritePlayerId || match.home.players[0].player_id} atSecond={second}/>}
        <div className="intelligence-grid">
          <section className="panel"><div className="panel-title"><span>PROOFTRAIL / VERIFIED MOMENTS</span><small>RULE-BASED · EVENT CITATIONS</small></div><div className="insight-list">{visibleInsights.length ? visibleInsights.map(insight => <article className="insight-card" key={insight.insight_id}><div><span className="insight-minute">{Math.floor(insight.match_second / 60)}′</span><div><strong>{insight.title}</strong><p>{insight.explanation}</p></div></div><button onClick={() => openProof(insight.insight_id)}>VIEW PROOF · {insight.supporting_event_ids.length} EVENTS <ArrowRight size={14}/></button></article>) : <div className="empty">Verified insights will appear as the replay reaches them.</div>}</div></section>
          <section className="panel"><div className="panel-title"><span>FANDNA / RECAP</span><small>{recap?.provider.replaceAll('_', ' ').toUpperCase() ?? 'LOADING'}</small></div><div className="recap-controls"><label>VIEW <select value={persona} onChange={e => setPersona(e.target.value)}><option value="casual">Casual fan</option><option value="analyst">Tactical analyst</option><option value="favorite_team">Favorite team</option><option value="favorite_player">Favorite player</option><option value="broadcaster">Broadcast producer</option></select></label><label>LANGUAGE <select value={locale} onChange={e => setLocale(e.target.value)}><option value="en">English</option><option value="es">Español</option><option value="hi">हिन्दी</option></select></label></div>{persona === 'favorite_team' && <div className="focus-control"><label>FOLLOW TEAM <select value={favoriteTeamId || match.home.team_id} onChange={e => setFavoriteTeamId(e.target.value)}><option value={match.home.team_id}>{match.home.name}</option><option value={match.away.team_id}>{match.away.name}</option></select></label></div>}{persona === 'favorite_player' && <div className="focus-control"><label>FOLLOW PLAYER <select value={favoritePlayerId || match.home.players[0].player_id} onChange={e => setFavoritePlayerId(e.target.value)}>{[...match.home.players, ...match.away.players].map(player => <option key={player.player_id} value={player.player_id}>{player.name}</option>)}</select></label></div>}<div className="recap-body"><p>{recap?.lead ?? 'Loading event-verified recap…'}</p>{recap?.moments.map(moment => <button key={moment.insight_id} onClick={() => { setSecond(moment.match_second); openProof(moment.insight_id) }}><span>{moment.text}</span><small>{moment.supporting_event_ids.length} SOURCE EVENTS</small></button>)}</div></section>
        </div>
        <section className="studio panel"><div className="panel-title"><span>BROADCAST STUDIO / MACHINE-READABLE CUES</span><label className="cue-toggle"><input type="checkbox" checked={showOverlays} onChange={e => setShowOverlays(e.target.checked)}/> SHOW OVERLAYS</label></div><div className="studio-layout"><div className="studio-screen"><span className="studio-label">PREVIEW · SYNTHETIC FIELD</span>{activeCue ? <div className="studio-lower"><small>{activeCue.overlay_type.toUpperCase()} / {clock(activeCue.start_match_second)}</small><strong>{activeCue.text}</strong><span>{activeCue.overlay_type === 'goal' ? `${activeCue.metrics.score_home} — ${activeCue.metrics.score_away}` : `${activeCue.metrics.momentum_previous} → ${activeCue.metrics.momentum_current} ACTIVITY POINTS`}</span></div> : <div className="studio-idle">CUE STANDBY</div>}<span className="safe-area">SAFE AREA</span></div><div className="studio-queue"><div className="studio-queue-head"><span>UPCOMING / ALL CUES</span><a href={`/api/matches/${matchId}/overlays`} download={`pulse-xi-${matchId}-cues.json`}>EXPORT ALL JSON ↗</a></div>{cues.map(cue => <div key={cue.cue_id} className="cue-entry"><button className={activeCue?.cue_id === cue.cue_id ? 'cue-row active' : 'cue-row'} onClick={() => { setSecond(cue.start_match_second); setPlaying(false) }}><span>{clock(cue.start_match_second)}</span><strong>{cue.text}</strong><small>{cue.show_duration_seconds}s</small></button><a aria-label={`Export ${cue.text} cue JSON`} href={`/api/matches/${matchId}/overlays/${cue.cue_id}`} download={`${cue.cue_id}.json`}>JSON</a></div>)}<p>Rule-scheduled overlays cite source events. No model inference has run.</p></div></div></section>
        {proof && <div className="proof-scrim" onClick={() => setProof(null)}><aside ref={proofDrawer} className="proof-drawer" role="dialog" aria-modal="true" aria-label="Insight evidence" onClick={event => event.stopPropagation()}><button className="proof-close" onClick={() => setProof(null)} aria-label="Close proof">×</button><div className="section-index">PROOFTRAIL / AUDITED EVIDENCE</div><h2>{proof.insight.title}</h2><p>{proof.insight.explanation}</p><div className="proof-verified">✓ {proof.insight.verification_status.replaceAll('_', ' ').toUpperCase()}</div><h3>CALCULATIONS</h3>{proof.insight.factual_claims.map(claim => <div className="proof-row" key={`${claim.metric}-${claim.window_start}`}><span>{claim.metric.replaceAll('_', ' ')} · {clock(claim.window_start)}–{clock(claim.at_second)}</span><strong>{claim.value}</strong></div>)}{proof.insight.comparison_window && <p>Compared with {clock(proof.insight.comparison_window[0])}–{clock(proof.insight.comparison_window[1])}</p>}<h3>SOURCE EVENTS</h3>{proof.source_events.map(event => <button className="proof-event" key={event.event_id} onClick={() => { setSecond(event.match_second); setProof(null) }}><b>{clock(event.match_second)} · {event.type.toUpperCase()}</b><code>{event.event_id}</code><small>{event.outcome}</small></button>)}<p className="proof-note">{proof.insight.data_quality} {proof.insight.uncertainty}</p></aside></div>}
        <footer><span>POWERED BY DETERMINISTIC SYNTHETIC EVENTS</span><span>MODEL INFERENCE: NOT CONFIGURED · RULE-BASED ENGINE</span><span>SCHEMA v1.0</span></footer>
      </>}
    </main>
  </div>
}
