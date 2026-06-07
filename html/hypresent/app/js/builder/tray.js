// tray.js — compose tray model + render
import { attachSorter } from './tray-sorter.js';

export function createTray({ listEl, onChange }) {
  const model = [];

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

      const pos = document.createElement('span');
      pos.className = 'tray-pos';
      pos.textContent = String(index + 1);
      li.appendChild(pos);

      const title = document.createElement('span');
      title.className = 'tray-title';
      title.textContent = rec.title || rec.id;
      li.appendChild(title);

      const badge = document.createElement('span');
      badge.className = 'tray-kind';
      badge.textContent = rec.kind || '';
      li.appendChild(badge);

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'tray-remove';
      removeBtn.textContent = '×';
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

  return { model, add, remove, setFromPreset, render, getOrder };
}
