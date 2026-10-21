import { defineConfig } from '@playwright/test'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

export default defineConfig({
  testDir: './tests',
  // Bound software-rendering concurrency on developer laptops and shared CI.
  // Dedicated multi-tab and SQLite race tests retain their own concurrency.
  workers: 2,
  use: { baseURL: 'http://127.0.0.1:8765', browserName: 'chromium', launchOptions: { args: ['--enable-unsafe-swiftshader'] } },
  webServer: {
    command: 'python -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8765',
    url: 'http://127.0.0.1:8765/health',
    // Each run owns its database and explicitly authorizes only the test importer.
    env: { PULSE_ENABLE_LOCAL_DATA_ADMIN: '1', PULSE_IMPORT_TOKEN: 'test-import-token-at-least-32-characters', PULSE_DB_PATH: join(mkdtempSync(join(tmpdir(), 'pulse-xi-browser-')), 'events.sqlite') },
    reuseExistingServer: false,
    timeout: 30000,
  },
})
