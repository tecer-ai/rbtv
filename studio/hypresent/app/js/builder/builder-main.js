// builder-main.js — prez-builder entry: rail + browse + tray + assemble wiring.
import { pickAndLoadLibrary } from './library-load.js';
import { pickAndLoadDeck, loadDeckByPath } from './deck-load.js';
import { renderBrowse, applyLangFilter, markTrayState } from './browse-pane.js';
import { createSlideStage } from './slide-stage.js';
import { createTray } from './tray.js';
import { buildDeckSrcdoc } from './previews.js';
import { pickDestination, assembleDeck, buildOutPath } from './assemble.js';
import { saveDeck } from './deck-save.js';
import { confirmSaveOverwrite } from '/app/js/shell/confirm-modal.js';

const state = { libraryPath: null, data: null, tray: null, slideLookup: null, deck: null, canSave: false };
let destFolder = null;
let accentChosen = false;

document.addEventListener("DOMContentLoaded", () => {
  const browse = document.getElementById("browse-groups");
  const trayList = document.getElementById("tray-list");
  if (!browse || !trayList) { console.error("Builder DOM not mounted"); return; }
  console.info("Builder shell mounted");

  const browsePane = document.getElementById('builder-browse');
  const browseEmpty = document.getElementById('browse-empty');
  const libraryName = document.getElementById('library-name');
  const libPath = document.getElementById('lib-path');
  const libMeta = document.getElementById('lib-meta');
  const libEmpty = document.getElementById('lib-empty');
  const pickBtn = document.getElementById('pick-library-btn');
  const browsePickBtn = document.getElementById('browse-pick-btn');
  const libChip = document.getElementById('lib-chip');
  const libChipName = document.getElementById('lib-chip-name');
  const libChipMeta = document.getElementById('lib-chip-meta');
  const libChipChange = document.getElementById('lib-chip-change');
  const langBlock = document.getElementById('lang-block');
  const langSeg = document.getElementById('lang-seg');
  const secBlock = document.getElementById('sec-block');
  const secNav = document.getElementById('sec-nav');
  const builderStatus = document.getElementById('builder-status');
  const presetSelect = document.getElementById('preset-select');
  const trayCount = document.getElementById('tray-count');
  const assembleBtn = document.getElementById('assemble-btn');
  const deckFilename = document.getElementById('deck-filename');
  const deckLang = document.getElementById('deck-lang');
  const deckTitle = document.getElementById('deck-title');
  const accentInput = document.getElementById('accent-input');
  const accentSwatch = document.getElementById('accent-swatch');
  const accentHex = document.getElementById('accent-hex');
  const pickDestBtn = document.getElementById('pick-dest-btn');
  const destPath = document.getElementById('dest-path');
  const openDeckBtn = document.getElementById('open-deck-btn');
  const deckChip = document.getElementById('deck-chip');
  const deckChipName = document.getElementById('deck-chip-name');
  const deckChipChange = document.getElementById('deck-chip-change');
  const deckSavePane = document.getElementById('deck-save-pane');
  const saveNewBtn = document.getElementById('save-new-btn');
  const saveOverwriteBtn = document.getElementById('save-overwrite-btn');
  const switchToEditorBtn = document.getElementById('switch-to-editor-btn');

  function setStatus(msg, type = '') {
    if (!builderStatus) return;
    builderStatus.textContent = msg;
    builderStatus.className = 'shell-status' + (type ? ' ' + type : '');
  }

  const tray = createTray({
    listEl: trayList,
    onChange: () => {
      const order = tray.getOrder();
      const items = tray.getItems();
      const total = items.length;
      if (assembleBtn) assembleBtn.disabled = order.length === 0;
      if (trayCount) trayCount.textContent = total + (total === 1 ? ' slide' : ' slides');
      markTrayState(order);
      state.canSave = state.deck && total > 0;
      if (saveNewBtn) saveNewBtn.disabled = !state.canSave;
      if (saveOverwriteBtn) saveOverwriteBtn.disabled = !state.canSave;
      if (switchToEditorBtn) switchToEditorBtn.disabled = !state.canSave;
    }
  });
  state.tray = tray;

  // ── mode-switch guard: leaving for the Editor discards the tray ───────
  const navEditorLink = document.getElementById('nav-editor');
  if (navEditorLink) {
    navEditorLink.addEventListener('click', (e) => {
      // Route the pill switch through the same save + confirm-overwrite modal as the
      // "Switch to editor" button, so switching never silently discards the tray.
      if (tray.getItems().length === 0) return;   // nothing to save → plain navigation
      e.preventDefault();
      if (switchToEditorBtn) switchToEditorBtn.click();
    });
  }

  // ── Add blank slide button ─────────────────────────────────────────────
  const addBlankBtn = document.getElementById('add-blank-btn');
  if (addBlankBtn) {
    addBlankBtn.addEventListener('click', () => tray.addBlank());
  }

  // ── left rail: language segmented filter ─────────────────────────────
  function buildLangSeg(langs) {
    if (!langSeg) return;
    langSeg.innerHTML = '';
    const options = [{ value: 'all', label: 'All' }]
      .concat(langs.map(l => ({ value: l, label: l.toUpperCase() })));
    options.forEach((opt, i) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.dataset.lang = opt.value;
      btn.textContent = opt.label;
      if (i === 0) btn.classList.add('is-active');
      btn.addEventListener('click', () => {
        langSeg.querySelectorAll('button').forEach(b => b.classList.toggle('is-active', b === btn));
        applyLangFilter(opt.value);
      });
      langSeg.appendChild(btn);
    });
    if (langBlock) langBlock.hidden = langs.length === 0;
  }

  // ── left rail: sections nav + scroll spy ─────────────────────────────
  function buildSectionsNav(data) {
    if (!secNav) return;
    secNav.innerHTML = '';
    const sections = (data.sections || []).filter(name =>
      (data.slides || []).some(s => s.section === name));
    sections.forEach((name, i) => {
      const a = document.createElement('a');
      a.dataset.section = name;
      if (i === 0) a.classList.add('is-active');
      const label = document.createElement('span');
      label.textContent = name;
      a.appendChild(label);
      const n = document.createElement('span');
      n.className = 'n';
      n.textContent = String((data.slides || []).filter(s => s.section === name).length);
      a.appendChild(n);
      a.addEventListener('click', (e) => {
        e.preventDefault();
        const target = browse.querySelector(`.browse-sec[data-section="${CSS.escape(name)}"]`);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setActiveSection(name);
      });
      secNav.appendChild(a);
    });
    if (secBlock) secBlock.hidden = sections.length === 0;
  }

  function setActiveSection(name) {
    if (!secNav) return;
    secNav.querySelectorAll('a').forEach(a =>
      a.classList.toggle('is-active', a.dataset.section === name));
  }

  if (browsePane) {
    let spyPending = false;
    browsePane.addEventListener('scroll', () => {
      if (spyPending) return;
      spyPending = true;
      requestAnimationFrame(() => {
        spyPending = false;
        const secs = browse.querySelectorAll('.browse-sec');
        if (!secs.length) return;
        const paneTop = browsePane.getBoundingClientRect().top;
        let current = secs[0];
        secs.forEach(sec => {
          if (sec.offsetParent === null) return; // hidden by filter
          if (sec.getBoundingClientRect().top - paneTop <= 60) current = sec;
        });
        setActiveSection(current.dataset.section);
      });
    }, { passive: true });
  }

  // ── library load (three entry points share one handler) ──────────────
  async function handlePickLibrary() {
    let result;
    try {
      result = await pickAndLoadLibrary();
    } catch (err) {
      setStatus('Library load failed: ' + err.message, 'error');
      return;
    }
    if (result === null) {
      return;
    }
    if (result.ok === false) {
      // Invalid-library state — show full §8 error list
      browse.innerHTML = '';
      if (browseEmpty) browseEmpty.style.display = 'none';
      const invalidBlock = document.createElement('div');
      invalidBlock.className = 'builder-invalid';
      const heading = document.createElement('p');
      heading.textContent = 'Invalid library';
      invalidBlock.appendChild(heading);
      const errorList = document.createElement('ul');
      (result.errors || []).forEach(err => {
        const li = document.createElement('li');
        li.textContent = typeof err === 'string' ? err : JSON.stringify(err);
        errorList.appendChild(li);
      });
      invalidBlock.appendChild(errorList);
      browse.appendChild(invalidBlock);
      if (libraryName) libraryName.textContent = 'Library';
      if (libPath) { libPath.hidden = true; }
      if (libMeta) { libMeta.hidden = true; }
      if (libEmpty) { libEmpty.hidden = false; }
      if (libChip) libChip.hidden = true;
      if (langBlock) langBlock.hidden = true;
      if (secBlock) secBlock.hidden = true;
      return;
    }

    state.libraryPath = result.path;
    state.data = result.data;
    tray.setLibrary(result.path);

    const name = result.data.name || result.path.split(/[\\/]/).pop() || 'library';
    const slides = result.data.slides || [];
    const sections = (result.data.sections || []).filter(sec => slides.some(s => s.section === sec));
    const langs = [...new Set(slides.map(s => s.lang).filter(Boolean))];

    // lib card
    if (libraryName) libraryName.textContent = name;
    if (libPath) { libPath.textContent = result.path; libPath.title = result.path; libPath.hidden = false; }
    if (libMeta) {
      libMeta.innerHTML = '';
      const parts = [slides.length + ' slides', sections.length + ' sections', 'valid ✓'];
      parts.forEach((txt, i) => {
        if (i > 0) {
          const dot = document.createElement('span');
          dot.className = 'dot';
          libMeta.appendChild(dot);
        }
        libMeta.appendChild(document.createTextNode(txt));
      });
      libMeta.hidden = false;
    }
    if (libEmpty) libEmpty.hidden = true;
    if (pickBtn) pickBtn.textContent = 'Change library…';

    // topbar chip
    if (libChip && libChipName && libChipMeta) {
      libChipName.textContent = name;
      libChipMeta.textContent = '· ' + slides.length + ' slides' + (langs.length ? ' · ' + langs.join(' + ') : '');
      libChip.hidden = false;
    }

    buildLangSeg(langs);
    state.slideLookup = new Map(slides.map(s => [s.id, s]));

    // close any open stage from a previous library, then (re)create
    if (state.stage) state.stage.close();
    state.stage = createSlideStage({
      container: browsePane,
      getLibraryPath: () => state.libraryPath,
      getSlideRecord: (id) => state.slideLookup ? state.slideLookup.get(id) : null,
      onAdd: (id) => {
        const rec = state.slideLookup ? state.slideLookup.get(id) : null;
        if (rec && !tray.has(id)) tray.add(rec);
      },
      isAdded: (id) => tray.has(id),
    });
    const onExpand = (id) => state.stage.open(id);

    // browse + sections nav (cards toggle add/remove on click)
    const onTag = (rec) => {
      if (tray.has(rec.id)) tray.remove(rec.id);
      else tray.add(rec);
    };
    renderBrowse(result.data, { onTag, libraryPath: result.path, onExpand });
    buildSectionsNav(result.data);
    markTrayState(tray.getOrder());

    // deck language options
    if (deckLang) {
      deckLang.innerHTML = '';
      (langs.length ? langs : ['en']).forEach(l => {
        const opt = document.createElement('option');
        opt.value = l;
        opt.textContent = l;
        deckLang.appendChild(opt);
      });
    }

    // presets
    if (presetSelect && result.data.presets) {
      presetSelect.innerHTML = '';
      const noneOpt = document.createElement('option');
      noneOpt.value = '';
      noneOpt.textContent = '(none — from scratch)';
      presetSelect.appendChild(noneOpt);
      result.data.presets.forEach(preset => {
        const opt = document.createElement('option');
        opt.value = preset.preset;
        opt.textContent = preset.title || preset.preset;
        presetSelect.appendChild(opt);
      });
    }

    if (result.warnings && result.warnings.length > 0) {
      setStatus(result.warnings.join('; '));
    } else {
      setStatus('');
    }
  }

  [pickBtn, browsePickBtn, libChipChange].forEach(btn => {
    if (btn) btn.addEventListener('click', handlePickLibrary);
  });

  // ── deck load ────────────────────────────────────────────────────────
  function loadDeckIntoTray(deckResult) {
    state.deck = {
      path: deckResult.path,
      name: deckResult.name,
      dir: deckResult.dir,
      head: deckResult.head,
      sections: deckResult.sections
    };

    // Switch to deck mode: hide assemble, show save pane
    if (assembleBtn) assembleBtn.closest('.assemble').hidden = true;
    if (deckSavePane) deckSavePane.hidden = false;

    if (deckChip && deckChipName) {
      deckChipName.textContent = deckResult.name;
      deckChip.hidden = false;
    }

    // Opening a deck nulls the tray library; clear the stale browse pane so no
    // leftover library card / open stage can add a library row with a null
    // libraryPath (would corrupt the deck-save items contract).
    if (state.stage) { state.stage.close(); state.stage = null; }
    state.libraryPath = null;
    state.data = null;
    state.slideLookup = null;
    browse.innerHTML = '';
    if (browseEmpty) browseEmpty.style.display = '';
    if (libChip) libChip.hidden = true;
    if (langBlock) langBlock.hidden = true;
    if (secBlock) secBlock.hidden = true;

    tray.setLibrary(null);
    tray.setSrcdocProvider((rec, index) => {
      const sec = deckResult.sections[rec.index];
      if (!sec) return Promise.resolve('');
      return Promise.resolve(buildDeckSrcdoc(deckResult.head, sec.html));
    });

    const slideLookup = new Map();
    const slideIds = [];
    deckResult.sections.forEach((sec, idx) => {
      const id = 'deck-section-' + idx;
      slideIds.push(id);
      slideLookup.set(id, {
        id,
        title: 'Slide ' + (idx + 1),
        kind: 'existing',
        lang: '',
        index: idx
      });
    });
    tray.setFromPreset(slideIds, slideLookup);

    setStatus('');
  }

  // After a new-file save, the current deck source is re-pointed to the freshly
  // written file. Reload that file's head+sections and rebase the tray model to
  // identity indices so the NEXT save recomposes against the new source faithfully
  // (without this, stale pre-save indices re-apply against the new file and a slide
  // is silently dropped while a duplicate gains an extra copy).
  async function rebaseDeckToSavedFile(savedPath) {
    const reloaded = await loadDeckByPath(savedPath);
    if (!reloaded || reloaded.ok !== true) {
      throw new Error(reloaded && reloaded.error ? reloaded.error : 'Reload after save failed');
    }
    state.deck.head = reloaded.head;
    state.deck.sections = reloaded.sections;
    tray.setSrcdocProvider((rec, index) => {
      const sec = reloaded.sections[rec.index];
      if (!sec) return Promise.resolve('');
      return Promise.resolve(buildDeckSrcdoc(reloaded.head, sec.html));
    });
    tray.rebaseToSavedDeck();
  }

  async function handlePickDeck() {
    if (state.deck && tray.getItems().length > 0) {
      if (!confirm('Replace current deck? Unsaved changes will be lost.')) {
        return;
      }
    }

    let result;
    try {
      result = await pickAndLoadDeck();
    } catch (err) {
      setStatus('Deck open failed: ' + err.message, 'error');
      return;
    }
    if (result === null) {
      return;
    }
    if (result.ok === false) {
      setStatus(result.error, 'error');
      return;
    }
    loadDeckIntoTray(result);
  }

  if (openDeckBtn) openDeckBtn.addEventListener('click', handlePickDeck);
  if (deckChipChange) deckChipChange.addEventListener('click', handlePickDeck);

  // ── presets ───────────────────────────────────────────────────────────
  if (presetSelect) {
    presetSelect.addEventListener('change', (e) => {
      const presetName = e.target.value;
      if (!presetName || !state.data || !state.data.presets) return;
      const preset = state.data.presets.find(p => p.preset === presetName);
      if (!preset) return;
      const slideLookup = state.slideLookup || new Map((state.data.slides || []).map(s => [s.id, s]));
      tray.setFromPreset(preset.slides, slideLookup);
      if (deckFilename) {
        deckFilename.value = preset.preset || '';
      }
      if (deckTitle && preset.title) {
        deckTitle.value = preset.title;
      }
      if (preset.lang && deckLang) {
        deckLang.value = preset.lang;
      }
    });
  }

  // ── accent picker ─────────────────────────────────────────────────────
  if (accentInput) {
    accentInput.addEventListener('input', () => {
      accentChosen = true;
      const v = accentInput.value;
      if (accentSwatch) accentSwatch.style.background = v;
      if (accentHex) accentHex.textContent = v.toUpperCase();
    });
  }

  // ── destination ───────────────────────────────────────────────────────
  if (pickDestBtn) {
    pickDestBtn.addEventListener('click', async () => {
      const folder = await pickDestination();
      if (folder === null) return;
      destFolder = folder;
      if (destPath) {
        destPath.textContent = folder;
        destPath.title = folder;
      }
      if (state.libraryPath && folder === state.libraryPath) {
        setStatus('Warning: output folder should be outside the library.', 'error');
      }
    });
  }

  // ── assemble ──────────────────────────────────────────────────────────
  if (assembleBtn) {
    assembleBtn.addEventListener('click', async () => {
      if (!state.libraryPath) {
        setStatus('No library loaded.');
        return;
      }
      const slides = tray.getOrder();
      if (slides.length === 0) {
        setStatus('Tray is empty.');
        return;
      }
      if (!destFolder) {
        setStatus('Choose a destination folder.');
        return;
      }
      const filename = deckFilename ? deckFilename.value : '';
      if (!filename) {
        setStatus('Enter a deck name.');
        return;
      }
      const outPath = buildOutPath(destFolder, filename);
      const lang = deckLang && deckLang.value ? deckLang.value : document.documentElement.lang;
      const title = deckTitle && deckTitle.value.trim() ? deckTitle.value.trim() : undefined;
      const accent = accentChosen && accentInput ? accentInput.value : undefined;
      try {
        const result = await assembleDeck({
          libraryPath: state.libraryPath,
          slides,
          outPath,
          lang,
          title,
          accent
        });
        if (result.ok) {
          const parts = [
            'Assembled: ' + result.output,
            'Assets: ' + (result.assetsCopied || []).length,
            'Unfilled tokens: ' + (result.unfilledTokens || []).length,
            result.asBuilt ? 'As-built entry recorded.' : ''
          ];
          setStatus(parts.filter(Boolean).join(' | '), 'success');
          window.location.href = '/app/?file=' + encodeURIComponent(result.output);
        } else {
          const errs = (result.errors || []).join('; ') || 'Assembly failed.';
          setStatus(errs, 'error');
        }
      } catch (err) {
        setStatus('Assemble failed: ' + err.message, 'error');
      }
    });
  }

  // ── deck save ───────────────────────────────────────────────────────────
  async function doSave(mode) {
    if (!state.deck) {
      setStatus('No deck loaded.');
      return;
    }
    const items = tray.getItems();
    if (items.length === 0) {
      setStatus('Tray is empty.');
      return;
    }
    try {
      const result = await saveDeck({ deck: state.deck, items, mode });
      if (result.cancelled) {
        return; // user cancelled dialog — no error
      }
      if (result.ok) {
        const parts = ['Saved: ' + result.path];
        if (result.assetsCopied.length > 0) {
          parts.push('Assets copied: ' + result.assetsCopied.length);
        }
        if (result.assetsSkipped.length > 0) {
          parts.push('Assets skipped: ' + result.assetsSkipped.join(', '));
        }
        if (result.assetsRenamed.length > 0) {
          parts.push(
            'Renamed: '
            + result.assetsRenamed.map(function (r) {
              return r.from + ' → ' + r.to;
            }).join(', ')
          );
        }
        if (result.assetsMissing.length > 0) {
          parts.push(
            '⚠ ' + result.assetsMissing.length
            + ' own-asset ref(s) not colocated — source files not found beside the deck'
          );
        }
        setStatus(parts.join(' | '), 'success');
        // After new-file save, point state.deck to the new file and rebase the
        // tray model to identity indices against it (prevents stale-index re-application
        // corrupting the next save).
        if (mode === 'new-file') {
          state.deck.path = result.path;
          state.deck.name = result.path.split(/[\\/]/).pop() || result.path;
          if (deckChipName) deckChipName.textContent = state.deck.name;
        }
        // Rebase after BOTH modes: an overwrite also restructures the saved file's
        // sections, so the tray model's existing-indices must be re-synced or the
        // next save resolves stale indices to the wrong sections.
        await rebaseDeckToSavedFile(result.path);
      } else {
        setStatus('Save failed.', 'error');
      }
    } catch (err) {
      setStatus('Save failed: ' + err.message, 'error');
    }
  }

  if (saveNewBtn) {
    saveNewBtn.addEventListener('click', () => doSave('new-file'));
  }
  if (saveOverwriteBtn) {
    saveOverwriteBtn.addEventListener('click', () => doSave('overwrite'));
  }

  // ── Switch to editor (bridge) ──────────────────────────────────────────
  if (switchToEditorBtn) {
    switchToEditorBtn.addEventListener('click', async () => {
      if (!state.deck) {
        setStatus('No deck loaded.', 'error');
        return;
      }
      const items = tray.getItems();
      if (items.length === 0) {
        setStatus('Tray is empty.', 'error');
        return;
      }
      try {
        let result;
        if (state.deck.path) {
          const choice = await confirmSaveOverwrite(state.deck.name || state.deck.path);
          if (choice === 'cancel') return;               // stay in the builder
          const mode = (choice === 'proceed') ? 'overwrite' : 'new-file';
          result = await saveDeck({ deck: state.deck, items, mode });
        } else {
          result = await saveDeck({ deck: state.deck, items, mode: 'new-file' });
        }
        if (result.cancelled) {
          return; // user cancelled dialog — stay put
        }
        if (!result.ok) {
          setStatus('Save failed.', 'error');
          return;
        }
        // Save succeeded — navigate to editor via existing handoff
        window.location.href = '/app/?file=' + encodeURIComponent(result.path);
      } catch (err) {
        setStatus('Save failed: ' + err.message, 'error');
      }
    });
  }

  // ── ?file= boot branch ───────────────────────────────────────────────
  const fileParam = new URLSearchParams(location.search).get('file');
  if (fileParam) {
    (async () => {
      try {
        const result = await loadDeckByPath(fileParam);
        if (result && result.ok) {
          loadDeckIntoTray(result);
        } else if (result && result.ok === false) {
          setStatus(result.error, 'error');
        }
      } catch (err) {
        console.error('Deck handoff failed:', err.message);
        setStatus('Deck open failed: ' + err.message, 'error');
      }
    })();
  }
});
