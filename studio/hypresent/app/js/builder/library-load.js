// library-load.js — pick folder + load catalog

export async function pickAndLoadLibrary() {
  const dialogRes = await fetch('/api/dialog-folder', { method: 'POST' });
  const dialogData = await dialogRes.json();
  if (dialogData.cancelled) {
    return null;
  }
  return loadLibraryByPath(dialogData.path);
}

// pickLibraryFolderForExport — pick a folder as an EXPORT TARGET only.
//
// The Export-to-library "Choose…" picker needs the target folder PATH, validated
// against what the export pipeline (/api/deck-export) actually requires — a
// parseable library.json plus a "## Slides" manifest table to append rows to —
// NOT the full slide catalog. It therefore validates via /api/library-validate-target
// instead of loadLibraryByPath, which runs the target library's vendored engine
// (assemble.py --catalog-data) and wrongly rejects any valid target that does not
// vendor that engine binary. Same folder dialog; lightweight, export-correct check.
//
// Returns:
//   null                                  — user cancelled the dialog
//   { ok: true,  path }                   — valid export target
//   { ok: false, path, errors: [...] }    — folder is not a valid export target
// Throws only on a transport/server fault (non-200 from the validate endpoint).
export async function pickLibraryFolderForExport() {
  const dialogRes = await fetch('/api/dialog-folder', { method: 'POST' });
  const dialogData = await dialogRes.json();
  if (dialogData.cancelled) {
    return null;
  }
  const path = dialogData.path;
  const res = await fetch('/api/library-validate-target', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  const envelope = await res.json();
  if (envelope.ok === false) {
    return { ok: false, path, errors: envelope.errors || [] };
  }
  return { ok: true, path: envelope.path || path };
}

export async function loadLibraryByPath(path) {
  const res = await fetch('/api/library-load', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  const envelope = await res.json();
  if (envelope.ok === false) {
    return { ok: false, path, errors: envelope.errors };
  }
  return { ok: true, path, data: envelope.catalog_data, warnings: envelope.warnings };
}
