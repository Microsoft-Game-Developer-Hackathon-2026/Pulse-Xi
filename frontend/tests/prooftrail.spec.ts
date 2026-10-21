import { expect, test } from '@playwright/test'

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
