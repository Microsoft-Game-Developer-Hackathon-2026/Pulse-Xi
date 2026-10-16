import { Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { useLoader } from '@react-three/fiber'
import { Box3, EdgesGeometry, Mesh, MeshStandardMaterial, Vector3 } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import type { EventSnapshot } from './eventSnapshot'
import type { GraphicsQuality } from './graphicsProfiles'
import { cloneTeamMarker } from './cloneTeamMarker'
import { createGrassTexture } from './grassTexture'
import { Stadium } from './Stadium'
import type { Object3D } from 'three'

function useDisposeMaterials(scene: Object3D) {
  useEffect(() => () => scene.traverse(object => {
    if (object instanceof Mesh) for (const material of Array.isArray(object.material) ? object.material : [object.material]) material.dispose()
  }), [scene])
}

const urls = [new URL('./assets/v2/field.glb', import.meta.url).href,
  new URL('./assets/v2/ball.glb', import.meta.url).href,
  new URL('./assets/v2/player-marker.glb', import.meta.url).href]
const stadiumUrl = new URL('./assets/v2/stadium.glb', import.meta.url).href
export type AssetStatus = { status: 'loading' | 'ready' | 'fallback' | 'procedural'; surfaceSize?: [number, number, number]; readyMs?: number }

function StadiumKit({ quality, ready }: { quality: GraphicsQuality; ready: () => void }) {
  const model = useLoader(GLTFLoader, stadiumUrl)
  const scene = useMemo(() => model.scene.clone(true), [model])
  useEffect(() => {
    scene.traverse(object => { if (object instanceof Mesh) { object.castShadow = quality === 'high'; object.receiveShadow = false } })
    ready()
  }, [scene, quality, ready])
  return <primitive object={scene} dispose={null}/>
}

export function AssetKit({ snapshot, lowPower, quality = 'standard', report }: {
  snapshot: EventSnapshot; lowPower: boolean; quality?: GraphicsQuality; report: (value: AssetStatus) => void
}) {
  const [field, ball, player] = useLoader(GLTFLoader, urls)
  const [stadiumReady, setStadiumReady] = useState(false)
  const markStadiumReady = useCallback(() => setStadiumReady(true), [])
  const grass = useMemo(createGrassTexture, [])
  useEffect(() => () => grass.dispose(), [grass])
  const paintOutlines = useMemo(() => {
    const result: EdgesGeometry[] = []
    field.scene.updateMatrixWorld(true)
    field.scene.traverse(object => {
      if (object instanceof Mesh && (Array.isArray(object.material) ? object.material : [object.material]).some(material => material.name === 'FieldWhite')) {
        result.push(new EdgesGeometry(object.geometry, 15).applyMatrix4(object.matrixWorld))
      }
    })
    return result
  }, [field])
  useEffect(() => () => paintOutlines.forEach(geometry => geometry.dispose()), [paintOutlines])
  const surfaceSize = useMemo(() => {
    const surface = field.scene.getObjectByName('PlayingSurface')
    if (!surface) throw new Error('Asset field surface is missing')
    field.scene.updateMatrixWorld(true)
    const size = new Box3().setFromObject(surface).getSize(new Vector3())
    if (Math.abs(size.x - 100) > .01 || Math.abs(size.z - 64) > .01 || size.y > .1) throw new Error('Asset coordinate/scale contract mismatch')
    return [size.x, size.y, size.z] as [number, number, number]
  }, [field])
  const surface = useMemo(() => {
    const scene = cloneTeamMarker(field.scene, '#ffffff')
    scene.traverse(object => {
      if (!(object instanceof Mesh)) return
      object.receiveShadow = true
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
        if (material.name === 'FieldWhite') { material.polygonOffset = true; material.polygonOffsetFactor = -1; material.polygonOffsetUnits = -1 }
      }
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
        if (material instanceof MeshStandardMaterial && ['Turf', 'CuttingBands'].includes(material.name) && !lowPower) {
          material.map = grass; material.color.set(material.name === 'Turf' ? '#e0eee0' : '#ffffff'); material.needsUpdate = true
        }
      }
    })
    return scene
  }, [field, grass, lowPower])
  const tinted = useMemo(() => {
    const clone = cloneTeamMarker(player.scene, snapshot.color)
    clone.traverse(object => { if (object instanceof Mesh) object.castShadow = true })
    return clone
  }, [player, snapshot.color])
  useDisposeMaterials(surface)
  useDisposeMaterials(tinted)
  useEffect(() => { report({ status: lowPower || stadiumReady ? 'ready' : 'loading', surfaceSize }) }, [report, surfaceSize, lowPower, stadiumReady])
  return <group>
    <primitive object={surface} dispose={null}/>
    {paintOutlines.map((geometry, index) => <lineSegments key={index} geometry={geometry} dispose={null} position={[0, .03, 0]}><lineBasicMaterial color="#dcebd5"/></lineSegments>)}
    {!lowPower && <Suspense fallback={<Stadium quality={quality}/>}><StadiumKit quality={quality} ready={markStadiumReady}/></Suspense>}
    {snapshot.origin && <group position={[snapshot.origin[0], .06, snapshot.origin[2]]}>
      {!lowPower && snapshot.actor_id ? <primitive object={tinted} dispose={null}/> : <mesh position={[0, .8, 0]}><sphereGeometry args={[1.1, 12, 8]}/><meshStandardMaterial color={snapshot.color}/></mesh>}
    </group>}
    {snapshot.target && <group position={snapshot.target} scale={2.7}><primitive object={ball.scene} dispose={null}/></group>}
  </group>
}
