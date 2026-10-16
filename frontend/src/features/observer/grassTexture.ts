import { DataTexture, LinearFilter, LinearMipmapLinearFilter, RepeatWrapping, RGBAFormat, SRGBColorSpace } from 'three'

/** Small original deterministic albedo, generated locally; no external texture. */
export function createGrassTexture() {
  const size = 128, data = new Uint8Array(size * size * 4)
  let seed = 7127
  for (let i = 0; i < size * size; i++) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0
    const variation = (seed >>> 24) / 255
    data.set([31 + variation * 13, 78 + variation * 24, 44 + variation * 12, 255], i * 4)
  }
  const texture = new DataTexture(data, size, size, RGBAFormat)
  texture.colorSpace = SRGBColorSpace; texture.wrapS = texture.wrapT = RepeatWrapping
  texture.magFilter = LinearFilter; texture.minFilter = LinearMipmapLinearFilter
  texture.generateMipmaps = true; texture.anisotropy = 2
  texture.repeat.set(28, 18); texture.needsUpdate = true
  return texture
}
