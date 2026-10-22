import { defineConfig } from '@playwright/test'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const testDirectory = mkdtempSync(join(tmpdir(), 'pulse-xi-browser-'))

export default defineConfig({
  testDir: './tests',
  // Bound software-rendering concurrency on developer laptops and shared CI.
  // Dedicated multi-tab and SQLite race tests retain their own concurrency.
  workers: 2,
  // Maximum-history replay is a resource probe, not a concurrent latency SLA.
  // Keep every functional assertion while giving ordinary journeys their own CPU budget.
  projects: [
    { name: 'regression', testIgnore: '**/forkcast-limit.spec.ts' },
    { name: 'bounded-forkcast', testMatch: '**/forkcast-limit.spec.ts', dependencies: ['regression'], workers: 1 },
  ],
  use: { baseURL: 'http://127.0.0.1:8765', browserName: 'chromium', launchOptions: { args: ['--enable-unsafe-swiftshader'] } },
  webServer: {
    command: 'python -m uvicorn app.main:app --loop app.local_event_loop:create_loop --app-dir ../backend --host 127.0.0.1 --port 8765',
    url: 'http://127.0.0.1:8765/health',
    // Each run owns both databases and authorizes only its test importer/operator.
    env: { PULSE_ENABLE_FOUNDRY: 'false', FOUNDRY_PROJECT_ENDPOINT: '', FOUNDRY_MODEL: '', PULSE_FOUNDRY_ADMIN_TOKEN: '', PULSE_ENABLE_LOCAL_DATA_ADMIN: '1', PULSE_IMPORT_TOKEN: 'test-import-token-at-least-32-characters', PULSE_RUNTIME_TOKEN: 'test-runtime-token-at-least-32-characters', PULSE_RUNTIME_TOKENS: JSON.stringify({operator: 'test-runtime-token-at-least-32-characters', 'forkcast-limit': 'test-forkcast-limit-token-at-least-32-characters'}), PULSE_RUNTIME_DRIVER: '1', PULSE_DB_PATH: join(testDirectory, 'events.sqlite'), PULSE_RUNTIME_DB_PATH: join(testDirectory, 'runtime.sqlite') },
    reuseExistingServer: false,
    timeout: 30000,
  },
})
