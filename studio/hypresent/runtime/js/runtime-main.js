import { emit, register } from "/runtime/js/bridge-iframe.js";
import { tag, byId } from "./element-registry.js";
import { select, clear, current, onSelectionChange } from "./selection.js";
import { undo, redo, state, push as historyPush } from "./history.js";
import { serialize } from "./serializer.js";
import { apply as applyFormat, snapshotSelection as formatSnapshot, applyAlign } from "./text-format.js";
import { resize as makeResizeCommand, move as makeMoveCommand, deleteElement as makeDeleteCommand, align as makeAlignCommand } from "./commands.js";
import { mount as interactionMount, unmount as interactionUnmount, remount as interactionRemount, isActive as interactionIsActive } from "./interaction.js";
import { readPalette, applyToken, applyElement, readElementColors } from "./color.js";
import {
  load as loadComments,
  toJson as commentsToJson,
  add as addComment,
  reply as replyComment,
  resolve as resolveComment,
  editComment as editComment,
  deleteComment as deleteComment,
  editReply as editReply,
  deleteReply as deleteReply,
  threads as getThreads,
  setAgentInstruction as setAgentInstruction,
  reanchorAfterMove as reanchorComments,
} from "./comments.js";
import "./text-edit.js";
import { initShortcuts } from "./shortcuts.js";
import { copy as clipboardCopy, hasContent as clipboardHasContent } from "./clipboard.js";
import { pasteFloat as doPasteFloat, pasteIntoLayout as doPasteLayout } from "./paste.js";

let activeTool = "edit";

// --- Paged-document navigation -------------------------------------------
// Multi-page documents (dashboards, tabbed views) keep inactive pages in the
// DOM but hidden via the `hidden` attribute. scrollIntoView is a no-op on an
// element inside a display:none subtree, so navigating to a comment whose
// anchor lives on an inactive page does nothing. revealPagedAncestors makes
// the anchor's hidden ancestors visible BEFORE scrolling.

function classTokens(el) {
  return (el.getAttribute("class") || "")
    .trim()
    .split(/\s+/)
    .filter((c) => c && !c.startsWith("hyp-"));
}

function sharesClass(aTokens, bTokens) {
  return aTokens.some((t) => bTokens.includes(t));
}

// Try the document's OWN navigation: a control (e.g. a nav link) whose target
// hash points at this page. Clicking it runs the document's handler, which
// updates page visibility AND its own nav state (active highlight) correctly.
// Returns true only if the page is no longer hidden afterward.
function tryDocumentNav(page) {
  if (!page.id) return false;
  let control = null;
  try {
    control = document.querySelector(
      `a[href="#${CSS.escape(page.id)}"], [data-target="#${CSS.escape(page.id)}"]`
    );
  } catch (_e) {
    control = null;
  }
  if (!control) return false;
  control.click();
  return !page.hasAttribute("hidden");
}

// Fallback: directly un-hide the page, re-hiding the sibling page(s) that were
// visible (same tag + a shared class token) so only one page shows.
function revealByAttribute(page) {
  const parent = page.parentElement;
  if (parent) {
    const pageTokens = classTokens(page);
    for (const sib of parent.children) {
      if (sib === page || sib.nodeType !== 1) continue;
      if (sib.tagName !== page.tagName) continue;
      if (sib.hasAttribute("hidden")) continue;
      if (sharesClass(pageTokens, classTokens(sib))) sib.setAttribute("hidden", "");
    }
  }
  page.removeAttribute("hidden");
}

function revealPagedAncestors(el) {
  const hidden = [];
  let cur = el;
  while (cur && cur !== document.documentElement) {
    if (cur.nodeType === 1 && cur.hasAttribute("hidden")) hidden.push(cur);
    cur = cur.parentElement;
  }
  // Outermost first, so an outer nav click can resolve inner pages too.
  for (let i = hidden.length - 1; i >= 0; i--) {
    const page = hidden[i];
    if (!page.hasAttribute("hidden")) continue; // already revealed
    if (!tryDocumentNav(page)) revealByAttribute(page);
  }
}

