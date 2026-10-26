// Recording helpers for the PULSE XI demo video. Every action is a real Playwright input event
// against the real application; the pointer and highlight rings are overlays drawn on top of it.
import { chromium } from './_pw.mjs'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

export const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
export const WIDTH = 1920
export const HEIGHT = 1080

// Playwright's recorder does not draw the OS cursor, so mirror real mouse events with a small ring.
const CURSOR_JS = `(() => {
  const make = () => {
    if (document.getElementById('__cursor')) return
    const cursor = document.createElement('div'); cursor.id = '__cursor'
    cursor.style.cssText = 'position:fixed;left:0;top:0;width:28px;height:28px;margin:-14px 0 0 -14px;border-radius:50%;border:2px solid #fff;background:rgba(182,228,213,.35);box-shadow:0 2px 12px rgba(0,0,0,.55);z-index:2147483647;pointer-events:none;opacity:0;transition:opacity .2s,transform .12s'
    document.documentElement.appendChild(cursor)
    addEventListener('mousemove', e => { const z = Number(getComputedStyle(document.documentElement).zoom) || 1; cursor.style.opacity = 1; cursor.style.left = (e.clientX / z) + 'px'; cursor.style.top = (e.clientY / z) + 'px' }, true)
    addEventListener('mousedown', () => { cursor.style.transform = 'scale(.7)' }, true)
    addEventListener('mouseup', () => { cursor.style.transform = 'scale(1)' }, true)
  }
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', make); else make()
})()`

export async function openScene({ name, outDir, width = WIDTH, height = HEIGHT, videoWidth = WIDTH, videoHeight = HEIGHT }) {
  mkdirSync(outDir, { recursive: true })
  const browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] })
  const recordingStarted = Date.now()
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: videoWidth / width, recordVideo: { dir: outDir, size: { width: videoWidth, height: videoHeight } } })
  await context.addInitScript(CURSOR_JS)
  const page = await context.newPage()
  const problems = []
  page.on('pageerror', error => problems.push(`pageerror: ${error.message}`))
  page.on('console', message => { if (message.type() === 'error') problems.push(`console: ${message.text()}`) })
  page.on('response', response => { if (response.url().includes('/api/') && response.status() >= 400) problems.push(`${response.status()} ${response.url()}`) })
  let origin = null
  let mouse = { x: width / 2, y: height / 2 }
  const scene = {
    page, problems, notes: {},
    zero() { origin = Date.now(); return this },
    elapsed() { return (Date.now() - origin) / 1000 },
    async at(seconds) { const wait = origin + seconds * 1000 - Date.now(); if (wait > 0) await sleep(wait); else if (wait < -400) scene.notes[`late@${seconds}`] = `${(-wait / 1000).toFixed(2)}s` },
    // Time-based so a slow page cannot stretch the movement and push later actions off the timeline.
    async glide(x, y, ms = 450) {
      const from = { ...mouse }, started = Date.now()
      for (;;) {
        const k = Math.min(1, (Date.now() - started) / ms), eased = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2
        await page.mouse.move(from.x + (x - from.x) * eased, from.y + (y - from.y) * eased)
        if (k >= 1) break
        await sleep(6)
      }
      mouse = { x, y }
    },
    async center(locator) { const box = await locator.boundingBox(); if (!box) throw new Error('element has no box'); return { x: box.x + box.width / 2, y: box.y + box.height / 2, box } },
    async ensureVisible(locator) {
      if (scene.noAutoScroll) return   // scenes that compose one fixed frame must not scroll under the viewer
      const box = await locator.boundingBox()
      if (box && box.y > 90 && box.y + box.height < height - 90) return
      // Dense pages tear while a smooth scroll rasterizes under software rendering; scenes can opt into instant jumps.
      const behavior = scene.instantScroll ? 'instant' : 'smooth'
      await locator.evaluate((element, behavior) => element.scrollIntoView({ block: 'center', behavior }), behavior); await sleep(scene.instantScroll ? 450 : 900)
    },
    async moveTo(locator, ms = 450) { await scene.ensureVisible(locator); const { x, y } = await scene.center(locator); await scene.glide(x, y, ms) },
    async click(locator, ms = 450) { await scene.moveTo(locator, ms); await sleep(140); await page.mouse.down(); await sleep(70); await page.mouse.up() },
    async choose(select, value, ms = 450) { await scene.moveTo(select, ms); await sleep(160); await select.selectOption(value) },
    async smoothScroll(top, ms = 1000) { await page.evaluate(y => window.scrollTo({ top: y, behavior: 'smooth' }), top); await sleep(ms) },
    async ring(locator, ms = 1800) {
      const box = await locator.boundingBox(); if (!box) return
      await page.evaluate(({ box, ms }) => {
        const zoom = Number(getComputedStyle(document.documentElement).zoom) || 1
        box = { x: box.x / zoom, y: box.y / zoom, width: box.width / zoom, height: box.height / zoom }
        const ring = document.createElement('div')
        ring.style.cssText = `position:fixed;left:${box.x - 8}px;top:${box.y - 8}px;width:${box.width + 16}px;height:${box.height + 16}px;border:3px solid #b6e4d5;border-radius:16px;box-shadow:0 0 0 6px rgba(182,228,213,.18),0 0 28px rgba(182,228,213,.45);z-index:2147483646;pointer-events:none;opacity:0;transition:opacity .25s`
        document.documentElement.appendChild(ring); requestAnimationFrame(() => { ring.style.opacity = 1 })
        setTimeout(() => { ring.style.opacity = 0; setTimeout(() => ring.remove(), 300) }, ms)
      }, { box, ms })
    },
    // scrollIntoView stays correct under html{zoom}; manual getBoundingClientRect + scrollTo does not.
    async reveal(selector, block = 'center', smooth = false, ms = 1000) {
      await page.evaluate(({ selector, block, smooth }) => document.querySelector(selector).scrollIntoView({ block, behavior: smooth ? 'smooth' : 'instant' }), { selector, block, smooth })
      await sleep(smooth ? ms : 700)
    },
    async zoom(factor) { await page.addStyleTag({ content: `html{zoom:${factor}}` }); await sleep(600) },
    async seekSlider(seconds) {
      await page.getByRole('slider', { name: 'Seek match time' }).evaluate((element, value) => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(element, String(value))
        element.dispatchEvent(new Event('input', { bubbles: true })); element.dispatchEvent(new Event('change', { bubbles: true }))
      }, seconds)
    },
    async finish(totalSeconds, extra = {}) {
      await scene.at(totalSeconds)
      const video = page.video()
      await context.close()
      const path = await video.path()
      const report = { name, video: path, trimStartSeconds: (origin - recordingStarted) / 1000, sceneSeconds: totalSeconds, problems, notes: scene.notes, ...extra }
      writeFileSync(join(outDir, `${name}.json`), JSON.stringify(report, null, 2))
      await browser.close()
      return report
    },
  }
  return scene
}
