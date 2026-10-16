import { Component, lazy, Suspense, useCallback, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { Event, Match } from '../../types'
import { eventSnapshot } from './eventSnapshot'
import type { ObserverScope } from './eventSnapshot'
import type { RendererMetrics } from './SceneCanvas'
import './observer.css'

const SceneCanvas = lazy(() => import('./SceneCanvas'))

class RenderBoundary extends Component<{ children: ReactNode; fail: () => void }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch() { this.props.fail() }
  render() { return this.state.failed ? null : this.props.children }
}

function supportsWebGL2() {
  try {
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('webgl2')
    if (!context) return false
    context.getExtension('WEBGL_lose_context')?.loseContext()
    return true
  } catch { return false }
}

export function ObserverSwitch({ match, event, atSecond, scope, children }: {
  match: Match; event?: Event; atSecond: number; scope?: ObserverScope; children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  const [failure, setFailure] = useState('')
  const [camera, setCamera] = useState<'broadcast' | 'tactical' | 'focus'>('broadcast')
  const [revision, setRevision] = useState(0)
  const [quality, setQuality] = useState<'low' | 'standard'>(() =>
    window.matchMedia('(prefers-reduced-motion: reduce), (max-width: 700px)').matches ? 'low' : 'standard')
  const [metrics, setMetrics] = useState<RendererMetrics | null>(null)
  const started = useRef(0)
  const snapshot = useMemo(() => eventSnapshot(match, event, atSecond, scope),
    [match, event, atSecond, scope])
  const fail = useCallback(() => { setFailure('The 3D renderer is unavailable. The recorded 2D pitch remains active.'); setOpen(false) }, [])
  const report = useCallback((value: RendererMetrics) => setMetrics(prior => ({ ...value, readyMs: prior?.readyMs ?? value.readyMs })), [])
  const enable = () => {
    setFailure('')
    if (!supportsWebGL2()) { setFailure('WebGL2 is unavailable. The recorded 2D pitch remains active.'); return }
    started.current = performance.now(); setMetrics(null); setOpen(true)
  }

  return <section className="observer" aria-label="Football pitch observer">
    <div className="observer-bar"><div><strong>EVENT OBSERVER</strong><span>RECORDED SNAPSHOTS · NO CONTINUOUS TRACKING</span></div><div className="observer-view"><button aria-pressed={!open} onClick={() => setOpen(false)}>2D pitch</button><button aria-pressed={open} onClick={enable}>3D observer</button></div></div>
    {failure && <p className="observer-notice" role="status">{failure}</p>}
    {!open ? children : <>
      <div className="observer-controls" aria-label="3D camera controls">
        <button aria-pressed={camera === 'broadcast'} onClick={() => setCamera('broadcast')}>Broadcast camera</button>
        <button aria-pressed={camera === 'tactical'} onClick={() => setCamera('tactical')}>Top-down camera</button>
        <button disabled={!snapshot.origin} aria-pressed={camera === 'focus'} onClick={() => setCamera('focus')}>Focus event</button>
        <button onClick={() => { setCamera('broadcast'); setRevision(value => value + 1) }}>Reset camera</button>
        <label>3D QUALITY <select value={quality} onChange={event => setQuality(event.target.value as 'low' | 'standard')}><option value="low">Low power</option><option value="standard">Standard</option></select></label>
      </div>
      <RenderBoundary key={revision} fail={fail}><Suspense fallback={<><p className="observer-notice" role="status">Loading optional 3D renderer…</p>{children}</>}>
        <SceneCanvas snapshot={snapshot} cameraPreset={camera} resetRevision={revision} quality={quality} fail={fail} report={report} startedAt={started.current}/>
      </Suspense></RenderBoundary>
      <div className="observer-caption" data-testid="observer-snapshot" data-event-id={snapshot.event_id ?? ''}><span>{snapshot.team_name ? `${snapshot.team_name} attacking frame` : 'Recorded event frame'} · {snapshot.event_type ?? 'no event'} · {Math.floor(atSecond / 60)}:{String(Math.floor(atSecond % 60)).padStart(2, '0')}</span><code>{snapshot.event_id ?? 'No visible source event'}</code></div>
      {snapshot.unavailable_reason && <p className="observer-notice">{snapshot.unavailable_reason}</p>}
      <p className="observer-note">Markers show recorded origins and endpoints only. Display units are schematic; no player movement, speed, defender location or live ball trajectory is inferred.</p>
      <details className="observer-diagnostics"><summary>Renderer diagnostics and provenance</summary><output data-testid="observer-metrics" data-sampled={metrics?.framesInSample !== null && metrics !== null} data-origin={JSON.stringify(snapshot.origin)} data-target={JSON.stringify(snapshot.target)}>{metrics ? `${metrics.calls} draw calls · ${metrics.triangles} triangles · ${metrics.geometries} geometries · ${metrics.textures} textures · first ready ${metrics.readyMs.toFixed(1)} ms · frames in 500 ms sample: ${metrics.framesInSample ?? 'sampling'}` : 'Renderer initializing'}</output><p>{snapshot.provenance} · match {snapshot.scope.match_id}{snapshot.scope.branch_id ? ` · branch ${snapshot.scope.branch_id}` : ''}. No observer-frame stream is connected.</p></details>
    </>}
  </section>
}
