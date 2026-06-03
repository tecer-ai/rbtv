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
 * Move command: applies a transform value.
 * @param {string} hypId
 * @param {string} before - previous inline transform value (may be empty)
 * @param {string} after  - new inline transform value
 */
export function move(hypId, before, after) {
  return {
    do() {
      const el = getElement(hypId);
      if (after === "" || after == null) {
        el.style.removeProperty("transform");
      } else {
        el.style.setProperty("transform", after);
      }
    },
    undo() {
      const el = getElement(hypId);
      if (before === "" || before == null) {
        el.style.removeProperty("transform");
      } else {
        el.style.setProperty("transform", before);
      }
    },
    label: "move",
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
