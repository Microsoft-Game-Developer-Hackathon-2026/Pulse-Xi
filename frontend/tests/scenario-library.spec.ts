import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import type { ScenarioArchive, View } from '../src/features/runtime/api'

const token = 'test-runtime-token-at-least-32-characters'
const headers = { Authorization: `Bearer ${token}` }

async function connect(page: Page) {
  await page.goto('/#/runtime')
  await page.getByLabel('Operator access token').fill(token)
  await page.getByRole('button', {name: 'Connect operator', exact: true}).click()
  await expect(page.getByRole('button', {name: 'Disconnect operator'})).toBeVisible()
  if (await page.getByLabel(/^Runtime \/ branch/).inputValue()) await expect(page.getByLabel('Authoritative match clock')).toBeVisible()
  if (!await page.getByRole('button', {name: 'Save scenario', exact: true}).isVisible()) {
    await page.getByText('Scenario builder', {exact: true}).click()
  }
  await expect(page.getByRole('button', {name: 'Save scenario', exact: true})).toBeVisible()
}

test('all presets save through the backend without creating a runtime', async ({page, request}) => {
  const sessionWrites: string[] = []
  page.on('request', req => { if (req.method() === 'POST' && req.url().endsWith('/api/sandbox/sessions')) sessionWrites.push(req.url()) })
  await connect(page)
  for (const preset of ['balanced', 'high-press', 'late-comeback', 'stalemate']) {
    await page.getByLabel(/^Scenario preset/).selectOption(preset)
    await page.getByLabel('Initial seed', {exact: true}).fill('192837')
    await page.getByRole('button', {name: 'Save scenario', exact: true}).click()
    await expect(page.locator('.runtime-notice')).toContainText('Scenario saved without creating a runtime session.')
    await expect(page.getByRole('region', {name: 'Saved scenario provenance'})).toContainText(`${preset} / 192837`)
  }
  const saved = await (await request.get('/api/sandbox/scenarios', {headers})).json()
  expect(saved.filter((s: {seed: number}) => s.seed === 192837)).toHaveLength(4)
  expect(sessionWrites).toEqual([])
})

