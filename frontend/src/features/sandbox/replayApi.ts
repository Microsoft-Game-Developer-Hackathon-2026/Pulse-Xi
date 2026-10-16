import type { Event } from '../../types'

export async function readReplayEvents(matchId: string, signal: AbortSignal): Promise<Event[]> {
  const result: Event[] = []
  let cursor = 0
  for (;;) {
    const response = await fetch(`/api/matches/${encodeURIComponent(matchId)}/events?limit=200&cursor=${cursor}`, { signal })
    if (!response.ok) throw new Error(`Event stream request failed (${response.status})`)
    const page = await response.json() as Event[]
    if (!page.length) return result
    if (page.some(event => event.match_id !== matchId || event.sequence <= cursor)) {
      throw new Error('Event stream cursor or match identity is inconsistent. Retry the connection.')
    }
    result.push(...page)
    cursor = page[page.length - 1].sequence
    if (page.length < 200) return result
  }
}
