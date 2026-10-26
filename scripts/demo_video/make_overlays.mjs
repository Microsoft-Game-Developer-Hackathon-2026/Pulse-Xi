// Render the original title card, end card and provenance chips as transparent 1920x1080 PNGs.
// Text only: no logos, third-party marks, stock imagery or copied assets.
import { chromium } from './_pw.mjs'
import { mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const outDir = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'artifacts', 'demo', 'work', 'overlays')
mkdirSync(outDir, { recursive: true })
const font = `-apple-system, "Segoe UI", Arial, sans-serif`
const base = `html,body{margin:0;width:1920px;height:1080px;background:transparent;font-family:${font};color:#f5f4ef}`

const pages = {
  title: `<style>${base}
    .wrap{position:absolute;inset:0;display:grid;place-items:center;background:radial-gradient(1100px 600px at 50% 40%,#17302bee 0%,#0b0d0ef7 70%)}
    .card{text-align:center}
    .eyebrow{font-size:26px;letter-spacing:6px;color:#b6e4d5;margin-bottom:24px}
    h1{font-size:176px;margin:0;letter-spacing:-6px;font-weight:700}h1 em{font-style:normal;color:#b6e4d5}
    p{font-size:44px;margin:28px 0 0;color:#d9dcdc}
    small{display:block;margin-top:40px;font-size:26px;letter-spacing:3px;color:#9aa3a3}</style>
    <div class="wrap"><div class="card"><div class="eyebrow">MICROSOFT GAME DEVELOPER HACKATHON 2026</div><h1>PULSE <em>XI</em></h1><p>Synthetic football intelligence, with evidence behind every story.</p><small>SYNTHETIC EVENTS · NO MATCH FOOTAGE</small></div></div>`,
  endcard: `<style>${base}
    .wrap{position:absolute;inset:0;display:grid;place-items:center;background:radial-gradient(1100px 600px at 50% 40%,#17302bf2 0%,#0b0d0efa 72%)}
    .card{text-align:center;max-width:1500px}
    h1{font-size:132px;margin:0;letter-spacing:-4px}h1 em{font-style:normal;color:#b6e4d5}
    p{font-size:38px;margin:22px 0 0;color:#d9dcdc}
    .links{margin-top:46px;font-size:34px;line-height:1.7;color:#f5f4ef}.links b{color:#b6e4d5;font-weight:600}
    .note{margin-top:38px;font-size:26px;color:#9aa3a3;line-height:1.5}</style>
    <div class="wrap"><div class="card"><h1>PULSE <em>XI</em></h1><p>Explainable match intelligence from synthetic football events.</p>
    <div class="links"><div><b>Live demo</b> &nbsp;pulse-xi-demo.onrender.com</div><div><b>Code</b> &nbsp;github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi</div></div>
    <div class="note">Rule-based explanations · Microsoft Agent Framework path verified offline · No hosted model claimed</div></div></div>`,
}
const chip = (dot, text) => `<style>${base}
  .chip{position:absolute;top:12px;left:50%;transform:translateX(-50%);display:flex;gap:12px;align-items:center;padding:8px 20px;border-radius:999px;background:#0b0d0ed9;border:1px solid #ffffff2e;font-size:23px;letter-spacing:.4px;white-space:nowrap}
  .dot{width:12px;height:12px;border-radius:50%;background:${dot}}</style><div class="chip"><span class="dot"></span><span>${text}</span></div>`
pages['chip-live'] = chip('#b6e4d5', 'LIVE DEMO · pulse-xi-demo.onrender.com · synthetic data')
pages['chip-local'] = chip('#efcda7', 'LOCAL RUN · operator tools are disabled on the public demo')
pages['chip-reel'] = chip('#b6e4d5', 'LIVE DEMO · event-derived highlight reel · no match footage')

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
for (const [name, html] of Object.entries(pages)) {
  await page.setContent(`<!doctype html><html><body>${html}</body></html>`)
  await page.screenshot({ path: join(outDir, `${name}.png`), omitBackground: true })
  console.log('overlay', name)
}
await browser.close()
