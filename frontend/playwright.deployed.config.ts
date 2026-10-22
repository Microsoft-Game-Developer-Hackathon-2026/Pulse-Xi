import { defineConfig } from '@playwright/test'

const baseURL = process.env.PULSE_DEMO_URL
if (!baseURL || !baseURL.startsWith('https://')) {
  throw new Error('PULSE_DEMO_URL must be the deployed HTTPS origin')
}

export default defineConfig({
  testDir: './tests-deployed',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL,
    browserName: 'chromium',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
})
