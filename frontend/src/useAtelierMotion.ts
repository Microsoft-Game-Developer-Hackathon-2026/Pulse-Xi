import { useLayoutEffect } from 'react'

/** Presentation only. Never observes clocks, events, credentials or request state. */
export function useAtelierMotion(route: string, matchId: string, loadedMatchId: string) {
  useLayoutEffect(() => {
    const preference = matchMedia('(prefers-reduced-motion: reduce)')
    if (preference.matches || !('IntersectionObserver' in window)) return
    const selector = '.topbar,.scoreboard,.content-grid,.intelligence-grid,.studio,.runtime-heading,.runtime-room>.panel,.data-hub>.panel,.sandbox-setup'
    const pending = new Set(Array.from(document.querySelectorAll<HTMLElement>(selector))
      .filter(element => element.checkVisibility() && !element.matches('.runtime-auth')))
    const revealAll = () => { pending.forEach(element => element.classList.add('atelier-in')); pending.clear() }
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) {
        entry.target.classList.add('atelier-in')
        observer.unobserve(entry.target)
        pending.delete(entry.target as HTMLElement)
      }
    }, { rootMargin: '64px 0px', threshold: 0.03 })
    // Attach before paint: visible content must never flash and then disappear.
    for (const element of pending) {
      element.classList.remove('atelier-in')
      element.classList.add('atelier-reveal')
    }
    // Commit the starting material once, before the intersection callback reveals it.
    // This is a single layout read per identity change, never a frame loop.
    if (pending.size) void document.documentElement.offsetHeight
    for (const element of pending) observer.observe(element)
    preference.addEventListener('change', revealAll)
    return () => { observer.disconnect(); revealAll(); preference.removeEventListener('change', revealAll) }
  }, [route, matchId, loadedMatchId])
}
