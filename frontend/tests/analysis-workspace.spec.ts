import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { csvCell, readBookmarks, readWorkspace } from '../src/features/sandbox/analysisStorage'

test('local schemas reject unsafe or oversized records and protect CSV cells', () => {
  let raw = ''
  const original = Object.getOwnPropertyDescriptor(globalThis,'localStorage')
  Object.defineProperty(globalThis,'localStorage',{ configurable:true, value:{ getItem:()=>raw } })
  try {
    const base={version:1,matchId:'m',second:12,eventId:'e',sequence:1,eventSecond:12,speed:1,filters:{team:'all',kind:'all'},view:'2d',quality:'standard',panel:'bookmarks'}
    raw=JSON.stringify(base);expect(readWorkspace().value?.second).toBe(12)
    for(const bad of [null,{...base,second:-1},{...base,quality:'ultra'},{...base,version:2},{...base,speed:100},{...base,filters:{team:'all',kind:'fake'}}]){
      raw=JSON.stringify(bad);expect(readWorkspace().value).toBeNull();expect(readWorkspace().notice).not.toBe('')
    }
    const b={matchId:'m',eventId:'e',sequence:1,second:12,note:'note'}
    raw=JSON.stringify({version:1,items:[b]});expect(readBookmarks().items).toHaveLength(1)
    for(const bad of [{version:1,items:[b,b]},{version:1,items:[{...b,note:'x'.repeat(501)}]},{version:1,items:Array(201).fill(b)}]){
      raw=JSON.stringify(bad);expect(readBookmarks().items).toHaveLength(0);expect(readBookmarks().notice).not.toBe('')
    }
    for(const cell of ['=1',' +formula','@macro','\ttext','\ufeff=1'])expect(csvCell(cell)).toMatch(/^"'/)
    expect(csvCell(0)).toBe('"0"');expect(csvCell(null)).toBe('""')
  } finally { if(original)Object.defineProperty(globalThis,'localStorage',original);else Reflect.deleteProperty(globalThis,'localStorage') }
})

test('real pass bookmark, refresh restoration, filtered and pass exports stay synchronized', async ({ page, request }, testInfo) => {
  const failures: string[] = []; page.on('pageerror', error => failures.push(error.message))
  const events = await (await request.get('/api/matches/comeback-1107/events?limit=1000')).json()
  const pass = events.find((event: {type:string;match_second:number}) => event.type === 'pass' && event.match_second > 500)
  await page.goto(`/#/sandbox?match=comeback-1107&at=${pass.match_second}&event=${pass.event_id}`)
  await expect(page.getByTestId('pass-inspector')).toHaveAttribute('data-event-id',pass.event_id)
  await page.getByLabel('Event note', { exact: true }).fill('=SUM(1,2)')
  await page.getByRole('button',{name:'Bookmark selected event',exact:true}).click()
  await expect(page.getByRole('list',{name:'Saved event bookmarks'}).getByRole('button',{name:/Go to/})).toHaveCount(1)
  await page.getByRole('combobox', {name:/^EVENT TYPE/}).selectOption('pass')
  await page.getByRole('button',{name:'4\u00d7',exact:true}).click()
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('pulse-xi-workspace-v1') ?? '{}').speed)).toBe(4)
  // Navigate without the explicit deep link so browser-local state controls restoration.
  await page.goto('/#/sandbox')
  await page.reload()
  await expect(page.getByRole('slider',{name:'Seek match time'})).toHaveValue(String(pass.match_second))
  await expect(page.getByTestId('pass-inspector')).toHaveAttribute('data-event-id',pass.event_id)
  await expect(page.getByRole('combobox', {name:/^EVENT TYPE/})).toHaveValue('pass')
  await expect(page.getByRole('button',{name:'4\u00d7',exact:true})).toHaveAttribute('class', /selected|active/)
  await page.getByRole('button',{name:'Analysis exports',exact:true}).click()
  const jsonDownload = page.waitForEvent('download'); await page.getByRole('button',{name:'Download analysis',exact:true}).click()
  const exported = JSON.parse(await readFile(await (await jsonDownload).path() as string,'utf8'))
  expect(exported.data).toEqual(events.filter((e:{type:string;match_second:number}) => e.type==='pass' && e.match_second<=pass.match_second))
  await page.getByLabel('Export category').selectOption('pass')
  const passDownload = page.waitForEvent('download'); await page.getByRole('button',{name:'Download analysis',exact:true}).click()
  const packet = JSON.parse(await readFile(await (await passDownload).path() as string,'utf8')).data[0]
  const authoritative = await (await request.get(`/api/matches/comeback-1107/passes/${pass.event_id}/difficulty?at_second=${pass.match_second}`)).json()
  expect(packet).toEqual(authoritative)
  await page.getByLabel('Export category').selectOption('bookmarks'); await page.getByLabel('Export format').selectOption('csv')
  const csvDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Download analysis',exact:true}).click()
  const csv = await readFile(await (await csvDownload).path() as string,'utf8')
  expect(csv).toContain(pass.event_id); expect(csv).toContain("'=SUM(1,2)")
  await page.getByRole('button',{name:/Saved events/}).click()
  await page.getByRole('region',{name:'Analysis workspace tools'}).screenshot({path:testInfo.outputPath('saved-analysis.png')})
  await page.getByRole('slider',{name:'Seek match time'}).fill('0')
  await page.getByRole('button',{name:'Analysis exports',exact:true}).click()
  await page.getByLabel('Export format').selectOption('json')
  const pastDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Download analysis',exact:true}).click()
  const past=JSON.parse(await readFile(await (await pastDownload).path() as string,'utf8'))
  expect(past.data).toEqual([])
  await page.getByRole('button',{name:/Saved events/}).click()
  await page.getByRole('button',{name:new RegExp(`Go to ${pass.event_id}`)}).click()
  await expect(page.getByTestId('pass-inspector')).toHaveAttribute('data-event-id',pass.event_id)
  await page.getByLabel('SELECT MATCH').selectOption('high-press-2209')
  await expect(page.getByLabel('SELECT MATCH')).toHaveValue('high-press-2209')
  await expect(page.getByText('No saved events for this match.',{exact:true})).toBeVisible()
  await expect(page.getByRole('list',{name:'Saved event bookmarks'}).getByRole('button')).toHaveCount(0)
  expect(failures).toEqual([])
})

