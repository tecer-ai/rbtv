/**
 * runtime/js/serializer.js
 *
 * Serializer: clone the live iframe document → strip ALL editor chrome by
 * namespace → restore original contenteditable state → re-embed comment JSON
 * island → node-count guard → emit standalone HTML string.
 *
 * Strip-only contract (A8/A11):
 *   • Remove every element whose id or any class token is "hyp-" prefixed.
 *   • Remove every data-hyp-* attribute from all surviving elements.
 *   • Remove every "hyp-" prefixed class token from class attributes.
 *   • Remove the injected edit-runtime <script type="module"> tag(s).
 *   • Remove editor-added contenteditable; best-effort restore original state.
 *   • Preserve the document's own <script>, inline handlers, <style>, SVG,
 *     and native data-* by NOT touching them.
 *   • NO DOMPurify or whole-document sanitizer pass.
 *
 * Public contract (module-map 03 §4):
 *   serialize() → htmlString | null
 */

import { stripIds } from "./element-registry.js";
import { emit } from "./bridge-iframe.js";

// --- Helpers ---

function isHypPrefixed(str) {
  return typeof str === "string" && str.startsWith("hyp-");
}

function hasHypClassToken(className) {
  if (!className) return false;
  return className
    .trim()
    .split(/\s+/)
    .some((t) => t.startsWith("hyp-"));
}

function isInjectedRuntimeScript(el) {
  if (el.tagName.toLowerCase() !== "script") return false;
  if (el.type !== "module") return false;
  const src = el.getAttribute("src") || "";
  return src.includes("/runtime/js/runtime-main.js");
}

function shouldRemoveElement(el) {
  const id = el.getAttribute("id") || "";
  if (isHypPrefixed(id)) return true;

  const className = el.getAttribute("class") || "";
  if (hasHypClassToken(className)) return true;

  if (isInjectedRuntimeScript(el)) return true;

  return false;
}

function countAllNodes(root) {
  let count = 1; // count the subtree root itself
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ALL);
  while (walker.nextNode()) {
    count++;
  }
  return count;
}

/**
 * Obtain the JSON string to re-embed as the comment island.
 * T15 hook: in-memory comment store takes precedence.
 * T9 fallback: read any existing island from the live document.
 */
function getCommentJson() {
  // Future T15 in-memory store
  if (
    window.hyp &&
    window.hyp.comments &&
    typeof window.hyp.comments.toJson === "function"
  ) {
    const json = window.hyp.comments.toJson();
    if (Array.isArray(json) && json.length > 0) {
      return JSON.stringify(json);
    }
  }

  // Fallback: existing island in the live document
  const island = document.getElementById("hyp-comments");
  if (island) {
    const text = island.textContent.trim();
    if (text) return text;
  }

  return null;
}

// --- Strip pass ---

/**
 * Perform the namespace strip on a cloned tree.
 * Returns the total number of nodes removed (including descendants).
 */
function stripClone(clone) {
  // Phase A: identify every element that must be removed
  const toRemove = [];
  const removeWalker = document.createTreeWalker(
    clone,
    NodeFilter.SHOW_ELEMENT
  );
  while (removeWalker.nextNode()) {
    if (shouldRemoveElement(removeWalker.currentNode)) {
      toRemove.push(removeWalker.currentNode);
    }
  }

  // Count all nodes inside the doomed subtrees
  let removedNodeCount = 0;
  for (const el of toRemove) {
    removedNodeCount += countAllNodes(el);
  }

  // Detach them
  for (const el of toRemove) {
    if (el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }

  // Phase B: clean surviving elements
  // Use stripIds for data-hyp-id removal (explicit contract requirement)
  stripIds(clone);

  const cleanWalker = document.createTreeWalker(
    clone,
    NodeFilter.SHOW_ELEMENT
  );
  while (cleanWalker.nextNode()) {
    const el = cleanWalker.currentNode;

    // Remove all remaining data-hyp-* attributes
    const attrs = Array.from(el.attributes);
    for (const attr of attrs) {
      if (attr.name.startsWith("data-hyp-")) {
        el.removeAttribute(attr.name);
      }
    }

    // Remove hyp- prefixed class tokens; drop empty class attr
    const className = el.getAttribute("class");
    if (className !== null) {
      const kept = className
        .trim()
        .split(/\s+/)
        .filter((t) => t && !t.startsWith("hyp-"));
      if (kept.length === 0) {
        el.removeAttribute("class");
      } else {
        el.setAttribute("class", kept.join(" "));
      }
    }
  }

  // Phase C: contenteditable sweep
  // The editor may have set contenteditable during an active text-edit session.
  // We remove it from every element that carries a data-hyp-id in the LIVE
  // document (those are editor-tagged elements). Without access to the
  // element-registry's private originalState WeakMap, this is the best-effort
  // approximation: editor-tagged elements should not retain editor-added
  // contenteditable. Document-native contenteditable on non-tagged elements is
  // untouched.
  const liveTagged = document.querySelectorAll("[data-hyp-id]");
  for (const liveEl of liveTagged) {
    // Map live element to clone element via a simple path walk.
    // Because clone is a deep clone of documentElement, the DOM structure
    // is identical at the moment of serialization.
    const cloneEl = resolveCloneNode(clone, liveEl);
    if (cloneEl) {
      cloneEl.removeAttribute("contenteditable");
    }
  }

  return removedNodeCount;
}

/**
 * Given a live element, find its counterpart in the cloned tree by walking
 * the identical structure using child indices.
 */
function resolveCloneNode(cloneRoot, liveNode) {
  if (liveNode === document.documentElement) return cloneRoot;

  const path = [];
  let cur = liveNode;
  while (cur && cur !== document.documentElement) {
    const parent = cur.parentNode;
    if (!parent) return null;
    const index = Array.from(parent.childNodes).indexOf(cur);
    path.unshift(index);
    cur = parent;
  }

  let cloneCur = cloneRoot;
  for (const idx of path) {
    const children = cloneCur.childNodes;
    if (idx < 0 || idx >= children.length) return null;
    cloneCur = children[idx];
  }
  return cloneCur;
}

// --- Public API ---

export function serialize() {
  // 1. Clone the live document
  const clone = document.documentElement.cloneNode(true);

  // 2. Capture comment JSON from the live document before strip alters structure
  const commentJson = getCommentJson();

  // 3. Pre-strip node count
  const preCount = countAllNodes(clone);

  // 4. Strip all editor chrome
  const removedNodeCount = stripClone(clone);

  // 5. Re-embed comment island (after strip so it survives)
  let islandCount = 0;
  if (commentJson) {
    const body = clone.querySelector("body");
    if (body) {
      const island = document.createElement("script");
      island.type = "application/json";
      island.id = "hyp-comments";
      island.textContent = commentJson;
      body.appendChild(island);
      islandCount = countAllNodes(island);
    }
  }

  // 6. Post-strip node count
  const postCount = countAllNodes(clone);

  // 7. Guard: delta must match removed chrome nodes ± re-embedded island
  const expectedPostCount = preCount - removedNodeCount + islandCount;
  if (postCount !== expectedPostCount) {
    emit("error", {
      scope: "serializer",
      message:
        `Serializer node-count guard failed: expected ${expectedPostCount} nodes, ` +
        `got ${postCount}. Pre=${preCount}, removed=${removedNodeCount}, ` +
        `island=${islandCount}. Aborting save to avoid data loss.`,
    });
    return null;
  }

  // 8. Emit standalone HTML
  return "<!doctype html>\n" + clone.outerHTML;
}
