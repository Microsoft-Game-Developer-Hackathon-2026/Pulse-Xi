import { useLayoutEffect, useRef, type RefObject } from 'react'

/** Glide existing rows to their new position when a keyed child is inserted or removed.
 * Only transforms inside the list are animated; surrounding layout is never touched.
 * Skipped entirely under prefers-reduced-motion. */
export function useFlipList(container: RefObject<HTMLElement | null>, signature: string) {
  const previous = useRef(new Map<string, number>())
  useLayoutEffect(() => {
    const root = container.current
    if (!root) return
    const rows = Array.from(root.querySelectorAll<HTMLElement>('[data-flip-key]'))
    const next = new Map(rows.map(row => [row.dataset.flipKey!, row.offsetTop]))
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!reduced && previous.current.size) {
      for (const row of rows) {
        const before = previous.current.get(row.dataset.flipKey!)
        const delta = before === undefined ? 0 : before - row.offsetTop
        if (delta && typeof row.animate === 'function') row.animate([{ transform: `translateY(${delta}px)` }, { transform: 'translateY(0)' }], { duration: 220, easing: 'cubic-bezier(.2,.8,.2,1)' })
      }
    }
    previous.current = next
  }, [container, signature])
}
