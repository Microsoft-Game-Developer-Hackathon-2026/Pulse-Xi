import { useEffect, useRef, useState } from 'react'
import type { Match } from '../../types'
import { download } from './analysisStorage'
import './dataHub.css'
import { UnavailableBookmarks } from './UnavailableBookmarks'

type Quality = { event_count: number; event_types: Record<string, number>; first_second: number | null; last_second: number | null; missing_start: number; missing_end: number; missing_actor: number; missing_recipient_on_passes: number; pass_count: number; passes_with_coordinates: number; limitations: string[]; sequence_consistent: boolean; duplicate_event_ids: number }
type Entry = { match: Match; origin: 'built-in' | 'imported'; quality: Quality; provenance: Record<string, string | null> | null; lifecycle: {generation:string; revision:number; archived:boolean} | null }
type Library = { import_enabled: boolean; local_admin_enabled:boolean; limits: { bytes: number; events: number; imported_matches: number }; matches: Entry[] }
type Preview = { match: Match; quality: Quality; status: 'new' | 'identical' | 'deleted'; deletion_id:string | null; warnings: string[] }

async function checked(response: Response) {
  if (response.ok) return response
  let detail: unknown
  try { detail = (await response.json()).detail } catch { /* A proxy may return non-JSON errors. */ }
  const text = Array.isArray(detail) ? detail.map((item: {loc?: string[]; msg?: string}) => `${item.loc?.join('.')}: ${item.msg}`).join('; ') : String(detail ?? `Request failed (${response.status})`)
  throw new Error(text.slice(0, 2000))
}

function QualityDetails({ value }: { value: Quality }) {
  return <div className="data-quality"><dl>
    <div><dt>Recorded events</dt><dd>{value.event_count}</dd></div>
    <div><dt>Time coverage (seconds)</dt><dd>{value.first_second ?? 'Unavailable'} to {value.last_second ?? 'Unavailable'}</dd></div>
    <div><dt>Missing start / end coordinates</dt><dd>{value.missing_start} / {value.missing_end}</dd></div>
    <div><dt>Missing actor identifiers</dt><dd>{value.missing_actor}</dd></div>
    <div><dt>Passes with both coordinates</dt><dd>{value.passes_with_coordinates} of {value.pass_count}</dd></div>
    <div><dt>Passes without a recipient</dt><dd>{value.missing_recipient_on_passes}</dd></div>
    <div><dt>Sequence / time ordering consistent</dt><dd>{value.sequence_consistent ? 'Yes' : 'No'}</dd></div>
    <div><dt>Duplicate event IDs</dt><dd>{value.duplicate_event_ids}</dd></div>
  </dl><p>Event categories: {Object.entries(value.event_types).map(([type, count]) => `${type}: ${count}`).join(', ') || 'No events'}</p>
  <ul>{value.limitations.map(text => <li key={text}>{text}</li>)}</ul></div>
}

