import { expect, test } from '@playwright/test'

test('loads, seeks without future spoilers, and inspects tactical evidence', async ({ page, request }) => {
  const response = await request.get('/api/matches/comeback-1107/tactics?at_second=0')
  expect(response.ok()).toBeTruthy()
  expect((await response.json()).computed_from_event_count).toBe(1)
  await page.goto('/')
  await expect(page.getByText('TACTICAL LAB / OBSERVED EVENTS')).toBeVisible()
  await expect(page.locator('.score')).toContainText('0:0')
  await expect(page.getByText('Verified insights will appear as the replay reaches them.')).toBeVisible()
  await page.getByRole('slider', { name: 'Seek match time' }).fill('3500')
  await expect(page.locator('.score')).toContainText('0:2')
  await expect(page.locator('.insight-card')).toHaveCount(2)
  await page.getByRole('slider', { name: 'Seek match time' }).fill('5400')
  await expect(page.locator('.score')).toContainText('3:2')
  await expect(page.locator('.insight-card').first()).toBeVisible()
  await page.locator('.insight-card').first().getByRole('button').click()
  await expect(page.getByRole('dialog', { name: 'Insight evidence' })).toBeVisible()
  await expect(page.locator('.proof-event').first()).toBeVisible()
  await page.getByRole('button', { name: 'Close proof' }).click()
  await page.getByRole('slider', { name: 'Seek match time' }).fill('1000')
  await expect(page.locator('.studio-lower')).toBeVisible()
  await page.getByLabel('SHOW OVERLAYS').uncheck()
  await expect(page.locator('.studio-lower')).toHaveCount(0)
  await expect(page.getByRole('link', { name: /Export .* cue JSON/ }).first()).toHaveAttribute('href', /\/overlays\/cue-/)
})

test('Control vs Chaos stays synchronized with matched replay windows', async ({ page, request }) => {
  const response = await request.get('/api/matches/comeback-1107/control-chaos?at_second=1200&window_seconds=600')
  expect(response.ok()).toBeTruthy()
  const packet = await response.json()
  expect(packet.schema_version).toBe('control-chaos/1')
  expect(packet.window).toEqual({ start_second: 600, end_second: 1200 })
  expect(packet.previous_window).toEqual({ start_second: 0, end_second: 600 })
  expect(packet.formula_version).toBe('control-chaos-formulas/1')

  await page.goto('/')
  await expect(page.getByRole('region', { name: 'Control vs Chaos analysis' })).toBeVisible()
  await page.getByRole('slider', { name: 'Seek match time' }).fill('1200')
  await page.getByLabel('Control vs Chaos window').selectOption('600')
  await expect(page.locator('.control-toolbar')).toContainText('CURRENT 10:00–20:00')
  await expect(page.locator('.control-toolbar')).toContainText('PREVIOUS 0:00–10:00')
  await expect(page.getByText('RHYTHM TIMELINE / DESCRIPTIVE ACTIVITY INDEX')).toBeVisible()
  await expect(page.getByText(/Observed possession IDs are not possession time/)).toBeVisible()
})

test('match selection and mobile replay controls', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByLabel('SELECT MATCH').selectOption('high-press-2209')
  await expect(page.getByRole('heading', { name: 'Northbank high press' })).toBeVisible()
  await page.getByRole('button', { name: 'Play', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Pause', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Pause', exact: true }).click()
  await expect(page.getByRole('slider', { name: 'Seek match time' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 2)).toBeTruthy()
})

test('FanDNA changes the actual recap focus at the replay time', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('slider', { name: 'Seek match time' }).fill('3500')
  await page.getByLabel('VIEW').selectOption('favorite_team')
  await page.getByLabel('FANDNA / RECAP: FOLLOW TEAM', { exact: true }).selectOption('northbank')
  await expect(page.locator('.recap-body')).toContainText('Northbank United focus: 2 verified goals')
  await page.getByLabel('VIEW').selectOption('favorite_player')
  await expect(page.locator('.recap-body')).toContainText('completed passes')
  await page.getByRole('slider', { name: 'Seek match time' }).fill('0')
  await expect(page.locator('.recap-body')).toContainText("by 0' in this synthetic replay")
})

