import { expect, test } from '@playwright/test'

test('recap respects Retry-After during playback and recovers at the paused cutoff', async ({ page }) => {
  let limited = false
  let limitedCalls = 0
  await page.route('**/api/matches/*/recap?**', async route => {
    if (!limited) return route.continue()
    limitedCalls++
    await route.fulfill({ status: 429, headers: { 'Retry-After': '2', 'Cache-Control': 'no-store' },
      contentType: 'application/json', body: JSON.stringify({ detail: 'Public operation budget exhausted; retry later.' }) })
  })
  await page.goto('/#/sandbox')
  const seek = page.getByRole('slider', { name: 'Seek match time' })
  const recap = page.locator('.recap-body')
  await seek.fill('1200')
  await expect(recap).toHaveAttribute('data-analysis-cutoff', '1200')
  limited = true
  await page.getByRole('button', { name: 'Play', exact: true }).click()
  await expect.poll(() => limitedCalls).toBe(1)
  await page.waitForTimeout(1200)
  expect(limitedCalls, '1Hz playback must not retry before the server cooldown').toBe(1)
  await expect(recap).toHaveAttribute('data-analysis-cutoff', '1200')
  await expect(page.getByRole('status').filter({ hasText: 'Recap temporarily limited' })).toBeVisible()
  await expect(page.getByRole('alert').filter({ hasText: 'Recap request failed' })).toHaveCount(0)
  limited = false
  await page.getByRole('button', { name: 'Pause', exact: true }).click()
  await seek.fill('300')
  await expect(recap).not.toHaveAttribute('data-analysis-cutoff', '1200')
  const cutoff = await seek.inputValue()
  await expect(recap).toHaveAttribute('data-analysis-cutoff', cutoff)
  await expect(page.getByRole('status').filter({ hasText: 'Recap temporarily limited' })).toHaveCount(0)
})

test('a service failure after a cooldown does not remain labelled rate limited', async ({ page }) => {
  let calls = 0
  await page.route('**/api/matches/*/recap?**', async route => {
    calls++
    await route.fulfill({ status: calls === 1 ? 429 : 500,
      headers: calls === 1 ? { 'Retry-After': '1' } : {}, contentType: 'application/json', body: '{}' })
  })
  await page.goto('/#/sandbox')
  const status = page.getByRole('status').filter({ hasText: 'Recap temporarily limited' })
  await expect(status).toBeVisible()
  await expect(page.getByRole('alert').filter({ hasText: 'Recap request failed' })).toBeVisible()
  await expect(status).toHaveCount(0)
})
