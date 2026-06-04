/**
 * runtime/js/text-format.js
 *
 * Inline formatting: bold/italic/font-size via execCommand + Selection API.
 * Operates only within an active contenteditable text edit.
 *
 * Public contract (module-map 03 §4):
 *   apply(op) where op ∈ {bold, italic, fontInc, fontDec}
 *
 * Hard invariants:
 *   - Only applies when there is an active contenteditable element.
 *   - Never mutates document-native classes/ids/attributes.
 *   - All changes go through commands.format + history.push for undo/redo.
 */

import { idOf } from "./element-registry.js";
import { format } from "./commands.js";
import { push } from "./history.js";

// --- R8 state: selection survival across the toolbar-click focus cycle ---
// The toolbar button's mousedown does preventDefault + iframe focus(), which
// collapses the iframe Selection to the editable root. We snapshot the live
// range on that mousedown (via the format-snapshot bridge command) and restore
// it on the next apply().
//
// We do NOT hold a live reference to the tracked font-size span: history.push
// runs the format command's `el.innerHTML = afterHtml`, which re-serialises the
// subtree and DETACHES any held node every press (RV?? — proven live in v3-t4).
// Instead the tracked span is marked with FONT_SPAN_MARKER and re-found by
// querySelector each press, so it survives the innerHTML round-trip. The marker
// is a data-hyp-* attribute, so serializer.js strips it from saved output.
let savedRange = null;
const FONT_SPAN_MARKER = "data-hyp-fontspan";

// --- Helpers ---

function activeEditable() {
  const a = document.activeElement;
  return a && a.getAttribute && a.getAttribute("contenteditable") === "true" ? a : null;
}

/** Snapshot the live selection range BEFORE the toolbar focus shift (R8). */
export function snapshotSelection() {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return;
  const r = sel.getRangeAt(0);
  const ed = activeEditable();
  if (ed && ed.contains(r.commonAncestorContainer)) {
    savedRange = r.cloneRange();
  }
}

/**
 * SNAPSHOT-ALWAYS-WINS validity (R8): the snapshot is usable iff its endpoints are
 * still in the live DOM (isConnected) AND its commonAncestorContainer is inside the
 * given active editable. This is the ONLY gate on restoring the snapshot — there is
 * deliberately NO check on the live selection's collapse state (that was brittle:
 * Chromium collapses to the first TEXT NODE after focus(), so an identity check on
 * the editable element never matched — RV04). When valid, the snapshot ALWAYS wins.
 */
function snapshotIsValid(el) {
  if (!savedRange) return false;
  if (!savedRange.startContainer.isConnected || !savedRange.endContainer.isConnected) return false;
  return el.contains(savedRange.commonAncestorContainer);
}

/** Clear R8 font state (called on edit commit so a new edit starts clean). */
export function clearFontState() {
  savedRange = null;
  // Strip the tracked-span marker so a fresh edit starts with no tracked span.
  // The marker is set only by this module, so a document-wide strip is safe.
  document
    .querySelectorAll(`span[${FONT_SPAN_MARKER}]`)
    .forEach((s) => s.removeAttribute(FONT_SPAN_MARKER));
}

function getActiveEditElement() {
  const active = document.activeElement;
  if (!active) return null;
  if (active.getAttribute("contenteditable") !== "true") return null;
  const hypId = idOf(active);
  return hypId ? active : null;
}

function expandToWord(range) {
  if (!range.collapsed) return range;
  const node = range.startContainer;
  if (node.nodeType !== Node.TEXT_NODE) return range;
  const text = node.textContent;
  const offset = range.startOffset;
  let start = offset;
  let end = offset;
  while (start > 0 && /\S/.test(text[start - 1])) start--;
  while (end < text.length && /\S/.test(text[end])) end++;
  if (end > start) {
    const r = document.createRange();
    r.setStart(node, start);
    r.setEnd(node, end);
    return r;
  }
  return range;
}

