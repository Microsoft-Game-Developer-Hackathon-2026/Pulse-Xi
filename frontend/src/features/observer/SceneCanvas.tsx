import { memo, useEffect, useMemo, useState } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { ACESFilmicToneMapping, BufferGeometry, Float32BufferAttribute, Quaternion, SRGBColorSpace, Vector3 } from 'three'
import type { EventSnapshot } from './eventSnapshot'
import { CameraRig } from './CameraRig'
import { Stadium } from './Stadium'
import { createGrassTexture } from './grassTexture'
import { graphicsProfiles } from './graphicsProfiles'
import type { CameraPreset, GraphicsQuality } from './graphicsProfiles'

export type RendererMetrics = { quality: GraphicsQuality; eventId: string | null; calls: number; triangles: number; geometries: number; textures: number; readyMs: number; framesInSample: number | null }
type Props = {
  snapshot: EventSnapshot; cameraPreset: CameraPreset; resetRevision: number
  quality: GraphicsQuality; reducedMotion: boolean; fail: () => void; report: (value: RendererMetrics) => void; startedAt: number
}

function pitchLines() {
  const points: number[] = []
  const segment = (x: number, z: number, x2: number, z2: number) => points.push(x * 100 / 105, .06, z * 64 / 68, x2 * 100 / 105, .06, z2 * 64 / 68)
  const box = (x: number, z: number, width: number, height: number) => {
    segment(x, z, x + width, z); segment(x + width, z, x + width, z + height)
    segment(x + width, z + height, x, z + height); segment(x, z + height, x, z)
  }
  box(-52.5, -34, 105, 68); segment(0, -34, 0, 34)
  box(-52.5, -20.16, 16.5, 40.32); box(36, -20.16, 16.5, 40.32)
  box(-52.5, -9.16, 5.5, 18.32); box(47, -9.16, 5.5, 18.32)
  for (let step = 0; step < 64; step++) {
    const a = step / 64 * Math.PI * 2, b = (step + 1) / 64 * Math.PI * 2
    segment(Math.cos(a) * 9.15, Math.sin(a) * 9.15, Math.cos(b) * 9.15, Math.sin(b) * 9.15)
  }
  for (const side of [-1, 1]) {
    const limit = Math.acos(5.5 / 9.15)
    for (let i = 0; i < 32; i++) {
      const a = -limit + i / 32 * limit * 2, b = -limit + (i + 1) / 32 * limit * 2
      segment(side * (41.5 - 9.15 * Math.cos(a)), 9.15 * Math.sin(a), side * (41.5 - 9.15 * Math.cos(b)), 9.15 * Math.sin(b))
    }
    segment(side * 41.5 - .15, 0, side * 41.5 + .15, 0)
    for (const end of [-1, 1]) for (let i = 0; i < 12; i++) {
      const a = i / 12 * Math.PI / 2, b = (i + 1) / 12 * Math.PI / 2
      segment(side * (52.5 - Math.cos(a)), end * (34 - Math.sin(a)), side * (52.5 - Math.cos(b)), end * (34 - Math.sin(b)))
    }
  }
  return new BufferGeometry().setAttribute('position', new Float32BufferAttribute(points, 3))
}

function Pitch({ quality }: { quality: GraphicsQuality }) {
  const grass = useMemo(createGrassTexture, [])
  useEffect(() => () => grass.dispose(), [grass])
  const lines = useMemo(pitchLines, [])
  useEffect(() => () => lines.dispose(), [lines])
  return <group>
    <mesh position={[0, -.65, 0]}><boxGeometry args={[108, 1.2, 72]}/><meshStandardMaterial color="#122e32"/></mesh>
    <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[100, 64]}/><meshStandardMaterial color={quality === 'low' ? '#1b594b' : '#ffffff'} map={quality === 'low' ? null : grass} roughness={.95}/></mesh>
    {[-45, -25, -5, 15, 35].map(x => <mesh key={x} position={[x, .01, 0]} rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[10, 64]}/><meshStandardMaterial color="#507c4d" transparent opacity={.18} roughness={1}/></mesh>)}
    <lineSegments geometry={lines}><lineBasicMaterial color="#b1d5bf"/></lineSegments>
    {[-50, 50].map(x => <group key={x}>
      {[-3.66, 3.66].map(z => <mesh key={z} position={[x, 1.25, z]}><boxGeometry args={[.3, 2.5, .3]}/><meshStandardMaterial color="#e1e9de"/></mesh>)}
      <mesh position={[x, 2.5, 0]}><boxGeometry args={[.3, .3, 7.62]}/><meshStandardMaterial color="#e1e9de"/></mesh>
    </group>)}
  </group>
}

