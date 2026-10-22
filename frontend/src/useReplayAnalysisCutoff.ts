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