test('bookmark notes are escaped, duplicates update, keyboard removal and missing sources recover', async ({ page, request }) => {
  const events=await (await request.get('/api/matches/comeback-1107/events?limit=1000')).json()
  const event=events.find((e:{type:string})=>e.type==='pass')
  await page.goto(`/#/sandbox?match=comeback-1107&at=${event.match_second}&event=${event.event_id}`)
  await page.getByLabel('Event note',{exact:true}).fill('<img src=x onerror=alert(1)>')
  await page.getByRole('button',{name:'Bookmark selected event',exact:true}).click()
  await page.getByRole('button',{name:'Update bookmark note',exact:true}).click()
  await expect(page.getByRole('list',{name:'Saved event bookmarks'}).getByRole('listitem')).toHaveCount(1)
  await expect(page.getByRole('list',{name:'Saved event bookmarks'}).locator('img')).toHaveCount(0)
  await page.getByLabel('Search bookmarks').fill('not-present');await expect(page.getByRole('list',{name:'Saved event bookmarks'}).getByRole('listitem')).toHaveCount(0)
  await page.getByLabel('Search bookmarks').fill('')
  const remove=page.getByRole('button',{name:`Remove bookmark ${event.event_id}`});await remove.focus();await page.keyboard.press('Enter')
  await expect(page.getByRole('list',{name:'Saved event bookmarks'}).getByRole('listitem')).toHaveCount(0)
  await page.evaluate(()=>localStorage.setItem('pulse-xi-bookmarks-v1',JSON.stringify({version:1,items:[{matchId:'comeback-1107',eventId:'missing',sequence:2,second:50,note:'review'}]})))
  await page.reload();await expect(page.getByRole('button',{name:/Go to missing/})).toBeDisabled()
  await expect(page.getByText('Source event is missing or changed; navigation unavailable.')).toBeVisible()
})

