export function stabilitySeconds(value) {
  const text = value ?? '0'
  if (!/^(0|[1-9]\d*)$/.test(text) || Number(text) > 900) {
    throw new Error('stability seconds must be an integer from 0 to 900')
  }
  return Number(text)
}

// The monotonic duration is measured, never inferred from cycle count or sleeps.
export async function runStability({ durationMs, report, checkpoint, step, sample,
  now = () => performance.now() }) {
  const started = now()
  const state = report.stability = { status: 'running', requestedDurationMs: durationMs,
    elapsedMs: 0, cyclesCompleted: 0, samples: [] }
  await checkpoint()
  try {
    while (now() - started < durationMs) {
      await step(state.cyclesCompleted)
      state.samples.push({ elapsedMs: now() - started, ...await sample() })
      state.cyclesCompleted++
      state.elapsedMs = now() - started
      await checkpoint()
    }
    state.status = 'passed'
  } catch (error) {
    state.status = 'failed'
    state.failure = error.message
    throw error
  } finally {
    state.elapsedMs = now() - started
    await checkpoint()
  }
}
