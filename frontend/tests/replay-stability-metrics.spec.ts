import { expect, test } from '@playwright/test'

// Measures passive replay: request volume per path, layout shift, principal container
// bounds and document scroll while the replay clock advances. Evidence is attached to the
// report so before/after runs are comparable on the same recorded workload.
const PANELS = ['.scoreboard', '.metrics', '.feed', '.moments', '.transport', '.fan-lens', '.recap-body', '.intelligence-grid']

for (const [width, speed] of [[1280, 1], [1280, 4], [390, 2]] as const) {
  test(`passive replay at ${speed}x keeps panel geometry stable at ${width}px`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const requests: Record<string, number> = {}
    page.on('request', request => {
      const url = new URL(request.url())
      if (!url.pathname.startsWith('/api/')) return
      const key = `${request.method()} ${url.pathname.replace(/\/matches\/[^/]+/, '/matches/:id')}`
      requests[key] = (requests[key] ?? 0) + 1
    })
    await page.goto('/')
    await expect(page.locator('.metrics')).toBeVisible()
    await page.getByRole('button', { name: `${speed}×`, exact: true }).click()
    // Let initial analysis settle, then scroll to the analysis region a reader would occupy.
    await expect(page.locator('.recap-body')).not.toContainText('Loading')
    await page.evaluate(() => {
      (window as any).__shifts = 0; (window as any).__panelShifts = 0; (window as any).__sources = []; (window as any).__heights = new Map()
      new PerformanceObserver(list => { for (const entry of list.getEntries() as any[]) if (!entry.hadRecentInput) { (window as any).__shifts += entry.value; const inPanel = (entry.sources ?? []).length > 0 && (entry.sources as any[]).every(source => (source.node as Element | null)?.closest?.('.feed-list')); if (inPanel) (window as any).__panelShifts += entry.value; for (const source of entry.sources ?? []) { const node = source.node as Element | null; (window as any).__sources.push(`${entry.value.toFixed(3)} ${node?.tagName}.${(node as HTMLElement | null)?.className} ${Math.round(source.previousRect.height)}->${Math.round(source.currentRect.height)} y${Math.round(source.previousRect.y)}->${Math.round(source.currentRect.y)}`) } } }).observe({ type: 'layout-shift', buffered: false })
    })
    await page.locator('.content-grid').scrollIntoViewIfNeeded()
    const scrollBefore = await page.evaluate(() => window.scrollY)
    for (const key of Object.keys(requests)) requests[key] = 0
    const samples: Record<string, Set<string>> = Object.fromEntries(PANELS.map(selector => [selector, new Set<string>()]))
    await page.getByRole('button', { name: 'Play', exact: true }).dispatchEvent('click')
    const started = Date.now()
    const startClock = Number(await page.getByRole('slider', { name: 'Seek match time' }).inputValue())
    while (Date.now() - started < 12000) {
      const boxes = await page.evaluate((selectors: string[]) => Object.fromEntries(selectors.map(selector => {
        const element = document.querySelector(selector); if (!element) return [selector, 'absent']
        const rect = element.getBoundingClientRect(); return [selector, `${Math.round(rect.width)}x${Math.round(rect.height)}`]
      })), PANELS)
      for (const [selector, box] of Object.entries(boxes)) samples[selector].add(box)
      await page.waitForTimeout(150)
    }
    const endClock = Number(await page.getByRole('slider', { name: 'Seek match time' }).inputValue())
    const scrollAfter = await page.evaluate(() => window.scrollY)
    const shifts = await page.evaluate(() => (window as any).__shifts as number)
    const panelShifts = await page.evaluate(() => (window as any).__panelShifts as number)
    const sources = await page.evaluate(() => (window as any).__sources as string[])
    const distinct = Object.fromEntries(Object.entries(samples).map(([selector, boxes]) => [selector, [...boxes]]))
    const report = { width, speed, seconds: 12, matchSecondsAdvanced: endClock - startClock, requests, cls: shifts, eventWireRowShift: panelShifts, pageCls: shifts - panelShifts, shiftSources: sources.slice(0, 12), scrollBefore, scrollAfter, distinctBoxes: distinct }
    await info.attach('replay-stability.json', { body: JSON.stringify(report, null, 2), contentType: 'application/json' })
    console.log(JSON.stringify(report))
    expect(endClock).toBeGreaterThan(startClock)
    expect(scrollAfter).toBe(scrollBefore)
    // Rows inside the fixed-size Event Wire move when a new event is inserted (content-driven,
    // reported separately). Nothing outside that panel may shift.
    expect(shifts - panelShifts).toBeLessThan(0.01)
    for (const selector of ['.scoreboard', '.metrics', '.transport', '.moments']) expect(distinct[selector], selector).toHaveLength(1)
  })
}
