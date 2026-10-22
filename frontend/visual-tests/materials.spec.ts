import { expect,test } from '@playwright/test'

for(const width of [1440,390]) test(`materials and real routes work at ${width}px`,async({page},info)=>{
  await page.setViewportSize({width,height:900})
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
  for(const route of ['replay','sandbox','data','runtime']) {
    await page.goto(route==='replay'?'/':`/#/${route}`)
    if(route==='runtime') {
      await page.getByLabel('Operator access token').fill('test-runtime-token-at-least-32-characters')
      await page.getByRole('button',{name:'Connect operator',exact:true}).click()
      await expect(page.getByRole('button',{name:'Disconnect operator'})).toBeVisible()
    } else if(route==='data') await expect(page.getByRole('button',{name:'Open for analysis',exact:true})).toHaveCount(3)
    else {
      await page.getByRole('slider',{name:'Seek match time'}).fill('3500')
      await expect(page.locator('.score')).toContainText('0:2')
    }
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true)
    expect(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--px-bg-base').trim())).toBe('#101012')
    await page.screenshot({path:info.outputPath(`${route}.png`),animations:'disabled'})
  }
  await page.emulateMedia({reducedMotion:'reduce'})
  await page.goto('/')
  await expect(page.getByRole('slider',{name:'Seek match time'})).toBeVisible()
  expect(await page.locator('.workspace-nav a').first().evaluate(e=>getComputedStyle(e).transitionDuration)).toBe('0s')
  expect(errors).toEqual([])
})
