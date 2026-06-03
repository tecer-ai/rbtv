/**
 * runtime/js/move.js
 *
 * Transform-translate move using Moveable (UMD) inside the iframe.
 * Mounts Moveable in drag mode on the selected element; writes ONLY
 * transform: translate(); computes and emits out-of-flow status.
 *
 * Public contract (module-map 03 §4):
 *   begin(hypId)
 *   end()
 *
 * Emits (via bridge-iframe.js):
 *   geometry-changed {hypId, prop, before, after}
 *   out-of-flow {hypId, bool}
 */

import { byId } from "./element-registry.js";
import { current } from "./selection.js";
import { move as makeMoveCommand } from "./commands.js";
import { push as historyPush } from "./history.js";
import { emit } from "./bridge-iframe.js";

// --- State ---

let moveableInstance = null;
let activeHypId = null;
let isActive = false;
let pollIntervalId = null;
let scriptLoadPromise = null;

let isDragging = false;
let beforeTransform = "";
let baseTranslate = [0, 0];

// --- Moveable script injection ---

function ensureMoveableScript() {
  if (window.Moveable) {
    return Promise.resolve();
  }
  if (scriptLoadPromise) {
    return scriptLoadPromise;
  }

  // If another module (e.g. resize) already injected the script, wait for it.
  const existing = document.querySelector(
    'script[src="/app/js/vendor/moveable.min.js"]'
  );
  if (existing) {
    scriptLoadPromise = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error("Moveable load timeout"));
      }, 10000);
      const check = () => {
        if (window.Moveable) {
          clearTimeout(timeout);
          resolve();
          return;
        }
        setTimeout(check, 50);
      };
      check();
    });
    return scriptLoadPromise;
  }

  scriptLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "/app/js/vendor/moveable.min.js";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Moveable"));
    document.head.appendChild(script);
  });
  return scriptLoadPromise;
}

// --- Transform helpers ---

function parseTranslate(str) {
  if (!str) return [0, 0];
  // translate(x, y)
  let m = str.match(
    /translate\((-?[\d.]+)(?:px)?(?:\s*,\s*(-?[\d.]+)(?:px)?)?\)/
  );
  if (m) return [parseFloat(m[1]), parseFloat(m[2] ?? 0)];
  // translateX(x) translateY(y)
  const mx = str.match(/translateX\((-?[\d.]+)(?:px)?\)/);
  const my = str.match(/translateY\((-?[\d.]+)(?:px)?\)/);
  if (mx || my) {
    return [parseFloat(mx?.[1]) || 0, parseFloat(my?.[1]) || 0];
  }
  // translate3d(x, y, z)
  m = str.match(/translate3d\((-?[\d.]+)(?:px)?,\s*(-?[\d.]+)(?:px)?/);
  if (m) return [parseFloat(m[1]), parseFloat(m[2])];
  return [0, 0];
}

function isZeroTranslate(str) {
  const t = parseTranslate(str);
  return Math.abs(t[0]) < 0.5 && Math.abs(t[1]) < 0.5;
}

function computeOutOfFlow(el) {
  return !isZeroTranslate(el.style.transform);
}

// --- Moveable lifecycle ---

function createMoveable(el) {
  const wrapper = document.createElement("div");
  wrapper.className = "hyp-moveable-wrapper-move";
  wrapper.id = "hyp-moveable-wrapper-move";
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
    draggable: true,
    resizable: false,
    edge: false,
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

function onDragStart(e) {
  isDragging = true;
  const el = e.target;
  beforeTransform = el.style.transform || "";
  baseTranslate = parseTranslate(beforeTransform);
}

function onDrag(e) {
  const el = e.target;
  const [dx, dy] = e.translate;
  const newX = baseTranslate[0] + dx;
  const newY = baseTranslate[1] + dy;
  el.style.transform = `translate(${newX}px, ${newY}px)`;
}

function onDragEnd() {
  isDragging = false;
  const el = byId(activeHypId);
  if (!el) {
    beforeTransform = "";
    baseTranslate = [0, 0];
    return;
  }

  const afterTransform = el.style.transform || "";

  // Only commit if transform actually changed
  if (beforeTransform !== afterTransform && activeHypId) {
    const cmd = makeMoveCommand(activeHypId, beforeTransform, afterTransform);
    historyPush(cmd);

    emit("geometry-changed", {
      hypId: activeHypId,
      prop: "transform",
      before: beforeTransform,
      after: afterTransform,
    });

    const outOfFlow = computeOutOfFlow(el);
    emit("out-of-flow", { hypId: activeHypId, bool: outOfFlow });
  }

  beforeTransform = "";
  baseTranslate = [0, 0];
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
          moveableInstance.on("dragStart", onDragStart);
          moveableInstance.on("drag", onDrag);
          moveableInstance.on("dragEnd", onDragEnd);
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
      moveableInstance.on("dragStart", onDragStart);
      moveableInstance.on("drag", onDrag);
      moveableInstance.on("dragEnd", onDragEnd);

      window.addEventListener("scroll", onViewportChange);
      window.addEventListener("resize", onViewportChange);

      startPolling();
    })
    .catch((err) => {
      emit("error", { scope: "move", message: String(err) });
      end();
    });
}

export function end() {
  if (isDragging) {
    // Commit any in-flight drag before tearing down
    const el = byId(activeHypId);
    if (el) {
      const afterTransform = el.style.transform || "";
      if (beforeTransform !== afterTransform && activeHypId) {
        const cmd = makeMoveCommand(
          activeHypId,
          beforeTransform,
          afterTransform
        );
        historyPush(cmd);
        emit("geometry-changed", {
          hypId: activeHypId,
          prop: "transform",
          before: beforeTransform,
          after: afterTransform,
        });
        const outOfFlow = computeOutOfFlow(el);
        emit("out-of-flow", { hypId: activeHypId, bool: outOfFlow });
      }
    }
    isDragging = false;
    beforeTransform = "";
    baseTranslate = [0, 0];
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
