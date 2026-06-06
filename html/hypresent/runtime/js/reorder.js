/**
 * runtime/js/reorder.js
 *
 * Pure drop-classification helpers for F3 (no history, no Moveable).
 * classifyDrop decides reorder vs reparent vs none from the pointer position.
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
  return axisFromDisplay(cs.display, cs.flexDirection);
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

export function classifyDrop(dragEl, clientX, clientY) {
  const none = { kind: "none", target: null, container: null, insertBefore: false };
  const hovered = elementUnderPointerSkippingHypChrome(clientX, clientY);
  if (!hovered) return none;
  const hov = hovered.closest("[data-hyp-id]");
  if (!hov || hov === dragEl) return none;

  // (1) same-parent sibling → reorder
  if (hov.parentElement === dragEl.parentElement) {
    const axis = dominantAxis(dragEl.parentElement);
    const r = hov.getBoundingClientRect();
    return {
      kind: "reorder",
      target: hov,
      container: dragEl.parentElement,
      insertBefore: midpointBefore(axis, r, clientX, clientY),
    };
  }

  // (2) different parent → reparent if hovered's parent qualifies as a container
  const container = hov.parentElement;
  if (container && container !== dragEl.parentElement && isContainer(container)) {
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
