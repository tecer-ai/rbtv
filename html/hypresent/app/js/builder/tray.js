// tray.js — compose tray model + render
import { attachSorter } from './tray-sorter.js';
import { getSlideSrcdoc } from './previews.js';

const GRIP_SVG = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="9" cy="6" r="1.7"/><circle cx="15" cy="6" r="1.7"/><circle cx="9" cy="12" r="1.7"/><circle cx="15" cy="12" r="1.7"/><circle cx="9" cy="18" r="1.7"/><circle cx="15" cy="18" r="1.7"/></svg>';
const X_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';

export function createTray({ listEl, onChange }) {
  const model = [];
  let libraryPath = null;
  let srcdocProvider = null;

  function renumber() {
    const rows = listEl.querySelectorAll('.tray-row');
    rows.forEach((row, idx) => {
      const posEl = row.querySelector('.tray-pos');
      if (posEl) posEl.textContent = String(idx + 1);
    });
  }

  function render() {
    listEl.innerHTML = '';
    model.forEach((rec, index) => {
      const li = document.createElement('li');
      li.className = 'tray-row';
      li.dataset.slideId = rec.id;
      li.style.animationDelay = Math.min(index * 0.03, 0.3) + 's';

      const grip = document.createElement('span');
      grip.className = 'grip';
      grip.title = 'Drag to reorder';
      grip.innerHTML = GRIP_SVG;
      li.appendChild(grip);

      const pos = document.createElement('span');
      pos.className = 'tray-pos';
      pos.textContent = String(index + 1);
      li.appendChild(pos);

      const thumb = document.createElement('div');
      thumb.className = 't-thumb';
      const iframe = document.createElement('iframe');
      iframe.setAttribute('tabindex', '-1');
      thumb.appendChild(iframe);
      li.appendChild(thumb);
      if (srcdocProvider) {
        srcdocProvider(rec, index)
          .then(srcdoc => { iframe.srcdoc = srcdoc; })
          .catch(() => { /* thumbnail is decorative; row stays functional */ });
      } else if (libraryPath) {
        getSlideSrcdoc(libraryPath, rec.id)
          .then(srcdoc => { iframe.srcdoc = srcdoc; })
          .catch(() => { /* thumbnail is decorative; row stays functional */ });
      }

      const title = document.createElement('span');
      title.className = 'tray-title';
      title.textContent = rec.title || rec.id;
      li.appendChild(title);

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'tray-remove';
      removeBtn.setAttribute('aria-label', 'Remove ' + (rec.title || rec.id));
      removeBtn.innerHTML = X_SVG;
      removeBtn.addEventListener('click', () => remove(rec.id));
      li.appendChild(removeBtn);

      listEl.appendChild(li);
    });

    attachSorter(listEl, {
      onReorder: (newOrderIds) => {
        // Sync model to new DOM order
        const map = new Map(model.map(m => [m.id, m]));
        const newModel = newOrderIds.map(id => map.get(id)).filter(Boolean);
        model.length = 0;
        model.push(...newModel);
        renumber();
        if (onChange) onChange();
      }
    });

    renumber();
  }

  function add(rec) {
    if (model.some(m => m.id === rec.id)) return;
    model.push({ id: rec.id, title: rec.title, kind: rec.kind, lang: rec.lang });
    render();
    if (onChange) onChange();
  }

  function remove(id) {
    const idx = model.findIndex(m => m.id === id);
    if (idx === -1) return;
    model.splice(idx, 1);
    render();
    if (onChange) onChange();
  }

  function setFromPreset(slideIds, slideLookup) {
    const newModel = [];
    slideIds.forEach(id => {
      const rec = slideLookup.get(id);
      if (rec) {
        newModel.push({ id: rec.id, title: rec.title, kind: rec.kind, lang: rec.lang });
      }
    });
    model.length = 0;
    model.push(...newModel);
    render();
    if (onChange) onChange();
  }

  function getOrder() {
    return model.map(m => m.id);
  }

  function has(id) {
    return model.some(m => m.id === id);
  }

  function setLibrary(path) {
    libraryPath = path;
    srcdocProvider = null;
  }

  function setSrcdocProvider(fn) {
    srcdocProvider = fn || null;
  }

  return { model, add, remove, setFromPreset, render, getOrder, has, setLibrary, setSrcdocProvider };
}
