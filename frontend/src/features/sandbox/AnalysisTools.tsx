import { useEffect, useRef, useState } from 'react'
import type { Event, Match } from '../../types'
import { BOOKMARK_KEY, bookmarkTransaction, csvCell, download, readBookmarks } from './analysisStorage'
import type { Bookmark, Filters } from './analysisStorage'

export function AnalysisTools({ match, events, selected, second, filters, panel, setPanel, select }: {
  match: Match; events: Event[]; selected?: Event; second: number; filters: Filters; panel: 'bookmarks' | 'exports';
  setPanel: (value: 'bookmarks' | 'exports') => void; select: (event: Event) => void
}) {
  const [initial] = useState(readBookmarks)
  const [bookmarks, setBookmarks] = useState(initial.items)
  const [notice, setNotice] = useState(initial.notice)
  const [note, setNote] = useState(''), [search, setSearch] = useState('')
  const [category, setCategory] = useState('filtered'), [format, setFormat] = useState('json')
  const [busy, setBusy] = useState(false), [confirmReset, setConfirmReset] = useState(false)
  const request = useRef<AbortController | null>(null)
  const mine = bookmarks.filter(b => b.matchId === match.match_id)
  const existing = mine.find(b => b.eventId === selected?.event_id)
  const authoritative = (b: Bookmark) => events.find(e => e.match_id === b.matchId && e.event_id === b.eventId && e.sequence === b.sequence && e.match_second === b.second)
  useEffect(() => { setNote(existing?.note ?? '') }, [selected?.event_id, match.match_id, existing?.note])
  useEffect(() => { request.current?.abort(); setBusy(false); return () => request.current?.abort() }, [match.match_id, second, selected?.event_id, filters.kind, filters.team, category, format])
  useEffect(() => {
    const sync = (event: StorageEvent) => { if (event.key === BOOKMARK_KEY) { const next = readBookmarks(); setBookmarks(next.items); setNotice(next.notice || 'Bookmarks updated from another tab.') } }
    window.addEventListener('storage', sync); return () => window.removeEventListener('storage', sync)
  }, [])
  const update = (transform: (items: Bookmark[]) => Bookmark[]) => {
    void bookmarkTransaction(() => {
    const latest = readBookmarks()
    if (latest.notice) { setNotice(latest.notice); return }
    const next = transform(latest.items)
    if (next.length > 200) { setNotice('Bookmark limit reached (200 across all matches). Remove one first.'); return }
    try { localStorage.setItem(BOOKMARK_KEY, JSON.stringify({ version: 1, items: next })); setBookmarks(next); setNotice('Bookmarks saved in this browser.') }
    catch { setNotice('Browser storage is unavailable; bookmark changes were not saved.') }
    }).catch(() => setNotice('Bookmark storage lock failed; changes were not saved.'))
  }
  const resetBookmarks = () => { void bookmarkTransaction(() => {
    try { localStorage.removeItem(BOOKMARK_KEY); setBookmarks([]); setNotice('Bookmarks reset.'); setConfirmReset(false) }
    catch { setNotice('Storage reset failed.') }
  }).catch(() => setNotice('Bookmark reset lock failed.')) }
  const exportData = async () => {
    request.current?.abort(); const controller = new AbortController(); request.current = controller
    setBusy(true); setNotice('')
    const cutoff = Math.floor(second), filename = match.match_id.replace(/[^A-Za-z0-9_-]/g, '_').slice(0,80) + `-${category}-${cutoff}.${format}`
    try {
      if (category === 'bookmarks') {
        const refs = mine.filter(b => b.second <= cutoff && authoritative(b)).sort((a,b) => a.sequence-b.sequence)
        const generatedAt = new Date().toISOString()
        const payload = format === 'json' ? JSON.stringify({ schema_version: 'bookmark-export/1', match_id: match.match_id, replay_cutoff: cutoff,
          generated_at: generatedAt, note_status: 'unverified analyst notes', provenance: { fixture_seed: match.seed, build_revision: null,
            engine_manifest: null, source_event_ids: refs.map(b => b.eventId), unavailable: ['build revision', 'engine manifest'] }, data: refs }, null, 2) : '\uFEFF' +
          [['schema_version','match_id','replay_cutoff','generated_at','fixture_seed','event_id','sequence','match_second','note','note_status'], ...refs.map(b =>
            ['bookmark-export/1', b.matchId, cutoff, generatedAt, match.seed, b.eventId, b.sequence, b.second, b.note, 'unverified analyst note'])].map(row => row.map(csvCell).join(',')).join('\r\n')
        download(new Blob([payload], { type: format === 'json' ? 'application/json;charset=utf-8' : 'text/csv;charset=utf-8' }), filename)
      } else {
        const params = new URLSearchParams({ category: category === 'filtered' ? 'events' : category, format, at_second: String(cutoff) })
        if (category === 'filtered') { if (filters.team !== 'all') params.set('team_id',filters.team); if (filters.kind !== 'all') params.set('event_type', filters.kind) }
        if (category === 'pass' && selected) params.set('event_id',selected.event_id)
        const response = await fetch(`/api/matches/${encodeURIComponent(match.match_id)}/analysis-export?${params}`, { signal: controller.signal })
        if (!response.ok) throw Error(`Export unavailable (${response.status}); narrow the cutoff/filter or retry.`)
        const blob = await response.blob()
        if (!controller.signal.aborted) download(blob,filename)
      }
      if (!controller.signal.aborted) setNotice('Export downloaded. Cutoff and provenance are included; notes are not verified claims.')
    } catch (error) { if (!controller.signal.aborted) setNotice(error instanceof Error ? error.message : 'Export failed.') }
    finally { if (request.current === controller) setBusy(false) }
  }
  const link = `${location.origin}${location.pathname}#/sandbox?${new URLSearchParams({ match: match.match_id, at: String(Math.floor(second)), ...(selected ? { event: selected.event_id } : {}) })}`
  return <section className="panel analysis-tools" aria-label="Analysis workspace tools">
    <div className="panel-title"><span>ANALYSIS WORKSPACE</span><small>LOCAL REFERENCES · NO ENGINE CHECKPOINT</small></div>
    <p>Selected event: <code>{selected?.event_id ?? 'No recorded event at this cutoff'}</code></p>
    <label>Event note <textarea maxLength={500} value={note} onChange={e => setNote(e.target.value)} disabled={!selected} /></label>
    <small>Up to 500 characters. Notes save when you bookmark or update; they are not verified football claims.</small>
    <button disabled={!selected} onClick={() => { if (selected) update(items => [...items.filter(b => b.matchId !== match.match_id || b.eventId !== selected.event_id),
      { matchId: match.match_id, eventId: selected.event_id, sequence: selected.sequence, second: selected.match_second, note }]) }}>{existing ? 'Update bookmark note' : 'Bookmark selected event'}</button>
    <div className="analysis-tabs"><button aria-pressed={panel === 'bookmarks'} onClick={() => setPanel('bookmarks')}>Saved events ({mine.length})</button><button aria-pressed={panel === 'exports'} onClick={() => setPanel('exports')}>Analysis exports</button></div>
    {panel === 'bookmarks' ? <>
      <label>Search bookmarks <input value={search} maxLength={160} onChange={e => setSearch(e.target.value)} /></label>
      <ul aria-label="Saved event bookmarks">{mine.filter(b => `${b.eventId} ${b.note}`.toLowerCase().includes(search.toLowerCase())).map(b => {
        const event = authoritative(b)
        return <li key={b.eventId}><button disabled={!event} onClick={() => { if(event) select(event) }}>Go to {b.eventId} · {Math.floor(b.second/60)}:{String(b.second%60).padStart(2,'0')}</button>
          <span>{event ? b.note : 'Source event is missing or changed; navigation unavailable.'}</span><button aria-label={`Remove bookmark ${b.eventId}`} onClick={() => update(items => items.filter(item => item.matchId !== b.matchId || item.eventId !== b.eventId))}>Remove</button></li>
      })}</ul>
      {!mine.length && <p>No saved events for this match.</p>}
      <button onClick={() => setConfirmReset(true)}>Reset all bookmarks</button>
      {confirmReset && <div role="group" aria-label="Confirm bookmark reset"><p>Delete bookmarks for all matches in this browser?</p><button onClick={resetBookmarks}>Confirm reset bookmarks</button><button onClick={() => setConfirmReset(false)}>Cancel reset</button></div>}
    </> : <div className="analysis-export-controls">
      <label>Export category <select value={category} onChange={e => setCategory(e.target.value)}><option value="filtered">Filtered visible events</option><option value="events">All events through cutoff</option><option value="pass" disabled={selected?.type !== 'pass'}>Selected pass analysis and factors</option><option value="metrics">Match statistics</option><option value="bookmarks">Visible bookmark references and notes</option></select></label>
      <label>Export format <select value={format} onChange={e => setFormat(e.target.value)}><option value="json">JSON</option><option value="csv">CSV</option></select></label>
      <button disabled={busy || category === 'pass' && selected?.type !== 'pass'} onClick={() => void exportData()}>{busy ? 'Preparing export…' : 'Download analysis'}</button>
      <p>Cutoff {Math.floor(second)}s. Events and metrics come from the backend; bookmarks and notes stay browser-local. Missing, changed or future bookmark references are excluded. Empty CSVs contain headers only.</p>
    </div>}
    <label>Analysis deep link <input readOnly value={link} onFocus={e => e.currentTarget.select()}/></label>
    {notice && <p role="status">{notice}</p>}
  </section>
}
