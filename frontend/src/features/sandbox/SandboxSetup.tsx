import { useEffect, useRef, useState } from 'react'
import type { Match } from '../../types'
import { generateFixture } from './api'
import './sandbox.css'

export function SandboxSetup({ match, onGenerated }: { match: Match; onGenerated: (match: Match) => void }) {
  const [seed, setSeed] = useState('4411')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const request = useRef<AbortController | null>(null)
  useEffect(() => {
    setPending(false)
    return () => request.current?.abort()
  }, [match.match_id])

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    setError(''); setNotice('')
    const value = Number(seed)
    if (!/^\d+$/.test(seed) || !Number.isSafeInteger(value) || value > 2_147_483_647) {
      setError('Use a whole-number seed from 0 to 2,147,483,647.'); return
    }
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    try {
      const generated = await generateFixture(value, controller.signal)
      if (!controller.signal.aborted) {
        onGenerated(generated)
        setNotice(`Replay ${generated.match_id} is ready. The same seed reproduces the same event stream on this build.`)
      }
    } catch (reason) {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Fixture generation failed.')
    } finally {
      if (!controller.signal.aborted) setPending(false)
    }
  }

  return <section className="sandbox-setup" aria-label="Sandbox fixture setup">
    <div className="sandbox-intro"><span className="section-index">SANDBOX LAB / FIXTURE WORKSPACE</span><h2>Start with a seed.<br/><em>Follow the evidence.</em></h2><p>Create a reproducible fictional match, explore its recorded events and inspect tactical calculations at your chosen replay time.</p><div className="sandbox-provenance"><span>SEED <strong>{match.seed}</strong></span><span>ACTIVE REPLAY <strong>{match.match_id}</strong></span></div></div>
    <div className="sandbox-create"><form onSubmit={create} aria-busy={pending}><label htmlFor="sandbox-seed">REPRODUCIBLE MATCH SEED</label><div className="sandbox-seed-row"><input id="sandbox-seed" inputMode="numeric" value={seed} onChange={event => setSeed(event.target.value)} aria-describedby="seed-help seed-error" disabled={pending}/><button type="submit" disabled={pending}>{pending ? 'Generating…' : 'Generate replay'}</button></div><p id="seed-help">Whole number · 0–2,147,483,647. Uses Harbour City and Northbank United with the current fixture generator.</p>{error && <p id="seed-error" className="sandbox-error" role="alert">{error}</p>}{notice && <p className="sandbox-success" role="status">{notice}</p>}</form><div className="sandbox-readiness"><span className="sandbox-status-dot"/><div><strong>Fixture replay available</strong><p>Live tactical changes, checkpoint restore and ForkCast are available in the Engine Control Room. The controls below explore this recorded event stream.</p></div></div></div>
  </section>
}
