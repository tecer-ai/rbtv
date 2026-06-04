/**
 * runtime/js/interaction.js
 *
 * Modeless combined interaction (U1, F2, F3): a SINGLE Moveable per selection
 * with draggable + resizable + Slides-style snapping/guides. On drop, hit-test
 * the pointer and reorder / reparent / keep-translate, committing one history
 * command and animating displaced siblings with FLIP.
 *
 * Public contract:
 *   mount(hypId), unmount(), suspend(), resume(), isActive(), remount(hypId)
 *
 * Emits (via bridge-iframe.js):
 *   geometry-changed {hypId, prop, before, after}
 *   out-of-flow {hypId, bool}
 */

import { byId, roleOf, idOf } from "./element-registry.js";
import { resize as makeResizeCommand, move as makeMoveCommand, reorder as makeReorderCommand } from "./commands.js";
import { push as historyPush } from "./history.js";
import { classifyDrop } from "./reorder.js";
import { reanchorAfterMove } from "./comments.js";
import { emit } from "./bridge-iframe.js";

// NOTE (R09): interaction.js does NOT import selection.js. The selection→mount
// wiring is registered explicitly in runtime-main.js boot() via selection.js's
// onSelectionChange observer (see PART F). This breaks the former import cycle
// runtime-main → text-edit → interaction → selection.

// Minimum cumulative drag distance (px, Euclidean) for a drag to count as a
// real move/reorder. Below this, a drop is a no-op (R05): a single click that
// Moveable reports as a zero-distance dragEnd must NOT translate or reorder.
const DRAG_THRESHOLD = 3;

// --- State ---
let moveable = null;
let wrapper = null;
let activeHypId = null;
let suspended = false;
let scriptLoadPromise = null;

// resize in-flight
let beforeSizing = null;
let beforeRect = null;
let originalTop = 0;
let originalLeft = 0;

// drag in-flight
let beforeTranslate = "";
let baseTranslate = [0, 0];
let lastPointer = { x: 0, y: 0 };
let dragDist = 0;   // cumulative Euclidean drag distance, updated in onDrag (R05)

// --- Moveable script (from resize.js, verbatim pattern) ---
function ensureMoveableScript() {
  if (window.Moveable) return Promise.resolve();
  if (scriptLoadPromise) return scriptLoadPromise;
  const existing = document.querySelector('script[src="/app/js/vendor/moveable.min.js"]');
  if (existing) {
    scriptLoadPromise = new Promise((resolve, reject) => {
      const t = setTimeout(() => reject(new Error("Moveable load timeout")), 10000);
      const check = () => { if (window.Moveable) { clearTimeout(t); resolve(); } else setTimeout(check, 50); };
      check();
    });
    return scriptLoadPromise;
  }
  scriptLoadPromise = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.id = "hyp-moveable-script";
    s.src = "/app/js/vendor/moveable.min.js";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Failed to load Moveable"));
    document.head.appendChild(s);
  });
  return scriptLoadPromise;
}

// --- translate helpers (CSS `translate` property; S1) ---
function parseTranslate(str) {
  if (!str) return [0, 0];
  // CSS translate property form: "Xpx Ypx" or "Xpx" (single value = X, Y=0)
  const parts = str.trim().split(/\s+/);
  const x = parseFloat(parts[0]) || 0;
  const y = parts.length > 1 ? parseFloat(parts[1]) || 0 : 0;
  return [x, y];
}
function computeOutOfFlow(el) {
  const t = parseTranslate(el.style.translate);
  return Math.abs(t[0]) >= 0.5 || Math.abs(t[1]) >= 0.5;
}

