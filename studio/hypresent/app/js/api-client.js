export async function open(path) {
  const response = await fetch('/api/open', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }

  return data;
}

export async function saveAs(path, html) {
  const response = await fetch('/api/save-as', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, html }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }

  return data;
}

export async function dialogOpen() {
  const response = await fetch('/api/dialog-open', { method: 'POST' });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data; // {html,dir,name} | {cancelled:true}
}

export async function dialogSaveAs(html) {
  const response = await fetch('/api/dialog-save-as', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ html }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data; // {ok,path} | {cancelled:true}
}

export async function save(html) {
  const response = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ html }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data; // {ok,path} | {no_open_file:true}
}

export async function resolveLibrary(deck_path, library_ref) {
  const response = await fetch('/api/resolve-library', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ deck_path, library_ref }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

export async function libraryAsset(path, name) {
  const response = await fetch('/api/library-asset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, name }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

export async function copyThemeAssets(deck_path, library_path, theme_name) {
  const response = await fetch('/api/copy-theme-assets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ deck_path, library_path, theme_name }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}
