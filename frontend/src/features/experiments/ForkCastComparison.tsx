import { comparisonProblems } from './comparisonContract'
import type { ProposedExperimentComparison, DescriptiveSummary } from './comparisonContract'
import './comparison.css'

const display = (value: number | null) => value === null ? 'Unavailable' : Number.isInteger(value) ? String(value) : value.toFixed(2)
const range = (value: DescriptiveSummary) => value.min === null ? 'No supported measurement' : `range ${display(value.min)}–${display(value.max)}`
const clock = (value: number) => `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`

export function ForkCastComparison({ result, loading = false, error }: {
  result: ProposedExperimentComparison | null; loading?: boolean; error?: string
}) {
  if (error) return <section className="comparison-state" role="alert">Comparison unavailable: {error}. The parent scenario must remain unchanged.</section>
  if (loading) return <section className="comparison-state" role="status">Waiting for authoritative experiment results…</section>
  if (!result) return <section className="comparison-state">No experiment is connected. Branch comparison requires checkpoint, intervention and manifest services.</section>
  const problems = comparisonProblems(result)
  if (problems.length) return <section className="comparison-state" role="alert"><strong>Comparison rejected</strong><ul>{problems.map((problem, index) => <li key={index}>{problem}</li>)}</ul></section>
  return <section className="forkcast-comparison" aria-label="ForkCast comparison" data-source={result.source}>
    {result.source === 'development_fixture' && <p className="comparison-fixture" role="status">DEVELOPMENT FIXTURE ONLY — no branch was run. These values test the proposed display contract.</p>}
    <header><div><small>FORKCAST / CONTROLLED SIMULATION COMPARISON</small><h1>One starting point.<br/>Two tactical paths.</h1></div><div className="comparison-window"><strong>{clock(result.window.start_second)}–{clock(result.window.end_second)}</strong><span>{result.paired_trial_ids.length} paired {result.paired_trial_ids.length === 1 ? 'trial' : 'trials'} · {result.verification_status.replaceAll('_', ' ')}</span></div></header>
    <div className="comparison-branches">{[result.baseline, result.alternative].map((branch, index) => <article key={branch.branch_id}><small>{index === 0 ? 'BASELINE' : 'ALTERNATIVE'}</small><h2>{branch.label}</h2><p>{branch.intervention_summary}</p><code>{branch.branch_id}</code></article>)}</div>
    <table><caption>Descriptive means and observed ranges. Differences do not imply real-world predictive probabilities.</caption><thead><tr><th scope="col">METRIC</th><th scope="col">BASELINE</th><th scope="col">ALTERNATIVE</th><th scope="col">DIFFERENCE</th></tr></thead><tbody>{result.metrics.map(metric => <tr key={metric.metric_id}><th scope="row">{metric.metric_id.replaceAll('_', ' ')}<small>{metric.units}</small></th><td>{display(metric.baseline.mean)}<small>{range(metric.baseline)}</small></td><td>{display(metric.alternative.mean)}<small>{range(metric.alternative)}</small></td><td>{metric.mean_delta === null ? 'Unavailable' : `${metric.mean_delta > 0 ? '+' : ''}${display(metric.mean_delta)}`}<small>{metric.unavailable_reason ?? 'alternative − baseline'}</small></td></tr>)}</tbody></table>
    <details><summary>Inspect comparison provenance and event evidence</summary><dl><dt>Parent checkpoint</dt><dd>{result.parent_checkpoint.checkpoint_id}</dd><dt>Immutable parent hash</dt><dd>{result.parent_checkpoint.state_hash}</dd><dt>Engine</dt><dd>{result.engine_version}</dd><dt>Manifest reference</dt><dd>{result.manifest_ref}</dd><dt>Paired seeds</dt><dd>{result.paired_seeds.join(', ')}</dd></dl>{result.metrics.map(metric => <div className="comparison-evidence" key={metric.metric_id}><strong>{metric.metric_id.replaceAll('_', ' ')}</strong>{metric.supporting_events.length ? <ul>{metric.supporting_events.map(event => <li key={`${event.trial_id}:${event.branch_id}:${event.event_id}`}><code>{event.event_id}</code> · {event.branch_id} · {event.trial_id} · {clock(event.match_second)}</li>)}</ul> : <p>No contributing events supplied. Zero counts and unavailable measurements remain distinct.</p>}</div>)}</details>
    <aside><strong>Interpret within this simulator.</strong><ul>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul><p>More activity or more goals in a small synthetic trial set is not a calibrated forecast. An intervention can be associated with a simulated difference without establishing real-world causation.</p></aside>
  </section>
}