test('FanDNA localizes controls, persists valid preferences, and announces recap updates', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Language').selectOption('es')
  await expect(page.getByRole('link', { name: 'Análisis del partido' })).toBeVisible()
  await page.getByLabel('Vista').selectOption('favorite_team')
  await expect(page.getByLabel('FanDNA / resumen: Seguir equipo', { exact: true })).toBeVisible()
  await page.getByLabel('Idioma').focus()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('FanDNA / resumen: Seguir equipo', { exact: true })).toBeFocused()
  await page.getByLabel('Idioma').selectOption('hi')
  await expect(page.getByRole('link', { name: 'मैच विश्लेषण' })).toBeVisible()
  await page.getByLabel('भाषा').selectOption('es')
  await page.getByLabel('FanDNA / resumen: Seguir equipo', { exact: true }).selectOption('northbank')
  await page.getByRole('slider', { name: 'Buscar momento del partido' }).fill('3500')
  await expect(page.locator('.recap-body')).toHaveAttribute('aria-live', 'polite')
  await expect(page.locator('.recap-body')).toContainText('Enfoque en Northbank United')
  await page.reload()
  await expect(page.getByLabel('Idioma')).toHaveValue('es')
  await expect(page.getByLabel('Vista')).toHaveValue('favorite_team')
  await expect(page.getByLabel('FanDNA / resumen: Seguir equipo', { exact: true })).toHaveValue('northbank')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  const transition = await page.locator('.recap-body').evaluate(element => getComputedStyle(element).transitionDuration)
  expect(Number.parseFloat(transition)).toBeLessThan(0.001)
})

test('FanDNA speaks the visible recap only after explicit request and supports stop', async ({ page }) => {
  await page.addInitScript(() => {
    const calls: { text: string; lang: string; voice: string | null }[] = []
    let cancellations = 0
    class MockUtterance {
      text: string; lang = ''; voice: { lang: string } | null = null
      onstart: (() => void) | null = null; onend: (() => void) | null = null; onerror: (() => void) | null = null
      constructor(text: string) { this.text = text }
    }
    const voices = [{ lang: 'en-US' }, { lang: 'es-ES' }, { lang: 'hi-IN' }]
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: MockUtterance })
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
      getVoices: () => voices,
      speak: (utterance: MockUtterance) => { calls.push({ text: utterance.text, lang: utterance.lang, voice: utterance.voice?.lang ?? null }); queueMicrotask(() => utterance.onstart?.()) },
      cancel: () => { cancellations++ },
    } })
    Object.defineProperty(window, '__speechHarness', { configurable: true, value: { calls, cancellations: () => cancellations } })
  })
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Read recap aloud' })).toBeEnabled()
  const expected = await page.locator('.recap-body').evaluate(element => {
    const lead = element.querySelector('p')?.textContent ?? ''
    const moments = [...element.querySelectorAll('button span')].map(node => node.textContent ?? '')
    return [lead, ...moments].filter(Boolean).join('. ')
  })
  expect(await page.evaluate(() => (window as Window & { __speechHarness?: { calls: unknown[] } }).__speechHarness?.calls.length)).toBe(0)
  await page.getByRole('button', { name: 'Read recap aloud' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Reading the recap aloud.' })).toBeVisible()
  const spoken = await page.evaluate(() => (window as Window & { __speechHarness?: { calls: { text: string; lang: string; voice: string | null }[] } }).__speechHarness?.calls[0])
  expect(spoken).toEqual({ text: expected, lang: 'en-US', voice: 'en-US' })
  await page.getByRole('button', { name: 'Stop narration' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Narration stopped.' })).toBeVisible()
  expect(await page.evaluate(() => (window as Window & { __speechHarness?: { cancellations: () => number } }).__speechHarness?.cancellations())).toBeGreaterThan(0)
  await expect(page.locator('.recap-body')).toBeVisible()
})

test('FanDNA reports a missing device voice without removing the text recap', async ({ page }) => {
  await page.addInitScript(() => {
    class MockUtterance { constructor(_text: string) {} }
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: MockUtterance })
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { getVoices: () => [{ lang: 'en-US' }], speak: () => { throw new Error('must not speak without matching locale voice') }, cancel: () => undefined } })
  })
  await page.goto('/')
  await page.getByLabel('Language').selectOption('hi')
  await expect(page.getByRole('button', { name: 'सारांश ज़ोर से पढ़ें' })).toBeEnabled()
  await page.getByRole('button', { name: 'सारांश ज़ोर से पढ़ें' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'इस डिवाइस पर हिन्दी की वाणी उपलब्ध नहीं है' })).toBeVisible()
  await expect(page.locator('.recap-body p')).not.toBeEmpty()
})

