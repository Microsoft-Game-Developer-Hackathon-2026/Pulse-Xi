import {test,expect} from '@playwright/test'
import {readFile} from 'node:fs/promises'
import {execFile} from 'node:child_process'
import {promisify} from 'node:util'
import {resolve} from 'node:path'
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
  expect(saved.created_at_utc).toMatch(/Z$/)
  await expect(source.locator('time')).toHaveAttribute('datetime',saved.created_at_utc)
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

test('cancelled checkpoint remains inspectable but cannot start an experiment',async ({page,request})=>{
  const config=(await (await request.get('/api/sandbox/presets',{headers})).json()).balanced
  config.duration_seconds=60
  const scenario=await (await request.post('/api/sandbox/scenarios',{headers,data:config})).json()
  const session=await (await request.post('/api/sandbox/sessions',{headers,data:{operation_id:'checkpoint-cancelled-source',scenario_id:scenario.scenario_id}})).json()
  const sid=session.session_id
  expect((await request.post(`/api/sandbox/sessions/${sid}/commands`,{headers,data:{operation_id:'cancel',expected_revision:0,kind:'cancel'}})).ok()).toBe(true)
  const saved=await (await request.post(`/api/sandbox/sessions/${sid}/commands`,{headers,data:{operation_id:'save',expected_revision:1,kind:'checkpoint'}})).json()
  const rejected=await request.post('/api/sandbox/experiments',{headers,data:{operation_id:'invalid-cancelled-experiment',checkpoint_id:saved.checkpoint_id,expected_revision:2,horizon:30}})
  expect(rejected.status()).toBe(422)
  expect((await rejected.json()).detail.code).toBe('invalid_experiment_boundary')
  await page.goto('/#/runtime');await page.getByLabel('Operator access token').fill(token)
  await page.getByRole('button',{name:'Connect operator',exact:true}).click()
  await page.getByLabel('Runtime / branch').selectOption(sid)
  await expect(page.getByLabel('Saved checkpoint')).toHaveValue(saved.checkpoint_id)
  await expect(page.getByRole('button',{name:'Run paired ForkCast',exact:true})).toBeDisabled()
  await expect(page.getByText('ForkCast requires a checkpoint saved while paused; this source is cancelled.',{exact:true})).toBeVisible()
  await page.getByText('Inspect saved checkpoint source',{exact:true}).click()
  const source=page.getByRole('region',{name:'Saved checkpoint source'})
  await expect(source.locator('time')).toHaveAttribute('datetime',saved.checkpoint_created_at_utc)
  const before=await (await request.get(`/api/sandbox/sessions/${sid}/state`,{headers})).json()
  // Render the truthful legacy-null boundary using the same immutable source snapshot.
  await page.getByText('Inspect saved checkpoint source',{exact:true}).click()
  await page.route(`**/checkpoints/${saved.checkpoint_id}`,async route=>{
    const response=await route.fetch();const data=await response.json()
    await route.fulfill({response,json:{...data,created_at_utc:null}})
  },{times:1})
  await page.getByText('Inspect saved checkpoint source',{exact:true}).click()
  await expect(source).toContainText('unavailable (historical record)')
  await expect(source.locator('time')).toHaveCount(0)
  expect((await (await request.get(`/api/sandbox/sessions/${sid}/state`,{headers})).json()).state_hash).toBe(before.state_hash)
})

test('large bounded ForkCast downloads verify offline without exceeding the online upload limit',async ({page,request},testInfo)=>{
  test.setTimeout(120000)
  const limitToken='test-forkcast-limit-token-at-least-32-characters'
  const headers={Authorization:`Bearer ${limitToken}`}
  const config=(await (await request.get('/api/sandbox/presets',{headers})).json()).balanced
  config.home.tactics.tempo=100;config.away.tactics.tempo=100
  config.home.tactics.pressing=100;config.away.tactics.pressing=100
  const scenario=await (await request.post('/api/sandbox/scenarios',{headers,data:config})).json()
  let current=await (await request.post('/api/sandbox/sessions',{headers,data:{operation_id:'large-forkcast-source',scenario_id:scenario.scenario_id}})).json()
  const sid=current.session_id
  for(let i=0;i<16;i++){
    const step=await request.post(`/api/sandbox/sessions/${sid}/commands`,{headers,data:{operation_id:`advance-${i}`,expected_revision:current.revision,kind:'step',ticks:300}})
    expect(step.ok()).toBe(true);current=await step.json()
  }
  const saved=await (await request.post(`/api/sandbox/sessions/${sid}/commands`,{headers,data:{operation_id:'save',expected_revision:current.revision,kind:'checkpoint'}})).json()
  const experiment=await request.post('/api/sandbox/experiments',{headers,data:{operation_id:'large-forkcast',checkpoint_id:saved.checkpoint_id,expected_revision:saved.revision,trials:5,horizon:600,variation:[{team_id:'home',field:'pressing',value:0},{team_id:'home',field:'tempo',value:20}]}})
  expect(experiment.ok()).toBe(true)
  const eid=(await experiment.json()).experiment_id
  const otherOwner={Authorization:`Bearer ${token}`}
  expect((await request.get(`/api/sandbox/experiments/${eid}`,{headers:otherOwner})).status()).toBe(404)
  expect((await (await request.get('/api/sandbox/experiments',{headers:otherOwner})).json()).some((item:{experiment_id:string})=>item.experiment_id===eid)).toBe(false)
  await expect.poll(async()=>(await (await request.get(`/api/sandbox/experiments/${eid}`,{headers})).json()).status,{timeout:90000,intervals:[250,500]}).toBe('completed')
  const parent=await (await request.get(`/api/sandbox/sessions/${sid}/state`,{headers})).json()
  expect(parent.state_hash).toBe(saved.state_hash)
  await page.goto('/#/runtime');await page.getByLabel('Operator access token').fill(limitToken)
  await page.getByRole('button',{name:'Connect operator',exact:true}).click()
  await page.getByLabel('Runtime / branch').selectOption(sid)
  await expect(page.getByRole('table')).toContainText('home / pressures',{timeout:30000})
  const uploads:string[]=[]
  page.on('request',r=>{if(r.url().endsWith('/api/sandbox/experiments/verify'))uploads.push(r.url())})
  await page.getByRole('button',{name:'Verify experiment independently',exact:true}).click()
  await expect(page.locator('.runtime-notice')).toContainText('exceeds the 2 MB online verification limit',{timeout:30000})
  await expect(page.locator('.runtime-notice')).toContainText('Verification has not been completed in this browser.')
  expect(uploads).toEqual([])
  const pending=page.waitForEvent('download')
  await page.getByRole('button',{name:'Download experiment manifest',exact:true}).click()
  const file=testInfo.outputPath('large-forkcast.json')
  await (await pending).saveAs(file)
  const bytes=await readFile(file)
  expect(bytes.byteLength).toBeGreaterThan(2_000_000)
  expect(bytes.byteLength).toBeLessThanOrEqual(20_000_000)
  expect(bytes.toString()).not.toContain(limitToken)
  const replay=await promisify(execFile)('python',['-m','app.sandbox.verify_experiment',file],{cwd:resolve('../backend'),timeout:30000})
  expect(JSON.parse(replay.stdout).verified).toBe(true)
  expect((await (await request.get(`/api/sandbox/sessions/${sid}/state`,{headers})).json()).state_hash).toBe(saved.state_hash)
})
