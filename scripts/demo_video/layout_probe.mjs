import { chromium } from './_pw.mjs'
const base = process.env.BASE_URL ?? 'http://127.0.0.1:8000'
const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] })
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } })
await p.goto(base + '/'); await p.waitForSelector('.metrics')
await p.getByRole('slider', { name: 'Seek match time' }).evaluate((el, v) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, String(v)); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })) }, 3500)
await p.waitForTimeout(2500)
const marks = await p.evaluate(() => Object.fromEntries(['.scoreboard', '.pitch-wrap', '.transport', '.moments', '.metrics', '.feed', '.analysis-tools', '.tactical-lab', '.pass-workbench', '.control-chaos', '.intelligence-grid', '.recap-body', '.fan-lens', '.studio'].map(s => { const e = document.querySelector(s); if (!e) return [s, null]; const r = e.getBoundingClientRect(); return [s, [Math.round(r.top + scrollY), Math.round(r.height)]] })))
console.log(JSON.stringify({ docHeight: await p.evaluate(() => document.documentElement.scrollHeight), marks }))
let i = 0
for (const y of (process.env.YS ?? '250,900,1700,2400,3100').split(',').map(Number)) { await p.evaluate(v => scrollTo(0, v), y); await p.waitForTimeout(500); await p.screenshot({ path: `${process.env.OUTDIR}/probe-${i++}-y${y}.png` }) }
await b.close()
