/** Bounded real-app graphics probe. Run after building and starting FastAPI. */
import { chromium, expect } from '@playwright/test'
import { readFile, mkdtemp, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { join, resolve } from 'node:path'
import { cpus, totalmem, release, platform } from 'node:os'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { recordProbe } from './graphics-report.mjs'
import { stabilitySeconds, runStability } from './graphics-stability.mjs'

const base = process.env.PULSE_GRAPHICS_URL ?? 'http://127.0.0.1:8000'
const root = new URL('../../', import.meta.url)
const outputRoot = process.env.PULSE_GRAPHICS_OUTPUT ?? new URL('test-results/graphics/', root)
await mkdir(outputRoot, { recursive: true })
const output = await mkdtemp(join(typeof outputRoot === 'string' ? resolve(outputRoot) : fileURLToPath(outputRoot), 'run-'))
console.log(`Graphics artifacts: ${output}`)
const hardware = process.env.PULSE_GRAPHICS_HARDWARE === '1'
let browser
let interrupted = null
let activeReport
const interrupt = signal => {
  interrupted = signal
  if (activeReport) activeReport.interruption = { signal, at: new Date().toISOString() }
  void browser?.close()
}
const onInterrupt = () => interrupt('SIGINT')
const onTerminate = () => interrupt('SIGTERM')
process.on('SIGINT', onInterrupt)
process.on('SIGTERM', onTerminate)
let deadline
const command = (executable, args) => {
  try { return execFileSync(executable, args, { encoding: 'utf8', timeout: 10_000, windowsHide: true }).trim() }
  catch { return null }
}
const workingTree = command('git', ['status', '--porcelain'])
try {
  const result = await recordProbe(output, {
    commit: command('git', ['rev-parse', 'HEAD']),
    dirty: workingTree === null ? null : workingTree !== '',
    mode: hardware ? 'headed physical GPU requested; inspect renderer' : 'headless renderer probe',
    machine: { cpu: cpus()[0]?.model ?? null, logicalCpus: cpus().length,
      ramBytes: totalmem(), os: `${platform()} ${release()}`,
      nvidia: command('nvidia-smi', ['--query-gpu=name,driver_version,memory.total', '--format=csv']) },
    workload: { match: 'comeback-1107', cutoff: 3500, warmupMs: 5000, repeats: 3,
      activeOrbitMs: 5000, idleMs: 30000, note: 'Bounded probe; not the proposed 15-minute soak. RAF pacing, not GPU timer queries.' },
    unavailable: ['GPU utilization/allocated VRAM', 'GPU timer queries', 'forced-GC leak assessment'],
  }, async (report, checkpoint) => {
    activeReport = report
    const extendedSeconds = stabilitySeconds(process.env.PULSE_GRAPHICS_STABILITY_SECONDS)
    report.workload.extendedStabilitySeconds = extendedSeconds
    report.workload.note = extendedSeconds ? 'Extended switching/remount stability plus bounded RAF samples; not GPU timer queries.' : report.workload.note
    deadline = setTimeout(() => interrupt('probe deadline'), 300_000 + extendedSeconds * 1000)
    const manifest = JSON.parse(await readFile(new URL('assets/manifest.json', root), 'utf8'))
    report.assetManifestSha256 = createHash('sha256').update(await readFile(new URL('assets/manifest.json', root))).digest('hex')
    report.assetManifest = manifest
    report.assetHashes = []
    for (const asset of manifest.assets) {
      const actual = createHash('sha256').update(await readFile(new URL(asset.output, root))).digest('hex')
      report.assetHashes.push({ name: asset.name, sha256: actual })
      if (actual !== asset.output_sha256) throw new Error(`Asset hash mismatch: ${asset.name}`)
    }
    browser = await chromium.launch({ headless: !hardware,
      args: [...(hardware ? [] : ['--enable-unsafe-swiftshader']), '--enable-precise-memory-info'] })
    browser.on('disconnected', () => { report.browserDisconnectedAt = new Date().toISOString() })
    const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
    page.setDefaultTimeout(15_000)
    report.browser = browser.version()
    const requests = {}, errors = []
    report.requests = requests; report.errors = errors
    page.on('crash', () => errors.push('Browser page crashed'))
    page.on('close', () => { report.pageClosedAt = new Date().toISOString() })
    page.on('request', request => { if (/\.glb$|SceneCanvas.*\.js/.test(request.url())) requests[request.url()] = (requests[request.url()] ?? 0) + 1 })
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(`${base}/#/sandbox`)
    await page.getByRole('slider', { name: 'Seek match time' }).fill('3500')
    if (Object.keys(requests).length) throw new Error('Default 2D requested renderer resources')
    await page.getByRole('button', { name: '3D observer', exact: true }).click()
    await expect(page.getByTestId('observer-canvas').locator('canvas')).toBeVisible()
    const assetStatus = page.getByTestId('asset-status')
    if (await assetStatus.count()) await expect(assetStatus).toHaveAttribute('data-status', 'ready')
    await page.getByText('Renderer diagnostics and provenance', { exact: true }).click()
    const gpu = await page.getByTestId('observer-canvas').locator('canvas').evaluate(canvas => {
      const gl = canvas.getContext('webgl2'), extension = gl.getExtension('WEBGL_debug_renderer_info')
      return { renderer: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unavailable', vendor: gl.getParameter(gl.VENDOR) }
    })
    const assetReadiness = await assetStatus.count() ? await assetStatus.textContent() : 'Procedural scene; no GLB activation'
    report.gpu = gpu; report.assetReadiness = assetReadiness
    report.viewport = page.viewportSize(); report.dpr = await page.evaluate(() => devicePixelRatio)
    if (hardware && /unavailable|SwiftShader|llvmpipe|software/i.test(gpu.renderer)) throw new Error(`Physical GPU required, received ${gpu.renderer}`)
    const expectedGpu = process.env.PULSE_GRAPHICS_EXPECT_GPU
    if (expectedGpu && !gpu.renderer.toLowerCase().includes(expectedGpu.toLowerCase())) throw new Error(`Expected GPU ${expectedGpu}, received ${gpu.renderer}`)
    await checkpoint()
    for (const quality of ['low', 'standard', 'high']) {
      report.phase = `profile-${quality}`
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
      await page.waitForTimeout(5000)
      const samples = []
      for (let repeat = 0; repeat < 3; repeat++) {
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
        // A page loss during mouse movement can reject this before its later await.
        // Observe immediately, while retaining the original rejection for that await.
        void sampling.catch(() => {})
        const motionStart = Date.now()
        while (Date.now() - motionStart < 5100) {
          const phase = (Date.now() - motionStart) / 300
          await page.mouse.move(bounds.x + bounds.width / 2 + Math.sin(phase) * 90,
            bounds.y + bounds.height / 2 + Math.cos(phase) * 35)
        }
        await page.mouse.up()
        const activeCamera = await sampling
        samples.push(activeCamera)
      }
      report.profiles.push({ quality, metrics: await metrics.textContent(), heapBytes: heap, activeCamera: samples })
      await checkpoint()
      await page.getByRole('region', { name: 'Football pitch observer' }).screenshot({ path: join(output, `${quality}.png`) })
    }
    const before = await page.evaluate(() => performance.memory?.usedJSHeapSize ?? null)
    for (let i = 0; i < 12; i++) {
      await page.getByRole('button', { name: ['Broadcast camera', 'Top-down camera', 'Isometric camera', 'Free camera', 'Focus event'][i % 5], exact: true }).click()
      await page.getByLabel('3D QUALITY').selectOption(i % 2 ? 'high' : 'standard')
      await page.getByRole('slider', { name: 'Seek match time' }).fill(String(2800 + i * 37))
      if (i % 4 === 0) {
        await page.getByRole('button', { name: '2D pitch', exact: true }).click()
        await page.getByRole('button', { name: '3D observer', exact: true }).click()
      }
    }
    if (extendedSeconds) {
      await page.getByRole('slider', { name: 'Seek match time' }).fill('3500')
      report.phase = 'extended-stability'
      console.log(`Beginning ${extendedSeconds}-second extended stability observation.`)
      await runStability({ durationMs: extendedSeconds * 1000, report, checkpoint,
        step: async cycle => {
          const quality = ['low', 'standard', 'high'][cycle % 3]
          await page.getByLabel('3D QUALITY').selectOption(quality)
          await page.getByRole('button', { name: ['Broadcast camera', 'Top-down camera', 'Isometric camera', 'Free camera', 'Focus event'][cycle % 5], exact: true }).click()
          if (cycle % 6 === 0) {
            await page.getByRole('button', { name: '2D pitch', exact: true }).click()
            await page.getByRole('button', { name: '3D observer', exact: true }).click()
          }
          await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status', 'ready')
          await expect(page.getByTestId('observer-metrics')).toHaveAttribute('data-quality', quality)
          await expect(page.getByTestId('observer-canvas').locator('canvas')).toBeVisible()
          await page.waitForTimeout(5000)
        },
        sample: async () => {
          if (errors.length) throw new Error('Runtime errors during extended stability')
          const value = await page.getByTestId('observer-canvas').locator('canvas').evaluate(canvas => {
            const gl = canvas.getContext('webgl2'), extension = gl?.getExtension('WEBGL_debug_renderer_info')
            return { renderer: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unavailable',
              heapBytes: performance.memory?.usedJSHeapSize ?? null, visibility: document.visibilityState }
          })
          if (value.renderer !== report.gpu.renderer) throw new Error(`Renderer changed during stability: ${value.renderer}`)
          return { ...value, metrics: await page.getByTestId('observer-metrics').textContent() }
        },
      })
    }
    await page.getByLabel('3D QUALITY').selectOption('standard')
    await expect(page.getByTestId('observer-metrics')).toHaveAttribute('data-quality', 'standard')
    await expect(page.getByTestId('observer-metrics')).toHaveAttribute('data-sampled', 'true')
    const after = await page.evaluate(() => performance.memory?.usedJSHeapSize ?? null)
    console.log('Beginning bounded 30-second idle/resource observation.')
    report.phase = 'idle-observation'
    await checkpoint()
    await page.waitForTimeout(30_000)
    const idleHeap = await page.evaluate(() => performance.memory?.usedJSHeapSize ?? null)
    report.interactionHeap = { before, after, afterThirtySecondIdle: idleHeap, note: 'No forced GC; bounded samples do not establish a leak or its absence.' }
    report.phase = 'final-metrics'
    if (!await page.getByTestId('observer-metrics').count()) {
      report.fallbackNotices = await page.getByRole('status').allTextContents()
      throw new Error('Observer metrics disappeared after switching/idle; inspect fallbackNotices')
    }
    report.finalMetrics = await page.getByTestId('observer-metrics').textContent()
    report.resources = await page.evaluate(() => performance.getEntriesByType('resource')
      .filter(entry => /\.glb|SceneCanvas/.test(entry.name))
      .map(entry => ({ name: new URL(entry.name).pathname, transferSize: entry.transferSize,
        encodedBodySize: entry.encodedBodySize, durationMs: entry.duration })))
    report.screenshots = []
    for (const [width, height] of [[1920,1080], [1366,768], [1024,768], [768,1024], [390,844], [360,800]]) {
      await page.setViewportSize({ width, height })
      await page.getByTestId('observer-canvas').scrollIntoViewIfNeeded()
      await expect(page.getByTestId('observer-canvas').locator('canvas')).toBeVisible()
      await page.waitForTimeout(250)
      const name = `viewport-${width}x${height}.png`
      await page.screenshot({ path: join(output, name) })
      report.screenshots.push(name)
    }
    if (interrupted) throw new Error(`Interrupted: ${interrupted}`)
  })
  console.log(JSON.stringify(result, null, 2))
} finally {
  clearTimeout(deadline)
  process.off('SIGINT', onInterrupt); process.off('SIGTERM', onTerminate)
  await browser?.close()
}
