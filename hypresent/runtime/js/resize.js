/**
 * runtime/js/resize.js
 *
 * Flow-aware resize using Moveable (UMD) inside the iframe.
 * Mounts Moveable on the selected element; on resize-end computes
 * the correct sizing property from layout role and writes it.
 * NEVER converts to absolute positioning.
 *
 * Public contract (module-map 03 §4):
 *   begin(hypId)
 *   end()
 *
 * Emits (via bridge-iframe.js):
 *   geometry-changed {hypId, prop, before, after}
 */

import { byId, roleOf } from "./element-registry.js";
import { current } from "./selection.js";
import { resize as makeResizeCommand } from "./commands.js";
import { push as historyPush } from "./history.js";
import { emit } from "./bridge-iframe.js";

// --- State ---

let moveableInstance = null;
let activeHypId = null;
let isActive = false;
let pollIntervalId = null;
let scriptLoadPromise = null;

let isResizing = false;
let beforeState = null;
let beforeRect = null;
let originalTop = 0;
let originalLeft = 0;

// --- Moveable script injection ---

function ensureMoveableScript() {
  if (window.Moveable) {
    return Promise.resolve();
  }
  if (scriptLoadPromise) {
    return scriptLoadPromise;
  }
  scriptLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = "hyp-moveable-script";
    script.src = "/app/js/vendor/moveable.min.js";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Moveable"));
    document.head.appendChild(script);
  });
  return scriptLoadPromise;
}

// --- Style helpers ---

function captureSizingState(el, role) {
  const style = el.style;
  const map = {};
  if (role === "absolute") {
    map.width = style.getPropertyValue("width") || "";
    map.height = style.getPropertyValue("height") || "";
    map.top = style.getPropertyValue("top") || "";
    map.left = style.getPropertyValue("left") || "";
  } else if (role === "flex-child") {
    map.flexBasis = style.getPropertyValue("flex-basis") || "";
    map.width = style.getPropertyValue("width") || "";
    map.height = style.getPropertyValue("height") || "";
  } else {
    // grid-child or block
    map.width = style.getPropertyValue("width") || "";
    map.height = style.getPropertyValue("height") || "";
  }
  return map;
}

function applyVisualResize(el, role, width, height, direction) {
  const parent = el.parentElement;
  const computedParent = parent ? getComputedStyle(parent) : null;
  const isFlexRow =
    computedParent &&
    (computedParent.flexDirection === "row" ||
      computedParent.flexDirection === "row-reverse");

  if (role === "flex-child" && parent) {
    if (isFlexRow) {
      if (width != null) el.style.flexBasis = width + "px";
      if (height != null) el.style.height = height + "px";
    } else {
      if (height != null) el.style.flexBasis = height + "px";
      if (width != null) el.style.width = width + "px";
    }
  } else {
    if (width != null) el.style.width = width + "px";
    if (height != null) el.style.height = height + "px";
  }

  if (role === "absolute") {
    const dw = width != null ? width - beforeRect.width : 0;
    const dh = height != null ? height - beforeRect.height : 0;
    if (direction && direction[0] === -1 && dw !== 0) {
      el.style.left = originalLeft - dw + "px";
    }
    if (direction && direction[1] === -1 && dh !== 0) {
      el.style.top = originalTop - dh + "px";
    }
  }
}

// --- Moveable lifecycle ---

function createMoveable(el) {
  const wrapper = document.createElement("div");
  wrapper.className = "hyp-moveable-wrapper";
  wrapper.id = "hyp-moveable-wrapper";
  wrapper.style.position = "fixed";
  wrapper.style.top = "0";
  wrapper.style.left = "0";
  wrapper.style.width = "100%";
  wrapper.style.height = "100%";
  wrapper.style.pointerEvents = "none";
  wrapper.style.zIndex = "999998";
  document.body.appendChild(wrapper);

  const moveable = new window.Moveable(wrapper, {
    target: el,
    resizable: true,
    keepRatio: false,
    edge: true,
    throttleResize: 1,
  });

  moveable._hypWrapper = wrapper;
  return moveable;
}

function destroyMoveable(moveable) {
  if (!moveable) return;
  moveable.destroy();
  if (moveable._hypWrapper && moveable._hypWrapper.parentNode) {
    moveable._hypWrapper.parentNode.removeChild(moveable._hypWrapper);
  }
}

