/**
 * runtime/js/commands.js
 *
 * Command factory: builds {do, undo, label} objects for each operation type,
 * capturing the inverse at creation from the live DOM pre-state where possible.
 *
 * Public contract (module-map 03 §4):
 *   text(hypId, beforeHtml, afterHtml) → command
 *   format(hypId, beforeHtml, afterHtml) → command
 *   resize(hypId, before, after) → command
 *   move(hypId, before, after) → command
 *   colorToken(name, value) → command
 *   colorElement(hypId, prop, value) → command
 *   comment(label, doFn, undoFn) → command
 *
 * Pure: applies nothing itself. history.push(cmd) runs cmd.do().
 */

import { byId } from "./element-registry.js";

// --- Helpers ---

function getElement(hypId) {
  const el = byId(hypId);
  if (!el) {
    throw new Error(`commands: element not found for hypId "${hypId}"`);
  }
  return el;
}

function kebabCase(prop) {
  if (prop.startsWith("--")) return prop;
  return prop.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());
}

function applyStyleMap(el, map) {
  for (const [prop, value] of Object.entries(map)) {
    const key = kebabCase(prop);
    if (value === "" || value == null) {
      el.style.removeProperty(key);
    } else {
      el.style.setProperty(key, value);
    }
  }
}

// --- Factories ---

/**
 * Text edit command: replaces innerHTML.
 * The caller captures beforeHtml at edit-start and afterHtml at commit.
 */
export function text(hypId, beforeHtml, afterHtml) {
  return {
    do() {
      const el = getElement(hypId);
      el.innerHTML = afterHtml;
    },
    undo() {
      const el = getElement(hypId);
      el.innerHTML = beforeHtml;
    },
    label: "text",
  };
}

/**
 * Format command: replaces innerHTML (snapshot before/after execCommand).
 */
export function format(hypId, beforeHtml, afterHtml) {
  return {
    do() {
      const el = getElement(hypId);
      el.innerHTML = afterHtml;
    },
    undo() {
      const el = getElement(hypId);
      el.innerHTML = beforeHtml;
    },
    label: "format",
  };
}

/**
 * Resize command: applies a map of CSS sizing properties.
 * @param {string} hypId
 * @param {Object} before - { [prop]: value } to restore
 * @param {Object} after  - { [prop]: value } to apply
 */
export function resize(hypId, before, after) {
  return {
    do() {
      const el = getElement(hypId);
      applyStyleMap(el, after);
    },
    undo() {
      const el = getElement(hypId);
      applyStyleMap(el, before);
    },
    label: "resize",
  };
}

/**
 * Move command (D2 + S1): applies the CSS individual `translate` property.
 * Writing `translate` instead of `transform: translate()` composes with any
 * document-owned `transform: rotate()/scale()` and never clobbers it.
 * @param {string} hypId
 * @param {string} before - previous inline `translate` value (may be empty), e.g. "10px 20px"
 * @param {string} after  - new inline `translate` value, e.g. "30px 40px" or ""
 */
export function move(hypId, before, after) {
  return {
    do() {
      const el = getElement(hypId);
      if (after === "" || after == null) {
        el.style.removeProperty("translate");
      } else {
        el.style.setProperty("translate", after);
      }
    },
    undo() {
      const el = getElement(hypId);
      if (before === "" || before == null) {
        el.style.removeProperty("translate");
      } else {
        el.style.setProperty("translate", before);
      }
    },
    label: "move",
  };
}

/**
 * Reorder / re-parent command (F3, S11).
 * Re-resolves the moved element and parents by hyp-id at run time.
 * do():   move dragEl into newParent before newNext (or append), clear translate.
 * undo(): move dragEl back into oldParent before oldNext (or append), restore translate.
 *
 * @param {string} hypId            data-hyp-id of the moved element
 * @param {string} oldParentHypId   data-hyp-id of the original parent
 * @param {string|null} oldPrevHypId  unused for restore; kept for audit
 * @param {string|null} oldNextHypId  data-hyp-id of the original next sibling (anchor for undo)
 * @param {string} newParentHypId   data-hyp-id of the destination parent
 * @param {string|null} newNextHypId  data-hyp-id of the destination next sibling (anchor for do)
 * @param {string} oldTranslate     the element's `translate` value before the drop
 */
export function reorder(
  hypId,
  oldParentHypId,
  oldPrevHypId,
  oldNextHypId,
  newParentHypId,
  newNextHypId,
  oldTranslate
) {
  function place(el, parentHypId, nextHypId) {
    const parent = byId(parentHypId);
    if (!parent) throw new Error(`reorder: parent not found "${parentHypId}"`);
    const next = nextHypId ? byId(nextHypId) : null;
    if (next && next.parentNode === parent) {
      parent.insertBefore(el, next);
    } else {
      parent.appendChild(el);
    }
  }
  return {
    do() {
      const el = getElement(hypId);
      place(el, newParentHypId, newNextHypId);
      el.style.removeProperty("translate");
    },
    undo() {
      const el = getElement(hypId);
      place(el, oldParentHypId, oldNextHypId);
      if (oldTranslate === "" || oldTranslate == null) {
        el.style.removeProperty("translate");
      } else {
        el.style.setProperty("translate", oldTranslate);
      }
    },
    label: "reorder",
  };
}

/**
 * Color token command: mutates a :root CSS custom property.
 * Captures the current inline value at creation time.
 */
