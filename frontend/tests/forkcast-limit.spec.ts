import {test,expect} from '@playwright/test'
import {readFile} from 'node:fs/promises'
import {execFile} from 'node:child_process'
import {promisify} from 'node:util'
import {resolve} from 'node:path'
const token='test-runtime-token-at-least-32-characters'

test('large bounded ForkCast downloads verify offline without exceeding the online upload limit',async ({page,request},testInfo)=>{
  test.setTimeout(240000)
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
  try {
    await expect(page.getByRole('table')).toContainText('home / pressures',{timeout:90000})
  } catch (reason) {
    throw new Error(`${String(reason)}; visible API/UI errors: ${JSON.stringify(await page.getByRole('alert').allTextContents())}; selected runtime: ${await page.getByLabel('Runtime / branch').inputValue()}`)
  }
  const archiveReads:string[]=[]
  page.on('request',r=>{if(r.method()==='GET' && /\/experiments\/[^/]+\/(manifest|reproduction)$/.test(r.url()))archiveReads.push(r.url())})
  const uploads:string[]=[]
  page.on('request',r=>{if(r.url().endsWith('/api/sandbox/experiments/verify'))uploads.push(r.url())})
  await page.getByRole('button',{name:'Verify experiment independently',exact:true}).click()
  await expect(page.locator('.runtime-notice')).toContainText('exceeds the 2 MB online verification limit',{timeout:90000})
  await expect(page.locator('.runtime-notice')).toContainText('Verification has not been completed in this browser.')
  expect(uploads).toEqual([])
  const pending=page.waitForEvent('download')
  await page.getByRole('button',{name:'Download experiment manifest',exact:true}).click()
  const file=testInfo.outputPath('large-forkcast.json')
  await (await pending).saveAs(file)
  expect(archiveReads).toHaveLength(1)
  expect(archiveReads[0]).toMatch(/\/reproduction$/)
  const bytes=await readFile(file)
  expect(bytes.byteLength).toBeGreaterThan(2_000_000)
  expect(bytes.byteLength).toBeLessThanOrEqual(20_000_000)
  expect(bytes.toString()).not.toContain(limitToken)
  const replay=await promisify(execFile)('python',['-m','app.sandbox.verify_experiment',file],{cwd:resolve('../backend'),timeout:30000})
  expect(JSON.parse(replay.stdout).verified).toBe(true)
  expect((await (await request.get(`/api/sandbox/sessions/${sid}/state`,{headers})).json()).state_hash).toBe(saved.state_hash)
})
