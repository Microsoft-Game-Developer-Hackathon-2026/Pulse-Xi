// Local-only, public fixture measurement. No authentication or provider calls.
import { chromium } from '@playwright/test'
import { writeFile } from 'node:fs/promises'
import { cpus, platform, release } from 'node:os'
import { performance } from 'node:perf_hooks'

const [baseline='http://127.0.0.1:8011',candidate='http://127.0.0.1:8000',output='ui-measurements.json',count='5']=process.argv.slice(2)
const samples=Number(count)
if(!Number.isInteger(samples)||samples<1||samples>20) throw new Error('Use 1?20 samples')
for(const input of [baseline,candidate]) if(!['localhost','127.0.0.1'].includes(new URL(input).hostname)) throw new Error('Only local preview URLs are supported')
const browser=await chromium.launch({args:['--enable-unsafe-swiftshader']})
const rows=[]
try {
  for(let sample=0;sample<samples;sample++) for(const [name,url] of [['baseline',baseline],['candidate',candidate]]) {
    const context=await browser.newContext({viewport:{width:1440,height:900},colorScheme:'dark'})
    try {
      const page=await context.newPage()
      const start=performance.now()
      await page.goto(url,{waitUntil:'domcontentloaded'})
      const slider=page.getByRole('slider',{name:'Seek match time'})
      await slider.waitFor()
      await page.waitForFunction(()=>{const e=document.querySelector('.scoreboard');return e&&getComputedStyle(e).opacity==='1'})
      const firstUsefulMs=performance.now()-start
      const metrics=page.waitForResponse(r=>r.url().includes('/metrics?at_second=3500')&&r.ok())
      const recap=page.waitForResponse(r=>r.url().includes('/recap?')&&r.url().includes('at_second=3500')&&r.ok())
      const seekStart=performance.now()
      await slider.fill('3500')
      const [response]=await Promise.all([metrics,recap])
      const source=await response.json()
      await page.waitForFunction(count=>document.querySelector('.metrics small')?.textContent?.includes(String(count)),source.computed_from_event_count)
      if((await page.locator('.score').textContent()).replace(/\s/g,'')!=='0:2') throw new Error('Unexpected fixture result')
      const seekToInsightMs=performance.now()-seekStart
      const frames=await page.evaluate(()=>new Promise(resolve=>{
        const deltas=[];let previous;let steps=0
        const tick=time=>{if(previous!==undefined)deltas.push(time-previous);previous=time;scrollBy(0,12);if(++steps<60)requestAnimationFrame(tick);else resolve(deltas)}
        requestAnimationFrame(tick)
      }))
      const preferences=await page.evaluate(()=>({reducedMotion:matchMedia('(prefers-reduced-motion:reduce)').matches,reducedTransparency:matchMedia('(prefers-reduced-transparency:reduce)').matches}))
      rows.push({name,sample,preferences,firstUsefulMs,seekToInsightMs,frameCallbackIntervalsMs:frames,sourceEventCount:source.computed_from_event_count})
    } finally { await context.close() }
  }
  const percentile=(values,p)=>{const ordered=[...values].sort((a,b)=>a-b);return ordered[Math.ceil(ordered.length*p)-1]}
  const summary=Object.fromEntries(['baseline','candidate'].map(name=>{const r=rows.filter(row=>row.name===name);return [name,{samples:r.length,firstUsefulP50:percentile(r.map(x=>x.firstUsefulMs),.5),firstUsefulP95:percentile(r.map(x=>x.firstUsefulMs),.95),seekToInsightP50:percentile(r.map(x=>x.seekToInsightMs),.5),seekToInsightP95:percentile(r.map(x=>x.seekToInsightMs),.95),scrollFrameCallbackP95:percentile(r.flatMap(x=>x.frameCallbackIntervalsMs),.95)}]}))
  await writeFile(output,JSON.stringify({environment:{os:platform(),release:release(),cpu:cpus()[0]?.model,browser:browser.version(),viewport:[1440,900]},limitations:'Local cold browser contexts with warm local services; five samples are descriptive, not a production latency or GPU/FPS guarantee. Scroll numbers are RAF callback intervals, not rendered-frame counts.',summary,rows},null,2))
  console.log(JSON.stringify(summary,null,2))
} finally { await browser.close() }
