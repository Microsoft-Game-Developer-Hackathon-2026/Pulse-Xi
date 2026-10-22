import {expect,test} from '@playwright/test'

test('glass preserves keyboard navigation and visible focus',async({page})=>{
  await page.goto('/')
  await expect(page.getByRole('slider',{name:'Seek match time'})).toBeVisible()
  const links=page.locator('.workspace-nav a')
  await links.first().focus();await page.keyboard.press('Tab')
  await expect(links.nth(1)).toBeFocused()
  expect(await links.nth(1).evaluate(e=>getComputedStyle(e).outlineStyle)).toBe('solid')
  expect(await links.nth(1).evaluate(e=>getComputedStyle(e).outlineWidth)).toBe('2px')
})

test('reduced motion keeps real proof accessible without decorative animation',async({page},info)=>{
  await page.emulateMedia({reducedMotion:'reduce'})
  await page.goto('/')
  await page.getByRole('slider',{name:'Seek match time'}).fill('5400')
  await page.locator('.insight-card').first().getByRole('button').click()
  const proof=page.getByRole('dialog',{name:'Insight evidence'})
  await expect(proof).toBeVisible()
  expect(await proof.evaluate(e=>getComputedStyle(e).animationName)).toBe('none')
  expect(await proof.evaluate(e=>getComputedStyle(e).transitionDuration)).toBe('0s')
  await proof.screenshot({path:info.outputPath('atelier-proof.png')})
  await page.keyboard.press('Escape');await expect(proof).toHaveCount(0)
})

test('high contrast uses opaque materials with readable semantic tokens',async({page})=>{
  await page.emulateMedia({contrast:'more'})
  await page.goto('/')
  await expect(page.getByRole('slider',{name:'Seek match time'})).toBeVisible()
  expect(await page.locator('.workspace-nav').evaluate(e=>getComputedStyle(e).backdropFilter)).toBe('none')
  expect(await page.locator('.workspace-nav').evaluate(e=>getComputedStyle(e).backgroundColor)).toMatch(/^rgb\(/)
  const ratio=await page.evaluate(()=>{
    const vars=getComputedStyle(document.documentElement)
    const luminance=(hex:string)=>{const c=hex.trim().slice(1).match(/../g)!.map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return .2126*c[0]+.7152*c[1]+.0722*c[2]}
    return (luminance(vars.getPropertyValue('--px-text-secondary'))+.05)/(luminance(vars.getPropertyValue('--px-surface'))+.05)
  })
  expect(ratio).toBeGreaterThanOrEqual(4.5)
  const cdp=await page.context().newCDPSession(page)
  await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-contrast',value:'no-preference'},{name:'prefers-reduced-transparency',value:'no-preference'}]})
  const normalBorder = await page.locator('.panel').first().evaluate(e=>getComputedStyle(e).borderTopColor)
  await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-contrast',value:'no-preference'},{name:'prefers-reduced-transparency',value:'reduce'}]})
  // Reduced transparency must not accidentally activate high-contrast outlines.
  expect(await page.locator('.panel').first().evaluate(e=>getComputedStyle(e).borderTopColor)).toBe(normalBorder)
  expect(await page.evaluate(()=>matchMedia('(prefers-reduced-transparency:reduce)').matches)).toBe(true)
  expect(await page.locator('.workspace-nav').evaluate(e=>getComputedStyle(e).backdropFilter)).toBe('none')
})


test('selected controls retain readable ink on hover',async({page})=>{
  await page.goto('/')
  await expect(page.getByRole('slider',{name:'Seek match time'})).toBeVisible()
  const selected=page.locator('.speed button.selected')
  await expect(selected).toHaveCSS('background-color','rgb(182, 228, 213)')
  await selected.hover()
  await expect(selected).toHaveCSS('background-color','rgb(211, 239, 226)')
  const ratio=await selected.evaluate(e=>{
    const s=getComputedStyle(e)
    const lum=(color:string)=>{const c=color.match(/[\d.]+/g)!.slice(0,3).map(Number).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return .2126*c[0]+.7152*c[1]+.0722*c[2]}
    const a=lum(s.color),b=lum(s.backgroundColor);return(Math.max(a,b)+.05)/(Math.min(a,b)+.05)
  })
  expect(ratio).toBeGreaterThanOrEqual(4.5)
})


test('route reveals settle and replay updates do not restart the presentation', async ({page}) => {
  await page.emulateMedia({reducedMotion:'no-preference'})
  await page.addInitScript(()=>{
    (window as unknown as {heroTransitions:number}).heroTransitions=0
    document.addEventListener('transitionrun',event=>{
      if((event.target as Element).matches('.scoreboard') && event.propertyName==='opacity')
        (window as unknown as {heroTransitions:number}).heroTransitions++
    })
  })
  await page.goto('/')
  const hero=page.getByRole('region',{name:'Match score'})
  await expect(hero).toHaveCSS('opacity','1')
  const transitions=await page.evaluate(()=>(window as unknown as {heroTransitions:number}).heroTransitions)
  expect(transitions).toBeGreaterThan(0)
  await page.getByRole('slider',{name:'Seek match time'}).fill('3500')
  await expect(page.locator('.score')).toHaveText('0:2')
  await expect(hero).toHaveCSS('opacity','1')
  await expect(hero).toHaveCSS('transform','none')
  expect(await page.evaluate(()=>(window as unknown as {heroTransitions:number}).heroTransitions)).toBe(transitions)
  await page.locator('.workspace-nav a[href="#/runtime"]').click()
  await expect(page.getByRole('button',{name:'Connect operator',exact:true})).toBeVisible()
  await expect(page.locator('.runtime-heading')).toHaveCSS('opacity','1')
  await page.emulateMedia({reducedMotion:'reduce'})
  await page.locator('.workspace-nav a[href="#/"]').click()
  await expect(hero).toHaveCSS('opacity','1')
  await expect(hero).toHaveCSS('transition-duration','0s')
  await expect(page.locator('.score')).toHaveText('0:2')
})


test('selected source-event text retains readable ink without changing the team marker', async ({page}) => {
  await page.goto('/#/sandbox')
  const source=page.locator('.sandbox-event-list button').first()
  const marker=await source.locator('i').evaluate(element=>getComputedStyle(element).backgroundColor)
  await source.click()
  await expect(source).toHaveAttribute('aria-pressed','true')
  const ink=await source.evaluate(element=>getComputedStyle(element).color)
  expect(await source.locator('strong').evaluate(element=>getComputedStyle(element).color)).toBe(ink)
  expect(await source.locator('time').evaluate(element=>getComputedStyle(element).color)).toBe(ink)
  expect(await source.locator('i').evaluate(element=>getComputedStyle(element).backgroundColor)).toBe(marker)
})
