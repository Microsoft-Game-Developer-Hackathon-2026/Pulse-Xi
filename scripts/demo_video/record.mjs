// Record one storyboard scene from the real PULSE XI application.
//
//   node scripts/demo_video/record.mjs <scene> [--base https://pulse-xi-demo.onrender.com]
//
// Scenes: replay | evidence | audience | intelligence | reel | control | close.  `control` needs a local
// server with an operator token (the public demo disables operator tools by design):
//   DEMO_RUNTIME_TOKEN=<token> node scripts/demo_video/record.mjs control --base http://127.0.0.1:8000
import { openScene, sleep } from './lib.mjs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const args = process.argv.slice(2)
const name = args[0]
const base = (args.includes('--base') ? args[args.indexOf('--base') + 1] : process.env.BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')
const outDir = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'artifacts', 'demo', 'work', 'clips')

const useZoom = !args.includes('--viewport')
async function ready(page, path = '/') {
  await page.goto(base + path, { waitUntil: 'domcontentloaded', timeout: 180000 })
  await page.waitForSelector('.metrics', { timeout: 180000 })
  await page.waitForFunction(() => !document.querySelector('.recap-body')?.textContent?.includes('Loading'), null, { timeout: 120000 })
}

const scenes = {
  // Beat 1: replay. Scoreboard, pitch, metrics, transport and event wire all fit one frame at scroll 400.
  async replay(scene) {
    const { page } = scene
    await ready(page)
    await page.evaluate(() => scrollTo(0, 400)); await sleep(900)
    scene.noAutoScroll = true   // scoreboard, pitch, metrics, transport and wire stay in one frame
    scene.zero()
    await scene.at(4.2)
    // Drag the real seek slider to 14:00 so the 16:40 goal arrives shortly after play.
    const slider = page.getByRole('slider', { name: 'Seek match time' }); const box = await slider.boundingBox()
    const thumbX = box.x + 14 + (box.width - 28) * 0 // currently at 0
    await scene.glide(thumbX, box.y + box.height / 2, 500); await page.mouse.down()
    await scene.glide(box.x + 14 + (box.width - 28) * (840 / 5400), box.y + box.height / 2, 700); await page.mouse.up()
    await scene.at(6.3)
    await scene.click(page.locator('.speed button', { hasText: '2×' }), 500)
    await scene.at(7.2)
    await scene.click(page.getByRole('button', { name: 'Play', exact: true }), 450)
    await scene.at(10.0); await scene.ring(page.locator('.scoreboard .score'), 2200)
    await scene.at(13.6); await scene.ring(page.locator('.metrics'), 2200)
    await scene.at(16.2); await scene.ring(page.locator('.feed'), 2200)
    await scene.at(19.0)
    await scene.click(page.getByRole('button', { name: 'Pause', exact: true }), 450)
    scene.notes.matchClock = await page.locator('.match-clock').innerText()
    return scene.finish(21.6, { matchClockAtEnd: scene.notes.matchClock })
  },

  // Beat 2: evidence drawer and One Moment, Three Stories.
  async evidence(scene) {
    const { page } = scene
    await ready(page)
    await (useZoom ? (f) => scene.zoom(f) : async () => {})(1.25)
    await scene.reveal('.studio', 'center')
    scene.zero()
    const entry = page.locator('.cue-entry').first()
    await scene.at(1.0); await scene.click(entry.locator('.cue-row'), 600)
    await scene.at(3.6); await scene.click(entry.locator('.cue-proof'), 500)
    const drawer = page.locator('.proof-drawer')
    await drawer.waitFor({ state: 'visible' })
    await page.getByTestId('three-stories').locator('[data-lens="fan"]').getByText('Loading').waitFor({ state: 'detached', timeout: 60000 }).catch(() => {})
    await scene.at(5.2); await drawer.evaluate(el => el.scrollTo({ top: 520, behavior: 'smooth' }))
    await scene.at(7.2); await drawer.evaluate(el => el.scrollTo({ top: 0, behavior: 'smooth' }))
    const stories = page.getByTestId('three-stories')
    await scene.at(8.8); await scene.ring(stories.locator('[data-lens="analyst"]'), 1500)
    await scene.at(10.4); await scene.ring(stories.locator('[data-lens="fan"]'), 1500)
    await scene.at(12.0); await scene.ring(stories.locator('[data-lens="director"]'), 1600)
    await scene.at(14.6); await scene.ring(stories.locator('.cue-status'), 3200)
    await scene.at(18.0); await scene.ring(stories.locator('.story-check'), 2200)
    scene.notes.storyCheck = await stories.locator('.story-check').innerText()
    scene.notes.director = await stories.locator('[data-lens="director"]').innerText()
    return scene.finish(22.0, { storyCheck: scene.notes.storyCheck })
  },

  // Beat 3: same facts, different audience and language.
  async audience(scene) {
    const { page } = scene
    await ready(page)
    await scene.seekSlider(4700); await sleep(2500)
    // No zoom: at 1080p the VIEW/LANGUAGE selects and the recap they change fit in one frame.
    await scene.reveal('.recap-controls', 'start'); await page.evaluate(() => scrollBy(0, -50)); await sleep(500)
    await page.waitForFunction(() => !document.querySelector('.recap-body')?.textContent?.includes('Loading'))
    scene.noAutoScroll = true
    scene.zero()
    const selects = page.locator('.recap-controls select')
    await scene.at(0.8); await scene.choose(selects.nth(0), 'analyst', 550)
    await scene.at(4.4); await scene.choose(selects.nth(0), 'broadcaster', 450)
    await scene.at(8.0); await scene.choose(selects.nth(1), 'es', 450)
    await scene.at(10.6); await scene.ring(page.locator('.recap-body'), 2000)
    scene.notes.recap = (await page.locator('.recap-body').innerText()).slice(0, 160)
    return scene.finish(12.6)
  },

  // Beat 4: Control vs Chaos, then the pass inspector.
  async intelligence(scene) {
    const { page } = scene
    await ready(page)
    await scene.seekSlider(4200); await sleep(2500)   // 70:00: a real rule-based turning point exists here
    await (useZoom ? (f) => scene.zoom(f) : async () => {})(1.3)
    await scene.reveal('.control-chaos .control-rhythm', 'center')
    scene.zero()
    await scene.at(0.8); await scene.ring(page.locator('.control-chaos .control-rhythm'), 2500)
    await scene.at(3.0)
    await scene.reveal('.control-chaos .control-turning-points', 'center', true, 800)
    await scene.click(page.locator('.control-turning-points button').first(), 500)
    await sleep(900)
    await scene.at(5.0)
    await scene.reveal('.pass-workbench', 'start', true, 1300)
    await scene.at(7.0); await scene.ring(page.locator('.pass-workbench .pass-score, .pass-workbench .pass-scorecard').first(), 2200)
    scene.notes.turningPoint = await page.locator('.control-turning-points button').first().innerText().catch(() => '')
    return scene.finish(11.0, { turningPoint: scene.notes.turningPoint })
  },

  // Beat 6: the highlight reel plays in real time; the editor trims an excerpt using dt0.
  async reel(scene) {
    const { page } = scene
    await page.goto(base + '/#/highlight-reel?match=comeback-1107&render=1', { waitUntil: 'domcontentloaded', timeout: 180000 })
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.waitForSelector('main.reel[data-manifest]', { timeout: 120000 })
    // The stage is 1280x720: x1.5 fills the frame. Pin the container to the stage height so 100vh does not offset it.
    await page.addStyleTag({ content: 'html{zoom:1.5} main.reel{min-height:720px!important;height:720px!important}' }); await sleep(600)
    scene.zero()
    scene.notes.dt0 = Number(await page.locator('main.reel').getAttribute('data-time'))
    await scene.at(24)
    scene.notes.dt1 = Number(await page.locator('main.reel').getAttribute('data-time'))
    return scene.finish(24.5, { dt0: scene.notes.dt0, dt1: scene.notes.dt1 })
  },

  // Beat 7: closing hold on the real app at full time (the end card is composited in the editor).
  async close(scene) {
    const { page } = scene
    await ready(page)
    await scene.seekSlider(5400); await sleep(2500)
    await page.evaluate(() => scrollTo(0, 400)); await sleep(900)
    scene.zero()
    await scene.at(2.0); await scene.ring(page.locator('.scoreboard .score'), 2600)
    await scene.at(6.0); await scene.ring(page.locator('.metrics'), 2600)
    scene.notes.clock = await page.locator('.match-clock').innerText()
    scene.notes.score = await page.locator('.scoreboard .score').innerText()
    return scene.finish(14.0, { clock: scene.notes.clock, score: scene.notes.score })
  },

  // Beat 5: Control Room on a local server. Marks let the editor shorten server wait time.
  async control(scene) {
    const { page } = scene
    const token = process.env.DEMO_RUNTIME_TOKEN
    if (!token) throw new Error('DEMO_RUNTIME_TOKEN is required for the control scene')
    await page.goto(base + '/#/runtime', { waitUntil: 'domcontentloaded' })
    await page.getByLabel('Operator access token').waitFor({ timeout: 60000 })
    await (useZoom ? (f) => scene.zoom(f) : async () => {})(1.2)
    scene.instantScroll = true
    const marks = {}
    scene.zero()
    const mark = label => { marks[label] = scene.elapsed() }
    await sleep(800)
    await scene.click(page.getByLabel('Operator access token'), 500); await page.keyboard.type(token, { delay: 4 })
    await scene.click(page.getByRole('button', { name: 'Connect operator', exact: true }), 450)
    await page.getByRole('button', { name: 'Disconnect operator' }).waitFor({ timeout: 60000 }); mark('connected')
    await page.waitForLoadState('networkidle')
    if (!(await page.getByRole('button', { name: 'Create authoritative scenario' }).isVisible())) await page.getByText('Scenario builder', { exact: true }).click()
    await page.getByLabel('Duration seconds', { exact: true }).fill('300')
    await page.getByLabel('Initial seed', { exact: true }).fill('98765')
    mark('configured')
    await scene.click(page.getByRole('button', { name: 'Create authoritative scenario', exact: true }), 500)
    await page.getByLabel('Authoritative match clock').filter({ hasText: '00:00' }).waitFor({ timeout: 60000 }); mark('created')
    await page.getByLabel('Step seconds').fill('20')
    await scene.click(page.getByRole('button', { name: 'Step engine', exact: true }), 500)
    await page.getByLabel('Authoritative match clock').filter({ hasText: '00:20' }).waitFor({ timeout: 60000 }); mark('stepped')
    await scene.click(page.getByRole('button', { name: 'Save exact checkpoint' }), 500)
    await page.getByLabel('Saved checkpoint').locator('option').nth(1).waitFor({ state: 'attached', timeout: 60000 }); mark('checkpoint')
    await scene.click(page.getByRole('button', { name: 'Apply future tactic' }), 500)
    await page.getByText(/Pending pressing = \d+ at 00:21/).waitFor({ timeout: 60000 }); mark('tactic')
    await page.getByLabel('Step seconds').fill('1')
    await scene.click(page.getByRole('button', { name: 'Step engine', exact: true }), 450)
    await page.getByLabel('Authoritative match clock').filter({ hasText: '00:21' }).waitFor({ timeout: 60000 }); mark('applied')
    const cp = await page.getByLabel('Saved checkpoint').locator('option').nth(1).getAttribute('value')
    await page.getByLabel('Saved checkpoint').selectOption(cp)
    await page.getByLabel('Paired trials').fill('1')
    await page.getByLabel('Experiment horizon seconds').fill('60')
    mark('fork-configured')
    await scene.click(page.getByRole('button', { name: 'Run paired ForkCast' }), 500); mark('fork-start')
    await page.getByText(/Experiment completed/).waitFor({ timeout: 120000 }); mark('fork-done')
    await page.getByRole('table').waitFor({ timeout: 60000 }); await sleep(600)
    await scene.click(page.getByRole('button', { name: 'Verify experiment independently', exact: true }), 600); mark('verify-start')
    await page.getByText('Experiment independently reproduced: paired branches and metrics match.').waitFor({ timeout: 120000 }); mark('verify-done')
    await sleep(2500); mark('end')
    return scene.finish(scene.elapsed() + 0.1, { marks })
  },
}

if (!scenes[name]) { console.error('unknown scene', name); process.exit(2) }
const vp = (args.includes('--viewport') ? args[args.indexOf('--viewport') + 1] : '1920x1080').split('x').map(Number)
const scene = await openScene({ name, outDir, width: vp[0], height: vp[1], videoWidth: 1920, videoHeight: 1080 })
try {
  const report = await scenes[name](scene)
  console.log(JSON.stringify({ ...report, video: undefined }))
} catch (error) {
  console.error('SCENE FAILED:', error.message); await scene.page.screenshot({ path: join(outDir, `${name}-failure.png`) }).catch(() => {}); process.exitCode = 1
  await scene.page.context().close().catch(() => {})
}
process.exit(process.exitCode ?? 0)
