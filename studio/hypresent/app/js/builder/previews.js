// previews.js — IntersectionObserver-gated srcdoc slide previews

const MOUNT_CAP = 24;

// caches are keyed by library path + theme so "Change library" or "Change
// theme" never serves stale assets
const themePromises = new Map();   // `${libraryPath}|${theme}` -> Promise<string>
const srcdocPromises = new Map();  // `${libraryPath}|${theme}|${slideId}` -> Promise<string>

function fetchAsset(libraryPath, name) {
  return fetch('/api/library-asset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: libraryPath, name })
  })
    .then(r => {
      if (!r.ok) throw new Error(name + ' fetch failed: ' + r.status);
      return r.json();
    })
    .then(data => data.content || '');
}

// Resolves to the ORDERED css layers for the active preview theme:
//   'default'  -> [ theme.css ]                     (base only)
//   named      -> [ theme.css, themes/{name}.css ]  (base THEN the named overlay)
// A named theme is pure skin BY DESIGN (convention-spec §6.7: role :root tokens
// only, NO structural selectors), so it MUST layer on top of the base theme.css
// that carries the layout — exactly as an assembled deck layers base.html's
// inlined theme.css + the separate <style data-theme> overlay. Injecting the
// overlay alone strips all layout and blanks every slide.
function fetchTheme(libraryPath) {
  const key = libraryPath + '|' + _previewTheme;
  if (themePromises.has(key)) return themePromises.get(key);
  const p = _previewTheme === 'default'
    ? fetchAsset(libraryPath, 'theme.css').then(base => [base])
    : Promise.all([
        fetchAsset(libraryPath, 'theme.css'),
        fetchAsset(libraryPath, 'themes/' + _previewTheme + '.css'),
      ]);
  themePromises.set(key, p);
  return p;
}

// _docBase/_libraryBase: URLs that srcdoc iframes use as their <base href> so
// relative assets/* refs resolve against the loaded deck or library root instead
// of the builder page's own /app/ origin.
const _docBase = window.location.origin + '/doc/';
let _libraryBase = window.location.origin + '/lib/';
let _previewTheme = 'default';

export function setLibraryBase(base) {
  _libraryBase = base || (window.location.origin + '/lib/');
}

export function setPreviewTheme(name) {
  _previewTheme = name || 'default';
}

// `theme` is either a single css string or an ordered array of css layers.
// Each layer becomes its own <style> block, in order, so a base + named overlay
// cascade exactly like an assembled deck's inlined base + <style data-theme>.
export function buildSrcdoc(theme, fragment) {
  const layers = Array.isArray(theme) ? theme : [theme];
  const styles = layers.map(css => `<style>${css}</style>`).join('');
  return `<!DOCTYPE html><html><head><base href="${_libraryBase}">${styles}</head><body>${fragment}</body></html>`;
}

export function buildDeckSrcdoc(head, fragment) {
  return `<!DOCTYPE html><html><head><base href="${_docBase}">${head}</head><body>${fragment}</body></html>`;
}

// Cached full srcdoc for one slide — shared by browse previews and tray thumbnails.
export function getSlideSrcdoc(libraryPath, slideId) {
  const key = libraryPath + '|' + _previewTheme + '|' + slideId;
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
