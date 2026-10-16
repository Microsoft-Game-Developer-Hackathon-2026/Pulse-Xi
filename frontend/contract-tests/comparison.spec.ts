import { expect, test } from '@playwright/test'
import { comparisonProblems } from '../src/features/experiments/comparisonContract'
import { fixture } from './fixtures'

test('comparison boundary rejects malformed input and unsupported contract values without crashing', () => {
  for (const value of [null, undefined, [], {}, { ...fixture, baseline: null },
    { ...fixture, metrics: [null] }, { ...fixture, paired_trial_ids: null }]) {
    expect(comparisonProblems(value as typeof fixture).length).toBeGreaterThan(0)
  }
  const changes = [
    (value: typeof fixture) => { value.parent_checkpoint.checkpoint_id = ' ' },
    (value: typeof fixture) => { value.baseline.trial_hashes.extra = 'unpaired-output' },
    (value: typeof fixture) => { value.baseline.trial_hashes.t1 = ' ' },
    (value: typeof fixture) => { value.verification_status = 'verified_rule_based' },
    (value: typeof fixture) => { value.metrics[0].metric_id = 'invented' as 'shots' },
    (value: typeof fixture) => { value.metrics[0].baseline.min = 1 },
    (value: typeof fixture) => { value.metrics[0].supporting_events.push(value.metrics[0].supporting_events[0]) },
  ]
  for (const change of changes) {
    const value = structuredClone(fixture); change(value)
    expect(comparisonProblems(value).length).toBeGreaterThan(0)
  }
})

test('proposed comparison rejects fabricated differences and invalid branch/trial/time provenance', () => {
  expect(comparisonProblems(fixture)).toEqual([])
  const bad = structuredClone(fixture)
  bad.metrics[0].mean_delta = 99
  expect(comparisonProblems(bad)).toContain('Calculated difference disagrees: shots.')
  bad.metrics[0].mean_delta = 1
  bad.metrics[0].supporting_events[0].match_second = 5401
  expect(comparisonProblems(bad)).toContain('Unsupported event scope/time: shots.')
  bad.metrics[0].supporting_events[0].match_second = 4000
  bad.alternative.branch_id = bad.baseline.branch_id
  expect(comparisonProblems(bad)).toContain('Distinct branch identities are required.')
  bad.paired_seeds = []
  expect(comparisonProblems(bad)).toContain('Paired trials/seeds are invalid or exceed the proposed limit.')
})

test('comparison fixture is explicitly labeled and evidence is keyboard accessible', async ({ page }, testInfo) => {
  await page.goto('/contract-tests/preview.html')
  await expect(page.getByRole('status')).toContainText('DEVELOPMENT FIXTURE ONLY')
  await expect(page.getByRole('row', { name: /shots event count/ })).toContainText('+1')
  await page.getByText('Inspect comparison provenance and event evidence', { exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('fixture-parent-hash', { exact: true })).toBeVisible()
  await expect(page.getByText('fixture-event', { exact: true })).toBeVisible()
  await page.getByRole('region', { name: 'ForkCast comparison' }).screenshot({ path: testInfo.outputPath('development-comparison.png') })
})

test('zero, missing, invalid, loading and error states stay distinct', async ({ page }) => {
  await page.goto('/contract-tests/preview.html')
  const state = page.getByLabel('PREVIEW STATE')
  await state.selectOption('zero')
  await expect(page.getByRole('row', { name: /shots event count/ })).toContainText('0')
  await state.selectOption('missing')
  await expect(page.getByRole('table')).toContainText('Unavailable')
  await state.selectOption('invalid')
  await expect(page.getByRole('alert')).toContainText('Comparison rejected')
  await state.selectOption('loading')
  await expect(page.getByRole('status')).toContainText('Waiting for authoritative experiment results')
  await state.selectOption('empty')
  await expect(page.getByText(/No experiment is connected/)).toBeVisible()
  await state.selectOption('error')
  await expect(page.getByRole('alert')).toContainText('Fixture API failure')
})

test('comparison display fits a mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/contract-tests/preview.html')
  await expect(page.getByRole('region', { name: 'ForkCast comparison' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2)).toBe(true)
})
