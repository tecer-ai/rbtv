// deck-select.js — Visual multi-select of slides in the tray when a deck is open.
//
// When the builder is in deck-mode (a deck loaded into the tray, not a library
// browse), the tray rows gain a checkbox-like selection affordance. This module
// manages the selection Set and exposes toggle/clear/getIds helpers; it also
// renders the selected state onto tray rows.

/**
 * createDeckSelection — wire selection behaviour onto the tray list element.
 *
 * @param {object} opts
 * @param {HTMLElement} opts.listEl       – the <ol class="tray-list"> element
 * @param {Function}    opts.onSelectionChange – called with (selectedUids: Set<string>)
 *                                              whenever the selection changes
 * @returns {object} – { toggle(uid), selectAll(), clearAll(), getSelectedUids(),
 *                       getSelectedSlideIds(), enable(), disable(), syncRow(liEl) }
 */
export function createDeckSelection({ listEl, onSelectionChange }) {
  const selected = new Set(); // Set of data-uid values (tray row identifiers)
  let enabled = false;

  function _notify() {
    onSelectionChange(new Set(selected));
  }

  function syncRow(liEl) {
    if (!liEl) return;
    const uid = liEl.dataset.uid;
    const isSel = selected.has(uid);
    liEl.classList.toggle('is-export-selected', isSel);
    const cb = liEl.querySelector('.export-cb');
    if (cb) cb.checked = isSel;
  }

  function syncAll() {
    if (!listEl) return;
    listEl.querySelectorAll('.tray-row').forEach(syncRow);
  }

  function toggle(uid) {
    if (selected.has(uid)) {
      selected.delete(uid);
    } else {
      selected.add(uid);
    }
    // Sync the specific row
    if (listEl) {
      const row = listEl.querySelector(`.tray-row[data-uid="${CSS.escape(uid)}"]`);
      syncRow(row);
    }
    _notify();
  }

  function selectAll() {
    if (!listEl) return;
    listEl.querySelectorAll('.tray-row').forEach(row => {
      if (row.dataset.uid) selected.add(row.dataset.uid);
    });
    syncAll();
    _notify();
  }

  function clearAll() {
    selected.clear();
    syncAll();
    _notify();
  }

  function getSelectedUids() {
    return new Set(selected);
  }

  /**
   * getSelectedSlideIds — returns the data-hyp-slide-id values for selected
   * rows. In deck-mode the tray rows carry data-slide-id which is the deck
   * section synthetic key (deck-section-{idx}). The server endpoint uses the
   * deck_path and these ids to locate the correct raw <section> spans on disk.
   */
  function getSelectedSlideIds() {
    if (!listEl) return [];
    const ids = [];
    listEl.querySelectorAll('.tray-row').forEach(row => {
      if (selected.has(row.dataset.uid) && row.dataset.slideId) {
        ids.push(row.dataset.slideId);
      }
    });
    return ids;
  }

  // Attach click listeners onto a newly rendered tray row (called after tray render).
  function attachRow(liEl) {
    if (!liEl || liEl.dataset.exportCbAttached) return;
    liEl.dataset.exportCbAttached = '1';

    // Create a checkbox overlay for explicit selection
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.className = 'export-cb';
    cb.setAttribute('aria-label', 'Select slide for export');
    cb.addEventListener('change', (e) => {
      e.stopPropagation();
      const uid = liEl.dataset.uid;
      if (uid) {
        if (e.target.checked) selected.add(uid);
        else selected.delete(uid);
        syncRow(liEl);
        _notify();
      }
    });
    // Insert before grip (first child)
    liEl.insertBefore(cb, liEl.firstChild);
  }

  // Observe new tray rows being added so we can wire checkboxes on them.
  let observer = null;

  function enable() {
    enabled = true;
    if (!listEl) return;

    // Wire existing rows
    listEl.querySelectorAll('.tray-row').forEach(row => {
      attachRow(row);
    });
    syncAll();

    // Observe future rows (tray re-renders innerHTML)
    if (!observer) {
      observer = new MutationObserver(() => {
        if (!enabled) return;
        listEl.querySelectorAll('.tray-row').forEach(row => {
          attachRow(row);
        });
        // Keep selection visual state consistent after re-render
        syncAll();
      });
      observer.observe(listEl, { childList: true, subtree: false });
    }
  }

  function disable() {
    enabled = false;
    clearAll();
    if (observer) {
      observer.disconnect();
      observer = null;
    }
    // Remove checkboxes from rows
    if (listEl) {
      listEl.querySelectorAll('.export-cb').forEach(cb => cb.remove());
      listEl.querySelectorAll('.tray-row').forEach(row => {
        delete row.dataset.exportCbAttached;
      });
    }
  }

  return { toggle, selectAll, clearAll, getSelectedUids, getSelectedSlideIds, enable, disable, syncRow };
}
