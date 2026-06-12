// deck-save.js — Save deck UI: new-file vs overwrite, POST to /api/deck-save.
// Calls tray.getItems() (from tray.js) and posts the result; does NOT modify tray.

export async function saveDeck({ deck, items, mode }) {
  // deck: { path, name } — the currently loaded deck
  // items: array from tray.getItems() — [{kind, index}, {kind, library_path, slide_id}, {kind: 'blank'}]
  // mode: 'new-file' | 'overwrite'

  if (!deck || !deck.path) {
    throw new Error('No deck loaded.');
  }
  if (!items || items.length === 0) {
    throw new Error('Tray is empty.');
  }

  let outPath;

  if (mode === 'new-file') {
    // Ask the server to launch a native save dialog; user picks the destination path.
    const dialogResp = await fetch('/api/dialog-save-path', { method: 'POST' });
    const dialogData = await dialogResp.json();
    if (!dialogResp.ok) {
      throw new Error(dialogData.error || 'Save dialog failed.');
    }
    if (dialogData.cancelled) {
      return { cancelled: true };
    }
    outPath = dialogData.path;
  } else if (mode === 'overwrite') {
    outPath = deck.path;
  } else {
    throw new Error(`Unknown save mode: ${mode}`);
  }

  // Gather the set of library paths referenced by library items.
  const libraries = {};
  items.forEach(item => {
    if (item.kind === 'library' && item.library_path) {
      libraries[item.library_path] = true;
    }
  });

  const body = {
    source_path: deck.path,
    out_path: outPath,
    items,
    libraries,
  };

  const resp = await fetch('/api/deck-save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await resp.json();

  if (!resp.ok) {
    throw new Error(data.error || 'Save failed.');
  }

  return {
    ok: true,
    path: data.path,
    assetsCopied: data.assets_copied || [],
    assetsSkipped: data.assets_skipped || [],
    assetsMissing: data.assets_missing || [],
  };
}
