// builder-main.js — prez-builder entry. Wiring is added by PB-T8..PB-T11.
import { pickAndLoadLibrary } from './library-load.js';
import { renderBrowse, applyLangFilter } from './browse-pane.js';
import { createTray } from './tray.js';
import { pickDestination, assembleDeck, buildOutPath } from './assemble.js';

const state = { libraryPath: null, data: null, tray: null };
let destFolder = null;

document.addEventListener("DOMContentLoaded", () => {
  const browse = document.getElementById("browse-groups");
  const trayList = document.getElementById("tray-list");
  if (!browse || !trayList) { console.error("Builder DOM not mounted"); return; }
  console.info("Builder shell mounted");

  const pickBtn = document.getElementById('pick-library-btn');
  const libraryName = document.getElementById('library-name');
  const builderStatus = document.getElementById('builder-status');
  const langFilter = document.getElementById('lang-filter');
  const presetSelect = document.getElementById('preset-select');
  const assembleBtn = document.getElementById('assemble-btn');
  const deckFilename = document.getElementById('deck-filename');
  const pickDestBtn = document.getElementById('pick-dest-btn');
  const destPath = document.getElementById('dest-path');

  const tray = createTray({
    listEl: trayList,
    onChange: () => {
      if (assembleBtn) {
        assembleBtn.disabled = tray.getOrder().length === 0;
      }
    }
  });
  state.tray = tray;

  if (pickBtn) {
    pickBtn.addEventListener('click', async () => {
      const result = await pickAndLoadLibrary();
      if (result === null) {
        return;
      }
      if (result.ok === false) {
        // Invalid-library state — show full §8 error list
        browse.innerHTML = '';
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
        if (libraryName) {
          libraryName.textContent = '';
        }
        return;
      }
      state.libraryPath = result.path;
      state.data = result.data;
      if (libraryName) {
        libraryName.textContent = result.data.name || '';
      }
      const slideLookup = new Map((result.data.slides || []).map(s => [s.id, s]));
      state.slideLookup = slideLookup;
      const onTag = (rec) => tray.add(rec);
      renderBrowse(result.data, { onTag, libraryPath: result.path });
      if (presetSelect && result.data.presets) {
        presetSelect.innerHTML = '';
        const noneOpt = document.createElement('option');
        noneOpt.value = '';
        noneOpt.textContent = '(none)';
        presetSelect.appendChild(noneOpt);
        result.data.presets.forEach(preset => {
          const opt = document.createElement('option');
          opt.value = preset.preset;
          opt.textContent = preset.title || preset.preset;
          presetSelect.appendChild(opt);
        });
      }
      if (builderStatus && result.warnings && result.warnings.length > 0) {
        builderStatus.textContent = result.warnings.join('; ');
      } else if (builderStatus) {
        builderStatus.textContent = '';
      }
    });
  }

  if (langFilter) {
    langFilter.addEventListener('change', (e) => {
      applyLangFilter(e.target.value);
    });
  }

  if (presetSelect) {
    presetSelect.addEventListener('change', (e) => {
      const presetName = e.target.value;
      if (!presetName || !state.data || !state.data.presets) return;
      const preset = state.data.presets.find(p => p.preset === presetName);
      if (!preset) return;
      const slideLookup = state.slideLookup || new Map((state.data.slides || []).map(s => [s.id, s]));
      tray.setFromPreset(preset.slides, slideLookup);
      if (deckFilename) {
        deckFilename.value = preset.title || presetName || '';
      }
      if (preset.lang) {
        document.documentElement.lang = preset.lang;
      }
    });
  }

  if (pickDestBtn) {
    pickDestBtn.addEventListener('click', async () => {
      const folder = await pickDestination();
      if (folder === null) return;
      destFolder = folder;
      if (destPath) {
        destPath.textContent = folder;
      }
      if (builderStatus && state.libraryPath && folder === state.libraryPath) {
        builderStatus.textContent = 'Warning: output folder should be outside the library.';
        builderStatus.className = 'shell-status error';
      }
    });
  }

  if (assembleBtn) {
    assembleBtn.addEventListener('click', async () => {
      if (!state.libraryPath) {
        if (builderStatus) builderStatus.textContent = 'No library loaded.';
        return;
      }
      const slides = tray.getOrder();
      if (slides.length === 0) {
        if (builderStatus) builderStatus.textContent = 'Tray is empty.';
        return;
      }
      if (!destFolder) {
        if (builderStatus) builderStatus.textContent = 'Choose a destination folder.';
        return;
      }
      const filename = deckFilename ? deckFilename.value : '';
      if (!filename) {
        if (builderStatus) builderStatus.textContent = 'Enter a filename.';
        return;
      }
      const outPath = buildOutPath(destFolder, filename);
      const lang = document.documentElement.lang !== 'en' ? document.documentElement.lang : undefined;
      const title = deckFilename && deckFilename.value ? deckFilename.value : undefined;
      try {
        const result = await assembleDeck({
          libraryPath: state.libraryPath,
          slides,
          outPath,
          lang,
          title
        });
        if (result.ok) {
          const parts = [
            'Assembled: ' + result.output,
            'Assets: ' + (result.assetsCopied || []).length,
            'Unfilled tokens: ' + (result.unfilledTokens || []).length,
            result.asBuilt ? 'As-built entry recorded.' : ''
          ];
          if (builderStatus) {
            builderStatus.textContent = parts.filter(Boolean).join(' | ');
            builderStatus.className = 'shell-status success';
          }
          window.location.href = '/app/?file=' + encodeURIComponent(result.output);
        } else {
          const errs = (result.errors || []).join('; ') || 'Assembly failed.';
          if (builderStatus) {
            builderStatus.textContent = errs;
            builderStatus.className = 'shell-status error';
          }
        }
      } catch (err) {
        if (builderStatus) {
          builderStatus.textContent = 'Assemble failed: ' + err.message;
          builderStatus.className = 'shell-status error';
        }
      }
    });
  }
});
