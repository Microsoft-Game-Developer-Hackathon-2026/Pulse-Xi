import type { Event, Match, Point } from '../../types'

export type ObserverScope = { match_id: string; scenario_id?: string; branch_id?: string }
export type ScenePoint = [number, number, number]
export type EventSnapshot = {
  scope: ObserverScope; at_second: number; event_id: string | null; event_type: string | null
  team_id: string | null; team_name: string | null; color: string
  actor_id: string | null; recipient_id: string | null
  origin: ScenePoint | null; target: ScenePoint | null
  provenance: 'recorded_synthetic_event'; unavailable_reason: string | null
}

// Display units only. Each team's attacking frame is shown independently.
export function projectPoint(point: Point | null): ScenePoint | null {
  if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y) ||
      point.x < 0 || point.x > 100 || point.y < 0 || point.y > 100) return null
  return [point.x - 50, 0.8, point.y * .64 - 32]
}

export function eventSnapshot(match: Match, event: Event | undefined, atSecond: number,
  scope: ObserverScope = { match_id: match.match_id }): EventSnapshot {
  const visible = Number.isFinite(atSecond) && atSecond >= 0 && scope.match_id === match.match_id &&
    event?.match_id === match.match_id && event.match_second <= atSecond
  const team = visible ? [match.home, match.away].find(item => item.team_id === event?.team_id) : undefined
  const validActor = !event?.actor_id || team?.players.some(player => player.player_id === event.actor_id)
  const validRecipient = !event?.recipient_id || team?.players.some(player => player.player_id === event.recipient_id)
  const accepted = visible && validActor && validRecipient && (!event?.team_id || !!team)
  const origin = accepted ? projectPoint(event?.start ?? null) : null
  return {
    scope, at_second: atSecond, event_id: accepted ? event!.event_id : null,
    event_type: accepted ? event!.type : null, team_id: team?.team_id ?? null,
    team_name: team?.name ?? null, color: team?.color ?? '#b2c9c1',
    actor_id: accepted ? event!.actor_id : null, recipient_id: accepted ? event!.recipient_id : null,
    origin, target: accepted && origin ? projectPoint(event?.end ?? null) : null,
    provenance: 'recorded_synthetic_event',
    unavailable_reason: !accepted ? 'No valid event at this replay time.' : !origin ? 'This event has no valid recorded position.' : null,
  }
}
