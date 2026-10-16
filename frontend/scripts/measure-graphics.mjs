/** Bounded real-app graphics probe. Run after building and starting FastAPI. */
import { chromium, expect } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { execFileSync } from 'node:child_process'

const base = process.env.PULSE_GRAPHICS_URL ?? 'http://127.0.0.1:8000'
const output = new URL('../../test-results/graphics/', import.meta.url)
await mkdir(output, { recursive: true })
const hardware = process.env.PULSE_GRAPHICS_HARDWARE === '1'
const browser = await chromium.launch({ headless: !hardware,
  args: [...(hardware ? [] : ['--enable-unsafe-swiftshader']), '--enable-precise-memory-info'] })
try {
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
  const requests = {}, errors = []
  page.on('request', request => { if (/\.glb$|SceneCanvas.*\.js/.test(request.url())) requests[request.url()] = (requests[request.url()] ?? 0) + 1 })
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(`${base}/#/sandbox`)
  await page.getByRole('slider', { name: 'Seek match time' }).fill('3500')
  if (Object.keys(requests).length) throw new Error('Default 2D requested renderer resources')
  await page.getByRole('button', { name: '3D observer', exact: true }).click()
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'ready')
  await page.getByText('Renderer diagnostics and provenance', { exact: true }).click()
  const gpu = await page.getByTestId('observer-canvas').locator('canvas').evaluate(canvas => {
    const gl = canvas.getContext('webgl2'), extension = gl.getExtension('WEBGL_debug_renderer_info')
    return { renderer: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unavailable', vendor: gl.getParameter(gl.VENDOR) }
  })
  const assetReadiness = await page.getByTestId('asset-status').textContent()
  const profiles = []
  if (hardware && /SwiftShader|llvmpipe|software/i.test(gpu.renderer)) throw new Error(`Physical GPU required, received ${gpu.renderer}`)
  for (const quality of ['low', 'standard', 'high']) {
    await page.getByLabel('3D QUALITY').selectOption(quality)
    const metrics = page.getByTestId('observer-metrics')
    await expect(metrics).toHaveAttribute('data-quality', quality)
    await expect(metrics).toHaveAttribute('data-sampled', 'true')
    await expect(page.getByTestId('observer-canvas')).toHaveAttribute('data-camera-settled', 'true')
    const heap = await page.evaluate(() => performance.memory?.usedJSHeapSize ?? null)
    // Exercise actual camera renders rather than reporting demand-rendered idle FPS.
    await page.getByRole('button', { name: 'Free camera', exact: true }).click()
    const canvas = page.getByTestId('observer-canvas').locator('canvas')
    const bounds = await canvas.boundingBox()
    if (!bounds) throw new Error('Observer canvas has no bounds')
    await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
    await page.mouse.down()
    const sampling = page.evaluate(() => new Promise(resolve => {
      const intervals = []; const start = performance.now(); let previous = start
      function sample(now) {
        intervals.push(now - previous); previous = now
        if (now - start < 5000) requestAnimationFrame(sample)
        else { intervals.sort((a, b) => a - b); resolve({ durationMs: now - start, frames: intervals.length,
          fps: intervals.length * 1000 / (now - start), medianFrameMs: intervals[Math.floor(intervals.length * .5)],
          p95FrameMs: intervals[Math.min(intervals.length - 1, Math.floor(intervals.length * .95))] }) }
      }
      requestAnimationFrame(sample)
    }))
    const motionStart = Date.now()
    while (Date.now() - motionStart < 5100) {
      const phase = (Date.now() - motionStart) / 300
      await page.mouse.move(bounds.x + bounds.width / 2 + Math.sin(phase) * 90,
        bounds.y + bounds.height / 2 + Math.cos(phase) * 35)
    }
    await page.mouse.up()
    const activeCamera = await sampling
    profiles.push({ quality, metrics: await metrics.textContent(), heapBytes: heap, activeCamera })
    await page.getByRole('region', { name: 'Football pitch observer' }).screenshot({ path: fileURLToPath(new URL(`${quality}.png`, output)) })
  }
  const before = await page.evaluate(() => performance.memory?.usedJSHeapSize ?? null)
  for (let i = 0; i < 12; i++) {
    await page.getByRole('button', { name: i % 2 ? 'Isometric camera' : 'Top-down camera', exact: true }).click()
    await page.getByLabel('3D QUALITY').selectOption(i % 2 ? 'high' : 'standard')
    await page.getByRole('slider', { name: 'Seek match time' }).fill(String(2800 + i * 37))
    if (i % 4 === 0) {
      await page.getByRole('button', { name: '2D pitch', exact: true }).click()
      await page.getByRole('button', { name: '3D observer', exact: true }).click()
    }
  }
  await page.getByLabel('3D QUALITY').selectOption('standard')
  await expect(page.getByTestId('observer-metrics')).toHaveAttribute('data-quality', 'standard')
  await expect(page.getByTestId('observer-metrics')).toHaveAttribute('data-sampled', 'true')
  const after = await page.evaluate(() => performance.memory?.usedJSHeapSize ?? null)
  console.log('Beginning bounded 30-second idle/resource observation.')
  await page.waitForTimeout(30_000)
  const idleHeap = await page.evaluate(() => performance.memory?.usedJSHeapSize ?? null)
  const result = { mode: hardware ? 'Headed physical GPU, five-second active orbit; requestAnimationFrame pacing, not GPU timer queries' : 'Headless renderer probe; inspect GPU identity',
    commit: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
    browser: browser.version(), viewport: page.viewportSize(), dpr: await page.evaluate(() => devicePixelRatio), assetReadiness, gpu, profiles, requests,
    interactionHeap: { before, after, afterThirtySecondIdle: idleHeap, note: 'No forced GC; bounded samples do not establish a leak or its absence.' },
    finalMetrics: await page.getByTestId('observer-metrics').textContent(), errors }
  await writeFile(new URL(hardware ? 'intel-hardware.json' : 'measurements.json', output), JSON.stringify(result, null, 2))
  console.log(JSON.stringify(result, null, 2))
  if (errors.length) throw new Error('Graphics probe reported runtime errors')
} finally { await browser.close() }
