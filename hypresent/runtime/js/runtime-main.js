import { emit, register } from "/runtime/js/bridge-iframe.js";
import { tag, regions, byId } from "./element-registry.js";
import { select, clear, current, onSelectionChange } from "./selection.js";
import { undo, redo, state, push as historyPush } from "./history.js";
import { serialize } from "./serializer.js";
import { apply as applyFormat, snapshotSelection as formatSnapshot } from "./text-format.js";
import { resize as makeResizeCommand, move as makeMoveCommand, deleteElement as makeDeleteCommand } from "./commands.js";
import { mount as interactionMount, unmount as interactionUnmount, remount as interactionRemount, isActive as interactionIsActive } from "./interaction.js";
import { readPalette, applyToken, applyElement, readElementColors } from "./color.js";
import {
  load as loadComments,
  toJson as commentsToJson,
  add as addComment,
  reply as replyComment,
  resolve as resolveComment,
  threads as getThreads,
  setAgentInstruction as setAgentInstruction,
  reanchorAfterMove as reanchorComments,
} from "./comments.js";
import "./text-edit.js";

let activeTool = "edit";

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
      select(payload.hypId);
      const el = byId(payload.hypId);
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

  register("delete-element", (payload) => {
    if (!payload || !payload.hypId) {
      throw new Error("delete-element: missing hypId");
    }
    // Edit-active guard (V3-S10): never delete while a text edit is active.
    const active = document.activeElement;
    if (active && active.getAttribute && active.getAttribute("contenteditable") === "true") {
      return { blocked: "editing" };
    }
    const el = byId(payload.hypId);
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
    const cmd = makeDeleteCommand(payload.hypId);
    historyPush({
      do() { cmd.do(); reanchorComments(); },
      undo() { cmd.undo(); reanchorComments(); },
      label: cmd.label,
    });
    clear();              // selection cleared → the observer unmounts the Moveable (V3-S9)
    return { deleted: payload.hypId };
  });

  register("format", (payload) => {
    if (!payload || !payload.op) {
      throw new Error("format: missing op");
    }
    const ok = applyFormat(payload.op);
    return { ok };
  });

  register("format-snapshot", () => {
    // R8: snapshot the live iframe Selection BEFORE the toolbar focus shift, so
    // font-size can restore it on the next apply() and bump one span repeatedly.
    formatSnapshot();
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

  // 3. Emit ready so the parent shell enables controls
  const palette = readPalette();
  emit("ready", { tokens: palette.tokens, sections: regions() });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}