test('Fan Lens follows event metrics at replay time and filters alert history', async ({ page, request }) => {
  const response = await request.get('/api/matches/comeback-1107/fan-lens?at_second=5400&metric_id=pressure_events&threshold_id=few&team_id=harbour')
  expect(response.ok()).toBeTruthy()
  const packet = await response.json()
  expect(packet.formula_version).toBe('fan-lens-windows/1')
  expect(packet.alerts.length).toBeGreaterThan(0)
  expect(packet.alerts.every((alert: { window_end: number; supporting_event_ids: string[] }) => alert.window_end <= 5400 && alert.supporting_event_ids.length > 0)).toBeTruthy()

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'FAN LENS / FOLLOW A METRIC' })).toBeVisible()
  await page.getByLabel('METRIC', { exact: true }).selectOption('shots')
  await page.getByLabel('ALERT THRESHOLD', { exact: true }).selectOption('few')
  await page.getByLabel('FAN LENS / FOLLOW A METRIC: FOLLOW TEAM', { exact: true }).selectOption('harbour')
  await page.getByRole('slider', { name: 'Seek match time' }).fill('5400')
  await expect(page.getByRole('region', { name: 'ALERTS' })).toContainText('shots')
  await page.getByLabel('LANGUAGE').selectOption('es')
  await expect(page.getByRole('heading', { name: 'FAN LENS / SEGUIR UNA MÉTRICA' })).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('MÉTRICA', { exact: true })).toHaveValue('shots')
})


test('localized preferences survive saved scenario navigation without persisting operator credentials', async ({ page }) => {
  const token = 'test-fandna-navigation-token-at-least-32-characters'
  await page.goto('/')
  await page.getByLabel('Language').selectOption('es')
  await page.getByLabel('Vista').selectOption('analyst')
  await page.locator('a[href="#/runtime"]').click()
  await page.getByLabel('Operator access token').fill(token)
  await page.getByRole('button', { name: 'Connect operator', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Disconnect operator' })).toBeVisible()
  if (!await page.getByRole('button', { name: 'Save scenario', exact: true }).isVisible()) await page.getByText('Scenario builder', { exact: true }).click()
  await page.getByLabel('Initial seed', { exact: true }).fill('54321')
  await page.getByRole('button', { name: 'Save scenario', exact: true }).click()
  await expect(page.locator('.runtime-notice')).toContainText('Scenario saved without creating a runtime session.')
  await page.locator('a[href="#/"]').click()
  await expect(page.getByLabel('Idioma')).toHaveValue('es')
  await expect(page.getByLabel('Vista')).toHaveValue('analyst')
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain(token)
  await page.reload()
  await expect(page.getByLabel('Idioma')).toHaveValue('es')
})
