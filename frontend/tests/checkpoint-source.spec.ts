import {test,expect} from '@playwright/test'
import {readFile} from 'node:fs/promises'
const token='test-runtime-token-at-least-32-characters'
const headers={Authorization:`Bearer ${token}`}

test('full-time checkpoint is inspectable, immutable and downloadable after recovery',async ({page,request})=>{
  const config=(await (await request.get('/api/sandbox/presets',{headers})).json()).balanced
  config.duration_seconds=60
  const scenario=await (await request.post('/api/sandbox/scenarios',{headers,data:config})).json()
  const session=await (await request.post('/api/sandbox/sessions',{headers,data:{operation_id:'checkpoint-acceptance-final',scenario_id:scenario.scenario_id}})).json()
  const sid=session.session_id
  expect((await request.post(`/api/sandbox/sessions/${sid}/commands`,{headers,data:{operation_id:'finish',expected_revision:0,kind:'step',ticks:60}})).ok()).toBe(true)
  await page.goto('/#/runtime'); await page.getByLabel('Operator access token').fill(token)
  await page.getByRole('button',{name:'Connect operator',exact:true}).click()
  await page.getByLabel('Runtime / branch').selectOption(sid)
  await expect(page.getByLabel('Authoritative match clock')).toHaveText('01:00')
  await expect(page.getByRole('button',{name:'Save exact checkpoint',exact:true})).toBeEnabled()
  await page.getByRole('button',{name:'Save exact checkpoint',exact:true}).click()
  await expect(page.getByLabel('Saved checkpoint')).not.toHaveValue('')
  await expect(page.getByRole('button',{name:'Run paired ForkCast',exact:true})).toBeDisabled()
  await expect(page.getByText('This checkpoint has no remaining simulation time.',{exact:false})).toBeVisible()
  const cp=await page.getByLabel('Saved checkpoint').inputValue()
  const saved=await (await request.get(`/api/sandbox/checkpoints/${cp}`,{headers})).json()
  await page.route(`**/checkpoints/${cp}`,r=>r.fulfill({status:503,body:'unavailable'}),{times:1})
  const summary=page.getByText('Inspect saved checkpoint source',{exact:true})
  await summary.focus(); await page.keyboard.press('Enter')
  const source=page.getByRole('region',{name:'Saved checkpoint source'})
  await expect(source.getByRole('alert')).toContainText('503')
  await source.getByRole('button',{name:'Retry checkpoint inspection'}).click()
  await expect(source).toContainText(saved.snapshot.state_hash)
  await expect(source).toContainText('Saved tick 01:00')
  await expect(source).toContainText('Actors: 22')
  await page.getByRole('button',{name:'Inspect saved checkpoint tick',exact:true}).click()
  await expect(page.getByLabel('Inspect committed match time')).toHaveValue('60')
  await expect(page.getByLabel('Authoritative match clock')).toHaveText('01:00')
  for(const [name,state] of Object.entries(saved.snapshot.state.rng)) {
    await expect(source.getByText(`${name} RNG counter`,{exact:true})).toBeVisible()
    expect((state as {counter:number}).counter).toBeGreaterThanOrEqual(0)
  }
  const pending=page.waitForEvent('download')
  await source.getByRole('button',{name:'Download saved checkpoint source'}).click()
  const exported=JSON.parse(await readFile((await (await pending).path())!,'utf8'))
  expect(exported).toEqual(saved); expect(JSON.stringify(exported)).not.toContain(token)
  const current=await (await request.get(`/api/sandbox/sessions/${sid}/state`,{headers})).json()
  expect(current.state_hash).toBe(saved.snapshot.state_hash)
  await page.getByLabel('Inspect committed match time').fill('30')
  await page.getByText('Inspect historical engine state',{exact:true}).click()
  const history=page.getByRole('region',{name:'Read-only historical engine state'})
  const expected=await (await request.get(`/api/sandbox/sessions/${sid}/history?at_tick=30`,{headers})).json()
  await expect(history).toContainText(expected.snapshot.state_hash)
  await expect(history).toContainText('Historical tick 00:30 / period 2')
  await expect(page.getByLabel('Authoritative match clock')).toHaveText('01:00')
  expect((await (await request.get(`/api/sandbox/sessions/${sid}/state`,{headers})).json()).state_hash).toBe(current.state_hash)
  await page.getByRole('button',{name:'Disconnect operator',exact:true}).click()
  await expect(history).toHaveCount(0)
  await expect(source).toHaveCount(0)
})
