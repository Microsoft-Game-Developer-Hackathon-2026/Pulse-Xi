export const WORKSPACE_KEY = 'pulse-xi-workspace-v1'
export const BOOKMARK_KEY = 'pulse-xi-bookmarks-v1'
export const eventKinds = ['all', 'kickoff', 'pass', 'carry', 'shot', 'goal', 'save', 'tackle', 'interception', 'pressure', 'recovery', 'turnover', 'clearance', 'foul', 'card', 'substitution', 'halftime', 'fulltime']
export type Filters = { team: string; kind: string }
export type Workspace = { version: 1; matchId: string; second: number; eventId: string; sequence: number | null;
  eventSecond: number | null; speed: number; filters: Filters; view: '2d' | '3d'; quality: 'low' | 'standard' | 'high'; panel: 'bookmarks' | 'exports' }
export type Bookmark = { matchId: string; eventId: string; sequence: number; second: number; note: string }
export function bookmarkTransaction(action: () => void): Promise<void> {
  return navigator.locks ? navigator.locks.request(BOOKMARK_KEY, action) : Promise.resolve().then(action)
}
export function deepWorkspace(): Workspace | null {
  const query = window.location.hash.split('?')[1]
  if (!query) return null
  if (query.length > 2048) throw Error('Analysis link is too long.')
  const params = new URLSearchParams(query), matchId = params.get('match'), eventId = params.get('event') ?? '', second = Number(params.get('at') ?? '0')
  if (!matchId || !id(matchId) || !id(eventId) || !integer(second)) throw Error('Analysis link has invalid identifiers or replay time.')
  return { version: 1, matchId, eventId, second, sequence: null, eventSecond: null, speed: 1, filters: { team: 'all', kind: 'all' }, view: '2d', quality: 'standard', panel: 'bookmarks' }
}
const id = (value: unknown): value is string => typeof value === 'string' && value.length <= 160 && !/[\x00-\x1f]/.test(value)
const integer = (value: unknown): value is number => Number.isInteger(value) && Number(value) >= 0 && Number(value) <= 100_000_000
export function readWorkspace(): { value: Workspace | null; notice: string } {
  try {
    const raw = localStorage.getItem(WORKSPACE_KEY)
    if (!raw) return { value: null, notice: '' }
    if (raw.length > 16000) throw Error()
    const v = JSON.parse(raw)
    if (!v || v.version !== 1 || !id(v.matchId) || !v.matchId || !id(v.eventId) || !integer(v.second) ||
        ![.5, 1, 2, 4].includes(v.speed) || !v.filters || !id(v.filters.team) || !eventKinds.includes(v.filters.kind) ||
        !['2d', '3d'].includes(v.view) || !['low', 'standard', 'high'].includes(v.quality) || !['bookmarks', 'exports'].includes(v.panel) ||
        !(v.sequence === null || integer(v.sequence)) || !(v.eventSecond === null || integer(v.eventSecond))) throw Error()
    return { value: v, notice: '' }
  } catch { return { value: null, notice: 'Saved workspace is unavailable or incompatible. Reset local workspace to recover.' } }
}
export function readBookmarks(): { items: Bookmark[]; notice: string } {
  try {
    const raw = localStorage.getItem(BOOKMARK_KEY)
    if (!raw) return { items: [], notice: '' }
    if (raw.length > 256000) throw Error()
    const value = JSON.parse(raw)
    if (value?.version !== 1 || !Array.isArray(value.items) || value.items.length > 200) throw Error()
    const keys = new Set<string>()
    for (const b of value.items) {
      if (!b || !id(b.matchId) || !b.matchId || !id(b.eventId) || !b.eventId || !integer(b.sequence) || !integer(b.second) ||
          typeof b.note !== 'string' || b.note.length > 500 || keys.has(JSON.stringify([b.matchId, b.eventId]))) throw Error()
      keys.add(JSON.stringify([b.matchId, b.eventId]))
    }
    return { items: value.items, notice: '' }
  } catch { return { items: [], notice: 'Saved bookmarks are corrupt, incompatible or over the storage limit. Reset bookmarks to recover.' } }
}
export function csvCell(value: unknown): string {
  let text = value === null || value === undefined ? '' : String(value)
  if (typeof value === 'string' && (/^[\s\uFEFF]*[=+\-@]/.test(text) || /^[\t\r\n]/.test(text))) text = "'" + text
  return '"' + text.replaceAll('"', '""') + '"'
}
export function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob), anchor = document.createElement('a')
  anchor.href = url; anchor.download = filename; document.body.append(anchor); anchor.click(); anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 2000)
}
