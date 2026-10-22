import { useState } from 'react'
import type { Cue, Event } from './types'

type StudioCue = Omit<Cue, 'safe_area'> & { order: number; end_match_second: number; priority: number; safe_area: 'lower_third' | 'top_left' | 'top_right'; transition: 'fade' | 'slide' | 'wipe' }
type Studio = { schema_version: 'director-studio/1'; match_id: string; revision: number; approved_revision: number | null; status: 'draft' | 'approved'; cues: StudioCue[]; audit_history?: { revision: number; action: string; at_utc: string }[] }

export function DirectorStudio({ matchId, atSecond, events, seek }: { matchId: string; atSecond: number; events: Event[]; seek: (second: number) => void }) {
  const [token, setToken] = useState('')
  const [studio, setStudio] = useState<Studio | null>(null)
  const [previewCue, setPreviewCue] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const base = `/api/matches/${encodeURIComponent(matchId)}/studio`
  const request = async <T,>(url: string, init: RequestInit = {}): Promise<T> => {
    const response = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...init.headers } })
    if (!response.ok) throw Error((await response.json().catch(() => ({}))).detail ?? `Studio request failed (${response.status})`)
    return response.json() as Promise<T>
  }
  const connect = async () => { setBusy(true); setMessage(''); try { setStudio(await request<Studio>(base)); setMessage('Local producer access connected.') } catch (error) { setMessage(String(error)) } finally { setBusy(false) } }
  const save = async () => {
    if (!studio) return
    setBusy(true); setMessage('')
    try {
      const result = await request<Studio>(base, { method: 'PUT', body: JSON.stringify({ expected_revision: studio.revision, cues: studio.cues.map(({ cue_id, order, start_match_second, show_duration_seconds, priority, visual_template, safe_area, transition }) => ({ cue_id, order, start_match_second, show_duration_seconds, priority, visual_template, safe_area, transition })) }) })
      setStudio(result); setMessage(`Draft saved as revision ${result.revision}.`)
    } catch (error) { setMessage(String(error)) } finally { setBusy(false) }
  }
  const approve = async () => {
    if (!studio) return
    setBusy(true); setMessage('')
    try { await request(`${base}/approve`, { method: 'POST', body: JSON.stringify({ expected_revision: studio.revision }) }); setStudio(await request<Studio>(base)); setMessage(`Revision ${studio.revision} approved.`) }
    catch (error) { setMessage(String(error)) } finally { setBusy(false) }
  }
  const exportApproved = async () => {
    setBusy(true); setMessage('')
    try {
      const packet = await request<Record<string, unknown>>(`${base}/export`)
      const url = URL.createObjectURL(new Blob([JSON.stringify(packet, null, 2)], { type: 'application/json' }))
      const link = document.createElement('a'); link.href = url; link.download = `${matchId}-studio-approved.json`; link.click(); URL.revokeObjectURL(url)
      setMessage('Approved revision exported.')
    } catch (error) { setMessage(String(error)) } finally { setBusy(false) }
  }
  const update = (index: number, patch: Partial<StudioCue>) => setStudio(current => current && ({ ...current, status: 'draft', cues: current.cues.map((cue, i) => i === index ? { ...cue, ...patch } : cue) }))
  const preview = studio?.cues.find(cue => cue.cue_id === previewCue)
  const program = studio?.status === 'approved' ? studio.cues.find(cue => atSecond >= cue.start_match_second && atSecond < cue.end_match_second) : undefined
  const upcoming = studio?.status === 'approved' ? studio.cues.find(cue => cue.start_match_second > atSecond) : undefined
  const selected = preview ?? program
  return <section className="studio-editor panel" aria-labelledby="director-studio-title">
    <div className="panel-title"><h3 id="director-studio-title">Director studio / Draft and approval</h3><small>{studio ? `REVISION ${studio.revision} · ${studio.status.toUpperCase()}` : 'LOCAL PRODUCER ACCESS'}</small></div>
    {!studio ? <div className="studio-auth"><label htmlFor="studio-token">Producer access token</label><input id="studio-token" type="password" autoComplete="off" value={token} onChange={event => setToken(event.target.value)} /><button disabled={!token || busy} onClick={() => void connect()}>{busy ? 'Connecting…' : 'Connect producer'}</button></div> : <>
      <div className="studio-editor-actions"><button disabled={busy} onClick={() => void save()}>Save draft</button><button disabled={busy || studio.status !== 'draft'} onClick={() => void approve()}>Approve revision</button><button disabled={busy || studio.approved_revision === null} onClick={() => void exportApproved()}>Export approved JSON</button><button onClick={() => { setStudio(null); setToken('') }}>Disconnect</button>{upcoming && <span role="status">Next approved cue in {Math.max(0, upcoming.start_match_second - atSecond)} match seconds.</span>}</div>
      <div className="studio-edit-preview"><div className="studio-screen" aria-label={selected ? `${selected.visual_template} preview` : 'Studio preview'}><span className="studio-label">{preview ? 'PREVIEW' : 'PROGRAM'} · {clock(atSecond)}</span>{selected ? <div className={`studio-lower ${selected.safe_area}`} data-transition={selected.transition}><small>{selected.overlay_type.toUpperCase()} / {clock(selected.start_match_second)}</small><strong>{selected.text}</strong><span>{selected.supporting_event_ids.length} verified source events</span></div> : <div className="studio-idle">CUE STANDBY</div>}<span className="safe-area">{selected?.safe_area.replaceAll('_', ' ').toUpperCase() ?? 'SAFE AREA'}</span></div>
        <div className="studio-cue-editor" aria-label="Editable cue queue">{studio.cues.map((cue, index) => <fieldset key={cue.cue_id}><legend>{index + 1}. {cue.text}</legend><div className="studio-edit-grid"><label>Match start <input type="number" min={cue.trigger_match_second} max="5400" value={cue.start_match_second} onChange={event => update(index, { start_match_second: Number(event.target.value) })}/></label><label>Duration (s) <input type="number" min="1" max="60" value={cue.show_duration_seconds} onChange={event => update(index, { show_duration_seconds: Number(event.target.value) })}/></label><label>Priority <input type="number" min="0" max="100" value={cue.priority} onChange={event => update(index, { priority: Number(event.target.value) })}/></label><label>Safe area <select value={cue.safe_area} onChange={event => update(index, { safe_area: event.target.value as StudioCue['safe_area'] })}><option value="lower_third">Lower third</option><option value="top_left">Top left</option><option value="top_right">Top right</option></select></label><label>Transition <select value={cue.transition} onChange={event => update(index, { transition: event.target.value as StudioCue['transition'] })}><option value="fade">Fade</option><option value="slide">Slide</option><option value="wipe">Wipe</option></select></label><label>Template <select value={cue.visual_template} onChange={event => update(index, { visual_template: event.target.value as Cue['visual_template'] })}><option value="score_lower_third">Score lower third</option><option value="tactical_lower_third">Tactical lower third</option></select></label></div><div className="studio-edit-actions"><button aria-label={`Move ${cue.text} up`} disabled={index === 0} onClick={() => setStudio(current => { if (!current || index === 0) return current; const cues = [...current.cues]; [cues[index - 1], cues[index]] = [cues[index], cues[index - 1]]; return { ...current, status: 'draft', cues: cues.map((item, order) => ({ ...item, order })) } })}>Move up</button><button disabled={busy} onClick={() => { setPreviewCue(cue.cue_id); seek(cue.start_match_second) }}>Preview cue</button>{cue.supporting_event_ids.slice(0, 2).map(id => <button key={id} onClick={() => { const source = events.find(event => event.event_id === id); if (source) seek(source.match_second) }}>Source {id}</button>)}</div></fieldset>)}</div></div>
      <details className="studio-audit"><summary>Revision and override audit ({studio.audit_history?.length ?? 0})</summary><ol>{studio.audit_history?.map((entry, index) => <li key={`${entry.revision}-${entry.action}-${index}`}>Revision {entry.revision} · {entry.action.replaceAll('_', ' ')} · {entry.at_utc}</li>)}</ol></details>
    </>}
    {message && <p role="status" aria-live="polite">{message}</p>}
  </section>
}

const clock = (seconds: number) => `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${Math.floor(seconds % 60).toString().padStart(2, '0')}`
