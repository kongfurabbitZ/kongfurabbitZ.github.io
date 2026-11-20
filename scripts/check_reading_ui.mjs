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
const visit = path => post('/url', {url: origin + path});
const shown = "[data-item]:not([hidden])";
const capture = async (name, dir) => {
  const image = await call('GET', '/session/' + session + '/screenshot');
  await writeFile(join(dir, name + '.png'), Buffer.from(image, 'base64'));
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
    await visit('/insights/timeline/?month=all');
    assert.equal(await js('return document.querySelectorAll(arguments[0]).length', shown), papers.length);
    const fits = await js("return document.documentElement.scrollWidth<=innerWidth+1 && [...document.querySelectorAll('.gantt-row:not([hidden]) .gantt-dot')].every(dot=>{const r=dot.getBoundingClientRect();return r.width>=32 && r.left>=-1 && r.right<=innerWidth+1;})");
    assert.ok(fits, 'Timeline overflow at '+width);
    const month = papers.map(a=>a.reading.day.slice(0,7)).sort().at(-1);
    await js("const el=document.querySelector('[name=month]'); el.value=arguments[0]; el.dispatchEvent(new Event('change',{bubbles:true}))", month);
    assert.equal(await js('return document.querySelectorAll(arguments[0]).length', shown), papers.filter(a=>a.reading.day.startsWith(month)).length);
    await capture('timeline-'+width, dir);
    const href = await js("return document.querySelector('.gantt-row:not([hidden]) .gantt-dot').getAttribute('href')");
    await js("document.querySelector('.gantt-row:not([hidden]) .gantt-dot').click()");
    assert.equal(await js("return document.querySelector('#content h1').textContent"), papers.find(a=>new URL(a.url).pathname===href).title);
  }
  console.log('READING_UI_OK '+JSON.stringify({widths:[1280,390],articles:index.articles.length,papers:papers.length,screenshots:dir}));
} finally {
  try { if (session) await call('DELETE','/session/'+session); } finally { driver.kill(); }
}
