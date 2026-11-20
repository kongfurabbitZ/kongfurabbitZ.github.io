(() => {
  'use strict';
  const view = document.querySelector('[data-catalog]');
  if (!view) return;
  const form = view.querySelector('[data-filters]');
  const timeline = view.dataset.catalog === 'timeline';
  const records = Array.from(view.querySelectorAll('[data-item]'), node => ({
    node, day: node.dataset.day, kind: node.dataset.kind,
    tags: JSON.parse(node.dataset.tags), text: node.dataset.search.toLocaleLowerCase()
  }));
  const dayMs = 86400000;
  const asTime = day => Date.parse(day + 'T00:00:00Z');
  const monthControl = form.elements.namedItem('month');
  const latestMonth = monthControl?.options[1]?.value || 'all';
  const label = tag => tag.replace(/^(主题|方法)·/, '');
  function restore() {
    const params = new URL(location.href).searchParams;
    for (const control of form.elements) {
      if (!control.name) continue;
      control.value = params.get(control.name) ?? (control.name === 'month' ? latestMonth : '');
      if (control.selectedIndex === -1 && control.type === 'select-one') {
        const wanted = params.get(control.name) || '';
        const alias = control.name === 'tag' && Array.from(control.options).find(o => label(o.value) === label(wanted));
        control.value = alias ? alias.value : (control.name === 'month' ? latestMonth : '');
      }
    }
  }
  function drawAxis(list, month) {
    const axis = view.querySelector('[data-axis]');
    axis.replaceChildren();
    if (!list.length) return;
    const days = list.map(r => asTime(r.day)).sort((a, b) => a - b);
    const first = month === 'all' ? new Date(days[0]) : new Date(asTime(month + '-01'));
    first.setUTCDate(1);
    const last = month === 'all' ? new Date(days[days.length - 1]) : new Date(first);
    last.setUTCMonth(last.getUTCMonth() + 1, 0);
    const span = Math.max(dayMs, last - first);
    const place = time => ((time - first) / span) * 100;
    const long = span > 45 * dayMs;
    for (let i = 0; i < 4; i++) {
      const tick = document.createElement('span');
      const time = +first + Math.round(span * i / (3 * dayMs)) * dayMs;
      tick.textContent = new Date(time).toISOString().slice(long ? 0 : 5, long ? 7 : 10);
      tick.style.left = place(time) + '%';
      axis.append(tick);
    }
    for (const row of list) row.node.style.setProperty('--position', place(asTime(row.day)) + '%');
  }
  function render() {
    const fields = new FormData(form);
    const tag = fields.get('tag'), kind = fields.get('kind'), month = fields.get('month');
    const terms = (fields.get('q') || '').trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const shown = [];
    for (const r of records) {
      r.node.hidden = Boolean((tag && !r.tags.some(t => label(t) === label(tag))) || (kind && kind !== r.kind) ||
        (month && month !== 'all' && !r.day.startsWith(month)) || !terms.every(t => r.text.includes(t)));
      if (!r.node.hidden) shown.push(r);
    }
    view.querySelector('[data-count]').textContent = shown.length + (timeline ? ' 篇论文' : ' 篇文章');
    view.querySelector('[data-empty]').hidden = shown.length !== 0;
    if (timeline) drawAxis(shown, month);
  }
  function change(push) {
    const url = new URL(location.href);
    for (const [k, v] of new FormData(form)) {
      if (v) url.searchParams.set(k, v);
      else url.searchParams.delete(k);
    }
    if (url.href !== location.href) history[push ? 'pushState' : 'replaceState'](null, '', url);
    render();
  }
  form.addEventListener('input', e => { if (e.target.type === 'search') change(false); });
  form.addEventListener('change', e => { if (e.target.tagName === 'SELECT') change(true); });
  form.addEventListener('submit', e => { e.preventDefault(); change(false); });
  form.addEventListener('reset', e => {
    e.preventDefault();
    for (const input of form.elements) if (input.name) input.value = input.name === 'month' ? 'all' : '';
    change(true);
  });
  addEventListener('popstate', () => { restore(); render(); });
  restore();
  render();
  view.classList.add('interactive');
})();
