// Render the event-derived highlight reel from a running PULSE XI server.
//
//   node scripts/render-highlights.mjs --match comeback-1107 --out ../docs/examples/highlights/comeback-1107.webm
//   node scripts/render-highlights.mjs --match comeback-1107 --frame 9.5 --out frame.png
//
// BASE_URL defaults to http://127.0.0.1:8000. No paid service, footage or external asset is used:
// the page draws the reel from /api/matches/{id}/highlights and Chromium records it. The manifest
// (and its sha256) is deterministic; the WebM is a screen recording, so its bytes are not.
import { chromium } from '@playwright/test'
import { mkdirSync, renameSync, writeFileSync, statSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, index, all) => (value.startsWith('--') ? [...pairs, [value.slice(2), all[index + 1] && !all[index + 1].startsWith('--') ? all[index + 1] : 'true']] : pairs), []))
const base = process.env.BASE_URL ?? 'http://127.0.0.1:8000'
const match = args.match ?? 'comeback-1107'
const out = resolve(args.out ?? `highlights-${match}.webm`)
const frame = args.frame !== undefined ? Number(args.frame) : null
mkdirSync(dirname(out), { recursive: true })

const manifestResponse = await fetch(`${base}/api/matches/${encodeURIComponent(match)}/highlights`)
if (!manifestResponse.ok) throw new Error(`manifest request failed: ${manifestResponse.status}`)
const manifest = await manifestResponse.json()
const { width, height, total_seconds: total } = manifest.video

const browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] })
try {
  if (frame !== null) {
    const page = await browser.newPage({ viewport: { width, height } })
    await page.goto(`${base}/#/highlight-reel?match=${match}&render=1&t=${frame}`)
    await page.waitForSelector(`main[data-manifest="${manifest.manifest_sha256}"]`)
    await page.screenshot({ path: out })
    console.log(JSON.stringify({ frame_seconds: frame, out, manifest_sha256: manifest.manifest_sha256 }))
  } else {
    const context = await browser.newContext({ viewport: { width, height }, recordVideo: { dir: dirname(out), size: { width, height } } })
    const page = await context.newPage()
    const started = Date.now()
    await page.goto(`${base}/#/highlight-reel?match=${match}&render=1`)
    await page.waitForSelector('main[data-state="complete"]', { timeout: (total + 30) * 1000 })
    const wallSeconds = (Date.now() - started) / 1000
    const video = page.video()
    await context.close()
    renameSync(await video.path(), out)
    const report = { match_id: match, manifest_sha256: manifest.manifest_sha256, clips: manifest.clips.length, planned_seconds: total, recorded_wall_seconds: Number(wallSeconds.toFixed(1)), bytes: statSync(out).size, resolution: `${width}x${height}`, container: 'webm', out }
    writeFileSync(out.replace(/\.webm$/, '.json'), JSON.stringify({ ...report, out: undefined, source_events: manifest.clips.map(clip => ({ clip_id: clip.clip_id, insight_id: clip.insight_id, event_ids: clip.source_events.map(source => source.event_id) })) }, null, 2))
    console.log(JSON.stringify(report))
  }
} finally {
  await browser.close()
}
