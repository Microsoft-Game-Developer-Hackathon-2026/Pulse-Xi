import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { Box3, Mesh, MeshStandardMaterial, Vector3 } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { cloneTeamMarker } from '../src/features/observer/cloneTeamMarker'

test('actual v2 GLB marker retains visible team materials and source color', async () => {
  const bytes = await readFile(new URL('../src/features/observer/assets/v2/player-marker.glb', import.meta.url))
  const model = await new GLTFLoader().parseAsync(Uint8Array.from(bytes).buffer, '')
  const size = new Box3().setFromObject(model.scene).getSize(new Vector3())
  expect(size.y).toBeGreaterThan(1.8)
  const originals: MeshStandardMaterial[] = []
  model.scene.traverse(object => {
    if (object instanceof Mesh) for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      if (material instanceof MeshStandardMaterial && material.name === 'TeamAccent') originals.push(material)
    }
  })
  expect(originals.length).toBeGreaterThan(0)
  const before = originals.map(material => material.color.getHexString())
  const clone = cloneTeamMarker(model.scene, '#40e3d9')
  clone.traverse(object => {
    if (object instanceof Mesh) {
      expect(Array.isArray(object.material)).toBe(false)
      const material = object.material as MeshStandardMaterial
      expect(material.visible).toBe(true); expect(material.opacity).toBe(1)
      if (material.name === 'TeamAccent') expect(material.color.getHexString()).toBe('40e3d9')
      material.dispose()
    }
  })
  expect(originals.map(material => material.color.getHexString())).toEqual(before)
  model.scene.traverse(object => { if (object instanceof Mesh) object.geometry.dispose() })
})

test('original graphics fit six viewports and Low does not request the stadium', async ({ page }, testInfo) => {
  const requested: string[] = []
  const errors: string[] = []
  page.on('request', request => { if (request.url().endsWith('.glb')) requested.push(request.url()) })
  page.on('pageerror', error => errors.push(error.message))
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/#/sandbox')
  expect(requested).toEqual([])
  await page.getByRole('slider', { name: 'Seek match time' }).fill('3500')
  await page.getByRole('button', { name: '3D observer', exact: true }).click()
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'ready')
  expect(requested.some(url => url.includes('stadium-'))).toBe(false)
  for (const [width, height] of [[1920,1080],[1366,768],[1024,768],[768,1024],[390,844],[360,800]]) {
    await page.setViewportSize({ width, height })
    await page.getByLabel('3D QUALITY').selectOption(width < 700 ? 'low' : 'standard')
    await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'ready')
    await expect(page.getByTestId('observer-canvas')).toHaveAttribute('data-camera-settled', 'true')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2)).toBe(true)
    await page.getByRole('region', { name: 'Football pitch observer' }).screenshot({ path: testInfo.outputPath(`observer-${width}.png`) })
  }
  await page.getByLabel('3D QUALITY').selectOption('standard')
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'ready')
  await page.getByRole('button', { name: 'Focus event', exact: true }).click()
  await expect(page.getByTestId('observer-canvas')).toHaveAttribute('data-camera-settled', 'true')
  await page.getByTestId('observer-canvas').screenshot({ path: testInfo.outputPath('focused-event.png') })
  expect(errors).toEqual([])
})

test('corrupt original GLB falls back without losing the replay clock', async ({ page }) => {
  await page.route('**/assets/ball-*.glb', route => route.fulfill({ status: 200, contentType: 'model/gltf-binary', body: 'not a GLB' }))
  await page.goto('/#/sandbox')
  await page.getByRole('slider', { name: 'Seek match time' }).fill('3500')
  await page.getByRole('button', { name: '3D observer', exact: true }).click()
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'fallback')
  await expect(page.getByTestId('observer-canvas').locator('canvas')).toBeVisible()
  await page.getByLabel('3D QUALITY').selectOption('high')
  await page.getByRole('button', { name: '2D pitch', exact: true }).click()
  await expect(page.getByRole('slider', { name: 'Seek match time' })).toHaveValue('3500')
  await expect(page.locator('.score')).toContainText('0:2')
})
