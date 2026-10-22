import { writeFileSync } from 'node:fs'
import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`replay keeps synchronized reading panels at ${width}px`, async ({ page }, info) => {
    test.setTimeout(90000)
    await page.setViewportSize({ width, height: 844 })
    await page.emulateMedia({ reducedMotion: 'reduce' })
    let requests = 0
    page.on('request', request => { if (/\/(metrics|tactics|recap)\?/.test(request.url())) requests++ })
    await page.goto('/')
    const seek = page.getByRole('slider', { name: 'Seek match time' })
    const samples: object[] = []
    for (const speed of [0.5, 1, 2, 4]) {
      await seek.fill('1000')
      await expect(page.locator('.recap-body')).not.toContainText('Loading')
      await expect(page.locator('.control-chaos .control-empty')).toHaveCount(0)
      await expect(page.locator('.metrics')).not.toContainText('?')
      await expect(page.locator('.tactical-lab .panel-title')).not.toContainText('SYNCHRONIZING')
      await page.getByRole('button', { name: `${speed}×`, exact: true }).click()
      await page.locator('.studio').evaluate(element => element.scrollIntoView({ block: 'start' }))
      const startRequests = requests
      const before = await page.evaluate(() => ({ scroll: scrollY, top: document.querySelector('.studio')!.getBoundingClientRect().top }))
      await page.getByRole('button', { name: 'Play', exact: true }).dispatchEvent('click')
      const rows = []
      for (let index = 0; index < 25; index++) {
        await page.waitForTimeout(100)
        rows.push(await page.evaluate(() => ({
          scroll: scrollY, top: document.querySelector('.studio')!.getBoundingClientRect().top,
          missingMetrics: document.querySelector('.metrics')!.textContent!.includes('—'),
          regions: Object.fromEntries([".content-grid", ".tactical-lab", ".control-chaos", ".intelligence-grid", ".pass-filters", ".pass-workbench", ".tactical-layout", ".tactical-controls"].map(s => [s, document.querySelector(s)!.getBoundingClientRect().height])),
          loadingRecap: document.querySelector('.recap-body')!.textContent!.includes('Loading'),
        })))
      }
      await page.getByRole('button', { name: 'Pause', exact: true }).dispatchEvent('click')
      samples.push({ speed, requests: requests - startRequests, before, rows })
    }
    writeFileSync(info.outputPath('measurements.json'), JSON.stringify({ width, samples }, null, 2))
    await info.attach('replay-measurements', { body: JSON.stringify({ width, samples }, null, 2), contentType: 'application/json' })
    for (const sample of samples as { rows: { missingMetrics: boolean; loadingRecap: boolean; top: number; scroll: number }[]; before: { top: number; scroll: number } }[]) {
      expect(sample.rows.filter(row => row.missingMetrics)).toHaveLength(0)
      expect(sample.rows.filter(row => row.loadingRecap)).toHaveLength(0)
      expect(Math.max(...sample.rows.map(row => Math.abs(row.scroll - sample.before.scroll)))).toBeLessThan(2)
      expect(Math.max(...sample.rows.map(row => Math.abs(row.top - sample.before.top)))).toBeLessThan(2)
    }
  })
}

test('backward seek and audience changes conceal incompatible pending responses', async ({ page }) => {
  await page.goto('/')
  const seek = page.getByRole('slider', { name: 'Seek match time' })
  await seek.fill('3500')
  await expect(page.locator('.recap-body')).toHaveAttribute('data-analysis-cutoff', '3500')
  await page.route('**/recap?**', async route => {
    const response = await route.fetch()
    await new Promise(resolve => setTimeout(resolve, 600))
    await route.fulfill({ response })
  })
  await seek.fill('20')
  // Future packets disappear in the same React update, before the delayed API.
  await expect(page.locator('.recap-body')).not.toHaveAttribute('data-analysis-cutoff', '3500')
  await expect(page.locator('.metrics')).not.toHaveAttribute('data-analysis-cutoff', '3500')
  await expect(page.locator('.recap-body')).toHaveAttribute('data-analysis-cutoff', '20')
  await page.locator('.recap-controls select').first().selectOption('analyst')
  await expect(page.locator('.recap-body')).toContainText('Synchronizing current source')
  await expect(page.locator('.recap-body')).toHaveAttribute('data-analysis-cutoff', '20')
})
