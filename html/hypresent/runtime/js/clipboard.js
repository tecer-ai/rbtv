/**
 * runtime/js/clipboard.js
 *
 * Single in-memory clipboard slot for component copy/paste.
 * Last copy wins. Clones are fully stripped of all data-hyp-* attributes
 * so paste re-tags cleanly and carries no editor state.
 */

import { stripIds } from "./element-registry.js";

// --- State ---

let slot = null;

// --- Helpers ---

/**
 * Remove every attribute whose name starts with `data-hyp-` from an element.
 */
function stripHypAttributes(el) {
  const attrs = Array.from(el.attributes);
  for (const attr of attrs) {
    if (attr.name.startsWith("data-hyp-")) {
      el.removeAttribute(attr.name);
    }
  }
}

/**
 * Fully strip all data-hyp-* attributes from a cloned tree.
 * Calls stripIds first, then removes any remaining data-hyp-* markers.
 */
function stripAllHyp(clone) {
  stripIds(clone);
  stripHypAttributes(clone);
  for (const descendant of clone.querySelectorAll("*")) {
    stripHypAttributes(descendant);
  }
}

// --- Public API ---

/**
 * Store a deep clone of `el` into the clipboard slot.
 * The clone has all data-hyp-* attributes stripped.
 * wasRegion is true when the original element was a direct child of document.body.
 */
export function copy(el) {
  const clone = el.cloneNode(true);
  stripAllHyp(clone);
  slot = {
    node: clone,
    wasRegion: el.parentElement === document.body,
    cascade: 0,
  };
}

/**
 * Return the current clipboard slot, or null if empty.
 */
export function get() {
  return slot;
}

/**
 * Return true if the clipboard slot holds content.
 */
export function hasContent() {
  return slot !== null;
}

/**
 * Increment the cascade counter. No-op if the slot is empty.
 */
export function bumpCascade() {
  if (slot) {
    slot.cascade++;
  }
}
