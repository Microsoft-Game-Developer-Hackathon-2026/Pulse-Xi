import { useEffect, useRef, useState } from 'react'

/** Replay rendering stays at 200ms; expensive server analysis samples at 1Hz.
 * Paused seeks are exact, including backward seeks. Never request a future tick.
 */
export function useReplayAnalysisCutoff(second: number, playing: boolean) {
  const latest = useRef(second)
  const [sample, setSample] = useState(second)
  useEffect(() => { latest.current = second }, [second])
  useEffect(() => {
    setSample(latest.current)
    if (!playing) return
    const timer = window.setInterval(() => setSample(latest.current), 1000)
    return () => window.clearInterval(timer)
  }, [playing])
  return Math.floor(playing ? Math.min(second, sample) : second)
}

/** The recap is a metered public POST, so while playing it refreshes only when a new verified
 * moment appears or every `intervalMs`; paused seeks and backward seeks stay exact. The returned
 * cutoff is never later than the replay cutoff, so no future event can be requested. */
export function useRecapCutoff(cutoff: number, playing: boolean, signature: string, intervalMs = 10000) {
  const [sampled, setSampled] = useState(cutoff)
  const last = useRef({ at: 0, signature })
  useEffect(() => {
    const now = performance.now()
    if (!playing || cutoff < sampled || signature !== last.current.signature || now - last.current.at >= intervalMs) {
      last.current = { at: now, signature }
      setSampled(cutoff)
    }
  }, [cutoff, playing, signature, intervalMs, sampled])
  return playing ? Math.min(sampled, cutoff) : cutoff
}