// --- resize sizing (folded from resize.js; verbatim logic) ---
function captureSizingState(el, role) {
  const s = el.style; const m = {};
  if (role === "absolute") {
    m.width = s.getPropertyValue("width") || ""; m.height = s.getPropertyValue("height") || "";
    m.top = s.getPropertyValue("top") || ""; m.left = s.getPropertyValue("left") || "";
  } else if (role === "flex-child") {
    m.flexBasis = s.getPropertyValue("flex-basis") || "";
    m.width = s.getPropertyValue("width") || ""; m.height = s.getPropertyValue("height") || "";
  } else {
    m.width = s.getPropertyValue("width") || ""; m.height = s.getPropertyValue("height") || "";
  }
  return m;
}
function applyVisualResize(el, role, width, height, direction) {
  const parent = el.parentElement;
  const cp = parent ? getComputedStyle(parent) : null;
  const isFlexRow = cp && (cp.flexDirection === "row" || cp.flexDirection === "row-reverse");
  if (role === "flex-child" && parent) {
    if (isFlexRow) { if (width != null) el.style.flexBasis = width + "px"; if (height != null) el.style.height = height + "px"; }
    else { if (height != null) el.style.flexBasis = height + "px"; if (width != null) el.style.width = width + "px"; }
  } else {
    if (width != null) el.style.width = width + "px"; if (height != null) el.style.height = height + "px";
  }
  if (role === "absolute") {
    const dw = width != null ? width - beforeRect.width : 0;
    const dh = height != null ? height - beforeRect.height : 0;
    if (direction && direction[0] === -1 && dw !== 0) el.style.left = originalLeft - dw + "px";
    if (direction && direction[1] === -1 && dh !== 0) el.style.top = originalTop - dh + "px";
  }
}

// --- guideline candidates (F2, S5) ---
function getElementGuidelines(targetEl) {
  const parent = targetEl.parentElement;
  const siblings = parent
    ? Array.from(parent.children).filter((c) => c !== targetEl && c.getAttribute("data-hyp-id"))
    : [];
  const slideRoot = targetEl.closest("section, .slide, [data-hyp-region], body") || document.body;
  const set = new Set([...siblings]);
  if (parent && parent !== targetEl) set.add(parent);
  set.add(slideRoot);
  set.delete(targetEl);
  let candidates = Array.from(set);
  if (candidates.length > 30) {
    const tr = targetEl.getBoundingClientRect();
    const tc = [(tr.left + tr.right) / 2, (tr.top + tr.bottom) / 2];
    candidates.sort((a, b) => {
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      const da = Math.hypot((ra.left + ra.right) / 2 - tc[0], (ra.top + ra.bottom) / 2 - tc[1]);
      const db = Math.hypot((rb.left + rb.right) / 2 - tc[0], (rb.top + rb.bottom) / 2 - tc[1]);
      return da - db;
    });
    candidates = candidates.slice(0, 30);
  }
  return candidates;
}

