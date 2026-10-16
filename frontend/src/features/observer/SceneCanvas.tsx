import { Component, memo, Suspense, useEffect, useLayoutEffect, useMemo } from 'react'
import type { ReactNode } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { BufferGeometry, Float32BufferAttribute, Vector3 } from 'three'
import type { EventSnapshot } from './eventSnapshot'
import { AssetKit } from './AssetKit'
import type { AssetStatus } from './AssetKit'

export type RendererMetrics = { calls: number; triangles: number; geometries: number; textures: number; readyMs: number; framesInSample: number | null }
type Props = {
  snapshot: EventSnapshot; cameraPreset: 'broadcast' | 'tactical' | 'focus'; resetRevision: number
  quality: 'low' | 'standard'; fail: () => void; report: (value: RendererMetrics) => void; startedAt: number
  assetStyle: 'original' | 'procedural'; assetStatus: AssetStatus['status']; reportAsset: (value: AssetStatus) => void
}

class AssetBoundary extends Component<{ children: ReactNode; fallback: ReactNode; fail: () => void }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch() { this.props.fail() }
  render() { return this.state.failed ? this.props.fallback : this.props.children }
}

function pitchLines() {
  const points: number[] = []
  const segment = (x: number, z: number, x2: number, z2: number) => points.push(x, .06, z, x2, .06, z2)
  const box = (x: number, z: number, width: number, height: number) => {
    segment(x, z, x + width, z); segment(x + width, z, x + width, z + height)
    segment(x + width, z + height, x, z + height); segment(x, z + height, x, z)
  }
  box(-50, -32, 100, 64); segment(0, -32, 0, 32)
  box(-50, -20, 16, 40); box(34, -20, 16, 40)
  box(-50, -9, 5.5, 18); box(44.5, -9, 5.5, 18)
  for (let step = 0; step < 64; step++) {
    const a = step / 64 * Math.PI * 2, b = (step + 1) / 64 * Math.PI * 2
    segment(Math.cos(a) * 9.15, Math.sin(a) * 9.15, Math.cos(b) * 9.15, Math.sin(b) * 9.15)
  }
  return new BufferGeometry().setAttribute('position', new Float32BufferAttribute(points, 3))
}

function Pitch() {
  const lines = useMemo(pitchLines, [])
  useEffect(() => () => lines.dispose(), [lines])
  return <group>
    <mesh position={[0, -.65, 0]}><boxGeometry args={[108, 1.2, 72]}/><meshStandardMaterial color="#122e32"/></mesh>
    <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[100, 64]}/><meshStandardMaterial color="#1b594b" roughness={1}/></mesh>
    {[-45, -25, -5, 15, 35].map(x => <mesh key={x} position={[x, .01, 0]} rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[10, 64]}/><meshStandardMaterial color="#206452" roughness={1}/></mesh>)}
    <lineSegments geometry={lines}><lineBasicMaterial color="#b1d5bf"/></lineSegments>
    {[-50, 50].map(x => <group key={x}>
      {[-3.66, 3.66].map(z => <mesh key={z} position={[x, 1.25, z]}><boxGeometry args={[.3, 2.5, .3]}/><meshStandardMaterial color="#e1e9de"/></mesh>)}
      <mesh position={[x, 2.5, 0]}><boxGeometry args={[.3, .3, 7.62]}/><meshStandardMaterial color="#e1e9de"/></mesh>
    </group>)}
  </group>
}

