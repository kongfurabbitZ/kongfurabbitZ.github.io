(() => {
  'use strict';
  const plot = document.querySelector('[data-plot]');
  if (!plot) return;
  const one = selector => document.querySelector(selector);
  const all = selector => Array.from(document.querySelectorAll(selector));
  const DAY = 86400000;
  const iso = time => new Date(time).toISOString().slice(0, 10);
  const midnight = time => Math.floor(time / DAY) * DAY;
  const atNoon = day => Date.parse(day + 'T12:00:00Z');
  const pretty = time => iso(time).replaceAll('-', '.');
  const tagName = tag => tag.replace(/^(主题|方法)·/, '');
  const records = all('.paper-record').map(node => {
    const link = node.querySelector('a');
    return {node, url: link.getAttribute('href'), title: link.textContent, topic: node.dataset.topic,
      day: node.dataset.day, time: atNoon(node.dataset.day), tags: JSON.parse(node.dataset.tags).map(tagName),
      search: node.dataset.search.toLocaleLowerCase()};
  });
  const empty = one('[data-empty]');
  if (!records.length) { empty.textContent = '还没有公开的论文研读。'; empty.hidden = false; return; }
  if (!window.vis?.Timeline) return; // The complete, linked paper list is available without the chart.

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const asc = (a, b) => a.time - b.time || a.title.localeCompare(b.title, 'zh-CN');
  const sorted = [...records].sort(asc);
  const first = sorted[0].time, last = sorted.at(-1).time;
  const form = one('[data-map-filters]');
  const dialog = one('.paper-dialog');
  const scales = ['day', 'week', 'month', 'quarter', 'year', 'all'];
  let filtered = records, scale = 'month', focus = last, drawing = '', tickKey = '', lastDialog = null;
  const tint = topic => [...topic].reduce((value, ch) => (value * 31 + ch.codePointAt(0)) >>> 0, 0) % 6;

  function floorPeriod(time, unit) {
    const d = new Date(time), y = d.getUTCFullYear(), m = d.getUTCMonth();
    if (unit === 'year') return Date.UTC(y, 0, 1);
    if (unit === 'quarter') return Date.UTC(y, m - m % 3, 1);
    if (unit === 'month') return Date.UTC(y, m, 1);
    if (unit === 'week') return midnight(time) - (d.getUTCDay() + 6) % 7 * DAY;
    return midnight(time);
  }
  function advance(time, unit, steps) {
    if (unit === 'day' || unit === 'week') return time + steps * (unit === 'day' ? 1 : 7) * DAY;
    const months = {month: 1, quarter: 3, year: 12}[unit];
    const d = new Date(time);
    return Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + steps * months, 1);
  }
  const min = floorPeriod(first, 'year') - 7 * DAY;
  const max = advance(floorPeriod(last, 'year'), 'year', 1) + 7 * DAY;
  function extent(list) {
    const entries = list.length ? list : records;
    const start = Math.min(...entries.map(r => r.time)), end = Math.max(...entries.map(r => r.time));
    const pad = Math.min(21, Math.max(1, Math.ceil((end - start) / DAY * .035))) * DAY;
    return [Math.max(min, midnight(start) - pad), Math.min(max, midnight(end) + DAY + pad)];
  }
  function period(unit, at) {
    if (unit === 'all') return extent(filtered);
    const start = floorPeriod(at, unit);
    return [start, advance(start, unit, 1)];
  }
  function periodTitle(unit, start, end) {
    const d = new Date(start), y = d.getUTCFullYear(), m = d.getUTCMonth() + 1;
    switch (unit) {
      case 'year': return y + ' 年';
      case 'quarter': return y + ' 年 · 第' + (Math.floor((m - 1) / 3) + 1) + '季度';
      case 'month': return y + ' 年 ' + m + ' 月';
      case 'day': return y + ' 年 ' + m + ' 月 ' + d.getUTCDate() + ' 日';
      case 'all': return '全部研读';
      default: return pretty(start) + ' – ' + (iso(start).slice(0, 4) === iso(end - 1).slice(0, 4) ? pretty(end - 1).slice(5) : pretty(end - 1));
    }
  }
  function applyFilters() {
    const term = form.elements.q.value.trim().toLocaleLowerCase();
    const words = term.split(/\s+/).filter(Boolean), tag = tagName(form.elements.tag.value);
    filtered = records.filter(r => (!tag || r.tags.includes(tag)) && words.every(w => r.search.includes(w)));
  }
  function stateFromUrl() {
    const p = new URL(location.href).searchParams, oldMonth = p.get('month');
    const opt = Array.from(form.elements.tag.options).find(o => tagName(o.value) === tagName(p.get('tag') || ''));
    form.elements.tag.value = opt?.value || '';
    form.elements.q.value = p.get('q') || '';
    applyFilters();
    const legacy = /^\d{4}-(0[1-9]|1[0-2])$/.test(oldMonth || '') ? atNoon(oldMonth + '-15') : NaN;
    const wanted = atNoon(p.get('date') || '');
    focus = [wanted, legacy, filtered[0]?.time, last].find(t => Number.isFinite(t) && t >= min && t < max);
    const from = Date.parse(p.get('from') || ''), to = Date.parse(p.get('to') || '');
    if (from >= min && to <= max && to - from >= DAY) { scale = 'custom'; return [from, to]; }
    scale = scales.includes(p.get('scale')) ? p.get('scale') : oldMonth === 'all' ? 'all' : 'month';
    return period(scale, focus);
  }
  const initial = stateFromUrl();
  document.documentElement.classList.add('enhanced');
  const timeline = new vis.Timeline(plot, [], [], {
    min, max, zoomMin: DAY, zoomMax: max - min, rtl: false,
    onInitialDrawComplete: () => {
      timeline.setWindow(initial[0], initial[1], {animation: false});
      render();
      requestAnimationFrame(() => { timeline.redraw(); plot.dataset.ready = 'true'; });
    },
    moment: value => vis.moment.utc(value), locale: 'en',
    format: {minorLabels: {weekday: 'D日', day: 'D日', week: 'M/D', month: 'M月', year: 'YYYY'},
      majorLabels: {weekday: 'YYYY年 M月', day: 'YYYY年 M月', week: 'YYYY年 M月', month: 'YYYY年', year: ''}},
    orientation: {axis: 'top', item: 'top'}, showCurrentTime: false, showTooltips: false,
    minHeight: 120, margin: {axis: 9, item: {horizontal: 7, vertical: 7}},
    selectable: false, editable: false, moveable: true, zoomable: true, zoomKey: 'ctrlKey',
    stack: true, groupOrder: 'order', groupHeightMode: 'auto', zoomFriction: 7
  });
  const windowRange = () => { const w = timeline.getWindow(); return [+w.start, +w.end]; };
  const inWindow = (r, start, end) => r.time >= start && r.time < end;
  one('#list-heading').textContent = '当前时段的论文';
  const overview = one('[data-overview]');
  const counts = new Map();
  for (const r of records) counts.set(r.day.slice(0, 7), (counts.get(r.day.slice(0, 7)) || 0) + 1);
  const maxCount = Math.max(...counts.values());
  for (let t = floorPeriod(first, 'month'); t <= last; t = advance(t, 'month', 1)) {
    const month = iso(t).slice(0, 7), n = counts.get(month), bar = el(n ? 'button' : 'span');
    if (n) {
      bar.type = 'button'; bar.dataset.month = month;
      bar.title = month + ' · ' + n + ' 篇'; bar.setAttribute('aria-label', bar.title + '，查看这个月');
      bar.style.setProperty('--height', Math.max(8, n / maxCount * 96) + '%');
      bar.addEventListener('click', () => jumpMonth(month));
    } else { bar.setAttribute('aria-hidden', 'true'); }
    overview.append(bar);
  }
  one('[data-overview-dates]').textContent = pretty(first).slice(0, 7) + ' — ' + pretty(last).slice(0, 7);

  function openCluster(entries, unit, trigger) {
    lastDialog = {entries, unit, trigger};
    one('[data-cluster-topic]').textContent = entries[0].topic + ' · ' + entries.length + ' 篇';
    const start = floorPeriod(entries[0].time, unit);
    one('#cluster-title').textContent = periodTitle(unit, start, advance(start, unit, 1));
    const list = one('[data-cluster-papers]');
    list.replaceChildren(...entries.map(r => {
      const a = el('a', 'dialog-entry');
      a.href = r.url;
      a.append(el('time', '', r.day), el('strong', '', r.title));
      return a;
    }));
    one('[data-focus-period]').hidden = scale === 'day';
    dialog.showModal(); dialog.querySelector('[data-close]').focus();
  }
  one('[data-close]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) {
    const r = dialog.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
  }});
  dialog.addEventListener('close', () => { if (lastDialog?.trigger.isConnected) lastDialog.trigger.focus({preventScroll: true}); });
  one('[data-focus-period]').addEventListener('click', () => {
    const {entries, unit} = lastDialog;
    dialog.close(); selectPeriod(unit, entries[0].time); plot.focus({preventScroll: true});
  });
  function makeMark(entries, unit, topic, time, align) {
    const first = entries[0], single = entries.length === 1;
    const node = el(single ? 'a' : 'button', 'mark');
    node.dataset.day = first.day;
    const date = single || unit === 'day' ? pretty(first.time).slice(5) : unit === 'month' ? Number(first.day.slice(5, 7)) + ' 月' : pretty(floorPeriod(time, 'week')).slice(5) + ' 周';
    const meta = el('span', 'mark-meta', date);
    meta.append(el('span', 'mark-count', single ? '↗' : entries.length + ' 篇 ›'));
    node.append(meta, el('span', 'mark-title', first.title));
    if (single) {
      node.href = first.url; node.title = first.day + ' · ' + first.title;
      node.setAttribute('aria-label', '阅读《' + first.title + '》，' + first.day);
    } else {
      node.type = 'button'; node.classList.add('cluster-mark');
      node.setAttribute('aria-haspopup', 'dialog');
      node.title = topic + ' · ' + entries.length + ' 篇';
      node.setAttribute('aria-label', date + '，' + topic + '，展开 ' + entries.length + ' 篇研读');
      node.addEventListener('click', () => openCluster(entries, unit, node));
    }
    return {id: first.url, start: new Date(time), group: topic, type: 'box', align,
      className: 'tone-' + tint(topic), content: node};
  }
  function drawItems(visible, start, end) {
    const span = (end - start) / DAY;
    const unit = span < 2 ? 'individual' : span <= 42 ? 'day' : span <= 150 ? 'week' : 'month';
    const bins = new Map(), topics = new Map();
    for (const r of visible) {
      const key = unit === 'individual' ? r.url : r.topic + '/' + floorPeriod(r.time, unit);
      if (!bins.has(key)) bins.set(key, []);
      bins.get(key).push(r);
      topics.set(r.topic, (topics.get(r.topic) || 0) + 1);
    }
    const shapes = Array.from(bins.values(), entries => {
      const time = (Math.min(...entries.map(r => r.time)) + Math.max(...entries.map(r => r.time))) / 2;
      const fraction = (time - start) / (end - start);
      return {entries, time, align: fraction < .3 ? 'left' : fraction > .7 ? 'right' : 'center'};
    });
    const signature = unit + '|' + shapes.map(s => s.align + s.entries.map(r => r.url).join(',')).join('|');
    if (signature === drawing) return;
    drawing = signature;
    const ordered = [...topics.keys()].sort((a, b) => topics.get(b) - topics.get(a) || a.localeCompare(b, 'zh-CN'));
    const groups = ordered.map((topic, order) => ({id: topic, order, content: el('span', 'lane-label tone-' + tint(topic), topic)}));
    const items = shapes.map(s => makeMark(s.entries, unit, s.entries[0].topic, s.time, s.align));
    timeline.setData({groups, items});
  }
  function updateAxis(start, end) {
    const width = Math.max(120, plot.clientWidth - (plot.clientWidth < 700 ? 85 : 146));
    const days = (end - start) / DAY * 52 / width;
    const ticks = [['day',1,1],['day',2,2],['day',5,5],['week',1,7],['week',2,14],['month',1,30],['month',2,61],['month',3,92],['month',6,183],['year',1,366],['year',5,1830]];
    const [unit, step] = (ticks.find(t => t[2] >= days) || ticks.at(-1));
    const key = unit + step;
    if (key !== tickKey) { tickKey = key; timeline.setOptions({timeAxis: {scale: unit, step}}); }
  }
  function render() {
    const [start, end] = windowRange();
    const visible = filtered.filter(r => inWindow(r, start, end));
    updateAxis(start, end);
    drawItems(visible, start, end);
    const show = new Set(visible);
    records.forEach(r => { r.node.hidden = !show.has(r); });
    one('[data-period]').textContent = periodTitle(scale, start, end);
    plot.dataset.start = String(start); plot.dataset.end = String(end);
    plot.dataset.scale = scale;
    one('[data-count]').textContent = visible.length + ' 篇';
    empty.hidden = visible.length !== 0;
    empty.textContent = filtered.length ? '这个时段没有研读。可切换周期或跳到有研读的月份。' : '没有匹配的论文，请调整关键词或标签。';
    all('[data-scale]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.scale === scale)));
    all('[data-step]').forEach(b => { b.disabled = !canStep(+b.dataset.step, start, end); });
    one('[data-zoom="1"]').disabled = end - start <= DAY + 1;
    one('[data-zoom="-1"]').disabled = end - start >= max - min - 1;
    const shownMonth = scale === 'month' ? iso(start).slice(0, 7) : '';
    form.elements.jump.value = counts.has(shownMonth) ? shownMonth : '';
    for (const b of overview.querySelectorAll('button')) {
      const t = floorPeriod(atNoon(b.dataset.month + '-01'), 'month');
      b.classList.toggle('in-window', start < advance(t, 'month', 1) && end > t);
    }
  }
  function saveView() {
    const u = new URL(location.href), p = u.searchParams;
    for (const key of ['q','tag','month','scale','date','from','to']) p.delete(key);
    if (form.elements.q.value.trim()) p.set('q', form.elements.q.value.trim());
    if (form.elements.tag.value) p.set('tag', form.elements.tag.value);
    if (scale === 'custom') {
      const [a,b] = windowRange(); p.set('from', new Date(a).toISOString()); p.set('to', new Date(b).toISOString());
    } else {
      p.set('scale', scale); if (scale !== 'all') p.set('date', iso(focus));
    }
    if (location.href !== u.href) history.replaceState(null, '', u);
  }
  function selectPeriod(unit, at) {
    scale = unit; focus = Math.max(min, Math.min(max - 1, at));
    const [a,b] = period(unit, focus);
    timeline.setWindow(a, b, {animation: false}); render(); saveView();
  }
  function jumpMonth(month) {
    const hit = filtered.find(r => r.day.startsWith(month));
    selectPeriod('month', hit?.time ?? atNoon(month + '-15'));
  }
  function canStep(step, a, b) {
    if (scale === 'all') return false;
    if (scale === 'custom') return step < 0 ? a > min + 1 : b < max - 1;
    return step < 0 ? a > floorPeriod(first, scale) : a < floorPeriod(last, scale);
  }
  function move(step) {
    const [a,b] = windowRange();
    if (!canStep(step, a, b)) return;
    if (scale === 'custom') { timeline.setWindow(a + step * (b-a), b + step * (b-a), {animation:false}); render(); saveView(); return; }
    const start = advance(a, scale, step), next = advance(start, scale, 1);
    const candidate = filtered.find(r => inWindow(r, start, next));
    selectPeriod(scale, candidate?.time ?? (start + next) / 2);
  }
  function zoom(direction) {
    const [a,b] = windowRange();
    const anchor = focus >= a && focus < b ? focus : (a+b)/2;
    const span = Math.max(DAY, Math.min(max-min, (b-a) * (direction > 0 ? .5 : 2)));
    const start = anchor - span * (anchor-a) / (b-a);
    scale = 'custom'; timeline.setWindow(start, start+span, {animation:false}); render(); saveView();
  }
  function filterChanged() {
    applyFilters();
    const [a,b] = windowRange();
    if (scale === 'all') selectPeriod('all', focus);
    else if (filtered.length && !filtered.some(r => inWindow(r, a, b))) selectPeriod(scale === 'custom' ? 'month' : scale, filtered[0].time);
    else { render(); saveView(); }
  }
  all('[data-scale]').forEach(b => b.addEventListener('click', () => selectPeriod(b.dataset.scale, focus)));
  all('[data-step]').forEach(b => b.addEventListener('click', () => move(+b.dataset.step)));
  all('[data-zoom]').forEach(b => b.addEventListener('click', () => zoom(+b.dataset.zoom)));
  one('[data-latest]').addEventListener('click', () => selectPeriod('month', filtered[0]?.time ?? last));
  form.addEventListener('submit', e => { e.preventDefault(); filterChanged(); });
  form.elements.q.addEventListener('input', filterChanged);
  form.elements.tag.addEventListener('change', filterChanged);
  form.elements.jump.addEventListener('change', e => { if (e.target.value) jumpMonth(e.target.value); });
  plot.addEventListener('keydown', e => {
    if (e.target !== plot || e.altKey || e.ctrlKey || e.metaKey) return;
    const shortcuts = {ArrowLeft: () => move(-1), ArrowRight: () => move(1), '+': () => zoom(1), '=': () => zoom(1), '-': () => zoom(-1), Home: () => selectPeriod('month', filtered[0]?.time ?? last)};
    if (shortcuts[e.key]) { e.preventDefault(); shortcuts[e.key](); }
  });
  timeline.on('rangechanged', e => {
    if (!e.byUser) return;
    scale = 'custom';
    const [a,b] = windowRange();
    const middle = (a+b)/2;
    focus = filtered.filter(r => inWindow(r, a,b)).reduce((best, r) => Math.abs(r.time-middle)<Math.abs(best-middle) ? r.time : best, Infinity);
    if (!Number.isFinite(focus)) focus = middle;
    render(); saveView();
  });
  addEventListener('popstate', () => {
    const [a,b] = stateFromUrl(); timeline.setWindow(a,b,{animation:false}); render();
  });
  let resizeTimer;
  addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 80); });
})();
