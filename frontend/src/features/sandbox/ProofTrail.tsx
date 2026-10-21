import { useState, type FormEvent } from 'react'
import './prooftrail.css'

type Metrics = { goals: number; shots: number; recoveries: number; turnovers: number; passes: number; carries: number }
type Window = { start_tick: number; end_tick: number; metrics_by_team: Record<string, Metrics>; evidence_event_ids: string[] }
type ProofTrail = {
  schema_version: 'sandbox-prooftrail/1'
  scenario_id: string
  branch_session_id: string
  baseline_session_id: string
  checkpoint_id: string
  intervention: { operation_id: string; team_id: string; field: string; previous_value: string | number; new_value: string | number; effective_tick: number }
  branch_before_window: Window
  baseline_before_window: Window
  branch_window: Window
  baseline_window: Window
  metric_deltas_by_team: Record<string, Metrics>
  manifest_hash: string
  verification_result: 'verified'
  interpretation: string
  uncertainty: string
}

const metricNames: (keyof Metrics)[] = ['goals', 'shots', 'recoveries', 'turnovers', 'passes', 'carries']

function WindowTable({ title, value }: { title: string; value: Window }) {
  return <section className="prooftrail-window">
    <h4>{title} · {value.start_tick}–{value.end_tick}s</h4>
    <table><thead><tr><th scope="col">Team</th>{metricNames.map(name => <th scope="col" key={name}>{name}</th>)}</tr></thead>
      <tbody>{Object.entries(value.metrics_by_team).map(([team, metrics]) => <tr key={team}><th scope="row">{team}</th>{metricNames.map(name => <td key={name}>{metrics[name]}</td>)}</tr>)}</tbody>
    </table>
    <details><summary>Evidence events ({value.evidence_event_ids.length})</summary><ul>{value.evidence_event_ids.map(id => <li key={id}><code>{id}</code></li>)}</ul></details>
  </section>
}

export function SandboxProofTrail() {
  const [token, setToken] = useState('')
  const [baseline, setBaseline] = useState('')
  const [branch, setBranch] = useState('')
  const [intervention, setIntervention] = useState('')
  const [atTick, setAtTick] = useState('120')
  const [result, setResult] = useState<ProofTrail | null>(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  async function compare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setResult(null)
    setPending(true)
    try {
      const query = new URLSearchParams({ baseline_session_id: baseline.trim(), intervention_id: intervention.trim(), at_tick: atTick })
      const response = await fetch(`/api/sandbox/sessions/${encodeURIComponent(branch.trim())}/prooftrail?${query}`, {
        headers: { Authorization: `Bearer ${token.trim()}` },
      })
      const body = await response.json() as ProofTrail | { detail?: { code?: string } }
      if (!response.ok) {
        const code = 'detail' in body ? body.detail?.code : undefined
        throw new Error(code ? `ProofTrail unavailable (${code}). Check the operator access and session IDs.` : 'ProofTrail request failed.')
      }
      setResult(body as ProofTrail)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'ProofTrail request failed.')
    } finally {
      setPending(false)
    }
  }

  return <section className="prooftrail-studio" aria-labelledby="prooftrail-title">
    <div className="prooftrail-heading"><div><span className="section-index">SANDBOX LAB / BRANCH EVIDENCE</span><h2 id="prooftrail-title">ProofTrail comparison</h2><p>Compare an operator-owned checkpoint branch with its baseline. Both manifests are independently replay-verified.</p></div></div>
    <form className="prooftrail-form" onSubmit={compare} aria-busy={pending}>
      <label>Operator bearer token<input type="password" autoComplete="off" value={token} onChange={event => setToken(event.target.value)} required aria-describedby="prooftrail-token-help"/></label>
      <p id="prooftrail-token-help">Sent only to this server for this request; it is held in page memory and is not saved to browser storage.</p>
      <label>Baseline session ID<input value={baseline} onChange={event => setBaseline(event.target.value)} required autoComplete="off"/></label>
      <label>Branch session ID<input value={branch} onChange={event => setBranch(event.target.value)} required autoComplete="off"/></label>
      <label>Intervention operation ID<input value={intervention} onChange={event => setIntervention(event.target.value)} required autoComplete="off"/></label>
      <label>Compare through tick<input type="number" min="1" max="5400" step="1" value={atTick} onChange={event => setAtTick(event.target.value)} required/></label>
      <div className="prooftrail-actions"><button type="submit" disabled={pending}>{pending ? 'Verifying…' : 'Verify and compare'}</button><button type="button" className="prooftrail-clear" onClick={() => { setToken(''); setBaseline(''); setBranch(''); setIntervention(''); setResult(null); setError('') }}>Clear</button></div>
    </form>
    {error && <p className="prooftrail-error" role="alert">{error}</p>}
    {result && <div className="prooftrail-result" aria-live="polite">
      <p className="prooftrail-verified"><strong>✓ {result.verification_result.toUpperCase()}</strong> · Scenario {result.scenario_id} · checkpoint <code>{result.checkpoint_id}</code></p>
      <p>Intervention: {result.intervention.field} for {result.intervention.team_id}, {String(result.intervention.previous_value)} → {String(result.intervention.new_value)} at tick {result.intervention.effective_tick}.</p>
      <div className="prooftrail-window-grid">
        <WindowTable title="Branch before" value={result.branch_before_window}/>
        <WindowTable title="Baseline before" value={result.baseline_before_window}/>
        <WindowTable title="Branch after" value={result.branch_window}/>
        <WindowTable title="Baseline after" value={result.baseline_window}/>
      </div>
      <h3>Change in branch vs baseline</h3><p>{result.interpretation}. {result.uncertainty}</p>
      <table><thead><tr><th scope="col">Team</th>{metricNames.map(name => <th scope="col" key={name}>{name}</th>)}</tr></thead><tbody>{Object.entries(result.metric_deltas_by_team).map(([team, metrics]) => <tr key={team}><th scope="row">{team}</th>{metricNames.map(name => <td key={name}>{metrics[name]}</td>)}</tr>)}</tbody></table>
      <p>Verified manifest pair <code>{result.manifest_hash}</code></p>
    </div>}
    <p className="prooftrail-caveat">These are counts from one deterministic synthetic trajectory per branch. They describe engine-specific association, not real-world tactical causation; statistical uncertainty is not estimated.</p>
  </section>
}