// --- wrapper ---
// R2 FIX: Moveable's control box + handles are plain light-DOM children of the
// pointer-events:none wrapper, and Moveable's compensating pointer-events CSS is
// :host-scoped (shadow-DOM only), so the controls inherit pointer-events:none and
// every handle is unhittable (elementFromPoint = null). We inject a hyp-scoped
// stylesheet that re-enables pointer-events:auto on Moveable's own control
// elements scoped under the wrapper. The wrapper STAYS pointer-events:none so
// empty-region clicks still pass through to select/clear.
const INTERACTION_STYLE_ID = "hyp-interaction-style";
function ensureInteractionStyle() {
  if (document.getElementById(INTERACTION_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = INTERACTION_STYLE_ID;
  style.textContent =
    "#hyp-interaction-wrapper .moveable-control.moveable-direction { pointer-events: auto; }";
  document.head.appendChild(style);
}
function removeInteractionStyle() {
  const s = document.getElementById(INTERACTION_STYLE_ID);
  if (s && s.parentNode) s.parentNode.removeChild(s);
}
function createWrapper() {
  ensureInteractionStyle();
  const w = document.createElement("div");
  w.className = "hyp-interaction-wrapper";
  w.id = "hyp-interaction-wrapper";
  Object.assign(w.style, {
    position: "absolute",
    top: "0",
    left: "0",
    width: Math.max(document.documentElement.scrollWidth, document.documentElement.clientWidth) + "px",
    height: Math.max(document.documentElement.scrollHeight, document.documentElement.clientHeight) + "px",
    pointerEvents: "none",
    zIndex: "999998",
  });
  document.body.appendChild(w);
  return w;
}
function removeWrapper() {
  if (wrapper && wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);
  wrapper = null;
}

// --- resize handlers ---
function onResizeStart(e) {
  const el = e.target; const role = roleOf(el);
  beforeSizing = captureSizingState(el, role);
  beforeRect = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  originalTop = parseFloat(cs.top) || 0; originalLeft = parseFloat(cs.left) || 0;
}
function onResize(e) { const el = e.target; applyVisualResize(el, roleOf(el), e.width, e.height, e.direction); }
function onResizeEnd() {
  const el = byId(activeHypId); if (!el) { beforeSizing = null; beforeRect = null; return; }
  const role = roleOf(el); const after = captureSizingState(el, role);
  let changed = false; for (const k of Object.keys(after)) if (beforeSizing[k] !== after[k]) { changed = true; break; }
  if (changed) {
    historyPush(makeResizeCommand(activeHypId, beforeSizing, after));
    emit("geometry-changed", { hypId: activeHypId, prop: "resize", before: beforeSizing, after });
  }
  beforeSizing = null; beforeRect = null;
}

// --- drag handlers (translate; S1) ---
function onDragStart(e) {
  const el = e.target;
  beforeTranslate = el.style.translate || "";
  baseTranslate = parseTranslate(beforeTranslate);
  dragDist = 0;                       // reset cumulative drag distance (R05)
}
function onDrag(e) {
  const el = e.target;
  const [dx, dy] = e.translate;       // Moveable's e.translate is cumulative from drag start
  el.style.translate = `${baseTranslate[0] + dx}px ${baseTranslate[1] + dy}px`;
  dragDist = Math.hypot(dx, dy);      // accumulate distance here (R05)
  // cache pointer for the drop hit-test (S7)
  const ie = e.inputEvent;
  if (ie && typeof ie.clientX === "number") lastPointer = { x: ie.clientX, y: ie.clientY };
}
function onDragEnd() {
  const el = byId(activeHypId); if (!el) { beforeTranslate = ""; baseTranslate = [0, 0]; dragDist = 0; return; }

  // (R05) Zero-distance drag = a click Moveable surfaced as a drag. Treat as a
  // no-op: restore the pre-drag translate (onDrag may have written a sub-pixel
  // value), do NOT classify/commit, do NOT push any command. Guards against a
  // spurious reorder from elementsFromPoint near the iframe corner.
  if (dragDist <= DRAG_THRESHOLD) {
    if (beforeTranslate === "" || beforeTranslate == null) el.style.removeProperty("translate");
    else el.style.setProperty("translate", beforeTranslate);
    beforeTranslate = ""; baseTranslate = [0, 0]; dragDist = 0;
    return;
  }

  // Temporarily disable pointer events on the dragged element so
  // elementsFromPoint can see what's underneath it (F3 hit-test).
  const savedPointerEvents = el.style.pointerEvents;
  el.style.pointerEvents = "none";
  const cls = classifyDrop(el, lastPointer.x, lastPointer.y);
  el.style.pointerEvents = savedPointerEvents || "";
  if (savedPointerEvents === "" || savedPointerEvents == null) {
    el.style.removeProperty("pointer-events");
  }
  if (cls.kind === "none") {
    // keep translate; commit a move command + emit out-of-flow
    const after = el.style.translate || "";
    if (beforeTranslate !== after) {
      historyPush(makeMoveCommand(activeHypId, beforeTranslate, after));
      emit("geometry-changed", { hypId: activeHypId, prop: "translate", before: beforeTranslate, after });
      emit("out-of-flow", { hypId: activeHypId, bool: computeOutOfFlow(el) });
    }
    beforeTranslate = ""; baseTranslate = [0, 0]; dragDist = 0;
    return;
  }
  commitDrop(el, cls);
  beforeTranslate = ""; baseTranslate = [0, 0]; dragDist = 0;
}

// --- drop commit + FLIP + reanchor (F3, S11/S12) ---
function childrenWithHypId(parent) {
  return parent ? Array.from(parent.children).filter((c) => c.getAttribute("data-hyp-id")) : [];
}
function commitDrop(dragEl, cls) {
  const oldParent = dragEl.parentElement;
  const oldPrev = dragEl.previousElementSibling?.getAttribute("data-hyp-id") ?? null;
  const oldNext = dragEl.nextElementSibling?.getAttribute("data-hyp-id") ?? null;
  const oldTranslate = dragEl.style.translate || "";

  // FLIP FIRST snapshot — DISPLACED SIBLINGS ONLY. The dragged element is
  // EXCLUDED (R10): it lands instantly at its new flow position; FLIP-animating
  // it would invert it back to its old spot for ~180ms (a visible flash).
  const affected = new Set(
    [...childrenWithHypId(oldParent), ...childrenWithHypId(cls.container)].filter((e) => e !== dragEl)
  );
  const first = new Map();
  for (const elx of affected) first.set(elx, elx.getBoundingClientRect());

  // compute destination next-sibling
  const ref = cls.insertBefore ? cls.target : cls.target.nextElementSibling;
  const newNext = ref ? ref.getAttribute("data-hyp-id") : null;

  const cmd = makeReorderCommand(
    dragEl.getAttribute("data-hyp-id"),
    oldParent.getAttribute("data-hyp-id"),
    oldPrev, oldNext,
    cls.container.getAttribute("data-hyp-id"),
    newNext, oldTranslate
  );
  cmd.label = cls.kind === "reparent" ? "reparent" : "reorder";
  historyPush(cmd); // runs do(): insertBefore + clear translate

  // FLIP PLAY
  requestAnimationFrame(() => {
    for (const [elx, before] of first) {
      const after = elx.getBoundingClientRect();
      const dx = before.left - after.left, dy = before.top - after.top;
      if (dx || dy) {
        elx.style.transition = "none";
        elx.style.transform = `translate(${dx}px, ${dy}px)`;
        requestAnimationFrame(() => {
          elx.style.transition = "transform 180ms ease";
          elx.style.transform = "";
          // clean the transient transition prop after it ends
          setTimeout(() => { elx.style.transition = ""; if (elx.style.transform === "") elx.style.removeProperty("transform"); }, 220);
        });
      }
    }
  });

  reanchorAfterMove();
  emit("geometry-changed", { hypId: activeHypId, prop: "reorder", before: oldTranslate, after: "" });
  remount(dragEl.getAttribute("data-hyp-id"));
}

// --- Moveable lifecycle ---
function buildMoveable(el) {
  return new window.Moveable(wrapper, {
    target: el,
    draggable: true, resizable: true, edge: true,
    throttleResize: 1, throttleDrag: 0,
    snappable: true, snapContainer: wrapper, snapThreshold: 5, snapGap: true,
    maxSnapElementGuidelineDistance: 600, snapRenderThreshold: 1, isDisplaySnapDigit: false,
    snapDirections: { left: true, top: true, right: true, bottom: true, center: true, middle: true },
    elementSnapDirections: { left: true, top: true, right: true, bottom: true, center: true, middle: true },
    elementGuidelines: getElementGuidelines(el),
  });
}
function wire(m) {
  m.on("resizeStart", onResizeStart); m.on("resize", onResize); m.on("resizeEnd", onResizeEnd);
  m.on("dragStart", onDragStart); m.on("drag", onDrag); m.on("dragEnd", onDragEnd);
}
function teardown() {
  if (moveable) { moveable.destroy(); moveable = null; }
  removeWrapper();
  removeInteractionStyle();
}

// --- Public API ---
export function mount(hypId) {
  if (!hypId) return;
  if (activeHypId === hypId && moveable) return;
  unmount();
  activeHypId = hypId;
  ensureMoveableScript().then(() => {
    if (activeHypId !== hypId) return;
    const el = byId(hypId); if (!el) return;
    wrapper = createWrapper();
    moveable = buildMoveable(el);
    wire(moveable);
    if (suspended) { moveable.draggable = false; moveable.resizable = false; }
  }).catch((err) => { emit("error", { scope: "interaction", message: String(err) }); unmount(); });
}
export function remount(hypId) {
  // re-point the existing Moveable to the (possibly reflowed) element
  if (!moveable) { mount(hypId); return; }
  const el = byId(hypId); if (!el) { unmount(); return; }
  activeHypId = hypId;
  if (wrapper) {
    wrapper.style.width = Math.max(document.documentElement.scrollWidth, document.documentElement.clientWidth) + "px";
    wrapper.style.height = Math.max(document.documentElement.scrollHeight, document.documentElement.clientHeight) + "px";
  }
  moveable.target = el;
  moveable.elementGuidelines = getElementGuidelines(el);
  moveable.updateRect();
}
export function unmount() { activeHypId = null; teardown(); }
export function suspend() {
  suspended = true;
  if (moveable) { moveable.draggable = false; moveable.resizable = false; }
}
export function resume() {
  suspended = false;
  if (moveable) { moveable.draggable = true; moveable.resizable = true; moveable.updateRect(); }
}
export function isActive() { return moveable != null; }

// --- Event-driven re-target (S4) ---
// The selection→mount/remount/unmount wiring lives in runtime-main.js boot()
// (PART F), which calls selection.js's onSelectionChange AFTER all modules are
// fully evaluated. interaction.js intentionally does NOT subscribe here, and
// does NOT import selection.js, to avoid an ES-module import cycle (R09).
// runtime-main holds the only reference to onSelectionChange and passes our
// mount/remount/unmount/isActive into it.
