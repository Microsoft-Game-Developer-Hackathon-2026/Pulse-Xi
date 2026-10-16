import { useEffect, useState } from 'react'
import type { Event, Match } from '../../types'
import type { EventSnapshot } from './eventSnapshot'
import type { PassDifficulty } from '../passes/types'

/** Read-only presentation of the existing scorer; never recalculates a claim. */
export function EventOverlay({ match, event, snapshot }: { match: Match; event?: Event; snapshot: EventSnapshot }) {
  const visible = event?.event_id === snapshot.event_id ? event : undefined
  const key = visible?.type === 'pass' ? `${match.match_id}:${visible.event_id}:${visible.match_second}` : null
  const [result, setResult] = useState<{ key: string; packet: PassDifficulty } | null>(null)
  const [failedKey, setFailedKey] = useState<string | null>(null)
  useEffect(() => {
    if (!key || !visible) return
    const controller = new AbortController()
    const cutoff = visible.match_second
    const path = `/api/matches/${encodeURIComponent(match.match_id)}/passes/${encodeURIComponent(visible.event_id)}/difficulty?at_second=${cutoff}`
    void fetch(path, { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('Pass analysis unavailable')
      const packet: PassDifficulty = await response.json()
      if (packet.match_id !== match.match_id || packet.event_id !== visible.event_id || packet.at_second !== cutoff ||
          packet.verification_status !== 'verified_rule_based' || packet.score !== null && (!Number.isInteger(packet.score) || packet.score < 0 || packet.score > 100)) throw new Error('Invalid pass packet')
      if (!controller.signal.aborted) setResult({ key, packet })
    }).catch(() => { if (!controller.signal.aborted) setFailedKey(key) })
    return () => controller.abort()
  }, [key, visible?.event_id, visible?.match_second, match.match_id])
  if (!visible) return null
  const actor = [match.home, match.away].flatMap(team => team.players).find(player => player.player_id === visible.actor_id)
  const packet = key && result?.key === key ? result.packet : null
  const point = (value: typeof visible.start) => value ? `${value.x.toFixed(1)}, ${value.y.toFixed(1)}` : 'unavailable'
  return <section className="observer-event-card" aria-label="Selected 3D event evidence" style={{ borderLeftColor: snapshot.color }}>
    <div><small>RECORDED EVENT / {Math.floor(visible.match_second / 60)}:{String(visible.match_second % 60).padStart(2, '0')}</small><strong>{visible.type.toUpperCase()} · {actor?.name ?? snapshot.team_name ?? 'Match official'}</strong><span>{visible.outcome ?? 'Outcome unavailable'} · start ({point(visible.start)}) → end ({point(snapshot.target ? visible.end : null)}) · normalized units</span></div>
    {key && <div data-testid="observer-pass-difficulty" data-event-id={visible.event_id}><small>HEURISTIC PASS DIFFICULTY</small><strong>{packet ? packet.score === null ? 'Unavailable' : `${packet.score}/100` : failedKey === key ? 'Unavailable' : 'Loading…'}</strong><span>Not a failure probability.</span>{packet && <a href={`/api/matches/${encodeURIComponent(match.match_id)}/passes/${encodeURIComponent(visible.event_id)}/difficulty/evidence?at_second=${visible.match_second}`} target="_blank" rel="noreferrer">Inspect verified evidence ↗</a>}</div>}
  </section>
}
