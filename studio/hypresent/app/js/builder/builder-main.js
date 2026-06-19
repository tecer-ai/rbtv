// builder-main.js — prez-builder entry: rail + browse + tray + assemble wiring.
import { pickAndLoadLibrary, loadLibraryByPath, pickLibraryFolderForExport } from './library-load.js';
import { pickAndLoadDeck, loadDeckByPath } from './deck-load.js';
import { renderBrowse, renderArchived, applyLangFilter, markTrayState } from './browse-pane.js';
import { archiveSlide, unarchiveSlide, listArchived } from './archive-actions.js';
import { createSlideStage } from './slide-stage.js';
import { createTray } from './tray.js';
import { buildDeckSrcdoc } from './previews.js';
import { pickDestination, assembleDeck, buildOutPath } from './assemble.js';
import { saveDeck } from './deck-save.js';
import { confirmSaveOverwrite } from '/app/js/shell/confirm-modal.js';
import { createDeckSelection } from './deck-select.js';
import { exportDeckSlides } from './deck-export.js';

const state = { libraryPath: null, data: null, tray: null, slideLookup: null, deck: null, canSave: false, showArchived: false };
let destFolder = null;
let accentChosen = false;
let exportLibPath = null; // target library for Export-to-library

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
  const viewBlock = document.getElementById('view-block');
  const showArchivedBtn = document.getElementById('show-archived-btn');
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

  // Export-to-library pane elements
  const deckExportPane = document.getElementById('deck-export-pane');
  const exportSelCount = document.getElementById('export-sel-count');
  const exportSelAllBtn = document.getElementById('export-sel-all-btn');
  const exportSelNoneBtn = document.getElementById('export-sel-none-btn');
  const exportPickLibBtn = document.getElementById('export-pick-lib-btn');
  const exportTargetPath = document.getElementById('export-target-path');
  const exportCtaBtn = document.getElementById('export-cta-btn');
  const exportResult = document.getElementById('export-result');

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

  // ── Export-to-library: selection manager ─────────────────────────────
  function updateExportCtaState(selUids) {
    const hasSelection = selUids.size > 0;
    const hasLib = !!exportLibPath;
    if (exportCtaBtn) exportCtaBtn.disabled = !(hasSelection && hasLib);
    if (exportSelCount) exportSelCount.textContent = selUids.size + (selUids.size === 1 ? ' selected' : ' selected');
  }

  const deckSelection = createDeckSelection({
    listEl: trayList,
    onSelectionChange: updateExportCtaState,
  });

  // ── Export-to-library: All / None buttons ────────────────────────────
  if (exportSelAllBtn) exportSelAllBtn.addEventListener('click', () => deckSelection.selectAll());
  if (exportSelNoneBtn) exportSelNoneBtn.addEventListener('click', () => deckSelection.clearAll());

  // ── Export-to-library: choose target library ─────────────────────────
  if (exportPickLibBtn) {
    exportPickLibBtn.addEventListener('click', async () => {
      // Pick the target folder and validate it as an EXPORT TARGET only. This
      // does NOT load the slide catalog (pickAndLoadLibrary runs the picked
      // library's vendored assemble.py engine, which wrongly rejects any valid
      // target that does not vendor that engine binary). The export pipeline
      // (/api/deck-export) requires only library.json + a "## Slides" manifest,
      // which is exactly what pickLibraryFolderForExport validates.
      let result;
      try {
        result = await pickLibraryFolderForExport();
      } catch (err) {
        setStatus('Library pick failed: ' + err.message, 'error');
        return;
      }
      if (!result) return; // cancelled
      if (result.ok === false) {
        const detail = (result.errors && result.errors.length)
          ? result.errors.join(' ')
          : 'folder is not a valid slide library.';
        setStatus('Invalid export target: ' + detail, 'error');
        return;
      }
      exportLibPath = result.path;
      if (exportTargetPath) {
        exportTargetPath.textContent = result.path;
        exportTargetPath.title = result.path;
        exportTargetPath.classList.add('has-path');
      }
      // Clear any prior error/status now that a valid target is set.
      setStatus('Export target set: ' + result.path, 'success');
      // Re-evaluate CTA state
      updateExportCtaState(deckSelection.getSelectedUids());
    });
  }

  // ── Export-to-library: show result/concerns ──────────────────────────
  function showExportResult(data, err) {
    if (!exportResult) return;
    exportResult.hidden = false;
    exportResult.innerHTML = '';
    exportResult.className = 'export-result';

    if (err) {
      exportResult.classList.add('is-err');
      exportResult.textContent = 'Export failed: ' + err.message;
      return;
    }

    // Empty-selection server response
    if (data.message && !data.exported) {
      exportResult.classList.add('is-warn');
      exportResult.textContent = data.message;
      return;
    }

    const exported = data.exported || 0;
    const concerns = data.concerns || [];
    const assetsSkipped = data.assets_skipped || [];
    const hasIssues = concerns.length > 0 || assetsSkipped.length > 0;

    exportResult.classList.add(hasIssues ? 'is-warn' : 'is-ok');

    const summary = document.createElement('b');
    summary.textContent = exported + ' slide' + (exported === 1 ? '' : 's') + ' exported — tagged to-review.';
    exportResult.appendChild(summary);

    if (concerns.length > 0) {
      const heading = document.createElement('div');
      heading.style.marginTop = '6px';
      heading.style.fontWeight = '700';
      heading.textContent = 'Concerns (review before using):';
      exportResult.appendChild(heading);
      const ul = document.createElement('ul');
      concerns.forEach(c => {
        const li = document.createElement('li');
        li.textContent = typeof c === 'string' ? c : JSON.stringify(c);
        ul.appendChild(li);
      });
      exportResult.appendChild(ul);
    }

    if (assetsSkipped.length > 0) {
      const heading = document.createElement('div');
      heading.style.marginTop = '6px';
      heading.style.fontWeight = '700';
      heading.textContent = 'Assets skipped (not found or collision):';
      exportResult.appendChild(heading);
      const ul = document.createElement('ul');
      assetsSkipped.forEach(a => {
        const li = document.createElement('li');
        li.textContent = typeof a === 'string' ? a : JSON.stringify(a);
        ul.appendChild(li);
      });
      exportResult.appendChild(ul);
    }
  }

  // ── Export-to-library: CTA handler ───────────────────────────────────
  if (exportCtaBtn) {
    exportCtaBtn.addEventListener('click', async () => {
      if (!state.deck || !state.deck.path) {
        setStatus('No deck loaded.', 'error');
        return;
      }
      const selectedIds = deckSelection.getSelectedSlideIds();
      if (selectedIds.length === 0) {
        // Empty-selection guard: no request sent, clear message shown
        if (exportResult) {
          exportResult.hidden = false;
          exportResult.className = 'export-result is-warn';
          exportResult.textContent = 'No slides selected — select at least one slide to export.';
        }
        return;
      }
      if (!exportLibPath) {
        setStatus('Choose a target library first.', 'error');
        return;
      }

      exportCtaBtn.disabled = true;
      setStatus('Exporting…');
      if (exportResult) exportResult.hidden = true;

      try {
        const data = await exportDeckSlides({
          deckPath: state.deck.path,
          selectedIds,
          libraryPath: exportLibPath,
        });
        showExportResult(data, null);
        const exported = data.exported || 0;
        setStatus('Exported ' + exported + ' slide' + (exported === 1 ? '' : 's') + '.', 'success');
      } catch (err) {
        showExportResult(null, err);
        setStatus('Export failed.', 'error');
      } finally {
        // Re-evaluate disabled state (selection unchanged, lib still set)
        updateExportCtaState(deckSelection.getSelectedUids());
      }
    });
  }

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

  // ── archive / restore gestures ───────────────────────────────────────
  const onExpand = (id) => { if (state.stage) state.stage.open(id); };
  const onTag = (rec) => { if (tray.has(rec.id)) tray.remove(rec.id); else tray.add(rec); };

  function renderLiveGrid() {
    renderBrowse(state.data, { onTag, libraryPath: state.libraryPath, onExpand, onArchive });
    buildSectionsNav(state.data);
    markTrayState(tray.getOrder());
  }

  async function reloadLibraryState() {
    const r = await loadLibraryByPath(state.libraryPath);
    if (!r || r.ok === false) { setStatus('Library reload failed', 'error'); return false; }
    state.data = r.data;
    state.slideLookup = new Map((r.data.slides || []).map(s => [s.id, s]));
    return true;
  }

  async function showArchivedView() {
    const res = await listArchived(state.libraryPath);
    if (!res || res.ok === false) { setStatus('Could not load archived slides', 'error'); return; }
    renderArchived(res.archived || [], { onRestore });
  }

  function renderCurrentMode() { if (state.showArchived) showArchivedView(); else renderLiveGrid(); }

  const onArchive = async (id) => {
    const res = await archiveSlide(state.libraryPath, id);
    if (res && res.ok) {
      setStatus('Archived ' + id, 'success');
      if (await reloadLibraryState()) renderCurrentMode();
    } else {
      setStatus('Archive failed: ' + ((res && res.error) || 'unknown'), 'error');
    }
  };

  const onRestore = async (id) => {
    const res = await unarchiveSlide(state.libraryPath, id);
    if (res && res.ok) {
      setStatus('Restored ' + id, 'success');
      if (await reloadLibraryState()) renderCurrentMode();
    } else {
      setStatus('Restore failed: ' + ((res && res.error) || 'unknown'), 'error');
    }
  };

  // ── left rail: archived view toggle ──────────────────────────────────
  if (showArchivedBtn) {
    showArchivedBtn.addEventListener('click', () => {
      state.showArchived = !state.showArchived;
      showArchivedBtn.classList.toggle('is-active', state.showArchived);
      showArchivedBtn.setAttribute('aria-pressed', String(state.showArchived));
      renderCurrentMode();
    });
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
    state.showArchived = false;
    renderLiveGrid();
    if (viewBlock) viewBlock.hidden = false;
    if (showArchivedBtn) {
      showArchivedBtn.classList.remove('is-active');
      showArchivedBtn.setAttribute('aria-pressed', 'false');
    }

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

    // Switch to deck mode: hide assemble, show save pane + export pane
    if (assembleBtn) assembleBtn.closest('.assemble').hidden = true;
    if (deckSavePane) deckSavePane.hidden = false;
    if (deckExportPane) deckExportPane.hidden = false;

    // Reset export state for the newly loaded deck
    deckSelection.clearAll();
    deckSelection.enable();
    exportLibPath = null;
    if (exportTargetPath) { exportTargetPath.textContent = 'No library chosen'; exportTargetPath.title = ''; exportTargetPath.classList.remove('has-path'); }
    if (exportResult) exportResult.hidden = true;
    if (exportCtaBtn) exportCtaBtn.disabled = true;
    if (exportSelCount) exportSelCount.textContent = '0 selected';

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
    state.showArchived = false;
    browse.innerHTML = '';
    if (browseEmpty) browseEmpty.style.display = '';
    if (libChip) libChip.hidden = true;
    if (langBlock) langBlock.hidden = true;
    if (secBlock) secBlock.hidden = true;
    if (viewBlock) viewBlock.hidden = true;

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
