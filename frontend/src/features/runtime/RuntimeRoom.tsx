import { useEffect, useRef, useState } from 'react'
import { clock, download, newId, request, root, RuntimeError } from './api'
import type { Audit, Checkpoint, Comparison, Config, Evidence, Experiment, Metric, NativeEvent, Receipt, Run, Session, Tactics, View } from './api'
import './runtime.css'

const fields = ['pressing', 'compactness', 'directness', 'tempo', 'risk'] as const
const formations = ['4-3-3', '4-4-2', '3-5-2'] as const
type Retry = { path: string; body: unknown; target: 'session' | 'command' | 'run' | 'experiment' | 'other' }
const active = (status?: string) => status === 'queued' || status === 'running'

export function RuntimeRoom() {
  const [credential, setCredential] = useState('')
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const live = useRef(true)
  const epoch = useRef(0)
  const sessionRef = useRef('')
  const [sessions, setSessions] = useState<Session[]>([])
  const [sessionId, setSessionId] = useState('')
  const [view, setView] = useState<View | null>(null)
  const [presets, setPresets] = useState<Record<string, Config>>({})
  const [config, setConfig] = useState<Config | null>(null)
  const [configJson, setConfigJson] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [transport, setTransport] = useState('Connecting')
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([])
  const [checkpointId, setCheckpointId] = useState('')
  const [audit, setAudit] = useState<Audit[]>([])
  const [stepTicks, setStepTicks] = useState(10)
  const [pace, setPace] = useState(5)
  const [run, setRun] = useState<Run | null>(null)
  const [team, setTeam] = useState('home')
  const [field, setField] = useState('pressing')
  const [value, setValue] = useState('100')
  const [cutoff, setCutoff] = useState<number | null>(null)
  const [selectedSequence, setSelectedSequence] = useState<number | null>(null)
  const [trials, setTrials] = useState(3)
  const [horizon, setHorizon] = useState(120)
  const [experiment, setExperiment] = useState<Experiment | null>(null)
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [metric, setMetric] = useState<Metric | null>(null)
  const [proof, setProof] = useState<NativeEvent | null>(null)
  const retry = useRef<Retry | null>(null)
  const [retryAvailable, setRetryAvailable] = useState(false)

  useEffect(() => { live.current = true; return () => { live.current = false; epoch.current++ } }, [])
  useEffect(() => { if (view) setTeam(view.state.scenario.config.home.team_id) }, [view?.scenario_id])

  async function perform(task: () => Promise<void>) {
    if (busyRef.current) return
    const current = epoch.current
    busyRef.current = true; setBusy(true); setError(''); setNotice('')
    try { await task() } catch (reason) {
      if (live.current && current === epoch.current) setError(reason instanceof Error ? reason.message : 'Runtime request failed.')
    } finally {
      if (live.current && current === epoch.current) { busyRef.current = false; setBusy(false) }
    }
  }

  async function post<T>(path: string, body: unknown, target: Retry['target'] = 'other'): Promise<T> {
    if (retryAvailable && retry.current && (retry.current.path !== path || JSON.stringify(retry.current.body) !== JSON.stringify(body))) {
      throw new Error('Reconcile the pending operation using Retry original operation safely before sending a new mutation.')
    }
    retry.current = { path, body, target }; setRetryAvailable(false)
    try {
      const result = await request<T>(token, path, body)
      retry.current = null
      return result
    } catch (reason) {
      // Keep the original operation ID after uncertain network/server failure.
      if (!(reason instanceof RuntimeError) || reason.status >= 500) setRetryAvailable(true)
      else retry.current = null
      throw reason
    }
  }

  function selectSession(sid: string) {
    sessionRef.current = sid; setSessionId(sid); setView(null); setRun(null); setCutoff(null); setSelectedSequence(null); setAudit([]); setCheckpoints([]); setCheckpointId('')
    try { sessionStorage.setItem('pulse-runtime-session', sid) } catch { /* Optional identity only, never credentials. */ }
  }

  async function refresh(sid = sessionRef.current) {
    if (!sid) return
    const current = epoch.current
    const result = await request<View>(token, `/sessions/${sid}/state`)
    if (!live.current || epoch.current !== current || sessionRef.current !== sid) return
    setView(previous => previous && previous.revision > result.revision ? previous : result)
    const [saved, log, all, runs] = await Promise.all([request<Checkpoint[]>(token, `/sessions/${sid}/checkpoints`), request<Audit[]>(token, `/sessions/${sid}/audit`), request<Session[]>(token, '/sessions'), request<Run[]>(token, `/sessions/${sid}/runs`)])
    if (!live.current || epoch.current !== current || sessionRef.current !== sid) return
    setCheckpoints(saved); setAudit(log); setSessions(all)
    setRun(runs.find(r => active(r.status)) ?? runs[0] ?? null)
    setCheckpointId(previous => saved.some(c => c.checkpoint_id === previous) ? previous : saved.at(-1)?.checkpoint_id ?? '')
  }

  useEffect(() => {
    if (!token || !sessionId) return
    let stopped = false
    let polling = false
    const sid = sessionId
    void refresh(sid).catch(reason => { if (!stopped) setError(String(reason.message)) })
    const url = new URL(root + `/sessions/${sid}/observe`, location.href); url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(url)
    socket.onopen = () => socket.send(JSON.stringify({ token }))
    socket.onmessage = event => {
      if (stopped || sessionRef.current !== sid) return
      try {
        const data = JSON.parse(String(event.data)) as { kind: string; view: View; from_cursor?: number; events?: NativeEvent[] }
        if (data.view.session_id !== sid || !Number.isSafeInteger(data.view.revision) || !Number.isSafeInteger(data.view.event_cursor)) throw new Error('Invalid observer message')
        setView(previous => {
          if (previous && previous.revision > data.view.revision) return previous
          if (data.kind === 'snapshot') return data.view
          if (data.kind !== 'delta' || !previous || previous.event_cursor !== data.from_cursor || !Array.isArray(data.events)) { polling = true; return previous }
          return { ...data.view, state: { ...data.view.state, events: [...previous.state.events, ...data.events] } }
        })
        setTransport('Live server observer')
      } catch { polling = true; setTransport('Polling authoritative state') }
    }
    socket.onclose = () => { if (!stopped) { polling = true; setTransport('Polling authoritative state') } }
    socket.onerror = () => { polling = true }
    // Recovery polling does not advance match time; the durable server driver does.
    let fetching = false
    const timer = window.setInterval(() => {
      if (!fetching) {
        fetching = true
        void (polling ? refresh(sid) : request<Audit[]>(token, `/sessions/${sid}/audit`).then(log => { if (!stopped) setAudit(log) }))
          .catch(reason => { if (!stopped) setError(String(reason.message)) }).finally(() => { fetching = false })
      }
    }, 1200)
    return () => { stopped = true; socket.close(); window.clearInterval(timer) }
  }, [token, sessionId])

  useEffect(() => {
    if (!token || !sessionId) return
    let stopped = false
    setExperiment(null); setComparison(null); setMetric(null); setProof(null)
    void request<Experiment[]>(token, '/experiments').then(async items => {
      const latest = items.find(item => item.parent_session_id === sessionId)
      if (!latest || stopped) return
      if (latest.status === 'completed') {
        const result = await request<Comparison>(token, `/experiments/${latest.experiment_id}/comparison`)
        if (!stopped) setComparison(result)
      }
      if (!stopped) setExperiment(latest)
    }).catch(reason => { if (!stopped) setError(reason.message) })
    return () => { stopped = true }
  }, [token, sessionId])

  useEffect(() => {
    if (!token || !run || !active(run.status)) return
    let stopped = false, fetching = false
    const timer = window.setInterval(() => {
      if (fetching) return
      fetching = true
      void request<Run>(token, `/runs/${run.run_id}`).then(result => {
        if (!stopped) { setRun(result); if (!active(result.status)) void refresh().catch(() => undefined) }
      }).catch(reason => { if (!stopped) setError(reason.message) }).finally(() => { fetching = false })
    }, 500)
    return () => { stopped = true; window.clearInterval(timer) }
  }, [token, run?.run_id, run?.status])

  useEffect(() => {
    if (!token || !experiment || !active(experiment.status)) return
    let stopped = false, fetching = false
    const timer = window.setInterval(() => {
      if (fetching) return
      fetching = true
      void request<Experiment>(token, `/experiments/${experiment.experiment_id}`).then(async result => {
        if (stopped) return
        if (result.status === 'completed') {
          const data = await request<Comparison>(token, `/experiments/${result.experiment_id}/comparison`)
          const all = await request<Session[]>(token, '/sessions')
          if (!stopped) { setComparison(data); setSessions(all); setExperiment(result) }
        } else setExperiment(result)
      }).catch(reason => { if (!stopped) setError(reason.message) }).finally(() => { fetching = false })
    }, 500)
    return () => { stopped = true; window.clearInterval(timer) }
  }, [token, experiment?.experiment_id, experiment?.status])

  async function connect(event: React.FormEvent) {
    event.preventDefault()
    await perform(async () => {
      await request(credential, '/versions')
      const [items, scenarios] = await Promise.all([request<Session[]>(credential, '/sessions'), request<Record<string, Config>>(credential, '/presets')])
      setToken(credential); setCredential(''); setPresets(scenarios); setConfig(scenarios.balanced); setSessions(items)
      let saved = ''; try { saved = sessionStorage.getItem('pulse-runtime-session') ?? '' } catch { /* Optional. */ }
      const selected = items.find(s => s.session_id === saved) ?? items[0]
      if (selected) selectSession(selected.session_id)
      setNotice('Operator connected. Credentials remain in memory and clear on refresh or exit.')
    })
  }

  async function send(kind: string, extra: Record<string, unknown> = {}) {
    if (!view) return
    await post<Receipt>(`/sessions/${view.session_id}/commands`, { operation_id: newId(), expected_revision: view.revision, kind, ...extra }, 'command')
    await refresh()
  }

  const state = view?.state
  const running = active(run?.status) || state?.lifecycle === 'running'
  const paused = state?.lifecycle === 'paused' && !active(run?.status)
  const terminal = state?.lifecycle === 'completed' || state?.lifecycle === 'cancelled'
  const inspectionTick = Math.min(cutoff ?? view?.tick ?? 0, view?.tick ?? 0)
  const seen = state?.events.filter(e => e.tick <= inspectionTick) ?? []
  const selected = seen.find(e => e.sequence === selectedSequence) ?? seen.at(-1)
  const checkpoint = checkpoints.find(c => c.checkpoint_id === checkpointId)

  async function inspectEvidence(ref: Evidence) {
    await perform(async () => {
      const page = await request<{ events: NativeEvent[] }>(token, `/sessions/${ref.session_id}/events?cursor=${ref.sequence - 1}&limit=1`)
      const event = page.events[0]
      if (!event || event.sequence !== ref.sequence || event.tick !== ref.tick) throw new Error('Evidence source no longer matches the comparison.')
      setProof(event)
    })
  }

  return <section className="runtime-room" aria-label="Authoritative Control Room">
    <div className="runtime-heading"><div><span className="section-index">AUTHORITATIVE SANDBOX / ENGINE CONTROL ROOM</span><h2>Change the tactics.<br/><em>Test the consequences.</em></h2><p>Fictional football. One server clock. Every branch can be replayed and verified.</p></div><a href="#/sandbox">Open recorded fixture workspace</a></div>
    {!token ? <form className="panel runtime-auth" onSubmit={connect} aria-busy={busy}><h3>Operator access</h3><p>Use your provisioned runtime operator token. It is never saved in browser storage or included in exports.</p><label>Operator access token<input type="password" autoComplete="off" value={credential} onChange={e => setCredential(e.target.value)} required minLength={32} disabled={busy}/></label><button disabled={busy}>{busy ? 'Connecting…' : 'Connect operator'}</button></form> : <>
      <div className="runtime-toolbar"><span>{transport}</span><button disabled={busy} onClick={() => void perform(() => refresh())}>Refresh authoritative state</button><button disabled={busy} onClick={() => { epoch.current++; setToken(''); setCredential(''); setView(null); setSessionId(''); sessionRef.current = ''; setNotice('Disconnected. Accepted server runs continue until paused, completed or cancelled.'); }}>Disconnect operator</button></div>
      <details className="panel runtime-setup" open={!view}><summary>Scenario builder</summary>{config && <form onSubmit={event => { event.preventDefault(); void perform(async () => {
        const scenario = await post<{ scenario_id: string }>('/scenarios', config)
        const created = await post<Receipt>('/sessions', { operation_id: newId(), scenario_id: scenario.scenario_id }, 'session')
        setSessions(await request<Session[]>(token, '/sessions')); selectSession(created.session_id); setNotice('A new paused engine session is ready at kickoff.')
      }) }} aria-busy={busy}><div className="runtime-form-grid">
        <label>Scenario preset<select value={config.preset} disabled={busy} onChange={e => { const next = presets[e.target.value] ?? { ...config, preset: 'custom' }; setConfig(structuredClone(next)) }}>{Object.keys(presets).map(name => <option key={name}>{name}</option>)}<option value="custom">custom</option></select></label>
        <label>Initial seed<input type="number" min={0} max={2147483647} required value={config.seed} disabled={busy} onChange={e => setConfig({ ...config, seed: e.target.valueAsNumber })}/></label>
        <label>Duration seconds<input type="number" min={60} max={5400} step={2} required value={config.duration_seconds} disabled={busy} onChange={e => setConfig({ ...config, duration_seconds: e.target.valueAsNumber })}/></label>
        <label>Home team name<input required maxLength={80} value={config.home.name} disabled={busy} onChange={e => setConfig({ ...config, home: { ...config.home, name: e.target.value } })}/></label>
        <label>Away team name<input required maxLength={80} value={config.away.name} disabled={busy} onChange={e => setConfig({ ...config, away: { ...config.away, name: e.target.value } })}/></label>
        <label>Initial home formation<select value={config.home.tactics.formation} disabled={busy} onChange={e => setConfig({ ...config, home: { ...config.home, tactics: { ...config.home.tactics, formation: e.target.value as Tactics['formation'] } } })}>{formations.map(f => <option key={f}>{f}</option>)}</select></label>
        {fields.map(f => <label key={f}>Initial home {f}<input type="number" min={0} max={100} required disabled={busy} value={config.home.tactics[f]} onChange={e => setConfig({ ...config, home: { ...config.home, tactics: { ...config.home.tactics, [f]: e.target.valueAsNumber } } })}/></label>)}
      </div><button disabled={busy}>Create authoritative scenario</button><button type="button" disabled={busy} onClick={() => download(config, 'pulse-scenario.json')}>Download scenario JSON</button>
      <details><summary>Custom rosters and JSON import</summary><p>Edit a complete scenario to configure each fictional player's passing, finishing and defending. The server validates all rosters and values.</p><textarea aria-label="Scenario configuration JSON" value={configJson} onChange={e => setConfigJson(e.target.value)} rows={6}/><button type="button" disabled={busy} onClick={() => void perform(async () => {
        if (configJson.length > 2000000) throw new Error('Scenario exceeds 2 MB.')
        const parsed: unknown = JSON.parse(configJson)
        const resolved = await post<{ config: Config }>('/scenarios', parsed)
        setConfig(resolved.config); setNotice('Scenario validated and saved. Create a session to run it.')
      })}>Validate and load scenario JSON</button></details></form>}</details>
      <label className="runtime-session">Runtime / branch<select value={sessionId} disabled={busy} onChange={e => selectSession(e.target.value)}><option value="">Select a runtime</option>{sessions.map(s => <option key={s.session_id} value={s.session_id}>{s.session_id.slice(-12)} · {clock(s.tick)} · {s.lifecycle}</option>)}</select></label>
      {view && state ? <>
        <section className="panel runtime-score" aria-label="Authoritative match state"><strong>{state.scenario.config.home.name}</strong><div><span className="runtime-status">{state.lifecycle.toUpperCase()}</span><b>{state.score[state.scenario.config.home.team_id]} : {state.score[state.scenario.config.away.team_id]}</b><output aria-label="Authoritative match clock">{clock(view.tick)}</output><small>Revision {view.revision} · Event cursor {view.event_cursor}</small></div><strong>{state.scenario.config.away.name}</strong></section>
        <section className="panel runtime-controls" aria-label="Engine transport"><div><label>Step seconds<input type="number" min={1} max={300} value={stepTicks} onChange={e => setStepTicks(e.target.valueAsNumber)}/></label><button disabled={busy || !paused || !Number.isInteger(stepTicks) || stepTicks < 1 || stepTicks > 300} onClick={() => void perform(() => send('step', { ticks: stepTicks }))}>Step engine</button></div>
          <div><label>Server progression rate<select value={pace} onChange={e => setPace(Number(e.target.value))}>{[1, 5, 15, 60].map(p => <option key={p} value={p}>{p} match seconds / server update</option>)}</select></label><button disabled={busy || running || terminal} onClick={() => void perform(async () => setRun(await post<Run>(`/sessions/${sessionId}/runs`, { operation_id: newId(), expected_revision: view.revision, target_tick: state.scenario.config.duration_seconds, ticks_per_step: pace }, 'run')))}>Run on server</button><button disabled={busy || !running} onClick={() => void perform(async () => {
            if (run && active(run.status)) setRun(await post<Run>(`/runs/${run.run_id}/cancel`, {}))
            else await send('pause')
            await refresh()
          })}>Pause engine</button></div><p>Progress runs on the server and continues if this tab closes. Viewing history does not rewind the engine.</p>{run && <p role="status">Server run: {run.status}{run.error ? ` · ${run.error}` : ''}</p>}
        </section>
        <div className="runtime-columns"><section className="panel runtime-observer"><h3>Committed event observer</h3><p>Inspecting {clock(inspectionTick)} · discrete action coordinates, no continuous player tracking.</p><input type="range" aria-label="Inspect committed match time" min={0} max={view.tick} value={inspectionTick} onChange={e => { setCutoff(Number(e.target.value)); setSelectedSequence(null) }}/><button disabled={busy} onClick={() => { setCutoff(null); setSelectedSequence(null) }}>Follow authoritative clock</button>
          <svg viewBox="0 0 100 64" role="img" aria-label={selected ? `Committed ${selected.type} at ${clock(selected.tick)}` : 'Committed event pitch'}><rect x="2" y="2" width="96" height="60" fill="#103b37" stroke="#a7d7c4"/><path d="M50 2V62M2 18H18V46H2M98 18H82V46H98" fill="none" stroke="#a7d7c4"/><circle cx="50" cy="32" r="10" fill="none" stroke="#a7d7c4"/>{selected && <><path d={`M${2 + selected.x * .96} ${2 + selected.y * .6} L${2 + selected.end_x * .96} ${2 + selected.end_y * .6}`} stroke="#66e5df" strokeWidth="1" strokeDasharray="2 1"/><circle cx={2 + selected.x * .96} cy={2 + selected.y * .6} r="1.5" fill="#fff"/></>}</svg>
          {selected && <p data-testid="selected-runtime-event">#{selected.sequence} · {clock(selected.tick)} · {selected.type} · {selected.outcome ?? 'match boundary'} · {selected.actor_id ?? 'official'}</p>}
          <ol className="runtime-events" aria-label="Committed event timeline">{seen.slice(-100).map(e => <li key={e.sequence}><button aria-pressed={selected?.sequence === e.sequence} onClick={() => setSelectedSequence(e.sequence)}>#{e.sequence} · {clock(e.tick)} · {e.type} · {e.team_id ?? 'match'}</button></li>)}</ol><p>Showing the latest 100 events at or before the inspection cutoff.</p>
        </section><div>
          <section className="panel runtime-tactics"><h3>Tactical intervention</h3><form onSubmit={e => { e.preventDefault(); void perform(() => send('intervene', { requested_tick: view.tick, team_id: team, field, value: field === 'formation' ? value : Number(value) })) }}>
            <label>Intervention team<select value={team} onChange={e => setTeam(e.target.value)}>{[state.scenario.config.home, state.scenario.config.away].map(t => <option key={t.team_id} value={t.team_id}>{t.name}</option>)}</select></label>
            <label>Tactical field<select value={field} onChange={e => { setField(e.target.value); setValue(e.target.value === 'formation' ? '3-5-2' : '100') }}>{['formation', ...fields].map(f => <option key={f}>{f}</option>)}</select></label>
            <label>New tactical value{field === 'formation' ? <select value={value} onChange={e => setValue(e.target.value)}>{formations.map(f => <option key={f}>{f}</option>)}</select> : <input type="number" min={0} max={100} required value={value} onChange={e => setValue(e.target.value)}/>}</label>
            <button disabled={busy || !paused}>Apply future tactic</button><p>Pause before editing. Accepted changes take effect at the next engine tick.</p>
          </form><div className="runtime-policies">{Object.entries(state.tactics).map(([id, t]) => <p key={id}><b>{id}</b> · {t.formation} · press {t.pressing} · tempo {t.tempo} · risk {t.risk}</p>)}</div>{state.pending.filter(p => p.kind === 'tactic').map((p, i) => <p key={i} role="status">Pending {p.field} = {p.value} at {clock(p.tick)}</p>)}</section>
          <section className="panel runtime-checkpoints"><h3>Exact checkpoints</h3><button disabled={busy || !paused} onClick={() => void perform(() => send('checkpoint'))}>Save exact checkpoint</button><label>Saved checkpoint<select value={checkpointId} onChange={e => setCheckpointId(e.target.value)}><option value="">Select checkpoint</option>{checkpoints.map(c => <option key={c.checkpoint_id} value={c.checkpoint_id}>{clock(c.tick)} · revision {c.revision}</option>)}</select></label><button disabled={busy || !checkpoint || running} onClick={() => void perform(async () => {
            if (!checkpoint) return
            const branch = await post<Receipt>(`/checkpoints/${checkpoint.checkpoint_id}/restore`, { operation_id: newId(), expected_revision: checkpoint.revision }, 'session')
            setSessions(await request<Session[]>(token, '/sessions')); selectSession(branch.session_id); setNotice('Checkpoint restored into an independent branch. Parent history is unchanged.')
          })}>Restore as new branch</button><p>Checkpoint state includes every RNG counter and pending action.</p></section>
          <section className="panel runtime-audit"><h3>Operator audit</h3><ol>{audit.slice(-12).map((a, i) => <li key={i}>{a.command.kind} · {a.result} · revision {a.revision}{a.intervention ? ` · ${a.intervention.field}: ${a.intervention.previous_value} → ${a.intervention.new_value} · effective ${clock(a.intervention.effective_tick)}` : ''}{a.code ? ` · ${a.code}` : ''}</li>)}</ol></section>
        </div></div>
        <section className="panel runtime-manifest"><h3>Reproducibility</h3><p>State hash <code>{view.state_hash}</code></p><button disabled={busy} onClick={() => void perform(async () => download(await request(token, `/sessions/${sessionId}/manifest`), 'pulse-runtime-manifest.json'))}>Download runtime manifest</button><button disabled={busy} onClick={() => void perform(async () => {
          const manifest = await request(token, `/sessions/${sessionId}/manifest`)
          const result = await request<{ verified: boolean; component: string | null }>(token, '/verify', manifest)
          setNotice(result.verified ? 'Runtime independently reproduced: event and state hashes match.' : `Verification failed: ${result.component}`)
        })}>Verify runtime</button></section>
        <section className="panel runtime-forkcast"><h3>ForkCast / paired tactical experiment</h3><p>Both arms start from the selected immutable checkpoint. Each pair uses equal, recorded RNG counter offsets. Differences describe this synthetic model.</p><form onSubmit={event => { event.preventDefault(); void perform(async () => {
          if (!checkpoint) return
          const result = await post<Experiment>('/experiments', { operation_id: newId(), checkpoint_id: checkpoint.checkpoint_id, expected_revision: checkpoint.revision, trials, horizon,
            baseline: [], variation: [{ team_id: team, field, value: field === 'formation' ? value : Number(value) }] }, 'experiment')
          setExperiment(result); setComparison(null); setMetric(null); setProof(null)
        }) }}><div className="runtime-form-grid"><label>Paired trials<input type="number" min={1} max={5} required value={trials} onChange={e => setTrials(e.target.valueAsNumber)}/></label><label>Experiment horizon seconds<input type="number" min={1} max={Math.min(600, state.scenario.config.duration_seconds - (checkpoint?.tick ?? 0))} required value={horizon} onChange={e => setHorizon(e.target.valueAsNumber)}/></label></div><p>Baseline: unchanged · Variation: {team} {field} = {value}. Choose the change in Tactical intervention above; it is applied only in the experimental variation branches.</p><button disabled={busy || !checkpoint || active(experiment?.status) || running}>Run paired ForkCast</button></form>
          {experiment && <div role="status">Experiment {experiment.status} · {Math.min(experiment.branch_index, experiment.request.trials * 2)}/{experiment.request.trials * 2} branches complete {experiment.error && `· ${experiment.error}`}{active(experiment.status) && <button disabled={busy} onClick={() => void perform(async () => setExperiment(await post<Experiment>(`/experiments/${experiment.experiment_id}/cancel`, {})))}>Cancel experiment</button>}</div>}
          {comparison && <><p>{comparison.verification_status} · {clock(comparison.start_tick)}–{clock(comparison.end_tick)} · {comparison.limitation}</p><div className="runtime-table-wrap"><table><caption>Paired results · variation minus baseline · mean [minimum, maximum]</caption><thead><tr><th>Team / metric</th><th>Baseline</th><th>Variation</th><th>Difference</th><th>Evidence</th></tr></thead><tbody>{comparison.metrics.map(m => <tr key={m.team_id + m.metric}><th>{m.team_id} / {m.metric.replaceAll('_', ' ')}</th><td>{m.baseline.mean} [{m.baseline.minimum}, {m.baseline.maximum}]</td><td>{m.variation.mean} [{m.variation.minimum}, {m.variation.maximum}]</td><td>{m.difference > 0 ? '+' : ''}{m.difference}</td><td><button disabled={busy} onClick={() => { setMetric(m); setProof(null) }}>Inspect {m.evidence_count} sources</button></td></tr>)}</tbody></table></div><details><summary>Trial provenance and branches</summary>{comparison.trials.map(t => <div key={t.trial}><p>Trial {t.trial + 1} · RNG offset {t.rng_counter_offset}</p><button disabled={busy} onClick={() => selectSession(t.baseline_session_id)}>Open baseline {t.trial + 1}</button><button disabled={busy} onClick={() => selectSession(t.variation_session_id)}>Open variation {t.trial + 1}</button><p><code>{t.baseline_event_hash}</code> / <code>{t.variation_event_hash}</code></p></div>)}</details><details><summary>Player involvement per trial</summary>{Object.entries(comparison.player_involvement).map(([arm, players]) => <p key={arm}>{arm}: {Object.entries(players).map(([id, count]) => `${id} ${count}`).join(' · ')}</p>)}</details><button disabled={busy} onClick={() => void perform(async () => download(await request(token, `/experiments/${comparison.experiment_id}/manifest`), 'pulse-forkcast-manifest.json'))}>Download experiment manifest</button>
          {metric && <section aria-label="Comparison evidence"><h4>{metric.team_id} / {metric.metric}</h4><p>{metric.evidence_truncated ? `Showing ${metric.evidence.length} of ${metric.evidence_count} event references; calculations use every source event.` : `${metric.evidence_count} event references.`}</p><ul>{metric.evidence.map(ref => <li key={`${ref.session_id}-${ref.sequence}`}><button disabled={busy} onClick={() => void inspectEvidence(ref)}>Trial {ref.trial + 1} · {ref.arm} · #{ref.sequence} · {clock(ref.tick)} · {ref.type} · contribution {ref.contribution}</button></li>)}</ul>{proof && <p role="status">Verified source #{proof.sequence} · {clock(proof.tick)} · {proof.type} · {proof.actor_id} · {proof.outcome}</p>}</section>}</>}
        </section>
      </> : <p role="status">Create a scenario or select an owned runtime to begin.</p>}
    </>}
    {error && <div className="runtime-error" role="alert">{error}{token && <button disabled={busy} onClick={() => void perform(() => refresh())}>Reload current revision</button>}</div>}
    {notice && <p className="runtime-notice" role="status">{notice}</p>}
    {retryAvailable && token && <button disabled={busy} onClick={() => void perform(async () => {
      const pending = retry.current; if (!pending) return
      const result = await post<Receipt & Run & Experiment>(pending.path, pending.body, pending.target)
      if (pending.target === 'session') { setSessions(await request<Session[]>(token, '/sessions')); selectSession(result.session_id) }
      else if (pending.target === 'run') setRun(result)
      else if (pending.target === 'experiment') setExperiment(result)
      else await refresh()
      setNotice('Original operation reconciled without applying it twice.')
    })}>Retry original operation safely</button>}
  </section>
}