/** Find this editor's currently-tracked font-size span inside `el` (re-found each
 *  call so it survives the history `innerHTML = afterHtml` round-trip). */
function trackedFontSpan(el) {
  return el.querySelector(`span[${FONT_SPAN_MARKER}]`);
}

/** Mark `span` as the single tracked font-size span; clear the marker from any
 *  other span in `el` (single-marker invariant). */
function setTrackedFontSpan(el, span) {
  el.querySelectorAll(`span[${FONT_SPAN_MARKER}]`).forEach((s) => {
    if (s !== span) s.removeAttribute(FONT_SPAN_MARKER);
  });
  if (span) span.setAttribute(FONT_SPAN_MARKER, "");
}

function adjustFontSize(el, delta) {
  const sel = window.getSelection();

  // (R8 step 1) SNAPSHOT-ALWAYS-WINS: if a VALID mousedown snapshot exists, restore
  // it. The post-toolbar-click live selection is focus-shift garbage by construction.
  if (snapshotIsValid(el)) {
    sel.removeAllRanges();
    sel.addRange(savedRange.cloneRange());
  }

  // (R8 step 2 — v3) Word-expand the candidate range FIRST, then decide usability by
  // COLLAPSE (not rangeCount). A collapsed range whose container is the editable root
  // (the post-press-1 focus-collapse, or a collapsed snapshot) is NOT usable for
  // formatting — both the live selection AND a restored collapsed snapshot land here.
  let range = sel && sel.rangeCount > 0 ? sel.getRangeAt(0).cloneRange() : null;
  if (range) range = expandToWord(range);

  // No range, or still collapsed after word-expansion → repeat path: re-find the
  // marked span and bump it. Race-free: independent of snapshot timing/identity.
  if (!range || range.collapsed) {
    const span = trackedFontSpan(el);
    if (span) {
      const cur = parseFloat(span.style.fontSize);
      span.style.fontSize = `${Math.max(8, Math.round(cur + delta))}px`;
    }
    savedRange = null; // consume the snapshot
    return;
  }

  // A real (non-collapsed) word range: commit it to the live selection.
  sel.removeAllRanges();
  sel.addRange(range);
  range = sel.getRangeAt(0);

  // Walk up to an existing font-size span and grow it instead of nesting a new one.
  let container = range.commonAncestorContainer;
  if (container.nodeType === Node.TEXT_NODE) {
    container = container.parentElement;
  }
  while (container && container !== el) {
    if (
      container.tagName.toLowerCase() === "span" &&
      container.style.fontSize
    ) {
      const currentSize = parseFloat(container.style.fontSize);
      container.style.fontSize = `${Math.max(8, Math.round(currentSize + delta))}px`;
      setTrackedFontSpan(el, container); // move the single marker here
      savedRange = null;                 // consume the snapshot
      return;
    }
    container = container.parentElement;
  }

  // Create a new span for this (new) word, sized from the selection start.
  let refNode = range.startContainer;
  if (refNode.nodeType === Node.TEXT_NODE) refNode = refNode.parentElement;
  const computedSize = parseFloat(window.getComputedStyle(refNode).fontSize);
  const newSize = Math.max(8, Math.round(computedSize + delta));

  const span = document.createElement("span");
  span.style.fontSize = `${newSize}px`;

  try {
    range.surroundContents(span);
  } catch (_e) {
    span.appendChild(range.extractContents());
    range.insertNode(span);
  }

  setTrackedFontSpan(el, span); // this new span is now the single tracked span
  savedRange = null;            // consume the snapshot

  // Reselect the wrapped content so subsequent ops apply cleanly.
  sel.removeAllRanges();
  const newRange = document.createRange();
  newRange.selectNodeContents(span);
  sel.addRange(newRange);
}

// --- Public API ---

/**
 * Apply a formatting operation.
 * @param {'bold'|'italic'|'fontInc'|'fontDec'} op
 * @returns {boolean} true if applied, false if no active edit
 */
