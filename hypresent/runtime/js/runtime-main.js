import { emit, register } from "/runtime/js/bridge-iframe.js";
import { tag, regions, byId } from "./element-registry.js";
import { select, clear, current } from "./selection.js";
import { undo, redo, state, push as historyPush } from "./history.js";
import { serialize } from "./serializer.js";
import { apply as applyFormat } from "./text-format.js";
import { resize as makeResizeCommand, move as makeMoveCommand } from "./commands.js";
import { begin as resizeBegin, end as resizeEnd } from "./resize.js";
import { begin as moveBegin, end as moveEnd } from "./move.js";
import { readPalette, applyToken, applyElement } from "./color.js";
import {
  load as loadComments,
  toJson as commentsToJson,
  add as addComment,
  reply as replyComment,
  resolve as resolveComment,
  threads as getThreads,
} from "./comments.js";
import "./text-edit.js";

let activeTool = "edit";

function boot() {
  // 1. Build registry: tag editable elements with data-hyp-id
  tag();

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

  register("format", (payload) => {
    if (!payload || !payload.op) {
      throw new Error("format: missing op");
    }
    const ok = applyFormat(payload.op);
    return { ok };
  });

  register("set-tool", (payload) => {
    if (!payload || !payload.tool) {
      throw new Error("set-tool: missing tool");
    }
    const oldTool = activeTool;
    const newTool = payload.tool;
    activeTool = newTool;

    if (oldTool === "resize") {
      resizeEnd();
    }
    if (oldTool === "move") {
      moveEnd();
    }
    if (newTool === "resize") {
      const info = current();
      if (info) {
        resizeBegin(info.hypId);
      }
    }
    if (newTool === "move") {
      const info = current();
      if (info) {
        moveBegin(info.hypId);
      }
    }
    return { tool: newTool };
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
    return addComment(payload.hypId, payload.body, payload.author);
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
