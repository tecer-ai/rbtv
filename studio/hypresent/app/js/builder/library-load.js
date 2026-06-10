// library-load.js — pick folder + load catalog

export async function pickAndLoadLibrary() {
  const dialogRes = await fetch('/api/dialog-folder', { method: 'POST' });
  const dialogData = await dialogRes.json();
  if (dialogData.cancelled) {
    return null;
  }
  return loadLibraryByPath(dialogData.path);
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