test('corrupt storage, unsupported schema, missing match and cross-tab conflict are explicit', async ({page})=>{
  await page.addInitScript(()=>{localStorage.setItem('pulse-xi-workspace-v1','{"version":99}');localStorage.setItem('pulse-xi-bookmarks-v1','{broken')})
  await page.goto('/#/sandbox')
  await expect(page.getByText('Saved workspace is unavailable or incompatible.',{exact:false})).toBeVisible()
  await expect(page.getByText('Saved bookmarks are corrupt, incompatible or over the storage limit.',{exact:false})).toBeVisible()
  await page.getByRole('button',{name:'Reset all bookmarks',exact:true}).click();await page.getByRole('button',{name:'Confirm reset bookmarks',exact:true}).click()
  await page.evaluate(()=>dispatchEvent(new StorageEvent('storage',{key:'pulse-xi-workspace-v1'})))
  await expect(page.getByRole('button',{name:'Keep this tab',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Keep this tab',exact:true}).click()
  await page.goto('/#/sandbox?match=missing-match&at=1')
  await expect(page.getByText('Saved or linked match is unavailable.',{exact:false})).toBeVisible()
})

test('saved view and quality restore, seek excludes future export and failed export can retry', async ({page,request})=>{
  const events=await (await request.get('/api/matches/comeback-1107/events?limit=1000')).json()
  const pass=events.find((e:{type:string})=>e.type==='pass')
  await page.goto(`/#/sandbox?match=comeback-1107&at=${pass.match_second}&event=${pass.event_id}`)
  await page.getByRole('button',{name:'3D observer',exact:true}).click()
  await page.getByLabel('3D QUALITY').selectOption('low')
  await expect.poll(()=>page.evaluate(()=>JSON.parse(localStorage.getItem('pulse-xi-workspace-v1')??'{}').view)).toBe('3d')
  await page.goto('/#/sandbox');await page.reload()
  await expect(page.getByLabel('3D QUALITY')).toHaveValue('low')
  await expect(page.getByTestId('observer-snapshot')).toHaveAttribute('data-event-id',pass.event_id)
  await page.getByRole('button',{name:'2D pitch',exact:true}).click()
  await page.getByRole('slider',{name:'Seek match time'}).fill('0')
  await page.getByRole('button',{name:'Analysis exports',exact:true}).click()
  await page.route('**/analysis-export?**',route=>route.fulfill({status:503,body:'unavailable'}))
  await page.getByRole('button',{name:'Download analysis',exact:true}).click();await expect(page.getByText('Export unavailable (503)',{exact:false})).toBeVisible()
  await page.unroute('**/analysis-export?**')
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download analysis',exact:true}).click()
  const data=JSON.parse(await readFile(await (await download).path() as string,'utf8'))
  expect(data.replay_cutoff).toBe(0);expect(data.data.every((e:{match_second:number})=>e.match_second===0)).toBe(true)
})

test('two tabs do not silently replace a working replay and bounded bookmark lists remain searchable', async ({page,context,request})=>{
  const events=await (await request.get('/api/matches/comeback-1107/events?limit=1000')).json()
  await page.addInitScript(items=>localStorage.setItem('pulse-xi-bookmarks-v1',JSON.stringify({version:1,items})),
    events.slice(0,200).map((e:{event_id:string;sequence:number;match_second:number})=>({matchId:'comeback-1107',eventId:e.event_id,sequence:e.sequence,second:e.match_second,note:'tag-'+e.sequence})))
  await page.goto('/#/sandbox')
  await expect(page.getByRole('list',{name:'Saved event bookmarks'}).getByRole('listitem')).toHaveCount(200)
  await page.getByLabel('Search bookmarks').fill('tag-199')
  await expect(page.getByRole('list',{name:'Saved event bookmarks'}).getByRole('listitem')).toHaveCount(1)
  await page.getByRole('slider',{name:'Seek match time'}).fill('1200')
  await expect.poll(()=>page.evaluate(()=>JSON.parse(localStorage.getItem('pulse-xi-workspace-v1')??'{}').second)).toBe(1200)
  const other=await context.newPage();await other.goto('/#/sandbox')
  await expect(other.getByRole('slider',{name:'Seek match time'})).toHaveValue('1200')
  await other.getByRole('slider',{name:'Seek match time'}).fill('1800')
  await expect(page.getByRole('button',{name:'Keep this tab',exact:true})).toBeVisible()
  await expect(page.getByRole('slider',{name:'Seek match time'})).toHaveValue('1200')
  await other.close()
})

test('seeking cancels an in-flight real export before it can download stale data',async({page})=>{
  await page.goto('/#/sandbox?match=comeback-1107&at=2000')
  await page.getByRole('button',{name:'Analysis exports',exact:true}).click()
  let release!:()=>void, entered!:()=>void, finished!:()=>void
  const hold=new Promise<void>(resolve=>{release=resolve}), started=new Promise<void>(resolve=>{entered=resolve}), done=new Promise<void>(resolve=>{finished=resolve})
  await page.route('**/analysis-export?**',async route=>{
    const response=await route.fetch();entered();await hold
    try { await route.fulfill({response}) } catch { /* Client cancellation is expected. */ } finally { finished() }
  })
  const downloads:string[]=[];page.on('download',d=>downloads.push(d.suggestedFilename()))
  await page.getByRole('button',{name:'Download analysis',exact:true}).click();await started
  await page.getByRole('slider',{name:'Seek match time'}).fill('0')
  await expect(page.getByRole('button',{name:'Download analysis',exact:true})).toBeEnabled()
  release();await done;await page.waitForTimeout(150)
  expect(downloads).toEqual([])
})
