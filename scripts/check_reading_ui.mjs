/** Browser regression check for the deployed catalog. Uses Chrome + ChromeDriver on the runner. */
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {setTimeout as pause} from 'node:timers/promises';

const origin = (process.env.READING_SITE || 'https://kongfurabbitz.github.io').replace(/\/$/, '');
const index = await (await fetch(origin + '/insights/index.json')).json();
const papers = index.articles.filter(a => a.reading);
const tagLabel = t => t.replace(/^(主题|方法)·/, '');
const tag = papers[0]?.tags.find(t => t.startsWith('主题·')) ?? papers[0]?.tags[0];
assert.ok(tag, 'Expected a paper tag');
const driver = spawn('chromedriver', ['--port=19515'], {stdio: 'ignore'});
const endpoint = 'http://127.0.0.1:19515';
let session;
async function call(method, path, data) {
  const res = await fetch(endpoint + path, {method, ...(data ? {headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)} : {})});
  const {value} = await res.json();
  if (!res.ok || value?.error) throw Error(value?.message || String(res.status));
  return value;
}
const post = (path, data) => call('POST', '/session/' + session + path, data);
const js = (script, ...args) => post('/execute/sync', {script, args});
const cdp = (cmd, params) => post('/goog/cdp/execute', {cmd, params});
const visit = path => post('/url', {url: origin + path});
const day = 86400000;
async function click(selector) {
  const element = await post('/element', {using: 'css selector', value: selector});
  await post('/element/' + element['element-6066-11e4-a52e-4f735466cecf'] + '/click', {});
}
async function waitFor(script, ...args) {
  for (let n = 0; n < 75; n++) {
    if (await js(script, ...args)) return;
    await pause(80);
  }
  const status = await js("const p=document.querySelector('[data-plot]'),v=p?.querySelector('.vis-timeline'),c=p?.querySelector('.vis-panel.vis-center');return {url:location.href,ready:p?.dataset.ready,scale:p?.dataset.scale,visibility:v && getComputedStyle(v).visibility,loading:!!p?.querySelector('.vis-loading-screen'),width:c?.clientWidth,items:p?.querySelectorAll('.mark').length,span:[p?.dataset.start,p?.dataset.end]};");
  throw Error('Browser assertion timed out: ' + script + ' · ' + JSON.stringify(status));
}
const range = () => js("const p=document.querySelector('[data-plot]');return [+p.dataset.start,+p.dataset.end]");
const span = async () => { const [start,end] = await range(); return end-start; };
const paperRows = () => js("return document.querySelectorAll('.paper-record:not([hidden])').length");
const choose = unit => click('[data-scale="' + unit + '"]');
const ready = () => waitFor("return document.querySelector('[data-plot]')?.dataset.ready==='true'");
async function chartPoint() {
  return js("const p=document.querySelector('.plot .vis-panel.vis-center');p.scrollIntoView({block:'center'});const r=p.getBoundingClientRect();const x=Math.round(r.left+r.width*.51),y=Math.round(Math.min(innerHeight-20,r.top+r.height*.55));const target=document.elementFromPoint(x,y);if(!target?.closest('.vis-timeline'))throw Error('Chart surface obscured by '+target?.className);return {x,y,dx:Math.round(Math.min(90,r.width*.23))}");
}
async function drag(mobile) {
  const {x,y,dx} = await chartPoint();
  if (mobile) {
    const touch = (type, offset) => cdp('Input.dispatchTouchEvent', {type, touchPoints: type === 'touchEnd' ? [] : [{x:x+offset,y,id:0}]});
    await touch('touchStart', 0);
    for (let i=1; i<=5; i++) { await touch('touchMove', dx*i/5); await pause(25); }
    await touch('touchEnd', dx);
  } else {
    await cdp('Input.dispatchMouseEvent', {type:'mousePressed',x,y,button:'left',buttons:1,clickCount:1});
    for (let i=1; i<=5; i++) await cdp('Input.dispatchMouseEvent', {type:'mouseMoved',x:x+dx*i/5,y,buttons:1});
    await cdp('Input.dispatchMouseEvent', {type:'mouseReleased',x:x+dx,y,button:'left',clickCount:1});
  }
}
async function gestureZoom(mobile) {
  const {x,y,dx} = await chartPoint();
  if (mobile) {
    const pinch = (type, gap) => cdp('Input.dispatchTouchEvent', {type, touchPoints: type === 'touchEnd' ? [] :
      [{x:x-gap,y,id:0}, {x:x+gap,y,id:1}]});
    await pinch('touchStart', dx/3);
    for (let i=1; i<=6; i++) { await pinch('touchMove', dx*(1/3+i/10)); await pause(28); }
    await pinch('touchEnd', 0);
  } else {
    await cdp('Input.dispatchMouseEvent', {type:'mouseWheel',x,y,deltaX:0,deltaY:-145,modifiers:2});
  }
}
const shown = "[data-item]:not([hidden])";
const capture = async (name, dir) => {
  const image = await call('GET', '/session/' + session + '/screenshot');
  await writeFile(join(dir, name + '.png'), Buffer.from(image, 'base64'));
  if (process.argv.includes('--preview-images')) {
    const jpeg = await cdp('Page.captureScreenshot', {format:'jpeg',quality:65,fromSurface:true});
    console.log('TIMELINE_IMAGE_' + name + '=' + jpeg.data);
  }
};
try {
  for (let n = 0; n < 50; n++) {
    try { if ((await call('GET', '/status')).ready) break; } catch {}
    await pause(150);
  }
  session = (await call('POST', '/session', {capabilities: {alwaysMatch: {browserName: 'chrome',
    'goog:chromeOptions': {args: ['--headless=new','--no-sandbox','--disable-dev-shm-usage']}}}})).sessionId;
  const dir = await mkdtemp(join(tmpdir(), 'reading-ui-'));
  for (const width of [1280, 390]) {
    await post('/window/rect', {width, height: 900});
    // CDP device metrics ensure true portrait width, even when desktop Chrome clamps the window.
    await post('/goog/cdp/execute', {cmd:'Emulation.setDeviceMetricsOverride', params:{width, height:900, deviceScaleFactor:1, mobile:width < 500}});
    await cdp('Emulation.setTouchEmulationEnabled', {enabled:width < 500,maxTouchPoints:5});
    await cdp('Emulation.setTimezoneOverride', {timezoneId: width < 500 ? 'America/Los_Angeles' : 'Asia/Shanghai'});
    await visit('/');
    for (let attempt = 0; attempt < 60; attempt++) {
      if (await js("return Boolean(document.querySelector('.home-filter'))")) break;
      await pause(200);
    }
    await js("document.querySelector('.home-filter select').value=arguments[0]; document.querySelector('.home-filter').requestSubmit()", tag);
    await js("return document.readyState");
    assert.ok((await call('GET', '/session/'+session+'/url')).includes('/insights/?tag='));
    assert.equal(await js('return document.querySelectorAll(arguments[0]).length', shown), index.articles.filter(a => a.tags.some(t => tagLabel(t) === tagLabel(tag))).length);
    await js("const el=document.querySelector('[name=q]'); el.value='__no_such_paper_9__'; el.dispatchEvent(new Event('input',{bubbles:true}))");
    assert.equal(await js('return document.querySelectorAll(arguments[0]).length', shown), 0);
    await js("document.querySelector('[data-filters]').reset()");
    assert.equal(await js('return document.querySelectorAll(arguments[0]).length', shown), index.articles.length);
    await visit('/insights/tags/');
    assert.ok(await js("return [...document.querySelectorAll('.tag-group a')].some(a=>new URL(a.href).searchParams.get('tag')===arguments[0])", tag));
    const month = papers.map(a=>a.reading.day.slice(0,7)).sort().at(-1);
    await visit('/insights/timeline/'); await ready();
    assert.equal(await paperRows(), papers.filter(a=>a.reading.day.startsWith(month)).length);
    await waitFor("const m=document.querySelector('.vis-item .mark');return m && m.getBoundingClientRect().width>60 && getComputedStyle(m).visibility==='visible' && !document.querySelector('.plot .vis-loading-screen')");
    await js("return document.fonts.ready.then(()=>true)");
    assert.ok(await js("return document.documentElement.scrollWidth<=innerWidth+1 && document.querySelector('.vis-panel.vis-center').clientWidth>=180"), 'Chart too narrow at '+width);
    if (width < 500) assert.ok(await js("return document.querySelector('.scale-switch').clientWidth >= document.querySelector('.map-head').clientWidth - 32"), 'Phone scale selector must use the full row');
    await capture('timeline-'+width, dir);
    for (const [unit,low,high] of [['day',1,1],['week',7,7],['month',28,31],['quarter',90,92],['year',365,366]]) {
      await choose(unit);
      const [a,b] = await range(); assert.ok((b-a)/day>=low && (b-a)/day<=high, 'Incorrect '+unit+' range');
      if (unit==='week') assert.equal(new Date(a).getUTCDay(),1);
      if (unit==='quarter') assert.equal(new Date(a).getUTCMonth()%3,0);
    }
    await visit('/insights/timeline/?month=all'); await ready(); assert.equal(await paperRows(), papers.length);
    await visit('/insights/timeline/?month='+month); await ready();
    const original=await range();
    await click('[data-step="-1"]'); assert.equal((await range())[1],original[0]);
    await click('[data-step="1"]'); assert.deepEqual(await range(),original);
    await click('[data-zoom="1"]'); assert.ok(await span()<original[1]-original[0]);
    const saved=await range(); await call('POST','/session/'+session+'/refresh',{}); await ready(); assert.deepEqual(await range(),saved);
    await click('[data-latest]'); await drag(width<500);
    await waitFor("return Number(document.querySelector('[data-plot]').dataset.start)!==arguments[0]",original[0]);
    await click('[data-latest]'); await gestureZoom(width<500);
    await waitFor("const p=document.querySelector('[data-plot]');return (+p.dataset.end-p.dataset.start)<arguments[0]",original[1]-original[0]);
    const recent=[...papers].sort((a,b)=>b.reading.day.localeCompare(a.reading.day));
    const topicOf=a=>a.tags.find(t=>t.startsWith('主题·')) || '';
    const sample=recent.find(a=>recent.filter(b=>b.reading.day===a.reading.day && topicOf(b)===topicOf(a)).length>1);
    if (sample) {
      const topic=topicOf(sample), date=sample.reading.day;
      await visit('/insights/timeline/?scale=month&date='+date+'&tag='+encodeURIComponent(topic)); await ready();
      const button='.cluster-mark[data-day="'+date+'"]';
      await waitFor("return !!document.querySelector(arguments[0])",button);
      await click(button); await waitFor("return !!document.querySelector('dialog[open] .dialog-entry')");
      const group=recent.filter(a=>a.reading.day===date && topicOf(a)===topic);
      const links=await js("return [...document.querySelectorAll('.dialog-entry')].map(a=>a.getAttribute('href'))");
      assert.deepEqual(links.sort(),group.map(a=>new URL(a.url).pathname).sort());
      await click('[data-focus-period]'); assert.equal(await span(),day);
      await waitFor("return !!document.querySelector('.vis-item a.mark')");
      const href=await js("return document.querySelector('.vis-item a.mark').getAttribute('href')");
      await click('.vis-item a.mark');
      await waitFor("return document.querySelector('#content h1')?.textContent===arguments[0]",papers.find(a=>new URL(a.url).pathname===href).title);
      await post('/back',{}); await ready(); assert.equal(await span(),day); assert.equal(await paperRows(),group.length);
    }
    await js("let e=document.querySelector('[name=q]');e.value='__absent_713__';e.dispatchEvent(new Event('input',{bubbles:true}))");
    assert.equal(await paperRows(),0); assert.equal(await js("return document.querySelector('[data-empty]').hidden"),false);
  }
  console.log('READING_UI_OK '+JSON.stringify({widths:[1280,390],articles:index.articles.length,papers:papers.length,screenshots:dir}));
} finally {
  try { if (session) await call('DELETE','/session/'+session); } finally { driver.kill(); }
}
