/**
 * runtime/js/history.js
 *
 * Unified undo/redo stack.
 * Single linear stack of commands covering ALL operation types (text, format,
 * resize, move, color, comments). Cursor-based; truncates redo tail on new push.
 *
 * Public contract (module-map 03 §4):
 *   push(cmd)   — executes cmd.do(), appends to stack, truncates redo tail
 *   undo()      — invokes cmd.undo() at cursor, moves cursor back
 *   redo()      — re-executes cmd.do() at cursor+1, moves cursor forward
 *   state() → {cursor, canUndo, canRedo}
 *
 * Emits (via bridge-iframe.js):
 *   history-changed {cursor, canUndo, canRedo}
 */

import { emit } from "./bridge-iframe.js";

// --- State ---

const stack = [];
let cursor = -1; // index of most recently executed command; -1 = empty

// --- Helpers ---

function notify() {
  emit("history-changed", state());
}

function isNativeFormControl(el) {
  if (!el || !el.tagName) return false;
  const tag = el.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select";
}

// --- Public API ---

export function push(cmd) {
  if (!cmd || typeof cmd.do !== "function" || typeof cmd.undo !== "function") {
    throw new Error("history.push: command must have do() and undo() methods");
  }

  // Truncate redo tail
  if (cursor < stack.length - 1) {
    stack.splice(cursor + 1);
  }

  cmd.do();
  stack.push(cmd);
  cursor = stack.length - 1;
  notify();
}

export function undo() {
  if (cursor < 0) return;
  const cmd = stack[cursor];
  cmd.undo();
  cursor -= 1;
  notify();
}

export function redo() {
  if (cursor >= stack.length - 1) return;
  const cmd = stack[cursor + 1];
  cmd.do();
  cursor += 1;
  notify();
}

export function state() {
  return {
    cursor,
    canUndo: cursor >= 0,
    canRedo: cursor < stack.length - 1,
  };
}

// --- Keyboard shortcuts ---
// Scoped so they do not hijack the document's own shortcuts inappropriately:
// we avoid intercepting when focus is inside a native form control
// (input/textarea/select), letting the browser's native undo/redo work there.

document.addEventListener("keydown", (event) => {
  const mod = event.ctrlKey || event.metaKey;
  if (!mod) return;

  const key = event.key.toLowerCase();

  // Ctrl+Z (no Shift) = undo
  if (key === "z" && !event.shiftKey) {
    if (isNativeFormControl(event.target)) return;
    event.preventDefault();
    undo();
    return;
  }

  // Ctrl+Shift+Z = redo
  if (key === "z" && event.shiftKey) {
    if (isNativeFormControl(event.target)) return;
    event.preventDefault();
    redo();
    return;
  }

  // Ctrl+Y = redo
  if (key === "y") {
    if (isNativeFormControl(event.target)) return;
    event.preventDefault();
    redo();
    return;
  }
});
