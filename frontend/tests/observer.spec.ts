import { expect, test } from '@playwright/test'
import { eventSnapshot, projectPoint } from '../src/features/observer/eventSnapshot'
import type { Event, Match } from '../src/types'
import { BoxGeometry, Mesh, MeshStandardMaterial } from 'three'
import { cloneTeamMarker } from '../src/features/observer/cloneTeamMarker'

test('team tint preserves single-mesh rendering and cached source materials', () => {
  const material = new MeshStandardMaterial({ color: '#777777' })
  material.name = 'TeamAccent'
  const source = new Mesh(new BoxGeometry(), material)
  const clone = cloneTeamMarker(source, '#27d5df') as Mesh
  expect(Array.isArray(clone.material)).toBe(false)
  expect((clone.material as MeshStandardMaterial).color.getHexString()).toBe('27d5df')
  expect(material.color.getHexString()).toBe('777777')
  expect(clone.geometry).toBe(source.geometry)
  expect(clone.material).not.toBe(source.material)
  source.geometry.dispose(); material.dispose(); (clone.material as MeshStandardMaterial).dispose()
})

test('event projection validates normalized coordinates and excludes future or foreign events', async ({ request }) => {
  expect(projectPoint({ x: 0, y: 0 })).toEqual([-50, .8, -32])
  expect(projectPoint({ x: 100, y: 100 })).toEqual([50, .8, 32])
  for (const point of [null, { x: NaN, y: 0 }, { x: 101, y: 50 }, { x: 50, y: -1 }]) expect(projectPoint(point)).toBeNull()
  const match: Match = await (await request.get('/api/matches/comeback-1107')).json()
  const events: Event[] = await (await request.get('/api/matches/comeback-1107/events?limit=1000')).json()
  const pass = events.find(event => event.type === 'pass')!
  expect(eventSnapshot(match, pass, pass.match_second).event_id).toBe(pass.event_id)
  expect(eventSnapshot(match, pass, pass.match_second - 1).event_id).toBeNull()
  expect(eventSnapshot(match, pass, 5400, { match_id: 'other' }).event_id).toBeNull()
  expect(eventSnapshot(match, { ...pass, actor_id: 'unknown' }, 5400).event_id).toBeNull()
  expect(eventSnapshot(match, { ...pass, recipient_id: 'unknown' }, 5400).event_id).toBeNull()
  expect(eventSnapshot(match, { ...pass, start: null }, 5400).origin).toBeNull()
  for (const match_second of [-1, -Infinity, NaN, 1.5]) {
    expect(eventSnapshot(match, { ...pass, match_second }, 5400).event_id).toBeNull()
  }
  expect(eventSnapshot(match, pass, 5401).event_id).toBeNull()
  expect(eventSnapshot(match, { ...pass, event_id: ' ' }, 5400).event_id).toBeNull()
  expect(eventSnapshot(match, { ...pass, sequence: 0 }, 5400).event_id).toBeNull()
})

