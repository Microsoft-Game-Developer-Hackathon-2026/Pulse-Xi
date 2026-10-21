export type Tactics = { formation: '4-3-3' | '4-4-2' | '3-5-2'; pressing: number; compactness: number; directness: number; tempo: number; risk: number }
export type Team = { team_id: string; name: string; color: string; players: { player_id: string; name: string; passing: number; finishing: number; defending: number }[]; tactics: Tactics }
export type Config = { engine_version: string; schema_version: string; seed: number; duration_seconds: number; preset: string; environment: string; home: Team; away: Team }
export type Scenario = { scenario_id: string; config_hash: string; config: Config }
export type ScenarioArchive = { archive_version: 'scenario-archive/1'; scenario: Scenario; rng_algorithm: string; rng_derivation: string; rng_streams: string[]; created_at_utc: string | null }
export type ScenarioSummary = { scenario_id: string; config_hash: string; seed: number; preset: string; created_at_utc: string | null }
export type NativeEvent = { sequence: number; tick: number; period: number; type: string; team_id: string | null; actor_id: string | null; recipient_id: string | null; outcome: string | null; x: number; y: number; end_x: number; end_y: number; possession_id: number; policy_revision: number }
export type State = { tick: number; revision: number; event_cursor: number; lifecycle: string; score: Record<string, number>; tactics: Record<string, Tactics>; scenario: { scenario_id: string; config_hash: string; config: Config }; pending: { kind: string; tick: number; team_id: string; field: string; value: string | number }[]; events: NativeEvent[] }
export type View = { session_id: string; scenario_id: string; tick: number; revision: number; event_cursor: number; state_hash: string; event_hash: string; state: State }
export type Session = { session_id: string; scenario_id: string; tick: number; revision: number; event_cursor: number; lifecycle: string }
export type Receipt = Session & { checkpoint_id: string | null }
export type Checkpoint = { checkpoint_id: string; session_id: string; tick: number; revision: number; event_cursor: number; state_hash: string }
export type Run = { run_id: string; session_id: string; status: string; tick: number; revision: number; event_cursor: number; error: string | null }
export type Experiment = { experiment_id: string; parent_session_id: string; status: string; branch_index: number; branches: string[]; request: { trials: number }; error: string | null }
export type Audit = { command: { operation_id: string; kind: string }; result: string; code: string | null; tick: number; revision: number; intervention: { field: string; previous_value: string | number; new_value: string | number; effective_tick: number } | null }
export type Summary = { mean: number; minimum: number; maximum: number; samples: number }
export type Evidence = { trial: number; arm: string; session_id: string; sequence: number; tick: number; type: string; actor_id: string | null; contribution: number }
export type Metric = { team_id: string; metric: string; baseline: Summary; variation: Summary; difference: number; evidence_count: number; evidence: Evidence[]; evidence_truncated: boolean }
export type Comparison = { experiment_id: string; parent_state_hash: string; start_tick: number; end_tick: number; verification_status: string; limitation: string; metrics: Metric[]; trials: { trial: number; rng_counter_offset: number; baseline_session_id: string; variation_session_id: string; baseline_event_hash: string; variation_event_hash: string }[]; player_involvement: Record<string, Record<string, number>> }
export const root = '/api/sandbox'
export const newId = () => crypto.randomUUID()
export const clock = (tick: number) => `${Math.floor(tick / 60).toString().padStart(2, '0')}:${(tick % 60).toString().padStart(2, '0')}`

export class RuntimeError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

export async function request<T>(token: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  return send<T>(token, path, body === undefined ? undefined : JSON.stringify(body), signal)
}

/** Send the original import bytes: parsing/restringifying here would hide duplicate keys. */
export async function importScenario(token: string, json: string): Promise<ScenarioArchive> {
  if (new TextEncoder().encode(json).byteLength > 2_000_000) throw new Error('Scenario exceeds 2 MB.')
  return send<ScenarioArchive>(token, '/scenarios/import', json)
}

async function send<T>(token: string, path: string, body?: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(root + path, { method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body, signal })
  if (!response.ok) {
    const failure = await response.json().catch(() => null) as { detail?: { code?: string } | string | {loc: (string | number)[]; msg: string}[] } | null
    const detail = failure?.detail
    const message = Array.isArray(detail) ? detail.slice(0, 5).map(e => `${e.loc.join('.')}: ${e.msg}`).join('; ')
      : typeof detail === 'string' ? detail : detail?.code
    throw new RuntimeError(response.status, message ?? `Request rejected (${response.status}). Check the values and refresh authoritative state.`)
  }
  return response.json() as Promise<T>
}

export function download(value: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }))
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
