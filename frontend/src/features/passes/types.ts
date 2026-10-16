import type { Point } from '../../types'

export type DifficultyFactor = {
  factor_id: 'distance' | 'progression' | 'pressure_context'
  available: boolean
  raw_value: number | null
  normalized_value: number | null
  effective_weight: number
  contribution_points: number | null
  units: string
  supporting_event_ids: string[]
  unavailable_reason: string | null
}

export type PassDifficulty = {
  match_id: string; event_id: string; match_second: number; at_second: number
  team_id: string; player_id: string; recipient_id: string | null
  start: Point | null; end: Point | null; outcome: string | null
  score: number | null; difficulty_band: 'low' | 'moderate' | 'high' | 'unavailable'
  formula_version: string; heuristic_label: string; factors: DifficultyFactor[]
  supporting_event_ids: string[]; unavailable_reason: string | null
  verification_status: string
}

export type DifficultyPage = {
  match_id: string; at_second: number; items: PassDifficulty[]
  total_visible_passes: number; next_cursor: number | null
}

export type PlayerDifficultySummary = {
  player_id: string; sample_count: number; unavailable_count: number
  mean_score: number | null; median_score: number | null
}
