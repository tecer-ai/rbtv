/**
 * runtime/js/reorder.js
 *
 * Pure drop-classification helpers for F3 (no history, no Moveable).
 * classifyDrop decides Shift-gated reorder vs reparent vs none from the pointer
 * position.
 *
 * Public contract:
 *   classifyDrop(dragEl, clientX, clientY) -> {kind, target, container, insertBefore}
 *   isContainer(el) -> boolean
 *   dominantAxis(containerEl) -> 'x' | 'y'
 *   midpointBefore(axis, rect, x, y) -> boolean      (pure, no DOM)
 *   axisFromDisplay(display, flexDirection) -> 'x' | 'y'  (pure, no DOM)
 */

// Tags that can never be a drop CONTAINER (inline/void/replaced/structural).
const NON_CONTAINER_TAGS = new Set([
  "img", "video", "audio", "picture", "br", "hr", "input", "textarea",
  "select", "button", "label", "progress", "meter", "canvas", "iframe",
  "embed", "object", "source", "track", "area", "map", "svg",
  "path", "circle", "rect", "line", "polyline", "polygon", "ellipse",
  "text", "tspan", "use", "g", "defs",
  "a", "abbr", "b", "bdi", "bdo", "cite", "code", "data", "dfn", "em",
  "i", "kbd", "mark", "q", "s", "samp", "small", "span", "strong",
  "sub", "sup", "time", "u", "var", "wbr", "font", "strike", "ins", "del", "big",
]);

export function axisFromDisplay(display, flexDirection) {
  if (display === "flex" || display === "inline-flex") {
    return (flexDirection || "").startsWith("row") ? "x" : "y";
  }
  // grid and block both default to DOM-order vertical reasoning
  return "y";
}

export function dominantAxis(container) {
  const cs = getComputedStyle(container);
  return layoutAxis(container, siblingsWithHypId(container, null), cs);
}

export function midpointBefore(axis, rect, x, y) {
  if (axis === "x") return x < rect.left + rect.width / 2;
  return y < rect.top + rect.height / 2;
}

export function isContainer(el) {
  if (!el) return false;
  const tag = el.tagName.toLowerCase();
  if (NON_CONTAINER_TAGS.has(tag)) return false;
  if (el.getAttribute("data-hyp-text") === "true") return false;
  // Leaf text element: no element children but has text → not a container.
  if (el.children.length === 0 && el.textContent.trim().length > 0) return false;
  return true;
}

function elementUnderPointerSkippingHypChrome(x, y) {
  const stack = document.elementsFromPoint(x, y);
  for (const el of stack) {
    if (!el || el.nodeType !== 1) continue;
    if (el.closest('[id^="hyp-"], [class^="hyp-"], [class*=" hyp-"]')) continue;
    return el;
  }
  return null;
}

function hasHypId(el) {
  return !!(el && el.getAttribute && el.getAttribute("data-hyp-id"));
}

function siblingsWithHypId(container, dragEl) {
  return Array.from(container.children).filter((el) => {
    if (el === dragEl) return false;
    if (!hasHypId(el)) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  });
}

function layoutAxis(container, elements, computedStyle = null) {
  const cs = computedStyle || getComputedStyle(container);
  if (cs.display === "flex" || cs.display === "inline-flex") {
    return axisFromDisplay(cs.display, cs.flexDirection);
  }
  if (elements.length < 2) return axisFromDisplay(cs.display, cs.flexDirection);

  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const el of elements) {
    const rect = el.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    minX = Math.min(minX, centerX);
    maxX = Math.max(maxX, centerX);
    minY = Math.min(minY, centerY);
    maxY = Math.max(maxY, centerY);
  }

  return (maxX - minX) > (maxY - minY) ? "x" : "y";
}

function containsOnCrossAxis(axis, rect, x, y) {
  if (axis === "x") return y >= rect.top && y <= rect.bottom;
  return x >= rect.left && x <= rect.right;
}

function classifySameParentByMidpoint(dragEl, clientX, clientY) {
  const container = dragEl.parentElement;
  const none = { kind: "none", target: null, container: null, insertBefore: false };
  if (!hasHypId(container)) return none;

  const siblings = siblingsWithHypId(container, dragEl);
  const axis = layoutAxis(container, siblings);
  for (const target of siblings) {
    const rect = target.getBoundingClientRect();
    if (!containsOnCrossAxis(axis, rect, clientX, clientY)) continue;
    if (axis === "x") {
      if (clientX >= rect.left && clientX <= rect.right) {
        return {
          kind: "reorder",
          target,
          container,
          insertBefore: midpointBefore(axis, rect, clientX, clientY),
        };
      }
    } else if (clientY >= rect.top && clientY <= rect.bottom) {
      return {
        kind: "reorder",
        target,
        container,
        insertBefore: midpointBefore(axis, rect, clientX, clientY),
      };
    }
  }
  return none;
}

export function classifyDrop(dragEl, clientX, clientY) {
  const none = { kind: "none", target: null, container: null, insertBefore: false };

  const sameParent = classifySameParentByMidpoint(dragEl, clientX, clientY);
  if (sameParent.kind !== "none") return sameParent;

  const hovered = elementUnderPointerSkippingHypChrome(clientX, clientY);
  if (!hovered) return none;
  const hov = hovered.closest("[data-hyp-id]");
  if (!hov || hov === dragEl) return none;

  // The command layer (commands.reorder) resolves BOTH parents by data-hyp-id,
  // so a drop CONTAINER that carries no data-hyp-id (e.g. <body>, which the
  // registry never tags) can never be a valid destination — building a reorder
  // command for it makes reorder.do() throw "parent not found null", which
  // silently aborts the whole drop (no history push, no dirty flag, orphaned
  // translate). Any such drop falls through to `none` = a keep-translate move.
  // (1) same-parent sibling → reorder
  if (hov.parentElement === dragEl.parentElement) {
    return none;
  }

  // (2) different parent → reparent if hovered's parent qualifies as a registered container
  const container = hov.parentElement;
  if (container && container !== dragEl.parentElement && isContainer(container) && hasHypId(container)) {
    const axis = dominantAxis(container);
    const r = hov.getBoundingClientRect();
    return {
      kind: "reparent",
      target: hov,
      container,
      insertBefore: midpointBefore(axis, r, clientX, clientY),
    };
  }

  return none;
}
