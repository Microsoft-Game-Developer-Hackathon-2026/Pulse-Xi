import { Component, lazy, Suspense, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { Event, Match } from '../../types'
import { eventSnapshot } from './eventSnapshot'
import { EventOverlay } from './EventOverlay'
import type { ObserverScope } from './eventSnapshot'
import type { RendererMetrics } from './SceneCanvas'
import type { AssetStatus } from './AssetKit'
import { graphicsProfiles } from './graphicsProfiles'
import type { CameraPreset, GraphicsQuality } from './graphicsProfiles'
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

export function ObserverSwitch({ match, event, atSecond, scope, children, preferredView, preferredQuality, onViewChange, onQualityChange, apiBase, load }: {
  apiBase?: string; load?: <T>(path: string, signal: AbortSignal) => Promise<T>;
  match: Match; event?: Event; atSecond: number; scope?: ObserverScope; children: ReactNode;
  preferredView?: '2d' | '3d'; preferredQuality?: GraphicsQuality; onViewChange?: (view: '2d' | '3d') => void; onQualityChange?: (quality: GraphicsQuality) => void
}) {
  const [open, setOpen] = useState(false)
  const [failure, setFailure] = useState('')
  const [camera, setCamera] = useState<CameraPreset>('broadcast')
  const [revision, setRevision] = useState(0)
  const [quality, setQuality] = useState<GraphicsQuality>(() =>
    window.matchMedia('(prefers-reduced-motion: reduce), (max-width: 700px)').matches ? 'low' : 'standard')
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const [metrics, setMetrics] = useState<RendererMetrics | null>(null)
  const [assetStyle, setAssetStyle] = useState<'original' | 'procedural'>('original')
  const [asset, setAsset] = useState<AssetStatus>({ status: 'loading' })
  const assetActivation = useRef(0)
  const started = useRef(0)
  const container = useRef<HTMLElement>(null)
  const snapshot = useMemo(() => eventSnapshot(match, event, atSecond, scope),
    [match, event, atSecond, scope])
  const fail = useCallback(() => { setFailure('The 3D renderer is unavailable. The recorded 2D pitch remains active.'); setOpen(false); onViewChange?.('2d') }, [onViewChange])
  useLayoutEffect(() => {
    const element = container.current
    const lost = (event: globalThis.Event) => { event.preventDefault(); fail() }
    // Capture on the stable parent, including the gap while a quality change
    // replaces the canvas before the new R3F effects have mounted.
    element?.addEventListener('webglcontextlost', lost, true)
    return () => element?.removeEventListener('webglcontextlost', lost, true)
  }, [fail])
  const report = useCallback((value: RendererMetrics) => setMetrics(prior => ({ ...value, readyMs: prior?.readyMs ?? value.readyMs })), [])
  const reportAsset = useCallback((value: AssetStatus) => {
    const changed = assetActivation.current !== started.current
    assetActivation.current = started.current
    setAsset(prior => ({ ...value, readyMs: (changed ? undefined : prior.readyMs) ??
      (value.status === 'ready' ? performance.now() - started.current : undefined) }))
  }, [])
  const enable = () => {
    setFailure('')
    if (!supportsWebGL2()) { setFailure('WebGL2 is unavailable. The recorded 2D pitch remains active.'); onViewChange?.('2d'); return }
    started.current = performance.now(); setMetrics(null); setOpen(true); onViewChange?.('3d')
  }
  useEffect(() => { if (preferredQuality) setQuality(preferredQuality) }, [preferredQuality])
  useEffect(() => { if (preferredView === '3d' && !open) enable(); else if (preferredView === '2d') setOpen(false) }, [preferredView])

  return <section ref={container} className="observer" aria-label="Football pitch observer">
    <div className="observer-bar"><div><strong>EVENT OBSERVER</strong><span>RECORDED SNAPSHOTS · NO CONTINUOUS TRACKING</span></div><div className="observer-view"><button aria-pressed={!open} onClick={() => { setOpen(false); onViewChange?.('2d') }}>2D pitch</button><button aria-pressed={open} onClick={enable}>3D observer</button></div></div>
    {failure && <p className="observer-notice" role="status">{failure}</p>}
    {!open ? children : <>
      <div className="observer-controls" aria-label="3D camera controls">
        <label>SCENE STYLE <select value={assetStyle} onChange={event => { setAssetStyle(event.target.value as 'original' | 'procedural'); setAsset({ status: 'loading' }); started.current = performance.now() }}><option value="original">Original Blender kit</option><option value="procedural">Procedural fallback</option></select></label>
        <button aria-pressed={camera === 'broadcast'} onClick={() => setCamera('broadcast')}>Broadcast camera</button>
        <button aria-pressed={camera === 'tactical'} onClick={() => setCamera('tactical')}>Top-down camera</button>
        <button aria-pressed={camera === 'isometric'} onClick={() => setCamera('isometric')}>Isometric camera</button>
        <button aria-pressed={camera === 'free'} onClick={() => setCamera('free')}>Free camera</button>
        <button disabled={!snapshot.origin} aria-pressed={camera === 'focus'} onClick={() => setCamera('focus')}>Focus event</button>
        <button onClick={() => { setCamera('broadcast'); setRevision(value => value + 1) }}>Reset camera</button>
        <label>3D QUALITY <select value={quality} onChange={event => { setQuality(event.target.value as GraphicsQuality); onQualityChange?.(event.target.value as GraphicsQuality) }}>{Object.entries(graphicsProfiles).map(([id, profile]) => <option key={id} value={id}>{profile.label}</option>)}</select></label>
      </div>
      <RenderBoundary key={revision} fail={fail}><Suspense fallback={<><p className="observer-notice" role="status">Loading optional 3D renderer…</p>{children}</>}>
        <SceneCanvas snapshot={snapshot} reducedMotion={reducedMotion} cameraPreset={camera} resetRevision={revision} quality={quality} fail={fail} report={report} startedAt={started.current} assetStyle={assetStyle} assetStatus={asset.status} reportAsset={reportAsset}/>
      </Suspense></RenderBoundary>
      <p className="observer-notice" data-testid="asset-status" data-status={assetStyle === 'procedural' ? 'procedural' : asset.status} data-surface-size={JSON.stringify(asset.surfaceSize)}>{assetStyle === 'procedural' ? 'Procedural field selected.' : asset.status === 'ready' ? `Original Blender geometry loaded in ${asset.readyMs?.toFixed(1)} ms.` : asset.status === 'fallback' ? 'Original assets unavailable; procedural geometry remains active.' : 'Loading original assets; procedural pitch remains available.'}</p>
      <EventOverlay match={match} event={event} snapshot={snapshot} apiBase={apiBase} load={load}/>
      <div className="observer-caption" data-testid="observer-snapshot" data-event-id={snapshot.event_id ?? ''}><span>{snapshot.team_name ? `${snapshot.team_name} attacking frame` : 'Recorded event frame'} · {snapshot.event_type ?? 'no event'} · {Math.floor(atSecond / 60)}:{String(Math.floor(atSecond % 60)).padStart(2, '0')}</span><code>{snapshot.event_id ?? 'No visible source event'}</code></div>
      {snapshot.unavailable_reason && <p className="observer-notice">{snapshot.unavailable_reason}</p>}
      <p className="observer-note">{camera === 'free' && 'Free camera: drag to orbit, scroll/pinch to zoom; focus the canvas and use arrow keys to pan. '}Markers show recorded origins and endpoints only. The ball is enlarged for readability; model height is illustrative. Display units are schematic; no player movement, speed, defender location or live ball trajectory is inferred.</p>
      <details className="observer-diagnostics"><summary>Renderer diagnostics and provenance</summary><output data-testid="observer-metrics" data-quality={metrics?.quality} data-event-id={metrics?.eventId ?? ''} data-sampled={metrics?.framesInSample !== null && metrics !== null} data-origin={JSON.stringify(snapshot.origin)} data-target={JSON.stringify(snapshot.target)}>{metrics ? `${metrics.calls} draw calls · ${metrics.triangles} triangles · ${metrics.geometries} geometries · ${metrics.textures} textures · first ready ${metrics.readyMs.toFixed(1)} ms · frames in 500 ms sample: ${metrics.framesInSample ?? 'sampling'}` : 'Renderer initializing'}</output><p>{snapshot.provenance} · match {snapshot.scope.match_id}{snapshot.scope.branch_id ? ` · branch ${snapshot.scope.branch_id}` : ''}. No observer-frame stream is connected.</p></details>
    </>}
  </section>
}
