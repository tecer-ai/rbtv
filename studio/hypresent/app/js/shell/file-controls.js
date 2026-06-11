import * as apiClient from '/app/js/api-client.js';
import { confirmSaveOverwrite } from '/app/js/shell/confirm-modal.js';

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
      getStatusSetter()('No document open.', 'error');
      return;
    }
    const serializeDoc = getSerializeDoc();
    if (!serializeDoc) return; // serializeDoc already set status on error

    const html = await serializeDoc();
    if (html == null) return; // serialization failed — status already set

    try {
      const docChip = document.getElementById('doc-chip');
      const docName = document.getElementById('doc-name');
      const hasOpenFile = !!(docChip && !docChip.hidden && docName && docName.textContent);
      let result;
      if (hasOpenFile) {
        const choice = await confirmSaveOverwrite(docName.textContent);
        if (choice === 'cancel') return;                  // stay in the editor
        if (choice === 'proceed') {
          result = await apiClient.save(html);            // overwrite the opened file
          if (result && result.no_open_file) result = await apiClient.dialogSaveAs(html);
        } else {
          result = await apiClient.dialogSaveAs(html);    // Save As — keep the original
        }
      } else {
        result = await apiClient.dialogSaveAs(html);      // never-saved deck → pick a path
      }
      if (result && result.cancelled) return;
      if (!result || !result.ok) {
        getStatusSetter()('Save failed.', 'error');
        return;
      }
      window.location.href = '/app/builder.html?file=' + encodeURIComponent(result.path);
    } catch (err) {
      getStatusSetter()('Save failed: ' + err.message, 'error');
    }
  });
}
