/**
 * runtime/js/text-edit.js
 *
 * contenteditable lifecycle: double-click a text-editable registered element
 * to enter edit mode; on blur/Esc capture before+after HTML, build a text
 * command via commands.js, and history.push it; then exit edit mode.
 *
 * Public contract (module-map 03 §4):
 *   Self-activates on import. No external API.
 *
 * Hard invariants:
 *   - Only toggles contenteditable on the targeted element.
 *   - Never mutates document-native classes/ids/attributes.
 *   - All edits go through commands + history for undo/redo.
 *   - Coexists with the document's own JS (no preventDefault/stopPropagation).
 */

import { byId, idOf } from "./element-registry.js";
import { text } from "./commands.js";
import { push } from "./history.js";
import { suspend as suspendInteraction, resume as resumeInteraction } from "./interaction.js";
import { clearFontState } from "./text-format.js";
import { emit } from "./bridge-iframe.js";

// --- Constants ---

const EXCLUDED_TAGS = new Set([
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

const INLINE_TAGS = new Set([
  "a", "abbr", "b", "bdi", "bdo", "cite", "code", "data", "dfn", "em",
  "i", "kbd", "mark", "q", "rp", "rt", "ruby", "s", "samp", "small",
  "span", "strong", "sub", "sup", "time", "u", "var", "wbr", "font",
  "strike", "ins", "del", "big"
]);

// --- State ---

let activeHypId = null;
let beforeHtml = null;
let priorContenteditable = null;

// --- Helpers ---

function isInsideSvg(el) {
  let p = el.parentElement;
  while (p) {
    if (p.tagName.toLowerCase() === "svg") return true;
    p = p.parentElement;
  }
  return false;
}

function canEditText(el) {
  const tag = el.tagName.toLowerCase();

  // SVG root and descendants are never text-editable
  if (tag === "svg") return false;
  if (isInsideSvg(el)) return false;

  // H4 opt-out
  if (el.getAttribute("data-hyp-text") === "false") return false;

  // H4 opt-in forces editability (skip structural leaf test)
  if (el.getAttribute("data-hyp-text") === "true") {
    if (EXCLUDED_TAGS.has(tag)) return false;
    return true;
  }

  // Structural leaf/inline-only children test
  if (EXCLUDED_TAGS.has(tag)) return false;

  for (const child of el.children) {
    if (!INLINE_TAGS.has(child.tagName.toLowerCase())) {
      return false;
    }
  }

  return el.textContent.trim().length > 0;
}

// --- Lifecycle ---

function enterEdit(hypId) {
  if (activeHypId === hypId) return;
  if (activeHypId) {
    commit();
  }

  const el = byId(hypId);
  if (!el) return;
  if (!canEditText(el)) return;

  activeHypId = hypId;
  beforeHtml = el.innerHTML;
  priorContenteditable = el.hasAttribute("contenteditable")
    ? el.getAttribute("contenteditable")
    : null;

  el.setAttribute("contenteditable", "true");
  el.focus();
  suspendInteraction();
  emit("edit-state", { editing: true, hypId });

  // One-shot blur listener; guarded by activeHypId so manual commit is safe
  el.addEventListener("blur", onBlur, { once: true });
}

function onBlur(event) {
  const el = event.target;
  const hypId = idOf(el);
  if (hypId && hypId === activeHypId) {
    commit();
  }
}

function commit() {
  if (!activeHypId) return;

  const el = byId(activeHypId);
  if (el) {
    const afterHtml = el.innerHTML;
    if (afterHtml !== beforeHtml) {
      const cmd = text(activeHypId, beforeHtml, afterHtml);
      push(cmd);
    }

    if (priorContenteditable === null) {
      el.removeAttribute("contenteditable");
    } else {
      el.setAttribute("contenteditable", priorContenteditable);
    }
  }

  activeHypId = null;
  beforeHtml = null;
  priorContenteditable = null;
  resumeInteraction();
  clearFontState();
  emit("edit-state", { editing: false });
}

// --- Event listeners ---

document.addEventListener("dblclick", (event) => {
  // Coexist with document JS: do not prevent default or stop propagation
  let node = event.target;

  // Start from element if target is a text node
  if (node.nodeType === Node.TEXT_NODE) {
    node = node.parentElement;
  }

  // Ignore clicks on injected hyp- artifacts
  if (node && node.nodeType === Node.ELEMENT_NODE) {
    if (node.matches('[class^="hyp-"], [class*=" hyp-"]')) {
      return;
    }
    const nearestHyp = node.closest('[class^="hyp-"], [class*=" hyp-"]');
    if (nearestHyp) return;
  }

  // Walk up to the nearest registered element
  while (node && node.nodeType === Node.ELEMENT_NODE && node !== document.body) {
    const hypId = idOf(node);
    if (hypId) {
      enterEdit(hypId);
      return;
    }
    node = node.parentElement;
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && activeHypId) {
    commit();
  }
});
