/**
 * runtime/js/element-registry.js
 *
 * Element detection + id tagging.
 * Detects editable elements from the live DOM (no class presupposition),
 * assigns additive data-hyp-id, records original state, resolves id↔node,
 * reports layout role + regions, and strips ids on demand.
 *
 * Public contract (module-map 03 §4):
 *   tag()
 *   byId(hypId) → Element|null
 *   idOf(el) → hypId|null
 *   roleOf(el) → 'flex-child'|'grid-child'|'absolute'|'block'
 *   regions() → [{hypId, label}]
 *   stripIds(clone)
 */

// --- Constants ---

const EXCLUDED_TAGS = new Set([
  'script', 'style', 'noscript', 'template', 'iframe', 'embed', 'object',
  'canvas', 'head', 'title', 'meta', 'link', 'base', 'source', 'track',
  'param', 'area', 'map'
]);

const SVG_GEOMETRY_TAGS = new Set([
  'path', 'circle', 'rect', 'line', 'polyline', 'polygon', 'ellipse',
  'text', 'textpath', 'tspan', 'defs', 'clippath', 'mask', 'g', 'use',
  'image', 'pattern', 'lineargradient', 'radialgradient', 'stop',
  'marker', 'symbol', 'feturbulence', 'fedisplacementmap', 'fecolormatrix'
]);

const SECTIONING_TAGS = new Set([
  'section', 'article', 'header', 'footer', 'main', 'aside', 'nav'
]);

// --- State ---

let nextId = 1;
const idToEl = new Map();
const elToId = new WeakMap();
const originalState = new WeakMap();

// --- Helpers ---

function isExplicitlyDecorative(el) {
  return el.getAttribute('data-hyp-decorative') === 'true';
}

function isDecorativeForRegions(el) {
  if (el.getAttribute('data-hyp-decorative') === 'true') return true;
  if (el.getAttribute('aria-hidden') === 'true') return true;
  return false;
}

function isInsideSvg(el) {
  let p = el.parentElement;
  while (p) {
    if (p.tagName.toLowerCase() === 'svg') return true;
    p = p.parentElement;
  }
  return false;
}

function shouldTag(el) {
  const tag = el.tagName.toLowerCase();
  if (tag === 'body') return false;
  if (EXCLUDED_TAGS.has(tag)) return false;
  if (tag === 'svg') return true;
  if (isInsideSvg(el)) return false;
  if (isExplicitlyDecorative(el)) return false;
  if (!document.body.contains(el)) return false;
  return true;
}

function countTextDescendants(el) {
  let count = 0;
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    if (walker.currentNode.textContent.trim().length > 0) {
      count++;
    }
  }
  return count;
}

function getSignature(el) {
  return `${el.tagName.toLowerCase()}|${el.className || ''}`;
}

function getRegionLabel(el) {
  const label = el.getAttribute('data-hyp-region');
  if (label) return label;
  const text = el.textContent.trim().replace(/\s+/g, ' ');
  if (text.length > 0) return text.slice(0, 60);
  return el.tagName.toLowerCase();
}

// --- Public API ---

/**
 * Walk the live DOM and assign data-hyp-id to all detected editable elements
 * that are not already tagged.
 */
export function tag() {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  while (walker.nextNode()) {
    const el = walker.currentNode;
    if (!shouldTag(el)) continue;
    if (elToId.has(el)) continue;

    let hypId;
    if (el.hasAttribute('data-hyp-id')) {
      // Adopt a pre-existing id (e.g. from a previous session) and bump
      // nextId past it so new ids never collide.
      hypId = el.getAttribute('data-hyp-id');
      const match = /^hyp-(\d+)$/.exec(hypId);
      if (match) {
        const num = parseInt(match[1], 10);
        if (num >= nextId) nextId = num + 1;
      }
    } else {
      hypId = `hyp-${nextId++}`;
      el.setAttribute('data-hyp-id', hypId);
    }

    idToEl.set(hypId, el);
    elToId.set(el, hypId);

    if (!originalState.has(el)) {
      originalState.set(el, {
        contenteditable: el.hasAttribute('contenteditable')
          ? el.getAttribute('contenteditable')
          : null
      });
    }
  }
}

