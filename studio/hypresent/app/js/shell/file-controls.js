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
  return result; // {html,dir,name}
}

export async function openViaDialog(iframe) {
  const result = await apiClient.dialogOpen();
  if (result && result.cancelled) return null;   // user cancelled: no-op
  await loadIntoIframe(result.name, iframe);
  return result; // {html,dir,name}
}

/**
 * Set up the "Open in builder" button. Caller provides serializeDoc() and setStatus().
 * The button is disabled when no document is open (bridge is null / no doc chip).
 */
export function setupOpenInBuilder({ getSerializeDoc, getStatusSetter, getBridge }) {
  const btn = document.getElementById('open-in-builder-btn');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    const bridge = getBridge();
    if (!bridge) {
      setStatusSetter()('No document open.', 'error');
      return;
    }
    const serializeDoc = getSerializeDoc();
    if (!serializeDoc) return; // serializeDoc already set status on error

    const html = await serializeDoc();
    if (html == null) return; // serialization failed — status already set

    try {
      const result = await apiClient.dialogSaveAs(html);
      if (result && result.cancelled) return; // user cancelled — stay put
      if (!result || !result.ok) {
        setStatusSetter()('Save failed.', 'error');
        return;
      }
      // Save succeeded — navigate to builder with ?file= handoff
      window.location.href = '/app/builder.html?file=' + encodeURIComponent(result.path);
    } catch (err) {
      setStatusSetter()('Save failed: ' + err.message, 'error');
    }
  });
}
