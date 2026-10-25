import { defineConfig } from '@playwright/test'

const baseURL = process.env.PULSE_DEMO_URL
// Loopback HTTP is accepted only with an explicit opt-in, so a public check can never run against http.
const loopback = process.env.PULSE_DEMO_ALLOW_LOOPBACK === '1' && /^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(baseURL ?? '')
if (!baseURL || !(baseURL.startsWith('https://') || loopback)) {
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