// --- Event handlers ---

function onResizeStart(e) {
  isResizing = true;
  const el = e.target;
  const role = roleOf(el);
  beforeState = captureSizingState(el, role);
  beforeRect = el.getBoundingClientRect();
  const computed = getComputedStyle(el);
  originalTop = parseFloat(computed.top) || 0;
  originalLeft = parseFloat(computed.left) || 0;
}

function onResize(e) {
  const el = e.target;
  const role = roleOf(el);
  applyVisualResize(el, role, e.width, e.height, e.direction);
}

function onResizeEnd() {
  isResizing = false;
  const el = byId(activeHypId);
  if (!el) {
    beforeState = null;
    beforeRect = null;
    return;
  }

  const role = roleOf(el);
  const afterState = captureSizingState(el, role);

  // Only commit if something actually changed
  let changed = false;
  for (const key of Object.keys(afterState)) {
    if (beforeState[key] !== afterState[key]) {
      changed = true;
      break;
    }
  }

  if (changed && activeHypId) {
    const cmd = makeResizeCommand(activeHypId, beforeState, afterState);
    historyPush(cmd);

    const changedProps = [];
    for (const key of Object.keys(afterState)) {
      if (beforeState[key] !== afterState[key]) {
        changedProps.push(key);
      }
    }

    emit("geometry-changed", {
      hypId: activeHypId,
      prop: changedProps.join(","),
      before: beforeState,
      after: afterState,
    });
  }

  beforeState = null;
  beforeRect = null;
}

// --- Window scroll/resize ---

function onViewportChange() {
  if (moveableInstance) {
    moveableInstance.updateRect();
  }
}

// --- Selection polling ---

function startPolling() {
  if (pollIntervalId) return;
  pollIntervalId = setInterval(() => {
    if (!isActive) return;
    const info = current();
    const nextHypId = info?.hypId || null;
    if (nextHypId !== activeHypId) {
      if (moveableInstance) {
        destroyMoveable(moveableInstance);
        moveableInstance = null;
      }
      activeHypId = nextHypId;
      if (nextHypId) {
        const el = byId(nextHypId);
        if (el) {
          moveableInstance = createMoveable(el);
          moveableInstance.on("resizeStart", onResizeStart);
          moveableInstance.on("resize", onResize);
          moveableInstance.on("resizeEnd", onResizeEnd);
        }
      }
    }
  }, 150);
}

function stopPolling() {
  if (pollIntervalId) {
    clearInterval(pollIntervalId);
    pollIntervalId = null;
  }
}

// --- Public API ---

export function begin(hypId) {
  if (isActive && activeHypId === hypId) return;

  end();

  if (!hypId) return;

  isActive = true;
  activeHypId = hypId;

  ensureMoveableScript()
    .then(() => {
      if (!isActive || activeHypId !== hypId) return;
      const el = byId(hypId);
      if (!el) return;

      moveableInstance = createMoveable(el);
      moveableInstance.on("resizeStart", onResizeStart);
      moveableInstance.on("resize", onResize);
      moveableInstance.on("resizeEnd", onResizeEnd);

      window.addEventListener("scroll", onViewportChange);
      window.addEventListener("resize", onViewportChange);

      startPolling();
    })
    .catch((err) => {
      emit("error", { scope: "resize", message: String(err) });
      end();
    });
}

export function end() {
  if (isResizing && beforeState) {
    // Commit any in-flight resize before tearing down
    const el = byId(activeHypId);
    if (el) {
      const role = roleOf(el);
      const afterState = captureSizingState(el, role);
      let changed = false;
      for (const key of Object.keys(afterState)) {
        if (beforeState[key] !== afterState[key]) {
          changed = true;
          break;
        }
      }
      if (changed && activeHypId) {
        const cmd = makeResizeCommand(activeHypId, beforeState, afterState);
        historyPush(cmd);
        emit("geometry-changed", {
          hypId: activeHypId,
          prop: "resize",
          before: beforeState,
          after: afterState,
        });
      }
    }
    isResizing = false;
    beforeState = null;
    beforeRect = null;
  }

  isActive = false;
  stopPolling();

  window.removeEventListener("scroll", onViewportChange);
  window.removeEventListener("resize", onViewportChange);

  if (moveableInstance) {
    destroyMoveable(moveableInstance);
    moveableInstance = null;
  }

  activeHypId = null;
}
