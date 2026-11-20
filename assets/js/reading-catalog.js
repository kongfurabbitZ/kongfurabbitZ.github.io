(() => {
  'use strict';
  const view = document.querySelector('[data-catalog]');
  if (!view) return;
  const form = view.querySelector('[data-filters]');
  const records = Array.from(view.querySelectorAll('[data-item]'), node => ({
    node, kind: node.dataset.kind,
    tags: JSON.parse(node.dataset.tags), text: node.dataset.search.toLocaleLowerCase()
  }));
  const label = tag => tag.replace(/^(主题|方法)·/, '');
  function restore() {
    const params = new URL(location.href).searchParams;
    for (const control of form.elements) {
      if (!control.name) continue;
      control.value = params.get(control.name) || '';
      if (control.selectedIndex === -1 && control.type === 'select-one') {
        const wanted = params.get(control.name) || '';
        const alias = control.name === 'tag' && Array.from(control.options).find(o => label(o.value) === label(wanted));
        control.value = alias ? alias.value : '';
      }
    }
  }
  function render() {
    const fields = new FormData(form);
    const tag = fields.get('tag'), kind = fields.get('kind');
    const terms = (fields.get('q') || '').trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const shown = [];
    for (const r of records) {
      r.node.hidden = Boolean((tag && !r.tags.some(t => label(t) === label(tag))) || (kind && kind !== r.kind) ||
        !terms.every(t => r.text.includes(t)));
      if (!r.node.hidden) shown.push(r);
    }
    view.querySelector('[data-count]').textContent = shown.length + ' 篇文章';
    view.querySelector('[data-empty]').hidden = shown.length !== 0;
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
    for (const input of form.elements) if (input.name) input.value = '';
    change(true);
  });
  addEventListener('popstate', () => { restore(); render(); });
  restore();
  render();
  view.classList.add('interactive');
})();
