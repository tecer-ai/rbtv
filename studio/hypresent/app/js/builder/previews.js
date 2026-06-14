// previews.js — IntersectionObserver-gated srcdoc slide previews

const MOUNT_CAP = 24;

// caches are keyed by library path so "Change library" never serves stale assets
const themePromises = new Map();   // libraryPath -> Promise<string>
const srcdocPromises = new Map();  // `${libraryPath}|${slideId}` -> Promise<string>

function fetchTheme(libraryPath) {
  if (themePromises.has(libraryPath)) return themePromises.get(libraryPath);
  const p = fetch('/api/library-asset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: libraryPath, name: 'theme.css' })
  })
    .then(r => {
      if (!r.ok) throw new Error('theme.css fetch failed: ' + r.status);
      return r.json();
    })
    .then(data => data.content || '');
  themePromises.set(libraryPath, p);
  return p;
}

// _docBase/_libraryBase: URLs that srcdoc iframes use as their <base href> so
// relative assets/* refs resolve against the loaded deck or library root instead
// of the builder page's own /app/ origin.
const _docBase = window.location.origin + '/doc/';
let _libraryBase = window.location.origin + '/lib/';

export function setLibraryBase(base) {
  _libraryBase = base || (window.location.origin + '/lib/');
}

export function buildSrcdoc(theme, fragment) {
  return `<!DOCTYPE html><html><head><base href="${_libraryBase}"><style>${theme}</style></head><body>${fragment}</body></html>`;
}

export function buildDeckSrcdoc(head, fragment) {
  return `<!DOCTYPE html><html><head><base href="${_docBase}">${head}</head><body>${fragment}</body></html>`;
}

// Cached full srcdoc for one slide — shared by browse previews and tray thumbnails.
export function getSlideSrcdoc(libraryPath, slideId) {
  const key = libraryPath + '|' + slideId;
  if (srcdocPromises.has(key)) return srcdocPromises.get(key);
  const p = Promise.all([
    fetchTheme(libraryPath),
    fetch('/api/library-asset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: libraryPath, name: 'slides/' + slideId + '.html' })
    }).then(r => {
      if (!r.ok) throw new Error('slide fetch failed: ' + r.status);
      return r.json();
    })
  ]).then(([theme, data]) => buildSrcdoc(theme, data.content || ''));
  srcdocPromises.set(key, p);
  return p;
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

  function mountIframe(iframe) {
    const id = iframe.dataset.slideId;
    if (!id || iframe.dataset.mounted) return;

    evictIfNeeded();

    getSlideSrcdoc(libraryPath, id)
      .then(srcdoc => {
        // Re-enforce the cap at registration: a fast scroll can start many
        // fetches before any registers, so the entry gate alone is not enough.
        evictIfNeeded();
        iframe.srcdoc = srcdoc;
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
          mountIframe(iframe);
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
