// Resolve Playwright from the frontend workspace so these scripts can live under scripts/.
import { createRequire } from 'node:module'
const require = createRequire(new URL('../../frontend/package.json', import.meta.url))
export const { chromium } = require('@playwright/test')
