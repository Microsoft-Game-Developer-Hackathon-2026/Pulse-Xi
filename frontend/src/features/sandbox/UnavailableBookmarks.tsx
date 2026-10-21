import { useEffect, useRef, useState } from 'react'
import { BOOKMARK_KEY, bookmarkTransaction, download, readBookmarks } from './analysisStorage'
import type { Bookmark } from './analysisStorage'

export function UnavailableBookmarks() {
  const [missing,setMissing] = useState<Bookmark[]>([]),[notice,setNotice] = useState('')
  const [busy,setBusy] = useState(false),[confirm,setConfirm] = useState<Bookmark | null>(null)
  const request = useRef<AbortController | null>(null)
  useEffect(()=>()=>request.current?.abort(),[])
  async function inspect() {
    request.current?.abort();const controller=new AbortController();request.current=controller;setBusy(true);setNotice('');setConfirm(null)
    try {
      const saved=readBookmarks();if(saved.notice)throw new Error(saved.notice)
      const absent=new Set<string>()
      // At most 200 references, one sequential request per distinct match. An
      // omission from the library does not prove a generated match is missing.
      // Private runtime sources require operator access in the live Control Room.
      for(const id of new Set(saved.items.filter(b=>b.source!=='runtime').map(b=>b.matchId))) {
        const response=await fetch(`/api/matches/${encodeURIComponent(id)}`,{signal:controller.signal})
        if(response.status===404)absent.add(id)
        else if(!response.ok)throw new Error('Source availability could not be verified. Notes were retained; retry when the server is available.')
      }
      if(!controller.signal.aborted){setMissing(saved.items.filter(b=>b.source!=='runtime'&&absent.has(b.matchId)));setNotice('Source check complete. Nothing was removed. Recover missing matches using their saved canonical packages.')}
    } catch(e) {if(!controller.signal.aborted)setNotice(e instanceof Error?e.message:'Source check failed')}
    finally {if(!controller.signal.aborted)setBusy(false)}
  }
  async function remove() {
    if(!confirm)return
    const selected=confirm
    await bookmarkTransaction(()=>{
      const latest=readBookmarks();if(latest.notice){setNotice(latest.notice);return}
      const current=latest.items.find(b=>b.matchId===selected.matchId&&b.eventId===selected.eventId&&b.source===selected.source)
      if(current && (current.note!==selected.note||current.sequence!==selected.sequence||current.second!==selected.second)){setNotice('The note changed in another tab. Recheck before removing it.');return}
      try{localStorage.setItem(BOOKMARK_KEY,JSON.stringify({version:1,items:latest.items.filter(b=>b.matchId!==selected.matchId||b.eventId!==selected.eventId||b.source!==selected.source)}));window.dispatchEvent(new Event('pulse-xi-bookmarks-changed'));setMissing(items=>items.filter(b=>b.matchId!==selected.matchId||b.eventId!==selected.eventId||b.source!==selected.source));setNotice('Selected browser-local reference and note removed by confirmation.')}
      catch{setNotice('Browser storage unavailable. The note was not removed.')}
    }).catch(()=>setNotice('Bookmark lock unavailable. The note was retained.'))
    setConfirm(null)
  }
  return <section className="panel hub-import" aria-label="Unavailable bookmark recovery"><h3>Saved references and recovery</h3><p>Deletion never removes browser-local notes. Check actual source availability, recover the dataset from a saved package, or explicitly clean up individual references.</p><button disabled={busy} onClick={()=>void inspect()}>{busy?'Checking saved sources...':'Check saved sources'}</button>{notice&&<p role="status">{notice}</p>}
    {missing.length>0&&<><button onClick={()=>download(new Blob([JSON.stringify({schema_version:'unavailable-bookmarks/1',status:'unverified analyst references and notes; source unavailable',items:missing},null,2)],{type:'application/json'}),'unavailable-bookmark-notes.json')}>Download retained notes</button><ul>{missing.map(b=><li key={`${b.matchId}/${b.eventId}`}><code>{b.matchId} / {b.eventId}</code><p>{b.note}</p><button onClick={()=>setConfirm(b)}>Remove local reference {b.eventId}</button></li>)}</ul></>}
    {confirm&&<div role="group" aria-label="Confirm local reference removal"><p>Remove this reference and its note from this browser? {confirm.eventId}. Download retained notes first if needed.</p><button onClick={()=>void remove()}>Confirm remove local reference</button><button onClick={()=>setConfirm(null)}>Keep note</button></div>}
  </section>
}
