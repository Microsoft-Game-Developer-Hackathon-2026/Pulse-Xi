import { useEffect, useLayoutEffect, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Vector3 } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import type { EventSnapshot } from './eventSnapshot'
import type { CameraPreset } from './graphicsProfiles'

export function CameraRig({ snapshot, cameraPreset, resetRevision, reducedMotion }: {
  snapshot: EventSnapshot; cameraPreset: CameraPreset; resetRevision: number; reducedMotion: boolean
}) {
  const { camera, gl, invalidate, size } = useThree()
  const target = useRef(new Vector3())
  const mounted = useRef(false)
  const transition = useRef<{ start: number; from: Vector3; to: Vector3; fromTarget: Vector3; toTarget: Vector3 } | null>(null)
  const originX = snapshot.origin?.[0], originZ = snapshot.origin?.[2]
  const targetX = snapshot.target?.[0], targetZ = snapshot.target?.[2]
  useLayoutEffect(() => {
    if (cameraPreset === 'free') { transition.current = null; return }
    const look = new Vector3()
    const distance = Math.max(1, Math.min(1.6, 1.55 / (size.width / size.height)))
    let position = new Vector3(0, 72, 94).multiplyScalar(distance)
    if (cameraPreset === 'tactical') position = new Vector3(0, 125 * distance, .01)
    if (cameraPreset === 'isometric') position = new Vector3(78, 78, 78).multiplyScalar(distance)
    if (cameraPreset === 'focus' && originX !== undefined && originZ !== undefined) {
      look.set((originX + (targetX ?? originX)) / 2, 0, (originZ + (targetZ ?? originZ)) / 2)
      const extent = Math.max(22, Math.hypot((targetX ?? originX) - originX, (targetZ ?? originZ) - originZ)) * distance
      position = look.clone().add(new Vector3(extent * .35, extent * .85, extent * .8))
    }
    camera.up.set(0, 1, 0)
    if (!mounted.current || reducedMotion) {
      camera.position.copy(position); target.current.copy(look); camera.lookAt(look)
      transition.current = null
    } else transition.current = { start: performance.now(), from: camera.position.clone(), to: position,
      fromTarget: target.current.clone(), toTarget: look }
    mounted.current = true
    invalidate()
  }, [camera, cameraPreset, resetRevision, reducedMotion, size.width, size.height, originX, originZ, targetX, targetZ, invalidate])

  useFrame(() => {
    const move = transition.current
    if (!move) return
    const t = Math.min(1, (performance.now() - move.start) / 420)
    const eased = t * t * (3 - 2 * t)
    camera.position.lerpVectors(move.from, move.to, eased)
    target.current.lerpVectors(move.fromTarget, move.toTarget, eased)
    camera.lookAt(target.current)
    if (t === 1) transition.current = null
    else invalidate()
  })

  useEffect(() => {
    if (cameraPreset !== 'free') return
    const canvas = gl.domElement
    canvas.tabIndex = 0
    canvas.setAttribute('aria-label', 'Free football camera. Drag to orbit, wheel to zoom, arrow keys to pan.')
    const controls = new OrbitControls(camera, canvas)
    controls.target.copy(target.current)
    controls.minDistance = 12; controls.maxDistance = 210
    controls.minPolarAngle = .08; controls.maxPolarAngle = Math.PI * .44
    controls.enableDamping = false; controls.screenSpacePanning = false
    controls.listenToKeyEvents(canvas)
    const changed = () => {
      controls.target.x = Math.max(-55, Math.min(55, controls.target.x))
      controls.target.z = Math.max(-38, Math.min(38, controls.target.z))
      controls.target.y = 0
      target.current.copy(controls.target); invalidate()
    }
    controls.addEventListener('change', changed); controls.update(); invalidate()
    return () => { controls.removeEventListener('change', changed); controls.stopListenToKeyEvents(); controls.dispose(); canvas.removeAttribute('aria-label'); canvas.removeAttribute('tabindex') }
  }, [camera, cameraPreset, gl, invalidate])
  return null
}
