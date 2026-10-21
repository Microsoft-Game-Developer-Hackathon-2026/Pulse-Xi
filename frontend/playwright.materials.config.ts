import { defineConfig } from '@playwright/test'
import base from './playwright.config'

export default defineConfig({
  ...base, testDir:'./visual-tests', workers:1,
  projects:[{name:'chromium',use:{browserName:'chromium'}},{name:'firefox',use:{browserName:'firefox'}},{name:'webkit',use:{browserName:'webkit'}}],
})
