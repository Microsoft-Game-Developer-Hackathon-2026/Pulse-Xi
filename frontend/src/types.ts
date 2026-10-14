export type Point = { x: number; y: number }
export type Team = { team_id: string; name: string; color: string; players: { player_id: string; name: string; role: string; shirt_number: number }[] }
export type Match = { match_id: string; title: string; seed: number; synthetic: true; home: Team; away: Team; duration_seconds: number }
export type Event = { event_id: string; match_id: string; sequence: number; match_second: number; period: number; team_id: string | null; actor_id: string | null; recipient_id: string | null; type: string; outcome: string | null; start: Point | null; end: Point | null; possession_id: string | null; qualifiers: Record<string, string | number | boolean> }
export type TeamMetrics = { goals: number; shots: number; passes: number; completed_passes: number; pass_completion_pct: number; final_third_entries: number; recoveries: number; turnovers: number; pressure_events: number }
export type Metrics = { match_id: string; at_second: number; home: TeamMetrics; away: TeamMetrics; computed_from_event_count: number }
