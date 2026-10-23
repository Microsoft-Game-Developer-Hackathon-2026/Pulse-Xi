import { expect, test } from '@playwright/test'

// Every top-level route must load cleanly on the real backend: no console errors, no failed
// API calls, no horizontal overflow, and a visible landmark.
const ROUTES = [['#/', 'Match Intelligence', 'Harbour City comeback'], ['#/sandbox', 'Sandbox Lab', 'Start with a seed'], ['#/runtime', 'Engine Control Room', 'Change the tactics'], ['#/data', 'Match Data Hub', 'Match Data Hub'], ['#/studio', 'Director Studio', 'Director Studio']] as const

for (const width of [1440, 390]) {
  for (const [hash, name, heading] of ROUTES) {
    test(`${name} loads cleanly at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      const problems: string[] = []
      page.on('console', message => { if (message.type() === 'error') problems.push(`console: ${message.text()}`) })
      page.on('pageerror', error => problems.push(`pageerror: ${error.message}`))
      page.on('response', response => { if (response.url().includes('/api/') && response.status() >= 500) problems.push(`${response.status()} ${response.url()}`) })
      await page.goto(`/${hash}`)
      await expect(page.locator('main, #root').first()).toBeVisible()
      await page.waitForLoadState('networkidle')
      await expect(page.locator('.loading')).toHaveCount(0, { timeout: 15000 })
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
      expect(overflow, 'horizontal overflow (px)').toBeLessThanOrEqual(1)
      await expect(page.locator('h2').filter({ hasText: heading }).first(), `${name} heading`).toBeVisible()
      expect(problems).toEqual([])
    })
  }
}
