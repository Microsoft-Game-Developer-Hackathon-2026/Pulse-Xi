import { useLayoutEffect, useRef } from 'react'
import { Color, InstancedMesh, Matrix4, Quaternion, Vector3 } from 'three'
import type { GraphicsQuality } from './graphicsProfiles'

/** Original architectural scenery only. Seats do not represent recorded spectators. */
export function Stadium({ quality }: { quality: GraphicsQuality }) {
  const seats = useRef<InstancedMesh>(null)
  const rows = quality === 'high' ? 10 : 6
  const count = rows * 64 * 2
  useLayoutEffect(() => {
    if (!seats.current) return
    const matrix = new Matrix4(), quaternion = new Quaternion(), scale = new Vector3(.85, .55, .85)
    for (let row = 0; row < rows; row++) for (let side = 0; side < 2; side++) for (let column = 0; column < 64; column++) {
      const index = (row * 2 + side) * 64 + column
      matrix.compose(new Vector3((column - 31.5) * 1.7, 1.6 + row * .85, (side ? 1 : -1) * (40 + row * 1.1)), quaternion, scale)
      seats.current.setMatrixAt(index, matrix)
      seats.current.setColorAt(index, new Color((column + row * 7) % 9 < 2 ? '#9eaaa1' : (column + row) % 3 ? '#214b52' : '#38676a'))
    }
    seats.current.instanceMatrix.needsUpdate = true
    if (seats.current.instanceColor) seats.current.instanceColor.needsUpdate = true
    seats.current.computeBoundingSphere()
  }, [rows])
  if (quality === 'low') return null
  return <group>
    <mesh castShadow={quality === 'high'} position={[0, -1.3, 0]} receiveShadow><boxGeometry args={[142, 1, 112]}/><meshStandardMaterial color="#17272c" roughness={1}/></mesh>
    {[-1, 1].map(side => <group key={side}>
      {Array.from({ length: rows }, (_, row) => <mesh key={row} position={[0, .4 + row * .85, side * (40 + row * 1.1)]}><boxGeometry args={[113, .85, 1.4]}/><meshStandardMaterial color="#20343b" roughness={1}/></mesh>)}
      <mesh castShadow={quality === 'high'} position={[0, rows * .85 + 3, side * (43 + rows * .65)]} rotation={[side * -.12, 0, 0]}><boxGeometry args={[119, .45, 13]}/><meshStandardMaterial color="#344a50" metalness={.45} roughness={.55}/></mesh>
      <mesh castShadow={quality === 'high'} position={[0, .65, side * 36.5]}><boxGeometry args={[111, 1.3, .35]}/><meshStandardMaterial color="#0b222e" emissive="#177b80" emissiveIntensity={.25}/></mesh>
      <mesh castShadow={quality === 'high'} position={[side * 59, 2.5, 0]}><boxGeometry args={[4, 5, 74]}/><meshStandardMaterial color="#213c45" roughness={.9}/></mesh>
    </group>)}
    <instancedMesh ref={seats} args={[undefined, undefined, count]}><boxGeometry/><meshStandardMaterial roughness={.8}/></instancedMesh>
    {quality === 'high' && [-1, 1].flatMap(x => [-1, 1].map(z => <group key={`${x}:${z}`} position={[x * 62, 0, z * 43]}>
      <mesh castShadow={quality === 'high'} position={[0, 13, 0]}><cylinderGeometry args={[.25, .55, 26, 8]}/><meshStandardMaterial color="#6c7c83" metalness={.7} roughness={.5}/></mesh>
      <mesh castShadow={quality === 'high'} position={[0, 26, 0]} rotation={[-.5 * z, 0, 0]}><boxGeometry args={[7, 3, .4]}/><meshStandardMaterial color="#dbe9e7" emissive="#c4e2e8" emissiveIntensity={1.4}/></mesh>
    </group>))}
  </group>
}
