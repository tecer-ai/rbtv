export async function pickDestination() {
  const res = await fetch('/api/dialog-folder', { method: 'POST' });
  const data = await res.json();
  if (data.cancelled) return null;
  return data.path || null;
}

export async function assembleDeck({ libraryPath, slides, outPath, lang, title, accent, client_logo, theme }) {
  const body = { path: libraryPath, slides, out: outPath };
  body.lang = lang;
  if (title !== undefined) body.title = title;
  if (accent !== undefined) body.accent = accent;
  if (client_logo !== undefined) body.client_logo = client_logo;
  if (theme !== undefined) body.theme = theme;

  const res = await fetch('/api/assemble', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const envelope = await res.json();
  return {
    ok: envelope.ok,
    output: envelope.output,
    assetsCopied: envelope.assets_copied,
    unfilledTokens: envelope.unfilled_tokens,
    asBuilt: envelope.as_built_entry,
    errors: envelope.errors
  };
}

export function buildOutPath(folder, filename) {
  const cleanFolder = folder.replace(/[\\/]+$/, '');
  const cleanName = filename.replace(/\.html$/i, '');
  return cleanFolder + '/' + cleanName + '.html';
}
