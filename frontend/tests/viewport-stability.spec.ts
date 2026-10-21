import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`replay updates retain the viewport and explicit navigation still scrolls at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 })
    await page.goto('/')
    const seek = page.getByRole('slider', { name: 'Seek match time' })
    await seek.fill('1000')
    await expect(page.locator('.recap-body')).not.toContainText('Loading')
    // Exercise near the document end, including temporary analytics loading collapse.
    await page.locator('.studio').scrollIntoViewIfNeeded()
    const initial = await page.evaluate(() => window.scrollY)
    expect(initial).toBeGreaterThan(500)
    // Change the real React replay control without Playwright scrolling it into view.
    // This exercises the same state and backend analytics as playback.
    for (const second of [3500, 5400, 1000, 3500]) {
      await seek.evaluate((element, value) => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(element, String(value))
        element.dispatchEvent(new Event('input', { bubbles: true }))
        element.dispatchEvent(new Event('change', { bubbles: true }))
      }, second)
      await expect(seek).toHaveValue(String(second))
      await expect(page.locator('.recap-body')).not.toContainText('Loading')
      await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(initial)
    }
    const beforePlayback = Number(await seek.inputValue())
    await page.getByRole('button', { name: 'Play', exact: true }).dispatchEvent('click')
    await expect.poll(async () => Number(await seek.inputValue())).toBeGreaterThan(beforePlayback + 60)
    expect(await page.evaluate(() => window.scrollY)).toBe(initial)
    await page.getByRole('button', { name: 'Pause', exact: true }).dispatchEvent('click')
    // Explicit user navigation is still allowed to bring an offscreen control into view.
    await page.getByRole('button', { name: 'Next event', exact: true }).click()
    expect(await page.evaluate(() => window.scrollY)).toBeLessThan(initial)
    await expect(page.getByRole('slider', { name: 'Seek match time' })).toBeInViewport()
    await page.evaluate(() => window.scrollTo(0, 0))
    await expect.poll(() => page.evaluate(() => Number.parseFloat(document.getElementById('root')!.style.minHeight))).toBe(844)
  })
}
