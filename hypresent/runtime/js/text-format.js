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

// --- Helpers ---

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

function adjustFontSize(el, delta) {
  const sel = window.getSelection();
  if (!sel.rangeCount) return;

  let range = sel.getRangeAt(0).cloneRange();
  range = expandToWord(range);

  const currentRange = sel.getRangeAt(0);
  if (currentRange.collapsed && range !== currentRange) {
    sel.removeAllRanges();
    sel.addRange(range);
  }

  range = sel.getRangeAt(0);

  // Walk up the ancestor chain to find an existing font-size span created
  // by this editor and update it instead of nesting a new one.
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
      const newSize = Math.max(8, Math.round(currentSize + delta));
      container.style.fontSize = `${newSize}px`;
      return;
    }
    container = container.parentElement;
  }

  // Compute reference size from the start of the selection
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

  // Reselect the wrapped content so subsequent ops apply cleanly
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
