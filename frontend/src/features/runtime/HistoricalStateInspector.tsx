import {useEffect,useState} from 'react'
import {clock,download,request} from './api'
import type {View} from './api'

type History = {session_id:string;source_revision:number;at_tick:number;read_only:boolean;
  snapshot:{engine_version:string;schema_version:string;state_hash:string;state:View['state'] & {period:number}}}

/** Read server-replayed history; the browser never advances or rewinds the engine. */
export function HistoricalStateInspector({token,view,tick}:{token:string;view:View;tick:number}) {
  const [open,setOpen]=useState(false),[retry,setRetry]=useState(0)
  const [result,setResult]=useState<{key:string;data:History}|null>(null),[error,setError]=useState('')
  const key=`${token}:${view.session_id}:${view.revision}:${tick}`
  useEffect(()=>{
    if(!open) return
    const controller=new AbortController();setError('')
    void request<History>(token,`/sessions/${encodeURIComponent(view.session_id)}/history?at_tick=${tick}`,undefined,controller.signal).then(data=>{
      if(!data.read_only || data.session_id!==view.session_id || data.at_tick!==tick || data.snapshot.state.tick!==tick || data.source_revision<view.revision)
        throw Error('Historical snapshot does not match the requested boundary.')
      if(!controller.signal.aborted) setResult({key,data})
    }).catch(reason=>{if(!controller.signal.aborted) setError(reason instanceof Error?reason.message:'Historical snapshot unavailable.')})
    return ()=>controller.abort()
  },[open,token,view.session_id,view.revision,tick,key,retry])
  const data=result?.key===key?result.data:null
  return <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>Inspect historical engine state</summary>
    {open && <section aria-label="Read-only historical engine state">
      {error?<p role="alert">{error} <button onClick={()=>setRetry(n=>n+1)}>Retry historical inspection</button></p>:!data?<p role="status">Replaying authoritative history on the server...</p>:<>
        <p>Historical tick {clock(data.at_tick)} / period {data.snapshot.state.period} / source revision {data.source_revision}.</p>
        <p>Historical state hash <code>{data.snapshot.state_hash}</code></p>
        <p>Score: {Object.entries(data.snapshot.state.score).map(([team,score])=>`${team} ${score}`).join(' / ')}. Events: {data.snapshot.state.events.length}.</p>
        <p>Computed by the server from an owned checkpoint and recorded commands. The authoritative clock and current branch are unchanged.</p>
        <button onClick={()=>download(data,'pulse-historical-state.json')}>Download historical source state</button>
      </>}
    </section>}
  </details>
}