function boot() {
  // 1. Build registry: tag editable elements with data-hyp-id
  tag();

  // Wire selection → combined interaction (R09): registered here, after all
  // modules are fully evaluated, so onSelectionChange is guaranteed defined.
  onSelectionChange((info) => {
    if (info && info.hypId) {
      if (interactionIsActive()) interactionRemount(info.hypId);
      else interactionMount(info.hypId);
    } else {
      interactionUnmount();
    }
  });

  // 2. selection.js and history.js self-activate on import (click / keyboard
  //    listeners). We wire their programatic APIs into the bridge so the parent
  //    can invoke them remotely.

  register("serialize", () => {
    return { html: serialize() };
  });

  register("undo", () => {
    undo();
    return state();
  });

  register("redo", () => {
    redo();
    return state();
  });

  register("get-selection", () => {
    return current();
  });

  register("select", (payload) => {
    if (payload && payload.hypId) {
      const el = byId(payload.hypId);
      // Reveal the anchor's page BEFORE selecting/scrolling, so a comment on an
      // inactive page of a multi-page document navigates there instead of
      // silently failing (scrollIntoView no-ops inside a hidden subtree).
      if (el) revealPagedAncestors(el);
      select(payload.hypId);
      if (el && el.scrollIntoView) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      return current();
    }
    return null;
  });

  register("clear-selection", () => {
    clear();
    return null;
  });

  function deleteComponentById(hypId) {
    // Edit-active guard (V3-S10): never delete while a text edit is active.
    const active = document.activeElement;
    if (active && active.getAttribute && active.getAttribute("contenteditable") === "true") {
      return { blocked: "editing" };
    }
    const el = byId(hypId);
    if (!el) {
      return { blocked: "not-found" };
    }
    // Last-region guard (V3-S7): never delete the only remaining top-level region.
    if (el.parentElement === document.body) {
      const bodyRegions = Array.from(document.body.children).filter((c) =>
        c.getAttribute("data-hyp-id")
      );
      if (bodyRegions.length <= 1 && bodyRegions[0] === el) {
        return { blocked: "last-region" };
      }
    }
    // V3-S8: reanchor after BOTH do() and undo() so deleted-element threads go unanchored
    // on delete AND re-anchor on undo (the Undo path runs cmd.undo() only).
    const cmd = makeDeleteCommand(hypId);
    historyPush({
      do() { cmd.do(); reanchorComments(); },
      undo() { cmd.undo(); reanchorComments(); },
      label: cmd.label,
    });
    clear();              // selection cleared → the observer unmounts the Moveable (V3-S9)
    return { deleted: hypId };
  }

  register("delete-element", (payload) => {
    if (!payload || !payload.hypId) {
      throw new Error("delete-element: missing hypId");
    }
    return deleteComponentById(payload.hypId);
  });

  register("format", (payload) => {
    if (!payload || !payload.op) {
      throw new Error("format: missing op");
    }
    const ok = applyFormat(payload.op, current());
    return { ok };
  });

  register("format-snapshot", () => {
    // R8: snapshot the live iframe Selection BEFORE the toolbar focus shift, so
    // font-size can restore it on the next apply() and bump one span repeatedly.
    formatSnapshot();
    return { ok: true };
  });

  register("align", (payload) => {
    if (!payload || !payload.axis || !payload.value) {
      throw new Error("align: missing axis or value");
    }
    const info = current();
    if (!info || !info.hypId) return { ok: false, reason: "no-selection" };
    const el = byId(info.hypId);
    if (!el) return { ok: false, reason: "not-found" };
    const cmd = makeAlignCommand(info.hypId, () => applyAlign(el, payload.axis, payload.value));
    historyPush(cmd);
    return { ok: true };
  });

  register("set-tool", (payload) => {
    // Compat shim (S2): the modeless model auto-mounts one combined Moveable on
    // selection. 'edit'/none unmounts; 'resize'/'move' mount on the current selection.
    const tool = payload && payload.tool ? payload.tool : "edit";
    const info = current();
    if (tool === "resize" || tool === "move") {
      if (info && info.hypId) interactionMount(info.hypId);
    } else {
      interactionUnmount();
    }
    return { tool };
  });

  register("resize-commit", (payload) => {
    if (!payload || !payload.hypId || !payload.before || !payload.after) {
      throw new Error("resize-commit: missing payload fields");
    }
    const cmd = makeResizeCommand(payload.hypId, payload.before, payload.after);
    historyPush(cmd);
    return { undoToken: true };
  });

  register("move-commit", (payload) => {
    if (!payload || !payload.hypId) {
      throw new Error("move-commit: missing payload fields");
    }
    const before = payload.before ?? "";
    const after = payload.after ?? "";
    const cmd = makeMoveCommand(payload.hypId, before, after);
    historyPush(cmd);
    return { undoToken: true };
  });

  register("palette-read", () => {
    return readPalette();
  });

  register("apply-color", (payload) => {
    if (!payload || !payload.scope || !payload.target || payload.value === undefined) {
      throw new Error("apply-color: missing scope, target, or value");
    }
    if (payload.scope === "token") {
      applyToken(payload.target, payload.value);
    } else if (payload.scope === "element") {
      const prop = payload.prop || "color";
      applyElement(payload.target, prop, payload.value);
    } else {
      throw new Error(`apply-color: unknown scope '${payload.scope}'`);
    }
    return { undoToken: true };
  });

  register("element-color-read", (payload) => {
    if (!payload || !payload.hypId) {
      throw new Error("element-color-read: missing hypId");
    }
    return readElementColors(payload.hypId);
  });

  // Comments: load existing island before emitting ready
  const existingIsland = document.getElementById("hyp-comments");
  let islandData = [];
  if (existingIsland) {
    try {
      islandData = JSON.parse(existingIsland.textContent.trim());
      if (!Array.isArray(islandData)) islandData = [];
    } catch {
      islandData = [];
    }
  }
  loadComments(islandData);

  register("add-comment", (payload) => {
    if (!payload || !payload.hypId || !payload.body || !payload.author) {
      throw new Error("add-comment: missing hypId, body, or author");
    }
    return addComment(payload.hypId, payload.body, payload.author, payload.agentInstruction === true);
  });

  register("reply-comment", (payload) => {
    if (!payload || !payload.commentId || !payload.body || !payload.author) {
      throw new Error("reply-comment: missing commentId, body, or author");
    }
    return replyComment(payload.commentId, payload.body, payload.author);
  });

  register("edit-comment", (payload) => {
    if (!payload || !payload.commentId || typeof payload.body !== "string") {
      throw new Error("edit-comment: missing commentId or body");
    }
    return editComment(payload.commentId, payload.body);
  });

  register("delete-comment", (payload) => {
    if (!payload || !payload.commentId) {
      throw new Error("delete-comment: missing commentId");
    }
    return deleteComment(payload.commentId);
  });

  register("edit-reply", (payload) => {
    if (!payload || !payload.commentId || typeof payload.replyIndex !== "number" || typeof payload.body !== "string") {
      throw new Error("edit-reply: missing commentId, replyIndex, or body");
    }
    return editReply(payload.commentId, payload.replyIndex, payload.body);
  });

  register("delete-reply", (payload) => {
    if (!payload || !payload.commentId || typeof payload.replyIndex !== "number") {
      throw new Error("delete-reply: missing commentId or replyIndex");
    }
    return deleteReply(payload.commentId, payload.replyIndex);
  });

  register("resolve-comment", (payload) => {
    if (!payload || !payload.commentId) {
      throw new Error("resolve-comment: missing commentId");
    }
    const resolved = payload.resolved !== undefined ? payload.resolved : true;
    return resolveComment(payload.commentId, resolved);
  });

  register("tag-agent", (payload) => {
    if (!payload || !payload.commentId) {
      throw new Error("tag-agent: missing commentId");
    }
    return setAgentInstruction(payload.commentId, payload.agentInstruction === true);
  });

  register("comments-read", () => {
    return { threads: getThreads() };
  });

  register("copy", () => { const info = current(); if (!info || !info.hypId) return { copied: false }; const el = byId(info.hypId); if (!el) return { copied: false }; clipboardCopy(el); return { copied: true }; });
  register("paste", (payload) => { doPasteFloat((payload && payload.x) || 0, (payload && payload.y) || 0); return { ok: true, hasContent: clipboardHasContent() }; });
  register("paste-into-layout", (payload) => { doPasteLayout((payload && payload.x) || 0, (payload && payload.y) || 0); return { ok: true }; });

  // Preserve existing window.hyp exposure
  window.hyp = {
    command(type, payload) {
      return { ack: true, type, payload };
    },
    version: "0.0.0-stub",
    comments: {
      toJson: commentsToJson,
    },
  };

  initShortcuts({
    bold: () => applyFormat("bold", current()),
    italic: () => applyFormat("italic", current()),
    deleteComponent: () => { const info = current(); if (info && info.hypId) deleteComponentById(info.hypId); },
    requestComment: () => emit("shortcut", { action: "comment" }),
    requestAgentComment: () => emit("shortcut", { action: "comment-agent" }),
    requestSave: () => emit("shortcut", { action: "save" }),
    requestSaveAs: () => emit("shortcut", { action: "save-as" }),
    requestShortcutsHelp: () => emit("shortcut", { action: "show-shortcuts" }),
    copy: () => { const info = current(); if (!info || !info.hypId) return false; const el = byId(info.hypId); if (!el) return false; clipboardCopy(el); return true; },
    pasteFloat: (x, y) => doPasteFloat(x, y),
    pasteLayout: (x, y) => doPasteLayout(x, y),
  });

  // 3. Emit ready so the parent shell enables controls
  const palette = readPalette();
  emit("ready", { tokens: palette.tokens });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}
