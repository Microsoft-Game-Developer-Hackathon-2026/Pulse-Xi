import { expect, test } from '@playwright/test'

test('real verified comparison cannot reappear after credentials and result are cleared', async ({page, request}) => {
  const token = 'test-runtime-token-at-least-32-characters'
  const headers = {Authorization: `Bearer ${token}`}
  const post = async (path: string, data: unknown) => {
    const response = await request.post(`/api/sandbox${path}`, {headers, data})
    expect(response.ok(), await response.text()).toBe(true)
    return response.json()
  }
  const config = (await (await request.get('/api/sandbox/presets', {headers})).json()).balanced
  config.duration_seconds = 120
  const scenario = await post('/scenarios', config)
  let baseline = await post('/sessions', {operation_id:'proof-clear-root', scenario_id:scenario.scenario_id})
  baseline = await post(`/sessions/${baseline.session_id}/commands`, {operation_id:'proof-clear-step', expected_revision:baseline.revision, kind:'step', ticks:20})
  baseline = await post(`/sessions/${baseline.session_id}/commands`, {operation_id:'proof-clear-checkpoint', expected_revision:baseline.revision, kind:'checkpoint'})
  let branch = await post(`/checkpoints/${baseline.checkpoint_id}/restore`, {operation_id:'proof-clear-restore', expected_revision:baseline.revision})
  branch = await post(`/sessions/${branch.session_id}/commands`, {operation_id:'press-change', expected_revision:branch.revision, kind:'intervene', team_id:config.home.team_id, field:'pressing', value:100, requested_tick:20})
  await post(`/sessions/${baseline.session_id}/commands`, {operation_id:'proof-clear-baseline-future', expected_revision:baseline.revision, kind:'step', ticks:100})
  await post(`/sessions/${branch.session_id}/commands`, {operation_id:'proof-clear-branch-future', expected_revision:branch.revision, kind:'step', ticks:100})
  await page.goto('/#/sandbox')
  await page.getByLabel('Operator bearer token').fill(token)
  await page.getByLabel('Baseline session ID').fill(baseline.session_id)
  await page.getByLabel('Branch session ID').fill(branch.session_id)
  await page.getByLabel('Intervention operation ID').fill('press-change')
  await page.getByLabel('Compare through tick').fill('120')
  await page.getByRole('button',{name:'Verify and compare',exact:true}).click()
  await expect(page.locator('.prooftrail-result')).toContainText('Verified manifest pair')
  let release!: () => void
  const blocked = new Promise<void>(resolve => { release = resolve })
  let arrived!: () => void
  const ready = new Promise<void>(resolve => { arrived = resolve })
  let delivered!: () => void
  const finished = new Promise<void>(resolve => { delivered = resolve })
  await page.route('**/api/sandbox/sessions/*/prooftrail**', async route => {
    const response = await route.fetch()
    expect(response.ok()).toBe(true)
    arrived(); await blocked
    await route.fulfill({response})
    delivered()
  })
  await page.getByRole('button',{name:'Verify and compare',exact:true}).click()
  await ready
  await page.getByRole('button',{name:'Clear',exact:true}).click()
  release(); await finished
  await expect(page.getByLabel('Operator bearer token')).toHaveValue('')
  await expect(page.locator('.prooftrail-result')).toHaveCount(0)
  expect(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))).not.toContain(token)
})

test('sandbox ProofTrail renders verified branch metrics and source citations', async ({ page }) => {
  await page.route('**/api/sandbox/sessions/*/prooftrail**', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      schema_version: 'sandbox-prooftrail/1',
      scenario_id: 'scenario-demo',
      branch_session_id: 'runtime-branch',
      baseline_session_id: 'runtime-base',
      checkpoint_id: 'checkpoint-demo',
      intervention: { operation_id: 'press-change', team_id: 'home', field: 'pressing', previous_value: 50, new_value: 100, effective_tick: 21 },
      branch_before_window: { start_tick: 0, end_tick: 21, metrics_by_team: { home: {goals:0,shots:0,recoveries:0,turnovers:0,passes:1,carries:1} }, evidence_event_ids: ['runtime-branch-1'] },
      baseline_before_window: { start_tick: 0, end_tick: 21, metrics_by_team: { home: {goals:0,shots:0,recoveries:0,turnovers:0,passes:1,carries:1} }, evidence_event_ids: ['runtime-base-1'] },
      branch_window: { start_tick: 21, end_tick: 40, metrics_by_team: { home: {goals:0,shots:1,recoveries:0,turnovers:0,passes:2,carries:0} }, evidence_event_ids: ['runtime-branch-8'] },
      baseline_window: { start_tick: 21, end_tick: 40, metrics_by_team: { home: {goals:0,shots:0,recoveries:0,turnovers:0,passes:1,carries:0} }, evidence_event_ids: ['runtime-base-7'] },
      metric_deltas_by_team: { home: {goals:0,shots:1,recoveries:0,turnovers:0,passes:1,carries:0} },
      manifest_hash: 'a'.repeat(64),
      branch_verification: 'verified',
      baseline_verification: 'verified',
      verification_result: 'verified',
      interpretation: 'single-run synthetic engine comparison; association only, not a real-world causal prediction',
      uncertainty: 'one deterministic trajectory per branch; statistical uncertainty is not estimated'
    }) })
  })

  await page.goto('/#/sandbox')
  await page.getByLabel('Operator bearer token').fill('a'.repeat(32))
  await page.getByLabel('Baseline session ID').fill('runtime-base')
  await page.getByLabel('Branch session ID').fill('runtime-branch')
  await page.getByLabel('Intervention operation ID').fill('press-change')
  await page.getByLabel('Compare through tick').fill('40')
  await page.getByRole('button', { name: 'Verify and compare' }).click()

  await expect(page.getByText('✓ VERIFIED')).toBeVisible()
  await expect(page.getByText(/association only, not a real-world causal prediction/)).toBeVisible()
  await page.locator('.prooftrail-window').nth(2).getByText('Evidence events (1)').click()
  await expect(page.getByText('runtime-branch-8')).toBeVisible()
  await expect(page.getByText('Verified manifest pair')).toBeVisible()
})
