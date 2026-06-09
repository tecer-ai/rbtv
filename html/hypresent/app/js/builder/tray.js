// tray.js — compose tray model + render
import { attachSorter } from './tray-sorter.js';
import { getSlideSrcdoc } from './previews.js';

const GRIP_SVG = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="9" cy="6" r="1.7"/><circle cx="15" cy="6" r="1.7"/><circle cx="9" cy="12" r="1.7"/><circle cx="15" cy="12" r="1.7"/><circle cx="9" cy="18" r="1.7"/><circle cx="15" cy="18" r="1.7"/></svg>';
const X_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';
const DUPLICATE_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';

const BLANK_SRCDOC = '<!DOCTYPE html><html><head><style>body{margin:0;display:flex;align-items:center;justify-content:center;height:100vh;background:#f8f9fa;color:#adb5bd;font-family:sans-serif;font-size:14px;}</style></head><body><span>Blank slide</span></body></html>';

export function createTray({ listEl, onChange }) {
  const model = [];
  let libraryPath = null;
  let srcdocProvider = null;
  let nextUid = 1;

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
      li.dataset.uid = String(rec.uid);
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

      const badge = document.createElement('span');
      badge.className = 'tray-badge';
      badge.textContent = rec.kind === 'existing' ? 'deck' : rec.kind === 'library' ? 'lib' : 'blank';
      badge.style.cssText = 'position:absolute;top:2px;left:2px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;padding:1px 5px;border-radius:4px;background:var(--line-2);color:var(--ink-faint);z-index:1;';
      thumb.appendChild(badge);
      li.appendChild(thumb);

      if (rec.kind === 'blank') {
        iframe.srcdoc = BLANK_SRCDOC;
      } else if (srcdocProvider) {
        srcdocProvider(rec, index)
          .then(srcdoc => { iframe.srcdoc = srcdoc; })
          .catch(() => { /* thumbnail is decorative; row stays functional */ });
      } else if (rec.libraryPath) {
        getSlideSrcdoc(rec.libraryPath, rec.id)
          .then(srcdoc => { iframe.srcdoc = srcdoc; })
          .catch(() => { /* thumbnail is decorative; row stays functional */ });
      } else if (libraryPath) {
        getSlideSrcdoc(libraryPath, rec.id)
          .then(srcdoc => { iframe.srcdoc = srcdoc; })
          .catch(() => { /* thumbnail is decorative; row stays functional */ });
      }

      const title = document.createElement('span');
      title.className = 'tray-title';

      if (rec.kind !== 'library') {
        const dupBtn = document.createElement('button');
        dupBtn.type = 'button';
        dupBtn.className = 'tray-duplicate';
        dupBtn.setAttribute('aria-label', 'Duplicate ' + (rec.title || rec.id));
        dupBtn.innerHTML = DUPLICATE_SVG;
        dupBtn.style.cssText = 'width:18px;height:18px;border-radius:4px;color:var(--ink-faint);display:inline-flex;align-items:center;justify-content:center;vertical-align:middle;margin-right:4px;cursor:pointer;background:transparent;border:0;padding:0;';
        dupBtn.addEventListener('click', (e) => { e.stopPropagation(); duplicate(rec.uid); });
        title.appendChild(dupBtn);
      }

      title.appendChild(document.createTextNode(rec.title || rec.id));
      li.appendChild(title);

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'tray-remove';
      removeBtn.setAttribute('aria-label', 'Remove ' + (rec.title || rec.id));
      removeBtn.innerHTML = X_SVG;
      removeBtn.addEventListener('click', () => removeByUid(rec.uid));
      li.appendChild(removeBtn);

      listEl.appendChild(li);
    });

    attachSorter(listEl, {
      onReorder: (newOrderUids) => {
        // Sync model to new DOM order
        const map = new Map(model.map(m => [String(m.uid), m]));
        const newModel = newOrderUids.map(uid => map.get(uid)).filter(Boolean);
        model.length = 0;
        model.push(...newModel);
        renumber();
        if (onChange) onChange();
      }
    });

    renumber();
  }

  function add(rec) {
    if (model.some(m => m.kind === 'library' && m.id === rec.id)) return;
    model.push({
      uid: nextUid++,
      kind: 'library',
      id: rec.id,
      title: rec.title,
      lang: rec.lang || '',
      libraryPath: libraryPath
    });
    render();
    if (onChange) onChange();
  }

  function remove(id) {
    // Remove the first library row with this id (used for card toggle)
    const idx = model.findIndex(m => m.kind === 'library' && m.id === id);
    if (idx === -1) return;
    model.splice(idx, 1);
    render();
    if (onChange) onChange();
  }

  function removeByUid(uid) {
    const idx = model.findIndex(m => m.uid === uid);
    if (idx === -1) return;
    model.splice(idx, 1);
    render();
    if (onChange) onChange();
  }

  function duplicate(uid) {
    const src = model.find(m => m.uid === uid);
    if (!src || src.kind === 'library') return;
    const idx = model.findIndex(m => m.uid === uid);
    if (idx === -1) return;
    const copy = {
      ...src,
      uid: nextUid++,
      id: src.kind === 'blank' ? ('blank-' + nextUid) : src.id
    };
    model.splice(idx + 1, 0, copy);
    render();
    if (onChange) onChange();
  }

  function addBlank() {
    const uid = nextUid++;
    model.push({
      uid,
      kind: 'blank',
      id: 'blank-' + uid,
      title: 'Blank slide',
      lang: ''
    });
    render();
    if (onChange) onChange();
  }

  function setFromPreset(slideIds, slideLookup) {
    const newModel = [];
    slideIds.forEach(id => {
      const rec = slideLookup.get(id);
      if (rec) {
        if (rec.kind === 'existing') {
          newModel.push({
            uid: nextUid++,
            kind: 'existing',
            id: rec.id,
            title: rec.title,
            lang: rec.lang || '',
            index: rec.index !== undefined ? rec.index : parseInt(String(rec.id).replace('deck-section-', ''), 10)
          });
        } else {
          newModel.push({
            uid: nextUid++,
            kind: 'library',
            id: rec.id,
            title: rec.title,
            lang: rec.lang || '',
            libraryPath: libraryPath
          });
        }
      }
    });
    model.length = 0;
    model.push(...newModel);
    render();
    if (onChange) onChange();
  }

  function getOrder() {
    return model.filter(m => m.kind === 'library').map(m => m.id);
  }

  function getItems() {
    return model.map(m => {
      if (m.kind === 'existing') {
        return { kind: 'existing', index: m.index };
      } else if (m.kind === 'library') {
        return { kind: 'library', library_path: m.libraryPath, slide_id: m.id };
      } else {
        return { kind: 'blank' };
      }
    });
  }

  function has(id) {
    return model.some(m => m.kind === 'library' && m.id === id);
  }

  function setLibrary(path) {
    libraryPath = path;
    srcdocProvider = null;
  }

  function setSrcdocProvider(fn) {
    srcdocProvider = fn || null;
  }

  return { model, add, remove, removeByUid, duplicate, addBlank, setFromPreset, render, getOrder, getItems, has, setLibrary, setSrcdocProvider };
}
