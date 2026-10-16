import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './contract-tests',
  outputDir: './test-results/contracts',
  use: { baseURL: 'http://127.0.0.1:8766', browserName: 'chromium' },
  webServer: { command: 'npm run dev -- --port 8766 --strictPort', url: 'http://127.0.0.1:8766/contract-tests/preview.html', reuseExistingServer: false, timeout: 30000 },
})
