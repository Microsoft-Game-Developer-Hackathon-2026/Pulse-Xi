import { expect, test } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

const sizes = [[1920,1080],[1440,900],[1280,800],[1024,768],[768,1024],[390,844],[375,812]]
const regions = '.rail,.header,.workspace-nav,.scoreboard,.content-grid,.pitch-wrap,.transport,.metrics,.feed,.analysis-tools,.tactical-lab,.intelligence-grid,.studio,.runtime-room,.runtime-heading,.runtime-setup,.runtime-form-grid,.runtime-score,.runtime-controls,.runtime-columns,.runtime-observer,.runtime-checkpoints,.runtime-forkcast,.data-hub,.observer,.observer-bar,.pass-workbench,.pass-inspection,.pass-method,.runtime-tactics,.runtime-audit,.runtime-manifest,.runtime-analysis,.hub-import,.hub-match,.sandbox-timeline,.tactical-layout,footer'

for (const [width,height] of sizes) {
  test(`Atelier keeps all four routes usable at ${width}x${height}`, async ({page}, info) => {
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
        // Tactics load on their own debounce; snapshot controls only after the momentum buttons exist, or the two snapshots race the response.
        await expect(page.locator('.momentum-bars button').first()).toBeVisible()
      } else { await expect(page.getByRole('heading',{name:/Match Data Hub/})).toBeVisible(); await page.getByLabel('Match origin').selectOption('built-in'); await page.getByLabel('Search matches',{exact:true}).fill('comeback-1107'); await expect(page.getByRole('button',{name:'Open for analysis',exact:true})).toHaveCount(1) }
      await page.waitForLoadState('networkidle')
      await page.emulateMedia({reducedMotion:'reduce'})
      await page.evaluate(()=>window.scrollTo(0,0))
      const controls = () => page.evaluate(() => [...document.querySelectorAll('a,button,input,select,textarea,summary')]
        .filter(element=>element.checkVisibility()).map(element=>[element.tagName,element.getAttribute('aria-label'),element.getAttribute('type'),element.tagName==='SELECT'?null:element.textContent?.trim()]))
      // Same DOM/source state, original presentation is captured for visual review only.
      // A redesigned surface is not required to inherit legacy dimensions.
      await page.evaluate(()=>document.documentElement.removeAttribute('data-px-material'))
      const originalControls=await controls()
      await page.screenshot({path:join(artifactRoot,`${route}-${width}-before.png`),animations:'disabled'})
      await page.evaluate(()=>document.documentElement.setAttribute('data-px-material','glass'))
      expect(await controls()).toEqual(originalControls)
      await expect(page.locator('.workspace-nav')).toBeVisible()
      for(const link of await page.locator('.workspace-nav a').all()) {
        const box=await link.boundingBox(); expect(box).not.toBeNull()
        expect(box!.height).toBeGreaterThanOrEqual(44)
        expect(box!.width).toBeGreaterThanOrEqual(44)
      }
      const layout=await page.evaluate(selector=>({
        boxes:[...document.querySelectorAll(selector)].filter(element=>element.checkVisibility()).map(element=>{const r=element.getBoundingClientRect();return {id:element.className,x:r.x,y:r.y+scrollY,width:r.width,height:r.height}}),
        overflow:document.documentElement.scrollWidth>innerWidth+2,
        clippedHeadings:[...document.querySelectorAll('.topbar h2,.runtime-heading h2,.brand h1,.panel-title,.data-hub h2')]
          .filter(element=>element.checkVisibility() && element.scrollWidth>element.clientWidth+2).map(element=>element.textContent),
        order:[...document.querySelectorAll('.topbar,.scoreboard,.content-grid,.intelligence-grid,.studio')].filter(element=>element.checkVisibility()).map(element=>element.classList[0]),
      }),regions)
      expect(layout.overflow,`${route}: viewport overflow`).toBe(false)
      expect(layout.clippedHeadings,`${route}: clipped heading`).toEqual([])
      for(const box of layout.boxes) {
        expect(box.width,`${route}: ${box.id} has a usable width`).toBeGreaterThan(0)
        expect(box.height,`${route}: ${box.id} has a usable height`).toBeGreaterThan(0)
        // Horizontal scroll belongs only inside existing table/event viewports.
        if(!box.id.includes('rail')) {
          expect(box.x,`${route}: ${box.id} left edge`).toBeGreaterThanOrEqual(-2)
          expect(box.x+box.width,`${route}: ${box.id} right edge`).toBeLessThanOrEqual(width+2)
        }
      }
      if(route==='replay'||route==='sandbox') {
        expect(layout.order).toEqual(['topbar','scoreboard','content-grid','intelligence-grid','studio'])
        const hero=page.locator('.scoreboard'), pitch=page.locator('.pitch-wrap').first()
        const h=await hero.boundingBox(), field=await pitch.boundingBox()
        expect(h!.height).toBeGreaterThanOrEqual(190)
        expect(field!.y).toBeGreaterThanOrEqual(h!.y+h!.height)
        await expect(page.locator('.score')).toHaveText('0:2')
      }
      if(route==='runtime') {
        await expect(page.getByLabel('Authoritative match clock')).toHaveText('00:20')
        for(const name of ['Step engine','Save exact checkpoint','Disconnect operator']) {
          const control=page.getByRole('button',{name,exact:true})
          await control.scrollIntoViewIfNeeded(); await expect(control).toBeVisible()
          expect((await control.boundingBox())!.height).toBeGreaterThanOrEqual(width<700?40:32)
        }
        await expect(page.getByLabel('Saved checkpoint').locator('option')).toHaveCount(2)
      }
      await page.evaluate(()=>window.scrollTo(0,0))
      await page.screenshot({path:join(artifactRoot,`${route}-${width}-after.png`),animations:'disabled'})
      if(width===1440) for(const part of route==='runtime'?['.runtime-checkpoints','.runtime-forkcast']:route==='replay'?['.pass-inspection','.analysis-tools']:[]) {
        const region=page.locator(part).first(); if(await region.isVisible()) await region.screenshot({path:join(artifactRoot,`${route}-${part.slice(1)}-after.png`),animations:'disabled'})
      }
      report[route]=layout
    }
    await writeFile(join(artifactRoot,`responsive-${width}.json`),JSON.stringify(report,null,2))
    await info.attach('responsive-layout',{body:JSON.stringify(report),contentType:'application/json'})
  })
}
