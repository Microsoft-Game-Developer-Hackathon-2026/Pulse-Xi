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

// ---- Judge journey and public boundary (same checks run against any deployed origin) ----
import AxeBuilder from '@axe-core/playwright'

const clockLabel = (second: number) => `${String(Math.floor(second / 60)).padStart(2, '0')}:${String(second % 60).padStart(2, '0')}`

test('judge journey: play, open a goal cue, inspect evidence and three stories without errors', async ({ page, request }) => {
  test.setTimeout(90_000)
  const problems: string[] = []
  page.on('pageerror', error => problems.push(`pageerror: ${error.message}`))
  page.on('console', message => { if (message.type() === 'error') problems.push(`console: ${message.text()}`) })
  page.on('response', response => { if (response.url().includes('/api/') && response.status() >= 400 && response.status() !== 429) problems.push(`${response.status()} ${response.url()}`) })
  let limited = 0
  page.on('response', response => { if (response.status() === 429) limited += 1 })
  const cues = await (await request.get('/api/matches/comeback-1107/overlays')).json() as { overlay_type: string; text: string; start_match_second: number }[]
  const cue = cues.find(item => item.overlay_type === 'goal')!
  await page.goto('/')
  await expect(page.locator('.metrics')).toBeVisible()
  await page.getByRole('button', { name: '4×', exact: true }).click()
  await page.getByRole('button', { name: 'Play', exact: true }).click()
  await page.waitForTimeout(35000)   // longer than the old per-second recap cadence needed to exhaust the 30/min shared budget
  await page.getByRole('button', { name: 'Pause', exact: true }).click()
  expect(limited, 'HTTP 429 responses during 35 s of playback').toBe(0)
  await expect(page.locator('.recap-body')).not.toContainText('temporarily limited')
  const evidence = page.getByRole('button', { name: `Inspect evidence for ${cue.text} at ${clockLabel(cue.start_match_second)}`, exact: true })
  await page.locator('.cue-entry').filter({ has: evidence }).locator('.cue-row').click()
  await evidence.click()
  const stories = page.getByTestId('three-stories')
  await expect(stories).toBeVisible()
  await expect(stories.locator('[data-lens="fan"]')).not.toContainText('Loading')
  await expect(stories.locator('.story-check')).toContainText('verified source events')
  await expect(page.locator('.proof-event').first()).toBeVisible()
  expect(problems).toEqual([])
})

test('judge journey: highlight manifest, pinned reel frame and axe scan', async ({ page, request }) => {
  const manifest = await (await request.get('/api/matches/comeback-1107/highlights')).json() as { manifest_sha256: string; clips: { title: string }[] }
  expect(manifest.clips.length).toBeGreaterThan(3)
  await page.goto('/#/highlight-reel?match=comeback-1107&render=1&t=10.5')
  await page.reload()
  await expect(page.locator('main.reel')).toHaveAttribute('data-manifest', manifest.manifest_sha256)
  await expect(page.locator('.reel-lower h2')).toHaveText(manifest.clips[1].title)
  await page.goto('/')
  await expect(page.locator('.metrics')).toBeVisible()
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  expect(result.violations.map(item => `${item.impact} ${item.id}`)).toEqual([])
})

test('public boundary: protected surfaces are denied and operator routes degrade gracefully', async ({ page, request }) => {
  for (const [method, path] of [['GET', '/docs'], ['GET', '/openapi.json'], ['GET', '/api/sandbox/sessions'], ['GET', '/api/agent-traces'], ['POST', '/api/matches/ingest'], ['POST', '/api/data-hub/import'], ['PUT', '/api/matches/comeback-1107/studio'], ['POST', '/api/insights/x/agent-run'], ['POST', '/api/matches/comeback-1107/highlights']] as const) {
    const response = await request.fetch(path, { method, data: {}, headers: { Authorization: `Bearer ${'x'.repeat(40)}` }, failOnStatusCode: false })
    expect(response.status(), `${method} ${path}`).toBe(403)
  }
  expect((await request.get('/ready')).status()).toBe(200)
  const health = await (await request.get('/health')).json()
  expect(health).toEqual({ status: 'ok', simulation: 'synthetic', narrative_provider: 'not_configured' })
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  for (const hash of ['#/runtime', '#/data', '#/studio']) {
    await page.goto(`/${hash}`)
    await page.waitForLoadState('networkidle')
    await expect(page.getByTestId('public-demo-notice'), `${hash} explains that operator tools are disabled`).toContainText('Public read-only demo')
  }
  expect(errors).toEqual([])
})
