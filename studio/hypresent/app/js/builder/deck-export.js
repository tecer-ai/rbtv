// deck-export.js — Export-to-library action: POST to /api/deck-export.
// Mirrors deck-save.js fetch idiom. Sends deck_path + selected_ids + library_path.
// The SERVER reads the raw on-disk deck source (data-hyp-* intact) — we never
// serialize the open deck DOM.

/**
 * exportDeckSlides — POST selected slide ids + deck path + target library path
 * to the export endpoint.
 *
 * @param {object} opts
 * @param {string}   opts.deckPath      – absolute path to the deck file on disk
 * @param {string[]} opts.selectedIds   – the data-hyp-slide-id values to export
 *                                        (as populated in state.selection by deck-select.js)
 * @param {string}   opts.libraryPath   – absolute path to the target library folder
 * @returns {Promise<object>} – { ok, exported, fragments, manifest_rows,
 *                                concerns, assets_skipped } on success;
 *                              { ok: true, message } on empty selection (server-side);
 *                              throws on network/server error.
 */
export async function exportDeckSlides({ deckPath, selectedIds, libraryPath }) {
  if (!deckPath) {
    throw new Error('No deck path — cannot export.');
  }
  if (!libraryPath) {
    throw new Error('No target library path — cannot export.');
  }
  if (!selectedIds || selectedIds.length === 0) {
    // Empty-selection guard: caller should catch this before calling, but we
    // handle it defensively here too.
    throw new Error('No slides selected.');
  }

  const body = {
    deck_path: deckPath,
    selected_ids: selectedIds,
    library_path: libraryPath,
  };

  const resp = await fetch('/api/deck-export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await resp.json();

  if (!resp.ok) {
    throw new Error(data.error || `Export failed (HTTP ${resp.status}).`);
  }

  return data;
}