export function apply(op) {
  const el = getActiveEditElement();
  if (!el) return false;

  const hypId = idOf(el);
  const beforeHtml = el.innerHTML;

  // Ensure focus for execCommand
  el.focus();

  switch (op) {
    case "bold":
      document.execCommand("bold", false, null);
      break;
    case "italic":
      document.execCommand("italic", false, null);
      break;
    case "fontInc":
      adjustFontSize(el, +2);
      break;
    case "fontDec":
      adjustFontSize(el, -2);
      break;
    default:
      return false;
  }

  const afterHtml = el.innerHTML;
  if (afterHtml !== beforeHtml) {
    const cmd = format(hypId, beforeHtml, afterHtml);
    push(cmd);
  }

  return true;
}

// --- R7: text alignment (V3-S15..S17) ---
// Horizontal is always available (text-align). Vertical depends on display:
// flex/grid container, table-cell, or a fixed-height block. Plain auto-height
// block → vertical disabled (never silently convert to flex; U13).

function hasFixedHeight(el) {
  const inline = el.style.height || el.style.minHeight;
  if (inline && inline !== "auto" && parseFloat(inline) > 0) return true;
  const cs = getComputedStyle(el);
  return cs.minHeight !== "0px" && cs.minHeight !== "auto";
}

/** Capabilities + per-button CSS mapping for the selected element (V3-S17). */
export function computeAlignCaps(el) {
  if (!el) return { horizontal: false, vertical: false, hMap: null, vMap: null };
  const cs = getComputedStyle(el);
  const d = cs.display;
  const fd = cs.flexDirection || "row";
  const isFlex = d === "flex" || d === "inline-flex";
  const isGrid = d === "grid" || d === "inline-grid";
  const isCell = d === "table-cell";

  // Horizontal mapping
  let hMap;
  if (isFlex) {
    hMap = fd.startsWith("row")
      ? { prop: "justifyContent", left: "flex-start", center: "center", right: "flex-end" }
      : { prop: "alignItems", left: "flex-start", center: "center", right: "flex-end" };
  } else if (isGrid) {
    hMap = { prop: "justifyItems", left: "start", center: "center", right: "end" };
  } else {
    hMap = { prop: "textAlign", left: "left", center: "center", right: "right" };
  }

  // Vertical availability + mapping
  let vertical = false;
  let vMap = null;
  if (isFlex) {
    vertical = true;
    vMap = fd.startsWith("row")
      ? { prop: "alignItems", top: "flex-start", middle: "center", bottom: "flex-end" }
      : { prop: "justifyContent", top: "flex-start", middle: "center", bottom: "flex-end" };
  } else if (isGrid) {
    vertical = true;
    vMap = { prop: "alignItems", top: "start", middle: "center", bottom: "end" };
  } else if (isCell) {
    vertical = true;
    vMap = { prop: "verticalAlign", top: "top", middle: "middle", bottom: "bottom" };
  } else if (hasFixedHeight(el)) {
    vertical = true;
    // converts to a flex column (acceptable — the user already fixed the height)
    vMap = { prop: "__flexColumn", top: "flex-start", middle: "center", bottom: "flex-end" };
  }

  return { horizontal: true, vertical, hMap, vMap };
}

/** Apply an alignment (axis 'h'|'v', value left/center/right or top/middle/bottom). */
export function applyAlign(el, axis, value) {
  if (!el) return;
  const caps = computeAlignCaps(el);
  if (axis === "h") {
    const m = caps.hMap;
    if (!m) return;
    el.style[m.prop] = m[value];
    return;
  }
  // vertical
  if (!caps.vertical || !caps.vMap) return; // plain auto-height block → no-op (U13)
  const m = caps.vMap;
  if (m.prop === "__flexColumn") {
    el.style.display = "flex";
    el.style.flexDirection = "column";
    el.style.justifyContent = m[value];
    return;
  }
  el.style[m.prop] = m[value];
}
