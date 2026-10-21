import { Mesh, MeshStandardMaterial } from 'three'
import type { Material, Object3D } from 'three'

export function cloneTeamMarker(source: Object3D, color: string) {
  const clone = source.clone(true)
  clone.traverse(object => {
    if (!(object instanceof Mesh)) return
    const original = object.material
    const materials: Material[] = Array.isArray(original) ? original : [original]
    const copies = materials.map(material => {
      const copy = material.clone()
      if (copy instanceof MeshStandardMaterial && copy.name === 'TeamAccent') copy.color.set(color)
      return copy
    })
    // A single-primitive GLB has no geometry groups. Turning its material into
    // an array would make Three.js skip the mesh entirely.
    object.material = Array.isArray(original) ? copies : copies[0]
  })
  return clone
}
