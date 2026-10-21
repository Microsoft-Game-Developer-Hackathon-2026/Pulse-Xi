import {test, expect} from '@playwright/test'
const token = 'test-runtime-token-at-least-32-characters'
const headers = {Authorization: `Bearer ${token}`}

test('native runtime Control vs Chaos uses authenticated source and cancels revoked views', async ({page,request}) => {
  const config = (await (await request.get('/api/sandbox/presets',{headers})).json()).balanced
  config.duration_seconds = 120
  const scenario = await (await request.post('/api/sandbox/scenarios',{headers,data:config})).json()
  const session = await (await request.post('/api/sandbox/sessions',{headers,data:{operation_id:'control-short-create',scenario_id:scenario.scenario_id}})).json()
  const sid = session.session_id
  expect((await request.post(`/api/sandbox/sessions/${sid}/commands`,{headers,data:{operation_id:'control-step',expected_revision:0,kind:'step',ticks:120}})).ok()).toBe(true)
  const publicReads: string[] = []
  page.on('request',r=>{if(r.url().includes(`/api/matches/${sid}`)) publicReads.push(r.url())})
  await page.goto('/#/runtime')
  await page.getByLabel('Operator access token').fill(token)
  await page.getByRole('button',{name:'Connect operator',exact:true}).click()
  await page.getByLabel('Runtime / branch').selectOption(sid)
  await expect(page.getByLabel('Authoritative match clock')).toHaveText('02:00')
  await page.getByText('Recorded-event analysis, bookmarks and 3D',{exact:true}).click()
  await page.getByText('Runtime Control vs Chaos',{exact:true}).click()
  const panel = page.getByRole('region',{name:'Control vs Chaos analysis'})
  await expect(panel).toContainText('Partial current window')
  await expect(panel).toContainText('two complete windows are not yet available')
  await panel.getByLabel('Control vs Chaos window').selectOption('600')
  await expect(panel).toContainText('control-chaos-formulas/1')
  const response = await request.get(`/api/sandbox/sessions/${sid}/control-chaos?at_second=120&window_seconds=600`,{headers})
  expect(response.ok()).toBe(true)
  expect((await response.json()).comparison_available).toBe(false)
  await page.setViewportSize({width:390,height:844})
  await expect(panel.getByLabel('Control vs Chaos window')).toBeVisible()
  await panel.getByLabel('Control vs Chaos window').focus()
  await expect(panel.getByLabel('Control vs Chaos window')).toBeFocused()
  let release!: ()=>void
  const blocked = new Promise<void>(r=>{release=r})
  let started!: ()=>void
  const intercepted = new Promise<void>(r=>{started=r})
  await page.route('**/control-chaos?**',async route=>{const result=await route.fetch(); started(); await blocked; await route.fulfill({response:result}).catch(()=>{})})
  await panel.getByLabel('Control vs Chaos window').selectOption('900')
  await intercepted
  await page.getByRole('button',{name:'Disconnect operator',exact:true}).click()
  release()
  await expect(panel).toHaveCount(0)
  expect(publicReads).toEqual([])
  expect(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))).not.toContain(token)
})