/**
 * Resolve a hypId to the live Element.
 * Validates that the element is still in the DOM and still carries the id.
 */
export function byId(hypId) {
  const el = idToEl.get(hypId);
  if (el && document.body.contains(el) && elToId.get(el) === hypId) {
    return el;
  }
  if (el) idToEl.delete(hypId);
  return null;
}

/**
 * Resolve an Element to its hypId.
 */
export function idOf(el) {
  return elToId.get(el) || null;
}

/**
 * Determine the layout role of an element from computed styles.
 */
export function roleOf(el) {
  const style = getComputedStyle(el);
  if (style.position === 'absolute') {
    return 'absolute';
  }
  const parent = el.parentElement;
  if (!parent) {
    return 'block';
  }
  const parentDisplay = getComputedStyle(parent).display;
  if (parentDisplay === 'flex' || parentDisplay === 'inline-flex') {
    return 'flex-child';
  }
  if (parentDisplay === 'grid' || parentDisplay === 'inline-grid') {
    return 'grid-child';
  }
  return 'block';
}

/**
 * Return detected regions for the outline/navigator.
 * Honors H3 (data-hyp-region) when present; falls back to the §4 heuristic.
 */
export function regions() {
  // H3 hint priority
  const h3Els = Array.from(document.querySelectorAll('[data-hyp-region]'))
    .filter(el => document.body.contains(el) && !isDecorativeForRegions(el));
  if (h3Els.length > 0) {
    return h3Els
      .map(el => {
        const hypId = elToId.get(el);
        if (!hypId) return null;
        return { hypId, label: el.getAttribute('data-hyp-region') || '' };
      })
      .filter(Boolean);
  }

  // Heuristic fallback per 02 §4
  const bodyChildren = Array.from(document.body.children)
    .filter(c => {
      const t = c.tagName.toLowerCase();
      return t !== 'script' && t !== 'style' && t !== 'noscript';
    });

  // Candidate pool: body children + their immediate children
  const candidates = [];
  for (const child of bodyChildren) {
    candidates.push(child);
    for (const grandchild of child.children) {
      candidates.push(grandchild);
    }
  }

  let contentRoot = null;
  let maxTextCount = -1;
  for (const cand of candidates) {
    const count = countTextDescendants(cand);
    if (count > maxTextCount) {
      maxTextCount = count;
      contentRoot = cand;
    }
  }

  if (!contentRoot) return [];

  const directChildren = Array.from(contentRoot.children)
    .filter(el => !isDecorativeForRegions(el));

  // Compute repeated-sibling signatures
  const sigCounts = new Map();
  for (const child of directChildren) {
    const sig = getSignature(child);
    sigCounts.set(sig, (sigCounts.get(sig) || 0) + 1);
  }

  const result = [];
  for (const child of directChildren) {
    const tag = child.tagName.toLowerCase();
    const sig = getSignature(child);
    const isRepeated = sigCounts.get(sig) > 1;
    const isSectioning = SECTIONING_TAGS.has(tag);

    if (isSectioning || isRepeated) {
      const hypId = elToId.get(child);
      if (hypId) {
        result.push({ hypId, label: getRegionLabel(child) });
      }
    }
  }

  return result;
}

/**
 * Strip all data-hyp-id attributes from a cloned tree.
 * Does not mutate the live DOM.
 */
export function stripIds(clone) {
  const walker = document.createTreeWalker(clone, NodeFilter.SHOW_ELEMENT);
  while (walker.nextNode()) {
    walker.currentNode.removeAttribute('data-hyp-id');
  }
}
