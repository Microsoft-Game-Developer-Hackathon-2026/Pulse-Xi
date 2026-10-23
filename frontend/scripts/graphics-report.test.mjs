import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, readFile, readdir } from 'node:fs/promises'
import { promisify } from 'node:util'
import { execFile } from 'node:child_process'
import { createServer } from 'node:net'
import { fileURLToPath } from 'node:url'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { recordProbe } from './graphics-report.mjs'
import { stabilitySeconds, runStability } from './graphics-stability.mjs'

test('CLI startup failure leaves an explicit failed report and exits nonzero', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pulse-graphics-cli-'))
  const socket = createServer()
  await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve))
  const port = socket.address().port
  await new Promise(resolve => socket.close(resolve))
  const script = process.env.GRAPHICS_TEST_SCRIPT ?? fileURLToPath(new URL('./measure-graphics.mjs', import.meta.url))
  await assert.rejects(promisify(execFile)(process.execPath, [script], {
    env: { ...process.env, PULSE_GRAPHICS_HARDWARE: '0',
      PULSE_GRAPHICS_URL: `http://127.0.0.1:${port}`, PULSE_GRAPHICS_OUTPUT: directory },
    timeout: 30_000, windowsHide: true,
  }))
  const runs = await readdir(directory)
  assert.equal(runs.length, 1, 'failed invocation must create its own report directory')
  const report = JSON.parse(await readFile(join(directory, runs[0], 'report.json')))
  assert.equal(report.status, 'failed')
  assert.match(report.failure, /ERR_CONNECTION_REFUSED/)
  assert.ok(report.endedAt)
})

test('closed browser preserves failed status and partial metrics, not success', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pulse-graphics-failure-'))
  await assert.rejects(recordProbe(directory, { commit: 'test' }, async (report, checkpoint) => {
    report.profiles.push({ quality: 'low', unavailable: null })
    report.interruption = { signal: 'SIGTERM', at: 'test observation, not a real OS signal' }
    await checkpoint()
    const running = JSON.parse(await readFile(join(directory, 'report.json')))
    assert.equal(running.status, 'running')
    assert.equal(running.endedAt, null)
    throw new Error('Target page, context or browser has been closed')
  }), /browser has been closed/)
  const report = JSON.parse(await readFile(join(directory, 'report.json')))
  assert.equal(report.status, 'failed')
  assert.match(report.failure, /browser has been closed/)
  assert.equal(report.profiles.length, 1)
  assert.equal(report.profiles[0].unavailable, null)
  assert.equal(report.interruption.signal, 'SIGTERM')
  assert.ok(report.endedAt)
})

test('runtime errors cannot publish a passed benchmark', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pulse-graphics-errors-'))
  await assert.rejects(recordProbe(directory, {}, async report => {
    report.errors.push('WebGL failure')
  }), /runtime errors/)
  assert.equal(JSON.parse(await readFile(join(directory, 'report.json'))).status, 'failed')
})

test('only a completed probe publishes success', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pulse-graphics-success-'))
  const result = await recordProbe(directory, {}, async report => {
    report.renderer = 'test renderer, no physical measurement'
  })
  assert.equal(result.status, 'passed')
  assert.equal(JSON.parse(await readFile(join(directory, 'report.json'))).endedAt, result.endedAt)
})

test('CLI rejects an unbounded extended session before browser/network work', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pulse-graphics-duration-'))
  await assert.rejects(promisify(execFile)(process.execPath,
    [fileURLToPath(new URL('./measure-graphics.mjs', import.meta.url))], {
      env: { ...process.env, PULSE_GRAPHICS_STABILITY_SECONDS: '901',
        PULSE_GRAPHICS_URL: 'http://127.0.0.1:1', PULSE_GRAPHICS_OUTPUT: directory },
      timeout: 30_000, windowsHide: true,
    }))
  const [run] = await readdir(directory)
  const report = JSON.parse(await readFile(join(directory, run, 'report.json')))
  assert.equal(report.status, 'failed')
  assert.match(report.failure, /stability seconds must be an integer from 0 to 900/)
  assert.equal(report.browser, undefined)
})

test('extended duration is opt-in and bounded', () => {
  assert.equal(stabilitySeconds(undefined), 0)
  assert.equal(stabilitySeconds('900'), 900)
  for (const value of ['901', '-1', '1.5', 'NaN', ' 900']) assert.throws(() => stabilitySeconds(value))
})

test('extended success requires the measured requested duration', async () => {
  let time = 0
  const report = {}, updates = []
  await runStability({ durationMs: 250, report, now: () => time,
    step: async () => { time += 100 }, sample: async () => ({ heapBytes: null }),
    checkpoint: async () => updates.push(structuredClone(report)) })
  assert.equal(updates[0].stability.status, 'running')
  assert.equal(report.stability.status, 'passed')
  assert.equal(report.stability.cyclesCompleted, 3)
  assert.ok(report.stability.elapsedMs >= 250)
  assert.equal(report.stability.samples[0].heapBytes, null)
})

test('extended interruption retains partial observations and failed status', async () => {
  let time = 0
  const report = {}
  await assert.rejects(runStability({ durationMs: 900, report, now: () => time,
    step: async cycle => { time += 100; if (cycle === 1) throw new Error('page closed') },
    sample: async () => ({ heapBytes: 123 }), checkpoint: async () => {} }), /page closed/)
  assert.equal(report.stability.status, 'failed')
  assert.equal(report.stability.samples.length, 1)
  assert.equal(report.stability.elapsedMs, 200)
  assert.ok(report.stability.elapsedMs < report.stability.requestedDurationMs)
})


test('checkpoint delays cannot replace measured stability observations', async () => {
  let time = 0
  const report = {}
  await runStability({ durationMs: 250, report, now: () => time,
    step: async () => { time += 100 }, sample: async () => ({ heapBytes: null }),
    checkpoint: async () => { time += 1000 } })
  assert.equal(report.stability.cyclesCompleted, 3)
  assert.equal(report.stability.observedWorkMs, 300)
  assert.equal(report.stability.samples.length, 3)
  assert.ok(report.stability.elapsedMs > report.stability.observedWorkMs)
})

test('missing stability observations fail and preserve completed samples', async () => {
  for (const missing of [undefined, null, []]) {
    let time = 0
    const report = {}
    await assert.rejects(runStability({ durationMs: 250, report, now: () => time,
      step: async () => { time += 100 },
      sample: async () => time === 100 ? { heapBytes: null } : missing,
      checkpoint: async () => {} }), /Missing stability observation/)
    assert.equal(report.stability.status, 'failed')
    assert.equal(report.stability.cyclesCompleted, 1)
    assert.equal(report.stability.samples.length, 1)
  }
})
