import type { Match } from '../../types'

export async function generateFixture(seed: number, signal: AbortSignal): Promise<Match> {
  const response = await fetch('/api/matches/generate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seed }), signal,
  })
  if (!response.ok) throw new Error(`Fixture generation failed (${response.status}). Your current replay is still available.`)
  return response.json() as Promise<Match>
}
