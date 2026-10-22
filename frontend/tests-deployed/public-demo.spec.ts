import { expect, test } from '@playwright/test'

test('public judge can load a synthetic fixture, seek, play, pause and generate a seed', async ({ page, request }) => {
  const pageErrors: string[] = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.goto('/#/sandbox')
  await expect(page.getByRole('region', { name: 'Sandbox fixture setup' })).toBeVisible()
  await expect(page.getByLabel('SELECT MATCH')).toHaveValue('comeback-1107')
  const seek = page.getByRole('slider', { name: 'Seek match time' })
  await expect(seek).toBeVisible()
  await seek.fill('1200')
  await expect(page.locator('.recap-body')).not.toContainText('Loading')
  await page.getByRole('button', { name: 'Play', exact: true }).click()
  await expect.poll(async () => Number(await seek.inputValue())).toBeGreaterThan(1200)
  await page.getByRole('button', { name: 'Pause', exact: true }).click()
  const pausedAt = Number(await seek.inputValue())
  await expect(page.getByRole('button', { name: 'Play', exact: true })).toBeVisible()
  await page.getByLabel('REPRODUCIBLE MATCH SEED').fill('123')
  await page.getByRole('button', { name: 'Generate replay' }).click()
  await expect(page.getByLabel('SELECT MATCH')).toHaveValue('custom-123')
  await expect(page.getByRole('status').filter({ hasText: 'Replay custom-123 is ready' })).toBeVisible()
  const response = await request.get('/api/matches/custom-123/events?limit=1000')
  expect(response.ok()).toBeTruthy()
  const events = await response.json() as Array<{ sequence: number; event_id: string }>
  expect(events.length).toBeGreaterThan(0)
  expect(new Set(events.map(event => event.event_id)).size).toBe(events.length)
  expect(pausedAt).toBeGreaterThan(1200)
  expect(pageErrors).toEqual([])
})
