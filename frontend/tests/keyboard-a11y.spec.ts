import { expect, test } from '@playwright/test'

// Keyboard and accessibility-tree checks. These are NOT a screen-reader test: no NVDA, JAWS or
// VoiceOver ran. They cover what can be asserted without one: focus management, names, order.
const clockLabel = (second: number) => `${String(Math.floor(second / 60)).padStart(2, '0')}:${String(second % 60).padStart(2, '0')}`

test('every visible interactive control has an accessible name and none uses a positive tabindex', async ({ page }) => {
  for (const hash of ['#/', '#/sandbox', '#/runtime', '#/data', '#/studio']) {
    await page.goto(`/${hash}`)
    await page.waitForLoadState('networkidle')
    const report = await page.evaluate(() => {
      const named = (element: Element) => {
        const html = element as HTMLElement
        const labelledBy = html.getAttribute('aria-labelledby')?.split(/\s+/).map(id => document.getElementById(id)?.textContent ?? '').join(' ').trim()
        const wrapped = html.closest('label')?.textContent?.trim()
        const forLabel = html.id ? document.querySelector(`label[for="${CSS.escape(html.id)}"]`)?.textContent?.trim() : ''
        return Boolean(html.getAttribute('aria-label')?.trim() || labelledBy || wrapped || forLabel || html.getAttribute('title')?.trim() ||
          (html.tagName !== 'SELECT' && html.textContent?.trim()) || (html as HTMLInputElement).placeholder)
      }
      const controls = [...document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[tabindex]')].filter(element => (element as HTMLElement).checkVisibility())
      return {
        unnamed: controls.filter(element => !named(element)).map(element => `${element.tagName}.${(element as HTMLElement).className}`),
        positive: controls.filter(element => Number(element.getAttribute('tabindex')) > 0).map(element => element.tagName),
        count: controls.length,
      }
    })
    expect(report.count, `${hash} controls`).toBeGreaterThan(5)
    expect(report.unnamed, `${hash} unnamed controls`).toEqual([])
    expect(report.positive, `${hash} positive tabindex`).toEqual([])
  }
})

test('keyboard users get a visible focus indicator on the first controls', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.metrics')).toBeVisible()
  const missing: string[] = []
  for (let index = 0; index < 12; index++) {
    await page.keyboard.press('Tab')
    const state = await page.evaluate(() => {
      const element = document.activeElement as HTMLElement | null
      if (!element || element === document.body) return null
      const style = getComputedStyle(element)
      const visible = (style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0) || style.boxShadow !== 'none'
      return { visible, label: `${element.tagName}:${element.getAttribute('aria-label') ?? element.textContent?.trim().slice(0, 24)}` }
    })
    expect(state, `Tab ${index + 1} must land on a control`).not.toBeNull()
    if (!state!.visible) missing.push(state!.label)
  }
  expect(missing, 'focused controls without outline or ring').toEqual([])
})

test('proof drawer traps focus, closes with Escape and returns focus to the control that opened it', async ({ page, request }) => {
  const cues = await (await request.get('/api/matches/comeback-1107/overlays')).json() as { overlay_type: string; text: string; start_match_second: number }[]
  const cue = cues.find(item => item.overlay_type === 'goal')!
  await page.goto('/')
  const opener = page.getByRole('button', { name: `Inspect evidence for ${cue.text} at ${clockLabel(cue.start_match_second)}`, exact: true })
  await page.locator('.cue-entry').filter({ has: opener }).locator('.cue-row').click()
  await opener.focus()
  await page.keyboard.press('Enter')
  const drawer = page.getByRole('dialog', { name: 'Insight evidence' })
  await expect(drawer).toBeVisible()
  await expect(drawer).toHaveAttribute('aria-modal', 'true')
  const insideDrawer = () => page.evaluate(() => Boolean(document.activeElement?.closest('.proof-drawer')))
  expect(await insideDrawer(), 'focus starts inside the drawer').toBe(true)
  for (let index = 0; index < 25; index++) { await page.keyboard.press('Tab'); expect(await insideDrawer(), `forward Tab ${index + 1}`).toBe(true) }
  for (let index = 0; index < 25; index++) { await page.keyboard.press('Shift+Tab'); expect(await insideDrawer(), `backward Tab ${index + 1}`).toBe(true) }
  await page.keyboard.press('Escape')
  await expect(drawer).toBeHidden()
  await expect.poll(() => page.evaluate(() => (document.activeElement as HTMLElement | null)?.getAttribute('aria-label') ?? '')).toBe(await opener.getAttribute('aria-label'))
})

test('changing content is exposed through live regions and status roles', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.recap-body')).not.toContainText('Loading')
  expect(await page.locator('.recap-body').getAttribute('aria-live')).toBe('polite')
  expect(await page.locator('[role=status]').count(), 'status regions').toBeGreaterThan(1)
  // The replay slider exposes a name and a value to assistive technology.
  const slider = page.getByRole('slider', { name: 'Seek match time' })
  await expect(slider).toHaveAttribute('aria-valuenow', /\d+/).catch(async () => { expect(await slider.inputValue()).toMatch(/\d+/) })
})
