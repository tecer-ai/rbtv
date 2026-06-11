/**
 * runtime/js/selection.js
 *
 * Selection state + visual ring.
 * Tracks the selected element; draws a hyp- classed selection ring;
 * clears on demand. Click-to-select a registered element without
 * swallowing the document's own click behavior.
 *
 * Public contract (module-map 03 §4):
 *   select(hypId)
 *   clear()
 *   current() → {hypId, role, rect, isText}
 *
 * Emits (via bridge-iframe.js):
 *   selection-changed {hypId, role, rect, isText}
 */

import { byId, idOf, roleOf } from "./element-registry.js";
import { emit } from "./bridge-iframe.js";
import { computeAlignCaps } from "./text-format.js";

// --- State ---

let selectedHypId = null;
let ringEl = null;

const selectionObservers = new Set();
export function onSelectionChange(cb) { selectionObservers.add(cb); return () => selectionObservers.delete(cb); }
function notifyObservers(info) { for (const cb of selectionObservers) { try { cb(info); } catch (_e) {} } }

// --- Helpers ---

function isInsideSvg(el) {
  let p = el.parentElement;
  while (p) {
    if (p.tagName.toLowerCase() === "svg") return true;
    p = p.parentElement;
  }
  return false;
}

function isTextEditable(el) {
  const tag = el.tagName.toLowerCase();

  // SVG root and SVG descendants are never text-editable
  if (tag === "svg") return false;
  if (isInsideSvg(el)) return false;

  // Hard-excluded tags (media, form, table, script, SVG geometry, etc.)
  const excluded = new Set([
    "script", "style", "noscript", "template", "iframe", "embed", "object",
    "canvas", "head", "title", "meta", "link", "base", "source", "track",
    "param", "area", "map", "img", "video", "audio", "picture", "br", "hr",
    "input", "textarea", "select", "button", "label", "fieldset", "legend",
    "progress", "meter", "details", "summary", "dialog", "menu",
    "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption",
    "colgroup", "col",
    "path", "circle", "rect", "line", "polyline", "polygon", "ellipse",
    "text", "textpath", "tspan", "defs", "clippath", "mask", "g", "use",
    "image", "pattern", "lineargradient", "radialgradient", "stop",
    "marker", "symbol"
  ]);
  if (excluded.has(tag)) return false;

  // Inline formatting tags that are allowed as children of a text node
  const inlineTags = new Set([
    "a", "abbr", "b", "bdi", "bdo", "cite", "code", "data", "dfn", "em",
    "i", "kbd", "mark", "q", "rp", "rt", "ruby", "s", "samp", "small",
    "span", "strong", "sub", "sup", "time", "u", "var", "wbr", "font",
    "strike", "ins", "del", "big", "svg"
  ]);

  for (const child of el.children) {
    if (!inlineTags.has(child.tagName.toLowerCase())) {
      return false;
    }
  }

  return el.textContent.trim().length > 0;
}

function domRectToPlain(rect) {
  return {
    x: rect.x,
    y: rect.y,
    width: rect.width,
    height: rect.height,
    top: rect.top,
    right: rect.right,
    bottom: rect.bottom,
    left: rect.left,
  };
}

function buildInfo(el) {
  const hypId = idOf(el);
  return {
    hypId,
    role: roleOf(el),
    rect: domRectToPlain(el.getBoundingClientRect()),
    isText: isTextEditable(el),
    alignCaps: computeAlignCaps(el),
  };
}

// --- Ring ---

function createRing() {
  const el = document.createElement("div");
  el.className = "hyp-selection-ring";
  el.style.position = "absolute";
  el.style.pointerEvents = "none";
  el.style.zIndex = "999999";
  el.style.boxSizing = "border-box";
  el.style.outline = "2px solid #0ea5e9";
  el.style.outlineOffset = "-2px";
  document.body.appendChild(el);
  return el;
}

function clearRing() {
  if (ringEl && ringEl.parentNode) {
    ringEl.parentNode.removeChild(ringEl);
  }
  ringEl = null;
}

function updateRing() {
  if (!ringEl || !selectedHypId) return;
  const el = byId(selectedHypId);
  if (!el) {
    clear();
    return;
  }
  const rect = el.getBoundingClientRect();
  const sx = window.scrollX || window.pageXOffset || 0;
  const sy = window.scrollY || window.pageYOffset || 0;
  ringEl.style.top = `${rect.top + sy}px`;
  ringEl.style.left = `${rect.left + sx}px`;
  ringEl.style.width = `${rect.width}px`;
  ringEl.style.height = `${rect.height}px`;
}

// --- Public API ---

export function select(hypId) {
  if (selectedHypId === hypId) {
    // Same selection — just refresh ring position in case DOM moved
    updateRing();
    return;
  }

  clearRing();

  const el = byId(hypId);
  if (!el) {
    selectedHypId = null;
    emit("selection-changed", null);
    notifyObservers(null);
    return;
  }

  selectedHypId = hypId;
  ringEl = createRing();
  updateRing();

  const info = buildInfo(el);
  emit("selection-changed", info);
  notifyObservers(info);
}

export function clear() {
  if (!selectedHypId) return;
  selectedHypId = null;
  clearRing();
  emit("selection-changed", null);
  notifyObservers(null);
}

export function current() {
  if (!selectedHypId) return null;
  const el = byId(selectedHypId);
  if (!el) {
    clear();
    return null;
  }
  return buildInfo(el);
}

// --- Click delegation ---
// Runs in the bubbling phase and NEVER prevents default or stops propagation,
// so the document's own click handlers continue to work.

document.addEventListener("click", (event) => {
  let node = event.target;

  // Skip clicks that land directly on injected hyp- artifacts
  if (node.nodeType === Node.ELEMENT_NODE) {
    if (
      node.matches('[class^="hyp-"], [class*=" hyp-"]')
    ) {
      return;
    }
    const nearestHyp = node.closest('[class^="hyp-"], [class*=" hyp-"]');
    if (nearestHyp) return;
  }

  // Walk up to the nearest registered element
  while (node && node.nodeType === Node.ELEMENT_NODE && node !== document.body) {
    const hypId = idOf(node);
    if (hypId) {
      select(hypId);
      return;
    }
    node = node.parentElement;
  }

  // Click on unregistered area — clear selection
  clear();
});

// --- Window scroll/resize — keep ring aligned ---

window.addEventListener("resize", updateRing);
window.addEventListener("scroll", updateRing, { passive: true });