function EventMarkers({ snapshot, spheres = true }: { snapshot: EventSnapshot; spheres?: boolean }) {
  const path = useMemo(() => snapshot.origin && snapshot.target ? new BufferGeometry().setFromPoints([
    new Vector3(...snapshot.origin), new Vector3(...snapshot.target),
  ]) : null, [snapshot.origin, snapshot.target])
  useEffect(() => () => path?.dispose(), [path])
  return <group>
    {spheres && snapshot.origin && <mesh position={snapshot.origin}><sphereGeometry args={[1.1, 16, 10]}/><meshStandardMaterial color={snapshot.color} emissive={snapshot.color} emissiveIntensity={.2}/></mesh>}
    {spheres && snapshot.target && <mesh position={snapshot.target}><sphereGeometry args={[.65, 12, 8]}/><meshStandardMaterial color="#f4f2db"/></mesh>}
    {path && <lineSegments geometry={path}><lineBasicMaterial color={snapshot.color}/></lineSegments>}
  </group>
}

function Camera({ snapshot, cameraPreset, resetRevision }: Pick<Props, 'snapshot' | 'cameraPreset' | 'resetRevision'>) {
  const { camera, invalidate } = useThree()
  useLayoutEffect(() => {
    camera.up.set(0, 1, 0)
    if (cameraPreset === 'tactical') { camera.position.set(0, 110, .01); camera.up.set(0, 0, -1); camera.lookAt(0, 0, 0) }
    else if (cameraPreset === 'focus' && snapshot.origin) {
      camera.position.set(snapshot.origin[0] + 25, 32, snapshot.origin[2] + 30)
      camera.lookAt(...snapshot.origin)
    } else { camera.position.set(72, 65, 82); camera.lookAt(0, 0, 0) }
    camera.updateProjectionMatrix(); invalidate()
  }, [camera, cameraPreset, resetRevision, snapshot.origin, invalidate])
  return null
}

function Probe({ snapshot, cameraPreset, quality, report, startedAt, assetStatus }: Props) {
  const { gl, invalidate } = useThree()
  useEffect(() => {
    let second = 0
    let timer = 0
    invalidate()
    const first = requestAnimationFrame(() => { second = requestAnimationFrame(() => {
      const metrics = { calls: gl.info.render.calls, triangles: gl.info.render.triangles,
        geometries: gl.info.memory.geometries, textures: gl.info.memory.textures,
        readyMs: performance.now() - startedAt, framesInSample: null }
      report(metrics)
      const before = gl.info.render.frame
      timer = window.setTimeout(() => report({ ...metrics, framesInSample: gl.info.render.frame - before }), 500)
    }) })
    return () => { cancelAnimationFrame(first); cancelAnimationFrame(second); window.clearTimeout(timer) }
  }, [snapshot.event_id, cameraPreset, quality, assetStatus, gl, invalidate, report, startedAt])
  return null
}

export default memo(function SceneCanvas(props: Props) {
  return <div className="observer-canvas" data-testid="observer-canvas" data-camera={props.cameraPreset} data-quality={props.quality}>
    <Canvas key={props.quality} frameloop="demand" dpr={props.quality === 'low' ? 1 : [1, 1.5]} camera={{ fov: 48, near: .1, far: 500 }} gl={{ antialias: props.quality !== 'low', powerPreference: 'low-power', alpha: false }} fallback={<p>WebGL is unavailable. Select 2D pitch.</p>}>
      <color attach="background" args={['#08191f']}/><hemisphereLight args={['#d1f3e6', '#1b323b', 2]}/><directionalLight position={[20, 50, 15]} intensity={2}/>
      {props.assetStyle === 'original' ? <AssetBoundary fail={() => props.reportAsset({ status: 'fallback' })} fallback={<><Pitch/><EventMarkers snapshot={props.snapshot}/></>}>
        <Suspense fallback={<><Pitch/><EventMarkers snapshot={props.snapshot}/></>}><AssetKit snapshot={props.snapshot} lowPower={props.quality === 'low'} report={props.reportAsset}/><EventMarkers snapshot={props.snapshot} spheres={false}/></Suspense>
      </AssetBoundary> : <><Pitch/><EventMarkers snapshot={props.snapshot}/></>}
      <Camera {...props}/><Probe {...props}/>
    </Canvas>
  </div>
})
