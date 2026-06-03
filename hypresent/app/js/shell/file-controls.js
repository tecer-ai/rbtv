import * as apiClient from '/app/js/api-client.js';

export async function openFile(path, iframe) {
  const result = await apiClient.open(path);
  const { name } = result;

  return new Promise((resolve, reject) => {
    const onLoad = () => {
      const doc = iframe.contentDocument;
      if (!doc) {
        resolve();
        return;
      }

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

export function initOpenControl(buttonEl, getPathFn, iframe) {
  buttonEl.addEventListener('click', async () => {
    const path = getPathFn();
    if (!path) return;
    try {
      await openFile(path, iframe);
    } catch {
      // Caller is responsible for error display.
    }
  });
}
