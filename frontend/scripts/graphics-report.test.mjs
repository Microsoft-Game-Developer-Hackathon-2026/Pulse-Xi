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
