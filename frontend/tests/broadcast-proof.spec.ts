import { expect, test } from '@playwright/test'
import type { Cue, Recap } from '../src/types'

for (const width of [1440, 390]) {
  test(`broadcast evidence and identical persona facts at ${width}px`, async ({ page, request }, testInfo) => {
    await page.setViewportSize({ width, height: 900 })
    const cues: Cue[] = await (await request.get('/api/matches/comeback-1107/overlays')).json()
    const cue = cues.find(item => item.overlay_type === 'goal')!
    const cutoff = cue.start_match_second
    const packets: Recap[] = []
    const personas = ['casual', 'analyst', 'broadcaster']
    for (const persona of personas) {
      const response = await request.post(`/api/matches/comeback-1107/recap?persona=${persona}&at_second=${cutoff}`)
      expect(response.ok()).toBeTruthy()
      packets.push(await response.json())
    }
    const facts = (packet: Recap) => packet.moments.map(({ insight_id, match_second, supporting_event_ids }) => ({ insight_id, match_second, supporting_event_ids }))
    expect(facts(packets[1])).toEqual(facts(packets[0]))
    expect(facts(packets[2])).toEqual(facts(packets[0]))
    expect(new Set(packets.map(packet => packet.moments.find(item => item.insight_id === cue.insight_id)?.text)).size).toBe(3)
    await page.goto('/')
    const evidence = page.getByRole('button', { name: `Inspect evidence for ${cue.text} at ${Math.floor(cutoff / 60).toString().padStart(2, '0')}:${(cutoff % 60).toString().padStart(2, '0')}`, exact: true })
    const entry = page.locator('.cue-entry').filter({ has: evidence })
    await expect(evidence).toBeDisabled()
    await entry.locator('.cue-row').click()
    await expect(page.getByRole('slider', { name: 'Seek match time' })).toHaveValue(String(cutoff))
    for (const [index, persona] of personas.entries()) {
      await page.getByLabel('VIEW').selectOption(persona)
      await expect(page.locator('.recap-body')).toContainText(packets[index].moments.find(item => item.insight_id === cue.insight_id)!.text)
      await expect(page.locator('.studio-lower')).toContainText(cue.text)
      await expect(page.getByRole('slider', { name: 'Seek match time' })).toHaveValue(String(cutoff))
    }
    await page.locator('.studio').screenshot({ path: testInfo.outputPath(`broadcast-cues-${width}.png`) })
    await evidence.focus()
    await page.keyboard.press('Enter')
    const drawer = page.getByRole('dialog', { name: 'Insight evidence' })
    await expect(drawer).toBeVisible()
    expect(await drawer.locator('.proof-event code').allTextContents()).toEqual(cue.supporting_event_ids)
    const source = await (await request.get(`/api/matches/comeback-1107/insights/${cue.insight_id}/evidence?at_second=${cutoff}`)).json()
    expect(source.source_events.every((event: { match_second: number }) => event.match_second <= cutoff)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath(`broadcast-proof-${width}.png`), fullPage: false })
    await page.keyboard.press('Escape')
    await expect(evidence).toBeFocused()
    const exported = await (await request.get((await entry.getByRole('link').getAttribute('href'))!)).json()
    expect(exported).toEqual(cue)
    await page.getByRole('slider', { name: 'Seek match time' }).fill(String(cue.end_match_second))
    await expect(entry.locator('.cue-row')).not.toHaveClass(/active/)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2)).toBe(true)
  })
}
