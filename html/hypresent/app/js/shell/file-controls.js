import * as apiClient from '/app/js/api-client.js';

function loadIntoIframe(name, iframe) {
  return new Promise((resolve) => {
    const onLoad = () => {
      const doc = iframe.contentDocument;
      if (!doc) { resolve(); return; }
      const existing = doc.querySelector('script[src="/runtime/js/runtime-main.js"]');
      if (!existing) {
        const script = doc.createElement('script');
        script.type = 'module';
        script.src = '/runtime/js/runtime-main.js';
        (doc.head || doc.documentElement).appendChild(script);
      }
      resolve();
    };
    iframe.addEventListener('load', onLoad, { once: true });
    iframe.src = '/doc/' + encodeURIComponent(name);
  });
}

export async function openFile(path, iframe) {
  const result = await apiClient.open(path);
  await loadIntoIframe(result.name, iframe);
}

export async function openViaDialog(iframe) {
  const result = await apiClient.dialogOpen();
  if (result && result.cancelled) return null;   // user cancelled: no-op
  await loadIntoIframe(result.name, iframe);
  return result; // {html,dir,name}
}
