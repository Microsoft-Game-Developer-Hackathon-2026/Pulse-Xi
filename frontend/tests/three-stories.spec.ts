import { expect, test } from '@playwright/test'
import type { Cue, Insight, Recap } from '../src/types'

const clockLabel = (second: number) => `${Math.floor(second / 60).toString().padStart(2, '0')}:${(second % 60).toString().padStart(2, '0')}`

for (const width of [1440, 390]) {
  test(`one moment shows analyst, fan and director lenses from the same source events at ${width}px`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 900 })
    const cues: Cue[] = await (await request.get('/api/matches/comeback-1107/overlays')).json()
    const cue = cues.find(item => item.overlay_type === 'goal')!
    const cutoff = cue.start_match_second
    const insight: Insight = (await (await request.get('/api/matches/comeback-1107/insights')).json() as Insight[]).find(item => item.insight_id === cue.insight_id)!
    const recap: Recap = await (await request.post(`/api/matches/comeback-1107/recap?persona=casual&at_second=${Math.floor(insight.match_second)}`)).json()
    const fanMoment = recap.moments.find(item => item.insight_id === insight.insight_id)
    await page.goto('/')
    const evidence = page.getByRole('button', { name: `Inspect evidence for ${cue.text} at ${clockLabel(cutoff)}`, exact: true })
    await page.locator('.cue-entry').filter({ has: evidence }).locator('.cue-row').click()
    await evidence.click()
    const stories = page.getByTestId('three-stories')
    await expect(stories).toBeVisible()
    await expect(stories.locator('[data-lens="analyst"]')).toContainText(insight.explanation)
    await expect(stories.locator('[data-lens="director"]')).toContainText(cue.text)
    await expect(stories.locator('[data-lens="director"]')).toContainText('PROPOSED')
    await expect(stories.locator('[data-lens="director"]')).toContainText('not producer-approved')
    if (fanMoment) await expect(stories.locator('[data-lens="fan"]')).toContainText(fanMoment.text)
    // The consistency claim must be computed from real IDs: all lens IDs are inside the insight's source set.
    expect(cue.supporting_event_ids.every(id => insight.supporting_event_ids.includes(id))).toBe(true)
    if (fanMoment) expect(fanMoment.supporting_event_ids.every(id => insight.supporting_event_ids.includes(id))).toBe(true)
    await expect(stories.locator('.story-check')).toContainText(`${insight.supporting_event_ids.length} verified source events`)
    // Source events remain inspectable from the same drawer.
    await expect(page.locator('.proof-event').first()).toBeVisible()
  })
}

test('a moment without a broadcast cue says so and does not invent one', async ({ page, request }) => {
  const insights: Insight[] = await (await request.get('/api/matches/comeback-1107/insights')).json()
  const target = insights.find(item => item.match_second < 5000)!
  await page.route('**/api/matches/comeback-1107/overlays', route => route.fulfill({ json: [] }))
  await page.goto('/')
  await page.getByRole('slider', { name: 'Seek match time' }).evaluate((element, value) => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(element, String(value))
    element.dispatchEvent(new Event('input', { bubbles: true })); element.dispatchEvent(new Event('change', { bubbles: true }))
  }, Math.ceil(target.match_second) + 5)
  await page.locator('.insight-card').filter({ hasText: target.title }).first().getByRole('button').click()
  const stories = page.getByTestId('three-stories')
  await expect(stories.locator('[data-lens="director"]')).toContainText('No broadcast cue was generated')
  await expect(stories.locator('[data-lens="director"]')).not.toContainText('PROPOSED')
  await expect(stories.locator('[data-lens="analyst"]')).toContainText(target.explanation)
})
