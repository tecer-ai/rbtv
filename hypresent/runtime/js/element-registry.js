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

// --- State ---

let nextId = 1;
const idToEl = new Map();
const elToId = new WeakMap();
const originalState = new WeakMap();

// --- Helpers ---

function isExplicitlyDecorative(el) {
  return el.getAttribute('data-hyp-decorative') === 'true';
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
 * Strip all data-hyp-id attributes from a cloned tree.
 * Does not mutate the live DOM.
 */
export function stripIds(clone) {
  const walker = document.createTreeWalker(clone, NodeFilter.SHOW_ELEMENT);
  while (walker.nextNode()) {
    walker.currentNode.removeAttribute('data-hyp-id');
  }
}
