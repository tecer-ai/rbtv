// previews.js — IntersectionObserver-gated srcdoc slide previews

const MOUNT_CAP = 24;

let themeCache = null;
let themePromise = null;

function fetchTheme(libraryPath) {
  if (themeCache) return Promise.resolve(themeCache);
  if (themePromise) return themePromise;
  themePromise = fetch('/api/library-asset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: libraryPath, name: 'theme.css' })
  })
    .then(r => {
      if (!r.ok) throw new Error('theme.css fetch failed: ' + r.status);
      return r.json();
    })
    .then(data => {
      themeCache = data.content || '';
      return themeCache;
    });
  return themePromise;
}

export function buildSrcdoc(theme, fragment) {
  return `<!DOCTYPE html><html><head><style>${theme}</style></head><body>${fragment}</body></html>`;
}

export function initPreviews(libraryPath, container) {
  const mounted = new Map(); // iframe -> { lastUsed }
  const intersecting = new Set();

  function isInViewport(iframe) {
    const rect = iframe.getBoundingClientRect();
    return (
      rect.top < window.innerHeight &&
      rect.bottom > 0 &&
      rect.left < window.innerWidth &&
      rect.right > 0
    );
  }

  function evictIfNeeded() {
    if (mounted.size < MOUNT_CAP) return;

    const now = performance.now();

    // Candidates: mounted iframes that are NOT intersecting
    const candidates = [];
    for (const [iframe] of mounted) {
      if (!intersecting.has(iframe) && !isInViewport(iframe)) {
        candidates.push(iframe);
      }
    }

    if (candidates.length === 0) {
      // All mounted iframes are in-view; raise cap transiently
      return;
    }

    // Evict LRU among non-intersecting candidates
    let lruIframe = null;
    let lruTime = Infinity;
    for (const iframe of candidates) {
      const meta = mounted.get(iframe);
      if (meta && meta.lastUsed < lruTime) {
        lruTime = meta.lastUsed;
        lruIframe = iframe;
      }
    }

    if (lruIframe) {
      lruIframe.srcdoc = '';
      delete lruIframe.dataset.mounted;
      mounted.delete(lruIframe);
      intersecting.delete(lruIframe);
    }
  }

  function mountIframe(iframe, theme) {
    const id = iframe.dataset.slideId;
    if (!id || iframe.dataset.mounted) return;

    evictIfNeeded();

    fetch('/api/library-asset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: libraryPath, name: 'slides/' + id + '.html' })
    })
      .then(r => {
        if (!r.ok) throw new Error('slide fetch failed: ' + r.status);
        return r.json();
      })
      .then(data => {
        const fragment = data.content || '';
        iframe.srcdoc = buildSrcdoc(theme, fragment);
        iframe.dataset.mounted = 'true';
        const now = performance.now();
        mounted.set(iframe, { lastUsed: now });
        if (isInViewport(iframe)) {
          intersecting.add(iframe);
        }
      })
      .catch(() => {
        // Silently fail; iframe remains unmounted
      });
  }

  const observer = new IntersectionObserver((entries) => {
    const now = performance.now();
    for (const entry of entries) {
      const iframe = entry.target;
      if (entry.isIntersecting) {
        intersecting.add(iframe);
        if (mounted.has(iframe)) {
          mounted.get(iframe).lastUsed = now;
        } else {
          fetchTheme(libraryPath).then(theme => mountIframe(iframe, theme));
        }
      } else {
        intersecting.delete(iframe);
      }
    }
  }, { root: container, rootMargin: '200px' });

  return { observer, mounted, intersecting };
}

export function mountPreviews(libraryPath, container) {
  const { observer } = initPreviews(libraryPath, container);
  const iframes = container.querySelectorAll('.slide-thumb-wrapper iframe[data-slide-id]');
  iframes.forEach(iframe => observer.observe(iframe));
}
