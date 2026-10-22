import {useEffect, useState} from 'react'
import {clock, download, request} from './api'
import type {Checkpoint, State} from './api'

type SavedCheckpoint = {
  created_at_utc: string | null
  checkpoint_id: string; session_id: string; scenario_id: string; tick: number; revision: number; event_cursor: number
  snapshot: {engine_version: string; schema_version: string; state_hash: string;
    state: State & {possession_team_id: string; possession_actor_id: string; actors: unknown[]; rng: Record<string,{counter:number}>}}
}

/** Inspect the immutable server snapshot; never serialize or restore engine state locally. */
export function CheckpointInspector({token, checkpoint}: {token: string; checkpoint: Checkpoint}) {
  const [open,setOpen] = useState(false), [retry,setRetry] = useState(0)
  const [result,setResult] = useState<{key:string; value:SavedCheckpoint}|null>(null)
  const [error,setError] = useState('')
  const key = `${token}:${checkpoint.checkpoint_id}`
  useEffect(()=>{
    if(!open) return
    const controller = new AbortController(); setError('')
    void request<SavedCheckpoint>(token,`/checkpoints/${encodeURIComponent(checkpoint.checkpoint_id)}`,undefined,controller.signal).then(value=>{
      if(value.checkpoint_id!==checkpoint.checkpoint_id || value.session_id!==checkpoint.session_id || value.snapshot.state_hash!==checkpoint.state_hash)
        throw Error('Checkpoint does not match the selected source boundary.')
      if(!controller.signal.aborted) setResult({key,value})
    }).catch(reason=>{if(!controller.signal.aborted) setError(reason instanceof Error?reason.message:'Checkpoint unavailable.')})
    return ()=>controller.abort()
  },[open,token,checkpoint.checkpoint_id,checkpoint.session_id,checkpoint.state_hash,key,retry])
  const data=result?.key===key?result.value:null
  return <details onToggle={e=>setOpen(e.currentTarget.open)}>
    <summary>Inspect saved checkpoint source</summary>
    {open && <section aria-label="Saved checkpoint source">
      {error?<p role="alert">{error} <button onClick={()=>setRetry(n=>n+1)}>Retry checkpoint inspection</button></p>:!data?<p role="status">Loading immutable checkpoint...</p>:<>
        <p>Checkpoint <code>{data.checkpoint_id}</code></p><p>Source runtime <code>{data.session_id}</code> / scenario <code>{data.scenario_id}</code></p>
        <p>Saved tick {clock(data.tick)} / revision {data.revision} / event cursor {data.event_cursor}.</p>
        <p>{data.snapshot.engine_version} / {data.snapshot.schema_version} / <code>{data.snapshot.state_hash}</code></p>
        <p>Saved score: {Object.entries(data.snapshot.state.score).map(([team,score])=>`${team} ${score}`).join(' / ')}.</p>
        <p>Possession: {data.snapshot.state.possession_team_id} / {data.snapshot.state.possession_actor_id}. Actors: {data.snapshot.state.actors.length}. Pending actions: {data.snapshot.state.pending.length}.</p>
        <dl>{Object.entries(data.snapshot.state.rng).map(([stream,state])=><div key={stream}><dt>{stream} RNG counter</dt><dd>{state.counter}</dd></div>)}</dl>
        <p>Inspection reads the original saved state and does not rewind or mutate the current runtime.</p>
        <p>Original creation UTC: {data.created_at_utc ? <time dateTime={data.created_at_utc}>{data.created_at_utc}</time> : 'unavailable (historical record)'}.</p>
        <button onClick={()=>download(data,'pulse-checkpoint-source.json')}>Download saved checkpoint source</button>
      </>}
    </section>}
  </details>
}
