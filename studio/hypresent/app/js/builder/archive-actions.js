// archive-actions.js — server archive endpoint wrappers

export async function archiveSlide(libraryPath, slideId) {
  const r = await fetch('/api/archive', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: libraryPath, slide_id: slideId }),
  });
  if (!r.ok) return { ok: false, error: 'HTTP ' + r.status };
  return await r.json();
}

export async function unarchiveSlide(libraryPath, slideId) {
  const r = await fetch('/api/unarchive', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: libraryPath, slide_id: slideId }),
  });
  if (!r.ok) return { ok: false, error: 'HTTP ' + r.status };
  return await r.json();
}

export async function listArchived(libraryPath) {
  const r = await fetch('/api/archive-list', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: libraryPath }),
  });
  if (!r.ok) return { ok: false, error: 'HTTP ' + r.status };
  return await r.json();
}