test('save, reload, archive import/export and real engine runs preserve configuration and event hash', async ({page, request}) => {
  await connect(page)
  await page.getByLabel(/^Scenario preset/).selectOption('high-press')
  await page.getByLabel('Initial seed', {exact: true}).fill('271828')
  await page.getByLabel('Duration seconds', {exact: true}).fill('120')
  await page.getByLabel('Initial away tempo', {exact: true}).fill('87')
  await page.getByRole('button', {name: 'Save scenario', exact: true}).click()
  await expect(page.locator('.runtime-notice')).toContainText('Scenario saved without creating a runtime session.')
  const id = await page.getByRole('combobox', {name: /^Saved scenario/}).inputValue()
  expect(id).toMatch(/^scenario-[a-f0-9]{64}$/)
  const download = page.waitForEvent('download')
  await page.getByRole('button', {name: 'Download scenario JSON', exact: true}).click()
  const packet: ScenarioArchive = JSON.parse(await readFile(await (await download).path() as string, 'utf8'))
  expect(packet.scenario.scenario_id).toBe(id)
  expect(packet.created_at_utc).toMatch(/Z$/)
  expect(packet.scenario.config.away.tactics.tempo).toBe(87)
  expect(JSON.stringify(packet)).not.toContain(token)
  expect(Object.keys(packet).sort()).toEqual(['archive_version', 'created_at_utc', 'rng_algorithm', 'rng_derivation', 'rng_streams', 'scenario'])
  await page.reload(); await connect(page)
  await page.getByRole('combobox', {name: /^Saved scenario/}).selectOption(id)
  await page.getByRole('button', {name: 'Load saved scenario', exact: true}).click()
  await expect(page.locator('.runtime-notice')).toContainText('Saved scenario loaded into the builder.')
  await expect(page.getByLabel('Initial seed', {exact: true})).toHaveValue('271828')
  await expect(page.getByLabel('Initial away tempo', {exact: true})).toHaveValue('87')
  await expect(page.getByRole('region', {name: 'Saved scenario provenance'})).toContainText(packet.scenario.config_hash)
  const eventHashes: string[] = []
  for (let run = 0; run < 2; run++) {
    if (run === 1) {
      if (!await page.getByRole('button', {name: 'Save scenario', exact: true}).isVisible()) await page.getByText('Scenario builder', {exact: true}).click()
      if (!await page.getByLabel('Import scenario file', {exact: true}).isVisible()) await page.getByText('Custom rosters and JSON import', {exact: true}).click()
      await page.getByLabel('Import scenario file', {exact: true}).setInputFiles({name: 'scenario.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(packet))})
      await page.getByRole('button', {name: 'Validate and load scenario JSON', exact: true}).click()
      await expect(page.locator('.runtime-notice')).toContainText('Scenario validated and saved.')
    }
    const previous = await page.getByLabel(/^Runtime \/ branch/).inputValue()
    await page.getByRole('button', {name: 'Create authoritative scenario', exact: true}).click()
    await expect(page.getByLabel(/^Runtime \/ branch/)).not.toHaveValue(previous)
    await expect(page.getByLabel('Authoritative match clock')).toHaveText('00:00')
    const sid = await page.getByLabel(/^Runtime \/ branch/).inputValue()
    const response = await request.post(`/api/sandbox/sessions/${sid}/commands`, {headers, data: {operation_id: `scenario-library-${run}`, expected_revision: 0, kind: 'step', ticks: 120}})
    expect(response.ok(), await response.text()).toBe(true)
    const view: View = await (await request.get(`/api/sandbox/sessions/${sid}/state`, {headers})).json()
    eventHashes.push(view.event_hash)
    expect(view.state.scenario).toEqual(packet.scenario)
  }
  expect(eventHashes[0]).toBe(eventHashes[1])
  const stored = await (await request.get(`/api/sandbox/scenarios/${id}/archive`, {headers})).json()
  expect(stored).toEqual(packet)
  expect(await page.evaluate(() => JSON.stringify({...localStorage, ...sessionStorage}))).not.toContain(token)
})

test('imports expose real validation, conflict, duplicate-key and size failures without a false success', async ({page, request}) => {
  await connect(page)
  await page.getByRole('button', {name: 'Save scenario', exact: true}).click()
  await expect(page.locator('.runtime-notice')).toContainText('Scenario saved without creating a runtime session.')
  const id = await page.getByRole('combobox', {name: /^Saved scenario/}).inputValue()
  const packet: ScenarioArchive = await (await request.get(`/api/sandbox/scenarios/${id}/archive`, {headers})).json()
  await page.getByText('Custom rosters and JSON import', {exact: true}).click()
  const json = page.getByRole('textbox', {name: 'Scenario configuration JSON', exact: true})
  await json.fill(JSON.stringify({...packet, scenario: {...packet.scenario, config_hash: '0'.repeat(64)}}))
  await page.getByRole('button', {name: 'Validate and load scenario JSON', exact: true}).click()
  await expect(page.getByRole('alert')).toContainText('scenario_hash_mismatch')
  await json.fill(JSON.stringify({...packet, archive_version: 'future/1'}))
  await page.getByRole('button', {name: 'Validate and load scenario JSON', exact: true}).click()
  await expect(page.getByRole('alert')).toContainText('archive_version')
  await json.fill('{"seed":1,"seed":2}')
  await page.getByRole('button', {name: 'Validate and load scenario JSON', exact: true}).click()
  await expect(page.getByRole('alert')).toContainText('ambiguous')
  await page.getByLabel('Import scenario file', {exact: true}).setInputFiles({name: 'oversized.json', mimeType: 'application/json', buffer: Buffer.alloc(2_000_001, ' ')})
  await expect(page.getByRole('alert')).toContainText('exceeds 2 MB')
  expect(await (await request.get(`/api/sandbox/scenarios/${id}/archive`, {headers})).json()).toEqual(packet)
})

test('disconnect discards an uncertain mutation and private builder state while retaining the server library', async ({page, request}) => {
  await connect(page)
  await page.getByLabel('Initial seed', {exact: true}).fill('314159')
  await page.route('**/api/sandbox/scenarios', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    const committed = await route.fetch()
    expect(committed.ok()).toBe(true)
    await route.fulfill({status: 503, json: {detail: {code: 'transaction_failed'}}})
  }, {times: 1})
  await page.getByRole('button', {name: 'Save scenario', exact: true}).click()
  await expect(page.getByRole('button', {name: 'Retry original operation safely'})).toBeVisible()
  await page.getByRole('button', {name: 'Disconnect operator'}).click()
  await connect(page)
  await expect(page.getByRole('button', {name: 'Retry original operation safely'})).toHaveCount(0)
  await expect(page.getByRole('region', {name: 'Saved scenario provenance'})).toHaveCount(0)
  await expect(page.getByLabel('Initial seed', {exact: true})).toHaveValue('7')
  const saved = await (await request.get('/api/sandbox/scenarios', {headers})).json()
  const record = saved.find((s: {seed: number}) => s.seed === 314159)
  expect(record).toBeTruthy()
  await page.getByRole('combobox', {name: /^Saved scenario/}).selectOption(record.scenario_id)
  await page.getByRole('button', {name: 'Load saved scenario', exact: true}).click()
  await expect(page.getByLabel('Initial seed', {exact: true})).toHaveValue('314159')
})
