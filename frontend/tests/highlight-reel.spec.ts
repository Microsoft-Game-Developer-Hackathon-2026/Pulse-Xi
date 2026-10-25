import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

type Manifest = { manifest_sha256: string; video: { total_seconds: number }; clips: { match_second: number; title: string; caption: string; score_before: { home: number; away: number }; score_after: { home: number; away: number }; source_events: { type: string }[] }[] }

test('highlight reel frames are pinned to the manifest and cite real source events', async ({ page, request }) => {
  const manifest: Manifest = await (await request.get('/api/matches/comeback-1107/highlights')).json()
  const intro = 3, clip = 6
  for (const index of [0, 1, manifest.clips.length - 1]) {
    const item = manifest.clips[index]
    // 0.5 s into a clip is before the score changes; 3 s in is after.
    await page.goto(`/#/highlight-reel?match=comeback-1107&render=1&t=${intro + index * clip + 0.5}`)
    await page.reload()
    const root = page.locator('main.reel')
    await expect(root).toHaveAttribute('data-manifest', manifest.manifest_sha256)
    await expect(root.locator('.reel-score')).toHaveText(`${item.score_before.home}:${item.score_before.away}`)
    await expect(root.locator('.reel-lower h2')).toHaveText(item.title)
    await expect(root.locator('.reel-lower p')).toHaveText(item.caption)
    await expect(root.locator('.reel-evidence')).toContainText(`${item.source_events.length} source events`)
    await page.goto(`/#/highlight-reel?match=comeback-1107&render=1&t=${intro + index * clip + 3}`)
    await page.reload()
    await expect(page.locator('.reel-score')).toHaveText(`${item.score_after.home}:${item.score_after.away}`)
  }
})

test('highlight reel reaches its complete state and offers the manifest download', async ({ page, request }) => {
  const manifest: Manifest = await (await request.get('/api/matches/comeback-1107/highlights')).json()
  await page.goto(`/#/highlight-reel?match=comeback-1107&t=${manifest.video.total_seconds}`)
  await page.reload()
  await expect(page.locator('main.reel')).toHaveAttribute('data-state', 'complete')
  const last = manifest.clips.at(-1)!
  await expect(page.locator('.reel-card h1')).toHaveText(`${last.score_after.home}–${last.score_after.away}`)
  await expect(page.getByRole('link', { name: 'Download manifest JSON' })).toHaveAttribute('href', '/api/matches/comeback-1107/highlights')
})

test('highlight reel reports an unavailable match instead of rendering fabricated content', async ({ page }) => {
  await page.goto('/#/highlight-reel?match=no-such-match&render=1&t=5')
  await page.reload()
  await expect(page.getByRole('alert')).toContainText('Highlights unavailable (404)')
})

test('highlight reel has no axe violations', async ({ page }) => {
  await page.goto('/#/highlight-reel?match=comeback-1107&t=10.5')
  await page.reload()
  await expect(page.locator('.reel-lower h2')).toBeVisible()
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  expect(result.violations.map(v => `${v.impact} ${v.id} ${v.nodes[0].target.join(' ')}`)).toEqual([])
})

test('Match Intelligence links to the highlight reel for the loaded match', async ({ page }) => {
  await page.goto('/')
  const link = page.getByRole('link', { name: /Open event-derived highlight reel/ })
  await expect(link).toHaveAttribute('href', '/#/highlight-reel?match=comeback-1107')
})
