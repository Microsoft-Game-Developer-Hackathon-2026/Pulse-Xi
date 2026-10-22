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

test('reduced motion keeps real proof accessible without decorative animation',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'})
  await page.goto('/')
  await page.getByRole('slider',{name:'Seek match time'}).fill('5400')
  await page.locator('.insight-card').first().getByRole('button').click()
  const proof=page.getByRole('dialog',{name:'Insight evidence'})
  await expect(proof).toBeVisible()
  expect(await proof.evaluate(e=>getComputedStyle(e).animationName)).toBe('none')
  expect(await proof.evaluate(e=>getComputedStyle(e).transitionDuration)).toBe('0s')
  await page.keyboard.press('Escape');await expect(proof).toHaveCount(0)
})

test('high contrast uses opaque materials with readable semantic tokens',async({page})=>{
  await page.emulateMedia({contrast:'more'})
  await page.goto('/')
  await expect(page.getByRole('slider',{name:'Seek match time'})).toBeVisible()
  expect(await page.locator('.header').evaluate(e=>getComputedStyle(e).backdropFilter)).toBe('none')
  expect(await page.locator('.header').evaluate(e=>getComputedStyle(e).backgroundColor)).toMatch(/^rgb\(/)
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
  expect(await page.locator('.header').evaluate(e=>getComputedStyle(e).backdropFilter)).toBe('none')
})


test('selected controls retain readable ink on hover',async({page})=>{
  await page.goto('/')
  await expect(page.getByRole('slider',{name:'Seek match time'})).toBeVisible()
  const selected=page.locator('.speed button.selected')
  await selected.hover()
  await expect(selected).toHaveCSS('background-color','rgb(187, 239, 234)')
  const ratio=await selected.evaluate(e=>{
    const s=getComputedStyle(e)
    const lum=(color:string)=>{const c=color.match(/[\d.]+/g)!.slice(0,3).map(Number).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return .2126*c[0]+.7152*c[1]+.0722*c[2]}
    const a=lum(s.color),b=lum(s.backgroundColor);return(Math.max(a,b)+.05)/(Math.min(a,b)+.05)
  })
  expect(ratio).toBeGreaterThanOrEqual(4.5)
})