test('lazy 3D snapshots, cameras, quality and context-loss fallback work', async ({ page, request }, testInfo) => {
  const chunks: string[] = []
  page.on('request', request => { if (/SceneCanvas.*\.js/.test(request.url())) chunks.push(request.url()) })
  await page.goto('/#/sandbox')
  await expect(page.getByRole('button', { name: '3D observer', exact: true })).toBeVisible()
  expect(chunks).toEqual([])
  const events: Event[] = await (await request.get('/api/matches/comeback-1107/events?limit=1000')).json()
  const pass = events.find(event => event.type === 'pass')!
  await page.getByRole('slider', { name: 'Seek match time' }).fill(String(pass.match_second))
  await page.getByRole('button', { name: '3D observer', exact: true }).click()
  await expect(page.getByTestId('observer-canvas').locator('canvas')).toBeVisible()
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'ready')
  const size = JSON.parse(await page.getByTestId('asset-status').getAttribute('data-surface-size') ?? '[]')
  expect(size[0]).toBeCloseTo(100, 2); expect(size[2]).toBeCloseTo(64, 2); expect(size[1]).toBeLessThan(.1)
  await page.getByText('Renderer diagnostics and provenance', { exact: true }).click()
  await expect(page.getByTestId('observer-metrics')).toHaveAttribute('data-sampled', 'true')
  await expect(page.getByTestId('observer-snapshot')).toHaveAttribute('data-event-id', pass.event_id)
  await expect(page.getByTestId('observer-metrics')).toHaveAttribute('data-origin', JSON.stringify(projectPoint(pass.start)))
  expect(chunks.length).toBeGreaterThan(0)
  const metrics = await page.getByTestId('observer-metrics').textContent()
  console.log(`3D measured: ${metrics}`)
  await testInfo.attach('renderer-metrics', { body: metrics ?? '', contentType: 'text/plain' })
  await page.getByTestId('observer-canvas').screenshot({ path: testInfo.outputPath('original-asset-observer.png') })
  await page.getByRole('button', { name: 'Top-down camera' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('observer-canvas')).toHaveAttribute('data-camera', 'tactical')
  await page.getByRole('button', { name: 'Focus event', exact: true }).click()
  await expect(page.getByTestId('observer-canvas')).toHaveAttribute('data-camera', 'focus')
  await page.getByRole('button', { name: 'Reset camera' }).click()
  await expect(page.getByTestId('observer-canvas')).toHaveAttribute('data-camera', 'broadcast')
  await page.getByLabel('3D QUALITY').selectOption('low')
  await expect(page.getByTestId('observer-canvas')).toHaveAttribute('data-quality', 'low')
  await page.getByTestId('observer-canvas').screenshot({ path: testInfo.outputPath('event-observer.png') })
  await page.getByRole('slider', { name: 'Seek match time' }).fill('0')
  await expect(page.getByTestId('observer-snapshot')).not.toHaveAttribute('data-event-id', pass.event_id)
  await page.getByTestId('observer-canvas').locator('canvas').evaluate(canvas => canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true })))
  await expect(page.getByText('The 3D renderer is unavailable. The recorded 2D pitch remains active.')).toBeVisible()
  await expect(page.getByRole('img', { name: /^Pitch position/ })).toBeVisible()
})

test('missing GLB assets fall back to a working procedural 3D pitch', async ({ page }) => {
  await page.route('**/assets/field-*.glb', route => route.abort())
  await page.goto('/#/sandbox')
  await page.getByRole('button', { name: '3D observer', exact: true }).click()
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'fallback')
  await expect(page.getByTestId('observer-canvas').locator('canvas')).toBeVisible()
  await page.getByRole('slider', { name: 'Seek match time' }).fill('3500')
  await expect(page.locator('.score')).toContainText('0:2')
  await page.getByLabel('SCENE STYLE').selectOption('procedural')
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'procedural')
})

test('slow asset loading leaves a usable pitch and does not block returning to 2D', async ({ page }) => {
  let release: () => void = () => {}
  const gate = new Promise<void>(resolve => { release = resolve })
  let requested: () => void = () => {}
  const started = new Promise<void>(resolve => { requested = resolve })
  await page.route('**/assets/field-*.glb', async route => {
    const response = await route.fetch(); requested(); await gate
    try { await route.fulfill({ response }) } catch { /* Observer may already be closed. */ }
  })
  await page.goto('/#/sandbox')
  await page.getByRole('button', { name: '3D observer', exact: true }).click()
  await started
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'loading')
  await expect(page.getByTestId('observer-canvas').locator('canvas')).toBeVisible()
  await page.getByRole('button', { name: '2D pitch', exact: true }).click()
  release()
  await expect(page.getByRole('img', { name: /^Pitch position/ })).toBeVisible()
})

test('mobile reduced-motion mode loads the kit at low power without overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/#/sandbox')
  await page.getByRole('button', { name: '3D observer', exact: true }).click()
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'ready')
  await expect(page.getByTestId('observer-canvas')).toHaveAttribute('data-quality', 'low')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2)).toBe(true)
})

test('unavailable WebGL preserves mobile 2D replay and reduced-motion defaults', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', { value: function(type: string, ...args: unknown[]) {
      if (type.startsWith('webgl')) return null
      return Reflect.apply(original, this, [type, ...args])
    } })
  })
  await page.goto('/#/sandbox')
  await page.getByRole('button', { name: '3D observer', exact: true }).click()
  await expect(page.getByText('WebGL2 is unavailable. The recorded 2D pitch remains active.')).toBeVisible()
  await page.getByRole('slider', { name: 'Seek match time' }).fill('3500')
  await expect(page.locator('.score')).toContainText('0:2')
  await expect(page.getByRole('button', { name: '2D pitch', exact: true })).toHaveAttribute('aria-pressed', 'true')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2)).toBe(true)
})
