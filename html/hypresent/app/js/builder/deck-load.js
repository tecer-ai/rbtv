// deck-load.js — pick file + load deck

export async function pickAndLoadDeck() {
  const dialogRes = await fetch('/api/dialog-open-path', { method: 'POST' });
  const dialogData = await dialogRes.json();
  if (dialogData.cancelled) {
    return null;
  }
  return loadDeckByPath(dialogData.path);
}

export async function loadDeckByPath(path) {
  const res = await fetch('/api/deck-load', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  const envelope = await res.json();
  if (envelope.ok !== true) {
    return { ok: false, error: envelope.error || 'Deck load failed' };
  }
  return {
    ok: true,
    path,
    name: envelope.name,
    dir: envelope.dir,
    head: envelope.head,
    sections: envelope.sections
  };
}
