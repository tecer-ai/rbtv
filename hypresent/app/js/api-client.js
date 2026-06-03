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
