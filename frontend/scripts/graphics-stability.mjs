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
    elapsedMs: 0, observedWorkMs: 0, cyclesCompleted: 0, samples: [] }
  try {
    await checkpoint()
    while (state.observedWorkMs < durationMs) {
      const cycleStarted = now()
      await step(state.cyclesCompleted)
      const observation = await sample()
      if (!observation || typeof observation !== 'object' || Array.isArray(observation)) {
        throw new Error('Missing stability observation')
      }
      state.observedWorkMs += now() - cycleStarted
      state.samples.push({ ...observation, elapsedMs: now() - started })
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
