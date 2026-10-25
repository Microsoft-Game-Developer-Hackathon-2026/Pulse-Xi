import { expect, test } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'

// Evidence probe, not a field-data benchmark: one Chromium run on software rendering.
// LCP/long tasks come from PerformanceObserver; heap is JSHeapUsedSize after a forced GC;
// "interaction latency" is a synthetic click -> next animation frame, NOT field INP.
test('route load, long tasks, interaction latency and heap during a 60 s replay at 4x', async ({ page, context }, info) => {
  test.setTimeout(150000)
  await page.addInitScript(() => {
    const w = window as any; w.__lcp = 0; w.__long = [] as number[]
    new PerformanceObserver(list => { for (const e of list.getEntries()) w.__lcp = e.startTime }).observe({ type: 'largest-contentful-paint', buffered: true })
    new PerformanceObserver(list => { for (const e of list.getEntries()) w.__long.push(e.duration) }).observe({ type: 'longtask', buffered: true })
  })
  const cdp = await context.newCDPSession(page)
  await cdp.send('Performance.enable')
  const heapMb = async () => {
    await cdp.send('HeapProfiler.collectGarbage')
    const { metrics } = await cdp.send('Performance.getMetrics')
    return (metrics.find(m => m.name === 'JSHeapUsedSize')!.value) / 1048576
  }
  const requests: string[] = []
  page.on('request', r => { if (r.url().includes('/api/')) requests.push(r.url()) })
  const t0 = Date.now()
  await page.goto('/')
  await expect(page.locator('.metrics')).toBeVisible()
  await expect(page.locator('.recap-body')).not.toContainText('Loading')
  const readyMs = Date.now() - t0
  const navigation = await page.evaluate(() => { const n = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming; return { domContentLoaded: n.domContentLoadedEventEnd, load: n.loadEventEnd } })
  const initialRequests = requests.length

  // Synthetic interaction latency: click a speed button, wait for the next frame after React commits.
  const latencies: number[] = []
  for (let i = 0; i < 30; i++) {
    latencies.push(await page.evaluate(async index => {
      const label = ['2×', '1×', '4×', '0.5×'][index % 4]
      const button = Array.from(document.querySelectorAll<HTMLButtonElement>('.speed button')).find(b => b.textContent === label)!
      const start = performance.now(); button.click()
      await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      return performance.now() - start
    }, i))
  }
  await page.getByRole('button', { name: '4×', exact: true }).click()
  await page.locator('.content-grid').scrollIntoViewIfNeeded()
  await page.getByRole('button', { name: 'Play', exact: true }).dispatchEvent('click')
  const heap: number[] = [await heapMb()]
  const requestsBefore = requests.length
  for (let i = 0; i < 4; i++) { await page.waitForTimeout(15000); heap.push(await heapMb()) }
  const playbackRequests = requests.length - requestsBefore
  const clock = Number(await page.getByRole('slider', { name: 'Seek match time' }).inputValue())
  const nodes = await page.evaluate(() => document.getElementsByTagName('*').length)
  const long: number[] = await page.evaluate(() => (window as any).__long)
  const sorted = [...latencies].sort((a, b) => a - b)
  const pct = (p: number) => sorted[Math.min(sorted.length - 1, Math.ceil(p * sorted.length) - 1)]
  const report = {
    environment: 'Chromium (Playwright), software rendering, local backend, built-in fixture comeback-1107, 1280x720',
    readyMs, navigation, lcpMs: await page.evaluate(() => (window as any).__lcp), initialApiRequests: initialRequests,
    syntheticInteraction: { samples: latencies.length, p50: pct(.5), p95: pct(.95), max: sorted.at(-1), note: 'click -> two animation frames; not field INP' },
    longTasks: { count: long.length, totalMs: long.reduce((a, b) => a + b, 0), maxMs: Math.max(0, ...long) },
    replay: { wallSeconds: 60, speed: 4, matchSecondsReached: clock, apiRequests: playbackRequests },
    heapUsedMbAfterGc: heap.map(v => Number(v.toFixed(1))), domNodesAtEnd: nodes,
  }
  // Evidence is only written when explicitly requested, so CI never modifies the repository.
  if (process.env.PULSE_WRITE_BENCHMARK) { mkdirSync('../docs/benchmarks', { recursive: true }); writeFileSync(process.env.PULSE_WRITE_BENCHMARK, JSON.stringify(report, null, 2)) }
  await info.attach('browser-metrics.json', { body: JSON.stringify(report, null, 2), contentType: 'application/json' })
  console.log(JSON.stringify(report))
  expect(clock).toBeGreaterThan(1000)
  expect(heap.at(-1)! - heap[0], 'heap growth over replay (MB)').toBeLessThan(25)
})
