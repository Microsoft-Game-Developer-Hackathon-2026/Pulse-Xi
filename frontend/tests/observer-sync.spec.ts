import {test,expect} from '@playwright/test'
import {eventSnapshot, replayObserverEvent} from '../src/features/observer/eventSnapshot'
import type {Event,Match} from '../src/types'
const all={team:'all',kind:'all'}

test('source selection follows replay and filters without carrying stale positions',async({request})=>{
  const match:Match=await(await request.get('/api/matches/comeback-1107')).json()
  const events:Event[]=await(await request.get('/api/matches/comeback-1107/events?limit=1000')).json()
  const pass=events.find(e=>e.type==='pass'&&e.start&&e.end&&e.actor_id&&e.recipient_id&&e.outcome==='complete')!
  const missing={...pass,event_id:'unlocated',sequence:pass.sequence+1,match_second:pass.match_second+1,start:null,end:null}
  expect(replayObserverEvent([pass,missing],match.match_id,missing.match_second,'',all)).toBe(missing)
  expect(replayObserverEvent([pass,missing],match.match_id,pass.match_second,'',all)).toBe(pass)
  expect(replayObserverEvent([pass],match.match_id,pass.match_second,pass.event_id,{team:'other',kind:'all'})).toBeUndefined()
  expect(eventSnapshot(match,missing,missing.match_second).ball).toBeNull()
  const start=eventSnapshot(match,pass,pass.match_second,undefined,'start')
  const end=eventSnapshot(match,pass,pass.match_second,undefined,'end')
  expect(start.ball).toEqual(start.origin);expect(end.ball).toEqual(end.target)
  expect(end.recipient_position).toEqual(end.target)
  expect(eventSnapshot(match,{...pass,outcome:'incomplete'},pass.match_second).recipient_position).toBeNull()
  expect(eventSnapshot(match,{...pass,end:null},pass.match_second).ball).toEqual(start.origin)
})

test('actual GLB scene follows seek, step, filters and recorded endpoint samples',async({page,request},info)=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
  const match:Match=await(await request.get('/api/matches/comeback-1107')).json()
  const events:Event[]=await(await request.get('/api/matches/comeback-1107/events?limit=1000')).json()
  const pass=events.find(e=>e.type==='pass'&&e.start&&e.end&&e.actor_id&&e.recipient_id&&e.outcome==='complete')!
  await page.emulateMedia({reducedMotion:'reduce'})
  await page.goto('/#/sandbox')
  const seek=page.getByRole('slider',{name:'Seek match time'})
  await seek.fill(String(pass.match_second))
  await page.getByRole('button',{name:'3D observer',exact:true}).click()
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status','ready')
  const snapshot=page.getByTestId('observer-snapshot'), metrics=page.getByTestId('observer-metrics')
  await expect(snapshot).toHaveAttribute('data-event-id',pass.event_id)
  const expected=eventSnapshot(match,pass,pass.match_second)
  await expect(metrics).toHaveAttribute('data-rendered-ball',JSON.stringify(expected.target))
  await expect(metrics).not.toHaveAttribute('data-rendered-actor','null')
  await expect(metrics).not.toHaveAttribute('data-rendered-recipient','null')
  await page.getByLabel('Recorded ball sample').selectOption('start')
  await expect(metrics).toHaveAttribute('data-rendered-ball',JSON.stringify(expected.origin))
  await page.getByLabel('Recorded ball sample').selectOption('end')
  await expect(metrics).toHaveAttribute('data-rendered-ball',JSON.stringify(expected.target))
  await page.getByTestId('observer-canvas').screenshot({path:info.outputPath('recorded-endpoint.png')})
  await page.getByRole('region',{name:'Sandbox event timeline'}).getByRole('combobox').nth(1).selectOption('goal')
  await expect(snapshot).toHaveAttribute('data-event-id','')
  await expect(metrics).toHaveAttribute('data-rendered-ball','null')
  await page.getByRole('region',{name:'Sandbox event timeline'}).getByRole('combobox').nth(1).selectOption('all')
  await seek.fill('0')
  await expect(snapshot).toHaveAttribute('data-event-id',events[0].event_id)
  await expect(metrics).toHaveAttribute('data-rendered-ball','null')
  await expect(metrics).toHaveAttribute('data-rendered-actor',JSON.stringify([0,.06,0]))
  await seek.fill(String(pass.match_second))
  await page.getByRole('button',{name:'Next event',exact:true}).click()
  const next=events.find(e=>e.match_second>pass.match_second)!
  await expect(snapshot).toHaveAttribute('data-event-id',next.event_id)
  await expect(snapshot).toHaveAttribute('data-cutoff',String(next.match_second))
  await page.getByRole('button',{name:/^4/}).click()
  await page.getByRole('button',{name:'Play',exact:true}).click()
  await expect(snapshot).not.toHaveAttribute('data-event-id',next.event_id)
  await page.getByRole('button',{name:'Pause',exact:true}).click()
  const cutoff=Number(await snapshot.getAttribute('data-cutoff'))
  const sourceId=await snapshot.getAttribute('data-event-id')
  expect(events.find(e=>e.event_id===sourceId)!.match_second).toBeLessThanOrEqual(cutoff)
  expect(errors).toEqual([])
})

test('real imported event with missing coordinates clears every prior marker',async({page,request})=>{
  const packet=await(await request.get('/api/matches/comeback-1107/package')).json()
  packet.schema_version='pulse-xi-match-package/1';delete packet.integrity
  packet.match.match_id='observer-coordinate-gap';packet.match.title='Recorded fixture with a declared coordinate gap'
  for(const event of packet.events) event.match_id=packet.match.match_id
  const source=packet.events.find((e:Event)=>e.type==='pass'&&e.actor_id)
  source.start=null;source.end=null
  packet.provenance.source='Repackaged existing synthetic events; selected pass coordinates omitted for recovery testing'
  const imported=await request.post('/api/data-hub/import',{headers:{Authorization:'Bearer test-import-token-at-least-32-characters'},data:packet})
  expect(imported.ok(),await imported.text()).toBe(true)
  await page.emulateMedia({reducedMotion:'reduce'})
  await page.goto(`/#/sandbox?match=${packet.match.match_id}&event=${source.event_id}&at=${source.match_second}`)
  await page.getByRole('button',{name:'3D observer',exact:true}).click()
  await expect(page.getByTestId('asset-status')).toHaveAttribute('data-status','ready')
  await expect(page.getByTestId('observer-snapshot')).toHaveAttribute('data-event-id',source.event_id)
  const metrics=page.getByTestId('observer-metrics')
  for(const marker of ['ball','actor','recipient']) await expect(metrics).toHaveAttribute(`data-rendered-${marker}`,'null')
  await expect(page.getByText('This event has no valid recorded position.',{exact:true})).toBeVisible()
})
