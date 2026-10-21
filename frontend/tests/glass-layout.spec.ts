import { expect, test } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

const sizes = [[1920,1080],[1440,900],[1280,800],[1024,768],[768,1024],[390,844],[375,812]]
const regions = '.rail,.header,.workspace-nav,.scoreboard,.content-grid,.pitch-wrap,.transport,.metrics,.feed,.analysis-tools,.tactical-lab,.intelligence-grid,.studio,.runtime-room,.runtime-heading,.runtime-setup,.runtime-form-grid,.runtime-score,.runtime-controls,.runtime-columns,.runtime-observer,.runtime-checkpoints,.runtime-forkcast,.data-hub,.observer,.observer-bar,.pass-workbench,.pass-inspection,.pass-method,.runtime-tactics,.runtime-audit,.runtime-manifest,.runtime-analysis,.hub-import,.hub-match,.sandbox-timeline,.tactical-layout,footer'

for (const [width,height] of sizes) {
  test(`glass preserves all four route layouts at ${width}x${height}`, async ({page}, info) => {
    test.setTimeout(45000)
    await page.setViewportSize({width,height})
    const cdp=await page.context().newCDPSession(page)
    await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-transparency',value:'no-preference'},{name:'prefers-contrast',value:'no-preference'},{name:'prefers-color-scheme',value:'dark'}]})
    const artifactRoot = process.env.PX_VISUAL_DIR || info.outputPath('materials')
    await mkdir(artifactRoot,{recursive:true})
    const report: Record<string,unknown> = {}
    for (const route of ['replay','sandbox','data','runtime']) {
      await page.goto(route==='replay'?'/':`/#/${route}`)
      if (route==='runtime') {
        await page.getByLabel('Operator access token').fill('test-runtime-token-at-least-32-characters')
        await page.getByRole('button',{name:'Connect operator',exact:true}).click()
        await expect(page.getByRole('button',{name:'Disconnect operator'})).toBeVisible()
        await page.waitForLoadState('networkidle')
        if(await page.getByLabel('Runtime / branch').inputValue()) await expect(page.getByLabel('Authoritative match clock')).toBeVisible()
        if(!await page.getByRole('button',{name:'Create authoritative scenario'}).isVisible()) await page.getByText('Scenario builder',{exact:true}).click()
        await page.getByLabel('Duration seconds',{exact:true}).fill('300')
        await page.getByRole('button',{name:'Create authoritative scenario'}).click()
        await expect(page.getByLabel('Authoritative match clock')).toHaveText('00:00')
        await page.getByLabel('Step seconds').fill('20')
        await page.getByRole('button',{name:'Step engine',exact:true}).click()
        await expect(page.getByLabel('Authoritative match clock')).toHaveText('00:20')
        await page.getByRole('button',{name:'Save exact checkpoint'}).click()
        await expect(page.getByLabel('Saved checkpoint').locator('option')).toHaveCount(2)
        if(!await page.getByRole('button',{name:'Save scenario',exact:true}).isVisible()) await page.getByText('Scenario builder',{exact:true}).click()
      } else if(route!=='data') {
        await page.getByRole('slider',{name:'Seek match time'}).fill('3500')
        await expect(page.locator('.recap-body')).not.toContainText('Loading')
      } else { await expect(page.getByRole('heading',{name:/Match Data Hub/})).toBeVisible(); await page.getByLabel('Match origin').selectOption('built-in'); await page.getByLabel('Search matches',{exact:true}).fill('comeback-1107'); await expect(page.getByRole('button',{name:'Open for analysis',exact:true})).toHaveCount(1) }
      await page.waitForLoadState('networkidle')
      await page.evaluate(()=>document.documentElement.removeAttribute('data-px-material'))
      await page.evaluate(()=>window.scrollTo(0,0))
      const capture = () => page.evaluate(selector => ({
        boxes:[...document.querySelectorAll(selector)].filter(e=>e.getClientRects().length && e.checkVisibility()).map(e=>{const r=e.getBoundingClientRect();return {id:e.className,tag:e.tagName,x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height}}),
        controls:[...document.querySelectorAll('a,button,input,select,textarea,summary')].filter(e=>e.getClientRects().length && e.checkVisibility()).map(e=>[e.tagName,e.getAttribute('aria-label'),e.tagName==='SELECT'?null:e.textContent?.trim(),e.getAttribute('type')]),
        overflow:document.documentElement.scrollWidth>innerWidth+2
      }),regions)
      const before=await capture()
      await page.screenshot({path:join(artifactRoot,`${route}-${width}-before.png`),fullPage:false,animations:'disabled'})
      await page.evaluate(()=>document.documentElement.setAttribute('data-px-material','glass'))
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))
      const after=await capture()
      expect(after.controls).toEqual(before.controls)
      expect(after.boxes.map(b=>[b.id,b.tag])).toEqual(before.boxes.map(b=>[b.id,b.tag]))
      let maxDelta=0
      for(let i=0;i<before.boxes.length;i++) for(const key of ['x','y','width','height'] as const) {
        const delta=Math.abs(after.boxes[i][key]-before.boxes[i][key]);maxDelta=Math.max(maxDelta,delta)
        expect(delta,`${route} ${before.boxes[i].id} ${key}`).toBeLessThanOrEqual(width<600?4:2)
      }
      expect(after.overflow).toBe(false)
      await page.screenshot({path:join(artifactRoot,`${route}-${width}-after.png`),fullPage:false,animations:'disabled'})
      if(width===1440) for(const part of route==='runtime'?['.runtime-checkpoints','.runtime-forkcast']:route==='replay'?['.pass-inspection','.analysis-tools']:[]) {
        const region=page.locator(part).first(); if(await region.isVisible()) await region.screenshot({path:join(artifactRoot,`${route}-${part.slice(1)}-after.png`),animations:'disabled'})
      }
      report[route]={before,after,maxDelta,materials:await page.evaluate(()=>({blur:getComputedStyle(document.querySelector('.header')!).backdropFilter,reducedTransparency:matchMedia('(prefers-reduced-transparency:reduce)').matches}))}
    }
    await writeFile(join(artifactRoot,`geometry-${width}.json`),JSON.stringify(report,null,2))
    await info.attach('geometry',{body:JSON.stringify(report),contentType:'application/json'})
  })
}
