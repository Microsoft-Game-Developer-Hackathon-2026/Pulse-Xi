import { useLayoutEffect } from 'react'

/** Keep the occupied viewport valid while async panels temporarily shrink. */
export function useStableViewport() {
  useLayoutEffect(() => {
    const root = document.getElementById('root')
    if (!root) return
    const previous = root.style.minHeight
    const reserveViewport = () => {
      // This is a layout floor, not a scroll lock: never call scrollTo or move focus.
      // Scrolling upward releases the space instead of retaining the page's peak height.
      root.style.minHeight = `${Math.ceil(window.scrollY + window.innerHeight)}px`
    }
    reserveViewport()
    window.addEventListener('scroll', reserveViewport, { passive: true })
    window.addEventListener('resize', reserveViewport)
    return () => {
      window.removeEventListener('scroll', reserveViewport)
      window.removeEventListener('resize', reserveViewport)
      root.style.minHeight = previous
    }
  }, [])
}