test('complete native windows expose real turning point sources and recover after failure', async ({page,request}) => {
  const config = (await (await request.get('/api/sandbox/presets',{headers})).json()).balanced
  config.seed = 7; config.duration_seconds = 1800
  const scenario = await (await request.post('/api/sandbox/scenarios',{headers,data:config})).json()
  let session = await (await request.post('/api/sandbox/sessions',{headers,data:{operation_id:'control-long-create',scenario_id:scenario.scenario_id}})).json()
  const sid = session.session_id
  for(let i=0;i<6;i++) session = await (await request.post(`/api/sandbox/sessions/${sid}/commands`,{headers,data:{operation_id:`control-long-${i}`,expected_revision:session.revision,kind:'step',ticks:300}})).json()
  let cutoff = 600
  for(;cutoff<=1800;cutoff+=300) {
    const result = await (await request.get(`/api/sandbox/sessions/${sid}/control-chaos?at_second=${cutoff}`,{headers})).json()
    if(result.analysis.interpretation.turning_points.length) break
  }
  expect(cutoff).toBeLessThanOrEqual(1800)
  await page.goto('/#/runtime')
  await page.getByLabel('Operator access token').fill(token)
  await page.getByRole('button',{name:'Connect operator',exact:true}).click()
  await page.getByLabel('Runtime / branch').selectOption(sid)
  await expect(page.getByLabel('Authoritative match clock')).toHaveText('30:00')
  await page.getByLabel('Inspect committed match time').fill(String(cutoff))
  await page.getByText('Recorded-event analysis, bookmarks and 3D',{exact:true}).click()
  await page.getByText('Runtime Control vs Chaos',{exact:true}).click()
  const panel = page.getByRole('region',{name:'Control vs Chaos analysis'})
  await expect(panel).toContainText('Complete current window.')
  await panel.locator('.control-turning-points button').first().click()
  const source = panel.locator('.control-source-list button').first()
  const label = await source.innerText()
  const id = label.split(' · ').at(-1)!
  await source.click()
  await page.getByRole('button',{name:'3D observer',exact:true}).click()
  await expect(page.getByTestId('observer-snapshot')).toHaveAttribute('data-event-id',id)
  await page.getByRole('button',{name:'2D pitch',exact:true}).click()
  // Source navigation can leave the preceding 300-second request in flight.
  // Fail only the requested window, so that request cannot consume the fault.
  const targetWindow = (url: URL) => url.pathname === `/api/sandbox/sessions/${sid}/control-chaos`
    && url.searchParams.get('window_seconds') === '600'
  await page.route(targetWindow,route=>route.fulfill({status:503,body:'unavailable'}),{times:1})
  const failedWindow = page.waitForResponse(response => targetWindow(new URL(response.url())) && response.status() === 503)
  await panel.getByLabel('Control vs Chaos window').selectOption('600')
  await failedWindow
  await expect(panel.getByRole('alert')).toContainText('503')
  await panel.getByRole('button',{name:'Retry Control vs Chaos'}).click()
  await expect(panel.getByRole('alert')).toHaveCount(0)
  await expect(panel).toContainText('control-chaos-formulas/1')
})

test('switching real runtime sessions discards a delayed private analysis response',async ({page,request},info)=>{
  async function create(duration:number) {
    const config = (await (await request.get('/api/sandbox/presets',{headers})).json()).balanced
    config.duration_seconds=duration
    const scenario = await (await request.post('/api/sandbox/scenarios',{headers,data:config})).json()
    const session = await (await request.post('/api/sandbox/sessions',{headers,data:{operation_id:`control-switch-${duration}`,scenario_id:scenario.scenario_id}})).json()
    expect((await request.post(`/api/sandbox/sessions/${session.session_id}/commands`,{headers,data:{operation_id:'switch-step',expected_revision:0,kind:'step',ticks:duration}})).ok()).toBe(true)
    return session.session_id as string
  }
  const first=await create(120), second=await create(60)
  await page.goto('/#/runtime')
  await page.getByLabel('Operator access token').fill(token)
  await page.getByRole('button',{name:'Connect operator',exact:true}).click()
  await page.getByLabel('Runtime / branch').selectOption(first)
  await expect(page.getByLabel('Authoritative match clock')).toHaveText('02:00')
  await page.getByText('Recorded-event analysis, bookmarks and 3D',{exact:true}).click()
  await page.getByText('Runtime Control vs Chaos',{exact:true}).click()
  const panel=page.getByRole('region',{name:'Control vs Chaos analysis'})
  await expect(panel).toContainText('control-chaos-formulas/1')
  let release!:()=>void, started!:()=>void
  const blocked=new Promise<void>(r=>{release=r}), intercepted=new Promise<void>(r=>{started=r})
  await page.route(`**/sessions/${first}/control-chaos?**`,async route=>{
    const response=await route.fetch(); started(); await blocked
    await route.fulfill({response}).catch(()=>{})
  })
  await panel.getByLabel('Control vs Chaos window').selectOption('600')
  await intercepted
  await page.getByLabel('Runtime / branch').selectOption(second)
  await expect(page.getByLabel('Authoritative match clock')).toHaveText('01:00')
  await page.getByText('Recorded-event analysis, bookmarks and 3D',{exact:true}).click()
  await page.getByText('Runtime Control vs Chaos',{exact:true}).click()
  await expect(panel).toContainText('control-chaos-formulas/1')
  release()
  await expect(page.locator('.runtime-analysis')).toContainText(second)
  await expect(page.locator('.runtime-analysis')).not.toContainText(first)
  await expect(panel.getByLabel('Control vs Chaos window')).toHaveValue('300')
  await page.setViewportSize({width:390,height:844})
  await panel.scrollIntoViewIfNeeded()
  await page.screenshot({path:info.outputPath('runtime-control-mobile.png'),fullPage:true})
})