export function MatchDataHub({ open }: { open: (match: Match) => void }) {
  const [library, setLibrary] = useState<Library | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [search, setSearch] = useState(''), [origin, setOrigin] = useState('all')
  const [status, setStatus] = useState('active')
  const [action,setAction] = useState<{entry:Entry;kind:'archive'|'restore'|'delete'} | null>(null)
  const [confirmation,setConfirmation] = useState('')
  const dialog = useRef<HTMLDialogElement>(null)
  const [token, setToken] = useState(''), [content, setContent] = useState<string | null>(null)
  const [filename, setFilename] = useState(''), [preview, setPreview] = useState<Preview | null>(null)
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [busy, setBusy] = useState(false)
  const request = useRef<AbortController | null>(null), fileRevision = useRef(0)
  useEffect(() => () => { request.current?.abort(); fileRevision.current++ }, [])
  useEffect(() => {
    const channel = 'BroadcastChannel' in window ? new BroadcastChannel('pulse-xi-library') : null
    if(channel)channel.onmessage=()=>setAttempt(n=>n+1)
    return ()=>channel?.close()
  },[])
  useEffect(() => { if (action && dialog.current && !dialog.current.open) dialog.current.showModal() }, [action])
  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/data-hub', {signal: controller.signal}).then(checked).then(r => r.json()).then((data: Library) => { if (!controller.signal.aborted) setLibrary(data) })
      .catch(e => { if (!controller.signal.aborted) setError(String(e.message)) })
    return () => controller.abort()
  }, [attempt])
  function invalidate() { request.current?.abort(); fileRevision.current++; setPreview(null); setAction(null); setBusy(false); setError(''); setNotice('') }
  async function loadFile(file?: File) {
    invalidate(); setContent(null); setFilename(file?.name ?? '')
    if (!file) return
    const revision = fileRevision.current
    try {
      if (!file.name.toLowerCase().endsWith('.json')) throw new Error('Choose a canonical JSON match package, not an analysis export or CSV file.')
      if (file.size > 2_000_000) throw new Error('File exceeds the 2 MB import limit.')
      const text = await file.text()
      if (revision !== fileRevision.current) return
      const parsed: unknown = JSON.parse(text)
      if (!parsed || typeof parsed !== 'object' || !['pulse-xi-match-package/1','pulse-xi-match-package/2'].includes(String((parsed as {schema_version?: string}).schema_version))) throw new Error('Unsupported package. Analysis exports are not complete importable match packages.')
      setContent(text); setNotice('File loaded locally. Validate and preview before importing; no match has been written.')
    } catch(e) { if (revision === fileRevision.current) setError(e instanceof Error ? e.message : 'Unable to read file') }
  }
  async function submit(commit: boolean) {
    if (!content || busy) return
    const controller = new AbortController(); request.current?.abort(); request.current = controller
    setBusy(true); setError(''); setNotice('')
    try {
      const recovering = commit && preview?.status === 'deleted'
      const body = content
      const response = await checked(await fetch(`/api/data-hub/${commit ? recovering ? 'recover' : 'import' : 'preview'}`, {method:'POST', headers:{'Content-Type':'application/json', Authorization:`Bearer ${token}`, ...(recovering ? {'X-Pulse-Deletion-ID':preview?.deletion_id ?? ''} : {})}, body, signal:controller.signal}))
      const result = await response.json()
      if (controller.signal.aborted) return
      if (commit) { setNotice(`Import stored: ${result.total} events; ${result.inserted} new. You can now open the match for analysis.`); setPreview(null); setAttempt(n => n + 1); if(recovering) announce(result.match_id,'recover') }
      else setPreview(result as Preview)
    } catch(e) { if (!controller.signal.aborted) { setPreview(null); setError(e instanceof Error ? e.message : 'Import request failed. Retry preview; identical imports are safe.') } }
    finally { if (!controller.signal.aborted) setBusy(false) }
  }
  function announce(match_id:string, action:string) {
    const detail = {match_id,action}
    window.dispatchEvent(new CustomEvent('pulse-xi-library-changed',{detail}))
    if ('BroadcastChannel' in window) { const channel = new BroadcastChannel('pulse-xi-library'); channel.postMessage(detail); channel.close() }
  }
  async function applyAction() {
    if (!action?.entry.lifecycle || busy) return
    const selected = action
    const controller = new AbortController();request.current?.abort();request.current=controller;setBusy(true);setError('')
    try {
      await checked(await fetch(`/api/data-hub/matches/${encodeURIComponent(selected.entry.match.match_id)}/lifecycle`,{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},body:JSON.stringify({action:selected.kind,confirm_match_id:selected.kind==='delete'?confirmation:selected.entry.match.match_id,generation:selected.entry.lifecycle?.generation,revision:selected.entry.lifecycle?.revision})}))
      if(controller.signal.aborted)return
      setAction(null);setAttempt(n=>n+1);setNotice(`${selected.entry.match.match_id}: ${selected.kind} completed. Browser-local notes were retained.`);announce(selected.entry.match.match_id,selected.kind)
    } catch(e) { if(!controller.signal.aborted) { setError(e instanceof Error?e.message:'Lifecycle operation failed');setAction(null);setAttempt(n=>n+1) } }
    finally {if(!controller.signal.aborted)setBusy(false)}
  }
  async function exportPackage(match: Match) {
    const controller = new AbortController(); request.current?.abort(); request.current = controller; setBusy(true); setError('')
    try { const response = await checked(await fetch(`/api/matches/${encodeURIComponent(match.match_id)}/package`, {signal:controller.signal})); const blob = await response.blob(); if (!controller.signal.aborted) download(blob, 'pulse-xi-match-package.json') }
    catch(e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Package download failed') }
    finally { if (!controller.signal.aborted) setBusy(false) }
  }
  const entries = library?.matches.filter(item => (origin === 'all' || item.origin === origin) && (status==='all'||status==='archived'&&item.lifecycle?.archived||status==='active'&&!item.lifecycle?.archived) && `${item.match.title} ${item.match.match_id} ${item.match.home.name} ${item.match.away.name}`.toLowerCase().includes(search.toLowerCase())) ?? []
  return <section className="data-hub" aria-label="Match Data Hub">
    <div className="topbar"><div><span className="section-index">RECORDED DATA / LOCAL ANALYSIS</span><h2>Match Data Hub</h2><p>Import compatible synthetic event packages and inspect their actual data coverage.</p></div></div>
    {error && <div className="error" role="alert">{error}<button onClick={() => { setError(''); setAttempt(n => n + 1) }}>Retry library</button></div>}
    {notice && <p role="status">{notice}</p>}
    <section className="panel hub-import" aria-label="Import match package"><h3>Import a match package</h3>
      <p>Canonical JSON only. Maximum 2 MB and 1,000 events. Analysis exports are not import packages. No files are uploaded until you request validation.</p>
      {library && !library.import_enabled && <p role="status">Imports disabled. Configure PULSE_IMPORT_TOKEN (at least 32 characters) on the server and restart it. Public installations must keep imports disabled unless access is explicitly authorized.</p>}
      <label>Import token <input type="password" autoComplete="off" value={token} maxLength={512} onChange={e => { invalidate(); setToken(e.target.value) }}/></label>
      <p>The token stays in this page's memory and is never saved in browser storage or exports. Use HTTPS for any remote server. Do not share the token with untrusted users.</p>
      <label>Canonical match JSON <input type="file" accept=".json,application/json" onChange={e => void loadFile(e.target.files?.[0])}/></label>
      <p>{filename}</p><button disabled={!content || !token || busy || !library?.import_enabled} onClick={() => void submit(false)}>Validate and preview</button>
      {busy && <p role="status">Processing recorded data...</p>}
      {preview && <div className="hub-preview" aria-label="Import preview"><h4>{preview.match.title}</h4><p>{preview.match.home.name} vs {preview.match.away.name} / {preview.match.match_id}</p><p>{preview.status === 'deleted'?'This identity was deleted. Explicit local administrator recovery is required; ordinary imports cannot recreate it.':preview.status === 'identical' ? 'Identical dataset already stored. Reimport is a safe no-op.' : 'New match. Preview has not written any data.'}</p><QualityDetails value={preview.quality}/><ul>{preview.warnings.map(w => <li key={w}>{w}</li>)}</ul><button disabled={busy||preview.status==='deleted'&&!library?.local_admin_enabled} onClick={() => void submit(true)}>{preview.status==='deleted'?'Confirm dataset recovery':'Confirm import'}</button><button disabled={busy} onClick={() => setPreview(null)}>Cancel import</button></div>}
    </section>
    {!library?.local_admin_enabled && <p>Archive, restore, deletion and deleted-dataset recovery require PULSE_ENABLE_LOCAL_DATA_ADMIN=1 on a direct local connection. Public/proxied destructive administration is unsupported.</p>}
    <section aria-label="Match library"><div className="hub-filters"><label>Search matches <input type="search" value={search} onChange={e => setSearch(e.target.value)}/></label><label>Match origin <select value={origin} onChange={e => setOrigin(e.target.value)}><option value="all">All sources</option><option value="built-in">Built-in</option><option value="imported">Imported</option></select></label><label>Archive status <select value={status} onChange={e=>setStatus(e.target.value)}><option value="active">Active</option><option value="archived">Archived</option><option value="all">Active and archived</option></select></label><button onClick={()=>setAttempt(n=>n+1)} disabled={busy}>Refresh library</button></div>
      {!library ? <p role="status">Loading match library...</p> : <p>{entries.length} matches / {library.matches.filter(m => m.origin === 'imported').length} of {library.limits.imported_matches} imported slots used</p>}
      {library && !entries.length && <p>No matches match these filters.</p>}
      <div className="hub-library">{entries.map(entry => <article className="panel hub-match" key={entry.match.match_id}><span className="section-index">{entry.origin.toUpperCase()} / {entry.lifecycle?.archived?'ARCHIVED':'ACTIVE'} / SYNTHETIC EVENTS</span><h3>{entry.match.title}</h3><p>{entry.match.home.name} vs {entry.match.away.name}</p><p className="hub-id">{entry.match.match_id}</p><p>{entry.quality.event_count} events / {entry.quality.first_second ?? '-'} to {entry.quality.last_second ?? '-'} seconds</p>
        <details><summary>Inspect metadata and data quality</summary><p>Declared duration: {entry.match.duration_seconds} seconds. Supplied seed: {entry.match.seed} (not verified engine provenance).</p>{entry.provenance && <p>Supplied source: {entry.provenance.source ?? 'Unavailable'}. Source application revision: {entry.provenance.application_revision ?? 'Unavailable'}. These claims are not independently authenticated.</p>}<QualityDetails value={entry.quality}/></details>
        <div className="hub-actions"><button onClick={() => open(entry.match)}>Open for analysis</button><button disabled={busy} onClick={() => void exportPackage(entry.match)}>Download complete package</button></div><p>Complete packages include all recorded events, regardless of replay cutoff. Built-in IDs must be renamed consistently before importing as a new match.</p>
        {entry.origin==='imported' && <div className="hub-actions"><button disabled={busy||!token||!library?.local_admin_enabled||!entry.lifecycle} onClick={()=>{setConfirmation('');setAction({entry,kind:entry.lifecycle?.archived?'restore':'archive'})}}>{entry.lifecycle?.archived?'Restore archived match':'Archive match'}</button><button disabled={busy||!token||!library?.local_admin_enabled||!entry.lifecycle} onClick={()=>{setConfirmation('');setAction({entry,kind:'delete'})}}>Delete imported match</button></div>}
      </article>)}</div>
    </section>
    <UnavailableBookmarks/>
    {action && <dialog className="hub-dialog" ref={dialog} aria-label="Confirm dataset operation" onCancel={event=>{if(busy)event.preventDefault();else setAction(null)}}><h3>{action.kind==='delete'?'Permanently delete dataset':action.kind==='archive'?'Archive dataset':'Restore archived dataset'}</h3><p><strong>{action.entry.match.title}</strong></p><code>{action.entry.match.match_id}</code><p>{action.entry.quality.event_count} recorded events. {action.kind==='delete'?'Recorded events, match metadata and provenance will be removed atomically. A minimal deletion ledger retains the ID and deletion time to block stale imports. Download a complete package first. Browser bookmarks and notes will remain; recovery requires a saved package.':'Events and provenance are retained. Archived analysis links remain readable. Archived datasets still count toward the 100-match limit.'}</p>{action.kind==='delete'&&<label>Type match ID to delete<input autoFocus value={confirmation} onChange={e=>setConfirmation(e.target.value)} autoComplete="off"/></label>}{busy&&<p role="status">Applying confirmed dataset operation. Wait for the result before leaving.</p>}<div className="hub-actions"><button disabled={busy||action.kind==='delete'&&confirmation!==action.entry.match.match_id} onClick={()=>void applyAction()}>{action.kind==='delete'?'Permanently delete match':action.kind==='archive'?'Confirm archive':'Confirm restore'}</button><button disabled={busy} onClick={()=>setAction(null)}>Cancel operation</button></div></dialog>}
  </section>
}
