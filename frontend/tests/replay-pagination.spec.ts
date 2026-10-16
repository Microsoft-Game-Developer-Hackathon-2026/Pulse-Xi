import { expect, test } from '@playwright/test'
import { readReplayEvents } from '../src/features/sandbox/replayApi'
import type { Event } from '../src/types'

// Transport corruption fixtures only; never registered as application APIs.
const event = (sequence: number): Event => ({ event_id: `test-${sequence}`, match_id: 'test', sequence,
  match_second: sequence, period: 1, type: 'pass', team_id: null, actor_id: null,
  recipient_id: null, outcome: null, start: null, end: null, possession_id: null, qualifiers: {} })

test('replay reader rejects duplicate identities, unordered clocks and malformed pages', async () => {
  const original = globalThis.fetch
  try {
    for (const page of [null, {}, [null], [event(2), event(1)], [event(1), event(1)],
      [event(1), { ...event(2), event_id: 'test-1' }],
      [event(1), { ...event(2), match_second: 0 }],
      [{ ...event(1), start: { x: 101, y: 0 } }]]) {
      globalThis.fetch = async () => new Response(JSON.stringify(page))
      await expect(readReplayEvents('test', new AbortController().signal)).rejects.toThrow(/Event stream/)
    }
  } finally { globalThis.fetch = original }
})

test('replay reader preserves tied timestamps and stops on abort', async () => {
  const original = globalThis.fetch
  try {
    const page = [event(1), { ...event(2), match_second: 1 }]
    globalThis.fetch = async () => new Response(JSON.stringify(page))
    expect(await readReplayEvents('test', new AbortController().signal)).toEqual(page)
    const controller = new AbortController(); controller.abort()
    await expect(readReplayEvents('test', controller.signal)).rejects.toThrow()
  } finally { globalThis.fetch = original }
})
