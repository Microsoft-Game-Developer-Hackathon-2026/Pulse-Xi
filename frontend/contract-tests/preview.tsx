import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { ForkCastComparison } from '../src/features/experiments/ForkCastComparison'
import { fixture } from './fixtures'



function Preview() {
  const [mode, setMode] = useState('complete')
  const result = structuredClone(fixture)
  if (mode === 'invalid') result.metrics[0].mean_delta = 99
  if (mode === 'zero') { result.metrics[0].baseline = { mean: 0, min: 0, max: 0 }; result.metrics[0].alternative = { mean: 0, min: 0, max: 0 }; result.metrics[0].mean_delta = 0; result.metrics[0].supporting_events = [] }
  if (mode === 'missing') { result.metrics[0].alternative = { mean: null, min: null, max: null }; result.metrics[0].mean_delta = null; result.metrics[0].unavailable_reason = 'Metric unsupported by fixture' }
  return <main style={{ maxWidth: 1000, margin: 'auto', padding: 18 }}><p>DEVELOPMENT CONTRACT PREVIEW — excluded from the production build.</p><label>PREVIEW STATE <select value={mode} onChange={event => setMode(event.target.value)}>{['complete', 'zero', 'missing', 'invalid', 'loading', 'empty', 'error'].map(value => <option key={value}>{value}</option>)}</select></label><div style={{ marginTop: 18 }}><ForkCastComparison result={mode === 'empty' ? null : result} loading={mode === 'loading'} error={mode === 'error' ? 'Fixture API failure' : undefined}/></div></main>
}
createRoot(document.getElementById('root')!).render(<Preview/> )
