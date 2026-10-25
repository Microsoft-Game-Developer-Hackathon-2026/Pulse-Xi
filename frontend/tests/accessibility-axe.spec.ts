import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

// Automated WCAG 2.0/2.1 A+AA scan (axe-core) of every route and the proof drawer. Axe finds a
// subset of issues; this is a regression gate, not a conformance claim.
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']

async function scan(page: Page) {
  const result = await new AxeBuilder({ page }).withTags(TAGS).analyze()
  return result.violations.map(v => `${v.impact} ${v.id} x${v.nodes.length} ${v.nodes[0].target.join(' ')}`)
}

for (const [hash, name] of [['#/', 'Match Intelligence'], ['#/sandbox', 'Sandbox Lab'], ['#/runtime', 'Engine Control Room'], ['#/data', 'Match Data Hub'], ['#/studio', 'Director Studio']] as const) {
  for (const width of [1440, 390]) {
    test(`${name} has no axe WCAG A/AA violations at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(`/${hash}`)
      await page.waitForLoadState('networkidle')
      await expect(page.locator('.loading')).toHaveCount(0, { timeout: 15000 })
      expect(await scan(page)).toEqual([])
    })
  }
}

for (const locale of ['es', 'hi'] as const) {
  test(`Match Intelligence has no axe violations in ${locale}`, async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.recap-body')).not.toContainText('Loading')
    await page.locator('.recap-controls select').nth(1).selectOption(locale)
    await expect(page.locator('html')).toBeVisible()
    await page.waitForLoadState('networkidle')
    expect(await scan(page)).toEqual([])
  })
}

test('proof drawer with Three Stories has no axe violations', async ({ page, request }) => {
  const cues = await (await request.get('/api/matches/comeback-1107/overlays')).json()
  const cue = cues.find((item: { overlay_type: string }) => item.overlay_type === 'goal')
  const label = `${String(Math.floor(cue.start_match_second / 60)).padStart(2, '0')}:${String(cue.start_match_second % 60).padStart(2, '0')}`
  await page.goto('/')
  const evidence = page.getByRole('button', { name: `Inspect evidence for ${cue.text} at ${label}`, exact: true })
  await page.locator('.cue-entry').filter({ has: evidence }).locator('.cue-row').click()
  await evidence.click()
  await expect(page.getByTestId('three-stories')).toBeVisible()
  await expect(page.getByTestId('three-stories').locator('[data-lens="fan"]')).not.toContainText('Loading')
  expect(await scan(page)).toEqual([])
})
