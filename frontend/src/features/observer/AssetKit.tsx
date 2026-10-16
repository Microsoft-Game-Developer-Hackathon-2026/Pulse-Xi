import { useEffect, useMemo } from 'react'
import { useLoader } from '@react-three/fiber'
import { Box3, Mesh, Vector3 } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import type { EventSnapshot } from './eventSnapshot'
import { cloneTeamMarker } from './cloneTeamMarker'

const urls = [new URL('./assets/field.glb', import.meta.url).href,
  new URL('./assets/ball.glb', import.meta.url).href,
  new URL('./assets/player-marker.glb', import.meta.url).href]

export type AssetStatus = { status: 'loading' | 'ready' | 'fallback' | 'procedural'; surfaceSize?: [number, number, number]; readyMs?: number }

export function AssetKit({ snapshot, lowPower, report }: {
  snapshot: EventSnapshot; lowPower: boolean; report: (value: AssetStatus) => void
}) {
  const [field, ball, player] = useLoader(GLTFLoader, urls)
  const surfaceSize = useMemo(() => {
    const surface = field.scene.getObjectByName('PlayingSurface')
    if (!surface) throw new Error('Asset field surface is missing')
    field.scene.updateMatrixWorld(true)
    const size = new Box3().setFromObject(surface).getSize(new Vector3())
    if (Math.abs(size.x - 100) > .01 || Math.abs(size.z - 64) > .01 || size.y > .1) {
      throw new Error('Asset coordinate/scale contract mismatch')
    }
    return [size.x, size.y, size.z] as [number, number, number]
  }, [field])
  const tinted = useMemo(() => cloneTeamMarker(player.scene, snapshot.color), [player, snapshot.color])
  useEffect(() => () => tinted.traverse(object => {
    if (object instanceof Mesh) for (const material of Array.isArray(object.material) ? object.material : [object.material]) material.dispose()
  }), [tinted])
  useEffect(() => { report({ status: 'ready', surfaceSize }) }, [report, surfaceSize])
  return <group>
    <primitive object={field.scene} dispose={null}/>
    {snapshot.origin && <group position={[snapshot.origin[0], .06, snapshot.origin[2]]}>
      {!lowPower && snapshot.actor_id ? <primitive object={tinted} dispose={null}/> : <mesh position={[0, .8, 0]}><sphereGeometry args={[1.1, 12, 8]}/><meshStandardMaterial color={snapshot.color}/></mesh>}
    </group>}
    {snapshot.target && <group position={snapshot.target}><primitive object={ball.scene} dispose={null}/></group>}
  </group>
}