export function colorToken(name, value) {
  const before = document.documentElement.style.getPropertyValue(name);
  return {
    do() {
      document.documentElement.style.setProperty(name, value);
    },
    undo() {
      if (before === "" || before == null) {
        document.documentElement.style.removeProperty(name);
      } else {
        document.documentElement.style.setProperty(name, before);
      }
    },
    label: "color-token",
  };
}

/**
 * Color element command: mutates an inline style property on an element.
 * Captures the current inline value at creation time.
 */
export function colorElement(hypId, prop, value) {
  const el = getElement(hypId);
  const key = kebabCase(prop);
  const before = el.style.getPropertyValue(key);
  return {
    do() {
      const target = getElement(hypId);
      if (value === "" || value == null) {
        target.style.removeProperty(key);
      } else {
        target.style.setProperty(key, value);
      }
    },
    undo() {
      const target = getElement(hypId);
      if (before === "" || before == null) {
        target.style.removeProperty(key);
      } else {
        target.style.setProperty(key, before);
      }
    },
    label: "color-element",
  };
}

/**
 * Border-color command (F4, U6/S14): sets border-color on all four sides.
 * If the element has no visible border (style none or width 0 on ALL sides),
 * also applies `border:1px solid <value>` so the border becomes visible.
 * Undo restores the prior inline border-related state in full.
 */
export function colorBorder(hypId, value) {
  const el = getElement(hypId);
  const SIDES = ["top", "right", "bottom", "left"];
  // Capture prior INLINE values (not computed) for exact undo.
  const before = {
    border: el.style.getPropertyValue("border"),
    "border-color": el.style.getPropertyValue("border-color"),
    "border-width": el.style.getPropertyValue("border-width"),
    "border-style": el.style.getPropertyValue("border-style"),
  };
  for (const s of SIDES) {
    before[`border-${s}-color`] = el.style.getPropertyValue(`border-${s}-color`);
  }

  function restore(target) {
    // Clear all border-related inline props, then re-apply captured ones.
    target.style.removeProperty("border");
    target.style.removeProperty("border-color");
    target.style.removeProperty("border-width");
    target.style.removeProperty("border-style");
    for (const s of SIDES) target.style.removeProperty(`border-${s}-color`);
    for (const [k, v] of Object.entries(before)) {
      if (v) target.style.setProperty(k, v);
    }
  }

  return {
    do() {
      const target = getElement(hypId);
      const cs = getComputedStyle(target);
      const noneOrZero = SIDES.every((s) => {
        const style = cs.getPropertyValue(`border-${s}-style`);
        const width = parseFloat(cs.getPropertyValue(`border-${s}-width`)) || 0;
        return style === "none" || width === 0;
      });
      if (noneOrZero) {
        target.style.setProperty("border", `1px solid ${value}`);
      } else {
        target.style.setProperty("border-color", value);
      }
    },
    undo() {
      restore(getElement(hypId));
    },
    label: "color-border",
  };
}

/**
 * Delete-element command (R3, V3-S5). Captures the parent (by hyp-id, or the
 * live body node if the parent has no hyp-id), the next sibling's hyp-id, and
 * the detached node REF so undo restores the exact subtree. Mirrors reorder's
 * place() insertion. The node keeps its data-hyp-id, so byId resolves it again
 * once re-attached.
 *
 * @param {string} hypId  data-hyp-id of the element to delete
 */
export function deleteElement(hypId) {
  const el = getElement(hypId);
  const parentEl = el.parentElement;
  const parentHypId = parentEl ? parentEl.getAttribute("data-hyp-id") : null;
  const nextHypId = el.nextElementSibling
    ? el.nextElementSibling.getAttribute("data-hyp-id")
    : null;
  const node = el; // capture the live node for exact-subtree undo

  function place() {
    // Resolve the destination parent: by hyp-id if it had one, else the original
    // parent node (e.g. document.body, which carries no hyp-id).
    const parent = parentHypId ? byId(parentHypId) : parentEl;
    if (!parent) throw new Error(`deleteElement: parent not found for "${hypId}"`);
    const next = nextHypId ? byId(nextHypId) : null;
    if (next && next.parentNode === parent) {
      parent.insertBefore(node, next);
    } else {
      parent.appendChild(node);
    }
  }

  return {
    do() {
      if (node.parentNode) node.parentNode.removeChild(node);
    },
    undo() {
      place();
    },
    label: "delete-element",
  };
}

/**
 * Align command (R7, V3-S15). Captures the prior inline values of EVERY
 * alignment property the apply logic may write, for exact undo (capture-all,
 * like colorBorder). The apply itself lives in text-format.applyAlign (imported
 * by runtime-main and called there); this factory only captures + restores.
 *
 * @param {string} hypId
 * @param {function} applyFn  () => void  (closure that calls applyAlign(el,axis,value))
 */
export function align(hypId, applyFn) {
  const el = getElement(hypId);
  const PROPS = [
    "text-align",
    "justify-content",
    "align-items",
    "justify-items",
    "align-content",
    "justify-self",
    "align-self",
    "vertical-align",
    "display",
    "flex-direction",
  ];
  const before = {};
  for (const p of PROPS) before[p] = el.style.getPropertyValue(p);

  return {
    do() {
      applyFn();
    },
    undo() {
      const target = getElement(hypId);
      for (const p of PROPS) {
        const v = before[p];
        if (v === "" || v == null) target.style.removeProperty(p);
        else target.style.setProperty(p, v);
      }
    },
    label: "align",
  };
}

/**
 * Comment command: generic wrapper for comment-store mutations.
 * The caller captures pre-state and provides do/undo closures.
 */
export function comment(label, doFn, undoFn) {
  return {
    do: doFn,
    undo: undoFn,
    label,
  };
}
