import { useEffect, useMemo, useRef, useState } from 'react'

type Source = { event_id: string; sequence: number; match_second: number; type: string; team_id: string | null; outcome: string | null; start: { x: number; y: number } | null; end: { x: number; y: number } | null }
type Clip = { clip_id: string; insight_id: string; category: string; match_second: number; team_id: string | null; title: string; caption: string; uncertainty: string; score_before: { home: number; away: number }; score_after: { home: number; away: number }; verification_status: string; source_events: Source[]; duration_seconds: number }
type Team = { team_id: string; name: string; color: string }
export type HighlightManifest = { schema_version: string; match_id: string; title: string; seed: number; home: Team; away: Team; video: { width: number; height: number; fps: number; intro_seconds: number; outro_seconds: number; total_seconds: number }; clips: Clip[]; provenance: { footage: string }; manifest_sha256: string }

const clock = (second: number) => `${String(Math.floor(second / 60)).padStart(2, '0')}:${String(second % 60).padStart(2, '0')}`
const ease = (value: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, value)), 3)

/** Standalone, frame-addressable player for a highlight manifest. `?t=` pins the timeline so any
 * frame is reproducible; without it the reel plays in real time and marks `data-state="complete"`. */
export default function HighlightReel() {
  const query = new URLSearchParams(window.location.hash.split('?')[1] ?? '')
  const matchId = query.get('match') ?? 'comeback-1107'
  const pinned = query.has('t') ? Number(query.get('t')) : null
  const rendering = query.get('render') === '1'
  const [manifest, setManifest] = useState<HighlightManifest | null>(null)
  const [error, setError] = useState('')
  const [now, setNow] = useState(pinned ?? 0)
  const [paused, setPaused] = useState(false)
  const nowRef = useRef(now)
  nowRef.current = now
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/matches/${encodeURIComponent(matchId)}/highlights`, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error(`Highlights unavailable (${response.status})`); return response.json() as Promise<HighlightManifest> })
      .then(setManifest).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Highlights unavailable') })
    return () => controller.abort()
  }, [matchId])
  const total = manifest?.video.total_seconds ?? 0
  useEffect(() => {
    if (!manifest || pinned !== null || paused) return
    let frame = 0
    const origin = performance.now() - nowRef.current * 1000
    const tick = () => {
      const elapsed = (performance.now() - origin) / 1000
      setNow(Math.min(total, elapsed))
      if (elapsed < total) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [manifest, pinned, paused, total])

  const clipSeconds = manifest?.clips[0]?.duration_seconds ?? 6
  const layout = useMemo(() => {
    if (!manifest) return null
    const { intro_seconds: intro, outro_seconds: outro } = manifest.video
    if (now < intro) return { kind: 'intro' as const, local: now }
    if (now < intro + manifest.clips.length * clipSeconds) {
      const index = Math.floor((now - intro) / clipSeconds)
      return { kind: 'clip' as const, clip: manifest.clips[index], index, local: now - intro - index * clipSeconds }
    }
    return { kind: 'outro' as const, local: now - (total - outro) }
  }, [manifest, now, total, clipSeconds])

  if (error) return <main className="reel" role="alert"><p>{error}</p></main>
  if (!manifest || !layout) return <main className="reel" role="status"><p>Loading highlight manifest…</p></main>
  const done = now >= total
  const finalScore = manifest.clips.at(-1)?.score_after ?? { home: 0, away: 0 }
  const clip = layout.kind === 'clip' ? layout.clip : null
  const score = clip ? (layout.local < 1.6 ? clip.score_before : clip.score_after) : layout.kind === 'outro' ? finalScore : { home: 0, away: 0 }
  const label = clip ? `${clip.title} at ${clock(clip.match_second)}. Score ${score.home} to ${score.away}.` : layout.kind === 'intro' ? `${manifest.title} highlights` : 'End of highlights'
  const fade = layout.kind === 'clip' ? Math.min(ease(layout.local / 0.5), ease((clipSeconds - layout.local) / 0.5)) : ease(layout.local / 0.6)

  return <main className="reel" data-state={done ? 'complete' : 'playing'} data-manifest={manifest.manifest_sha256} data-time={now.toFixed(2)} aria-label="Highlight reel">
    <style>{css}</style>
    <div className="reel-stage" role="img" aria-label={label} style={{ width: manifest.video.width, height: manifest.video.height }}>
      <header>
        <span className="reel-team" style={{ borderColor: manifest.home.color }}>{manifest.home.name}</span>
        <strong className="reel-score">{score.home}<i>:</i>{score.away}</strong>
        <span className="reel-team" style={{ borderColor: manifest.away.color }}>{manifest.away.name}</span>
      </header>
      <section style={{ opacity: fade }}>
        {layout.kind === 'intro' && <div className="reel-card"><small>SYNTHETIC MATCH · EVENT-DERIVED HIGHLIGHTS</small><h1>{manifest.title}</h1><p>{manifest.clips.length} verified moments · seed {manifest.seed} · no match footage</p></div>}
        {layout.kind === 'clip' && <>
          <Pitch clip={layout.clip} local={layout.local} manifest={manifest} />
          <div className="reel-lower">
            <small>{clock(layout.clip.match_second)} · {layout.clip.category.replace('_', ' ').toUpperCase()} · CLIP {layout.index + 1}/{manifest.clips.length}</small>
            <h2>{layout.clip.title}</h2><p>{layout.clip.caption}</p>
            <small className="reel-evidence">{layout.clip.verification_status.replaceAll('_', ' ').toUpperCase()} · {layout.clip.source_events.length} source events: {layout.clip.source_events.map(source => `${source.type} ${clock(source.match_second)}`).join(' · ')}</small>
          </div></>}
        {layout.kind === 'outro' && <div className="reel-card"><small>SCORE AFTER THE LAST HIGHLIGHTED MOMENT</small><h1>{finalScore.home}–{finalScore.away}</h1><p>Every caption cites source events · manifest {manifest.manifest_sha256.slice(0, 12)}</p></div>}
      </section>
    </div>
    {!rendering && <nav className="reel-controls" aria-label="Highlight reel controls">
      <button onClick={() => setPaused(value => !value)} disabled={pinned !== null || done}>{paused ? 'Resume' : 'Pause'}</button>
      <a href={`/api/matches/${encodeURIComponent(matchId)}/highlights`} download={`pulse-xi-${matchId}-highlights.json`}>Download manifest JSON</a>
      <a href="#/">Back to PULSE XI</a>
    </nav>}
  </main>
}

function Pitch({ clip, local, manifest }: { clip: Clip; local: number; manifest: HighlightManifest }) {
  const colorFor = (teamId: string | null) => (teamId === manifest.home.team_id ? manifest.home.color : teamId === manifest.away.team_id ? manifest.away.color : '#b6e4d5')
  return <svg className="reel-pitch" viewBox="0 0 100 64" aria-hidden="true">
    <rect x="0" y="0" width="100" height="64" rx="1.2" fill="#10201c" />
    <rect x="0.5" y="0.5" width="99" height="63" fill="none" stroke="#ffffff30" strokeWidth=".3" />
    <line x1="50" y1="0.5" x2="50" y2="63.5" stroke="#ffffff30" strokeWidth=".3" />
    <circle cx="50" cy="32" r="8" fill="none" stroke="#ffffff30" strokeWidth=".3" />
    {clip.source_events.map((source, index) => {
      const reveal = ease((local - (0.6 + index * 0.5)) / 0.5)
      const start = source.start; const end = source.end ?? source.start
      if (reveal <= 0 || !start || !end) return null
      const color = colorFor(source.team_id)
      return <g key={source.event_id} opacity={reveal}>
        {source.end && <line x1={start.x} y1={start.y * .64} x2={start.x + (end.x - start.x) * reveal} y2={start.y * .64 + (end.y - start.y) * .64 * reveal} stroke={color} strokeWidth=".7" strokeLinecap="round" />}
        <circle cx={end.x} cy={end.y * .64} r={source.type === 'goal' || source.type === 'shot' ? 1.6 : 1.1} fill={color} />
      </g>
    })}
    <text x="2" y="62" fontSize="2.2" fill="#ffffff80">normalized event coordinates · markers are recorded events, not tracking</text>
  </svg>
}

const css = `
.reel{min-height:100vh;display:grid;place-items:center;background:#0b0d0e;color:#f5f4ef;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;margin:0}
.reel-stage{position:relative;overflow:hidden;background:radial-gradient(1200px 600px at 30% 0%,#17302b 0%,#0e1112 60%);display:grid;grid-template-rows:96px 1fr;font-variant-numeric:tabular-nums}
.reel-stage header{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:32px;padding:0 56px;border-bottom:1px solid #ffffff14}
.reel-team{font-size:28px;font-weight:600;border-bottom:4px solid;padding-bottom:6px;width:max-content}
.reel-stage header .reel-team:last-child{justify-self:end}
.reel-score{font-size:56px;font-weight:600;letter-spacing:-1px}.reel-score i{opacity:.4;font-style:normal;padding:0 12px}
.reel-stage section{display:grid;align-content:center;padding:24px 56px 32px;gap:20px}
.reel-card{text-align:center}.reel-card h1{font-size:72px;margin:12px 0;letter-spacing:-2px}.reel-card p{font-size:24px;color:#b7babe}.reel-card small,.reel-lower small{font-size:15px;letter-spacing:1.5px;color:#b6e4d5}
.reel-pitch{width:100%;max-height:330px;border-radius:18px}
.reel-lower{background:#202426f0;border:1px solid #ffffff1f;border-radius:22px;padding:22px 28px;display:grid;gap:8px}
.reel-lower h2{font-size:40px;margin:0;letter-spacing:-1px}.reel-lower p{font-size:22px;margin:0;color:#e7e6e0}.reel-lower .reel-evidence{color:#efcda7;font-size:14px;letter-spacing:.4px}
.reel-controls{position:fixed;bottom:12px;left:50%;transform:translateX(-50%);display:flex;gap:16px;background:#202426f0;border:1px solid #ffffff30;padding:8px 16px;border-radius:999px}
.reel-controls button,.reel-controls a{color:#f5f4ef;background:none;border:0;font:inherit;font-size:14px;text-decoration:underline;cursor:pointer;padding:6px 4px}.reel-controls button:disabled{opacity:.5;cursor:default}
`
