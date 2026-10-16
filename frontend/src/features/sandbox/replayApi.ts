import type { Event } from '../../types'

const PAGE_SIZE = 200
const MAX_EVENTS = 100_000
const invalidStream = () => new Error('Event stream cursor, ordering or data is inconsistent. Retry the connection.')
const optionalId = (value: unknown) => value === null || typeof value === 'string'
function validEvent(value: unknown, matchId: string): value is Event {
  if (!value || typeof value !== 'object') return false
  const event = value as Record<string, unknown>
  const point = (value: unknown) => value === null || !!value && typeof value === 'object' &&
    ['x', 'y'].every(key => {
      const coordinate = (value as Record<string, unknown>)[key]
      return typeof coordinate === 'number' && Number.isFinite(coordinate) && coordinate >= 0 && coordinate <= 100
    })
  return event.match_id === matchId && typeof event.event_id === 'string' && !!event.event_id.trim() &&
    Number.isSafeInteger(event.sequence) && Number(event.sequence) > 0 &&
    Number.isSafeInteger(event.match_second) && Number(event.match_second) >= 0 && Number(event.match_second) <= 5400 &&
    [1, 2].includes(Number(event.period)) && typeof event.type === 'string' &&
    ['team_id', 'actor_id', 'recipient_id', 'outcome', 'possession_id'].every(key => optionalId(event[key])) &&
    point(event.start) && point(event.end) && !!event.qualifiers && typeof event.qualifiers === 'object' && !Array.isArray(event.qualifiers)
}

export async function readReplayEvents(matchId: string, signal: AbortSignal): Promise<Event[]> {
  const result: Event[] = []
  const identities = new Set<string>()
  let cursor = 0
  let lastSecond = 0
  for (;;) {
    signal.throwIfAborted()
    const response = await fetch(`/api/matches/${encodeURIComponent(matchId)}/events?limit=${PAGE_SIZE}&cursor=${cursor}`, { signal })
    if (!response.ok) throw new Error(`Event stream request failed (${response.status})`)
    const page: unknown = await response.json()
    signal.throwIfAborted()
    if (!Array.isArray(page) || page.length > PAGE_SIZE) throw invalidStream()
    if (!page.length) return result
    if (result.length + page.length > MAX_EVENTS) throw new Error('Event stream exceeds the 100,000-event browser replay limit.')
    for (const event of page) {
      if (!validEvent(event, matchId) || event.sequence <= cursor || event.match_second < lastSecond || identities.has(event.event_id)) throw invalidStream()
      identities.add(event.event_id)
      cursor = event.sequence
      lastSecond = event.match_second
      result.push(event)
    }
    if (page.length < PAGE_SIZE) return result
  }
}
