import { chromium } from './_pw.mjs'
const base = process.env.BASE_URL ?? 'http://127.0.0.1:8000'
const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] })
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } })
await p.goto(base + '/'); await p.waitForSelector('.metrics'); await p.waitForTimeout(1500)
await p.screenshot({ path: process.env.OUT ?? 'recon-1920.png' })
await p.evaluate(() => { document.documentElement.style.zoom = '1.25' }); await p.waitForTimeout(800)
await p.screenshot({ path: (process.env.OUT ?? 'recon').replace('.png', '') + '-zoom125.png' })
console.log(JSON.stringify(await p.evaluate(() => ({ w: innerWidth, h: innerHeight, classes: [...new Set([...document.querySelectorAll('section,div')].map(e => e.className).filter(c => /control|chaos|tactical|pass|analysis|studio|fan-lens|intelligence/i.test(String(c))))].slice(0, 30) }))))
await b.close()