function EventMarkers({ snapshot }: { snapshot: EventSnapshot }) {
  const arrow = useMemo(() => {
    if (!snapshot.origin || !snapshot.target) return null
    const direction = new Vector3(...snapshot.target).sub(new Vector3(...snapshot.origin))
    return direction.lengthSq() > .01 ? { rotation: new Quaternion().setFromUnitVectors(new Vector3(0, 1, 0), direction.normalize()), position: new Vector3(...snapshot.target).addScaledVector(direction, -1.8) } : null
  }, [snapshot.origin, snapshot.target])
  const path = useMemo(() => snapshot.origin && snapshot.target ? new BufferGeometry().setFromPoints([
    new Vector3(...snapshot.origin), new Vector3(...snapshot.target),
  ]) : null, [snapshot.origin, snapshot.target])
  useEffect(() => () => path?.dispose(), [path])
  return <group>
    {snapshot.origin && <mesh position={snapshot.origin}><sphereGeometry args={[1.1, 16, 10]}/><meshStandardMaterial color={snapshot.color} emissive={snapshot.color} emissiveIntensity={.2}/></mesh>}
    {snapshot.target && <mesh position={snapshot.target}><sphereGeometry args={[.65, 12, 8]}/><meshStandardMaterial color="#f4f2db"/></mesh>}
    {snapshot.origin && <mesh position={[snapshot.origin[0], .12, snapshot.origin[2]]} rotation={[-Math.PI / 2, 0, 0]}><ringGeometry args={[1.8, 2.15, 40]}/><meshBasicMaterial color={snapshot.color} toneMapped={false}/></mesh>}
    {snapshot.target && arrow && <mesh position={arrow.position} quaternion={arrow.rotation}><coneGeometry args={[.8, 2.1, 12]}/><meshBasicMaterial color={snapshot.color} toneMapped={false}/></mesh>}
    {path && <lineSegments geometry={path}><lineBasicMaterial color={snapshot.color}/></lineSegments>}
  </group>
}

function Probe({ snapshot, cameraPreset, quality, report, startedAt }: Props) {
  const { gl, invalidate } = useThree()
  useEffect(() => {
    let second = 0
    let timer = 0
    invalidate()
    const first = requestAnimationFrame(() => { second = requestAnimationFrame(() => {
      const metrics = { quality, eventId: snapshot.event_id, calls: gl.info.render.calls, triangles: gl.info.render.triangles,
        geometries: gl.info.memory.geometries, textures: gl.info.memory.textures,
        readyMs: performance.now() - startedAt, framesInSample: null }
      report(metrics)
      const before = gl.info.render.frame
      timer = window.setTimeout(() => report({ ...metrics, framesInSample: gl.info.render.frame - before }), 500)
    }) })
    return () => { cancelAnimationFrame(first); cancelAnimationFrame(second); window.clearTimeout(timer) }
  }, [snapshot.event_id, cameraPreset, quality, gl, invalidate, report, startedAt])
  return null
}

export default memo(function SceneCanvas(props: Props) {
  const profile = graphicsProfiles[props.quality]
  const [cameraSettled, setCameraSettled] = useState(false)
  return <div className="observer-canvas" data-testid="observer-canvas" data-camera={props.cameraPreset} data-quality={props.quality} data-camera-settled={cameraSettled}>
    <Canvas shadows={profile.shadows} frameloop="demand" dpr={profile.dpr} camera={{ fov: 48, near: .5, far: 350 }} gl={{ antialias: props.quality !== 'low', powerPreference: 'low-power', alpha: false, toneMapping: ACESFilmicToneMapping, toneMappingExposure: profile.exposure, outputColorSpace: SRGBColorSpace }} fallback={<p>WebGL is unavailable. Select 2D pitch.</p>}>
      <color attach="background" args={['#101d29']}/><fog attach="fog" args={['#101d29', 150, 340]}/><hemisphereLight args={['#d1e7f4', '#25312a', 2.2]}/><directionalLight position={[-25, 70, 25]} intensity={3} color="#fff1d9" castShadow={profile.shadows} shadow-mapSize={[profile.shadowSize, profile.shadowSize]} shadow-camera-left={-80} shadow-camera-right={80} shadow-camera-top={65} shadow-camera-bottom={-65} shadow-camera-far={160} shadow-bias={-.0003}/>
      <Pitch quality={props.quality}/><Stadium quality={props.quality}/><EventMarkers snapshot={props.snapshot}/><CameraRig {...props} onSettled={setCameraSettled}/><Probe {...props}/>
    </Canvas>
  </div>
})
