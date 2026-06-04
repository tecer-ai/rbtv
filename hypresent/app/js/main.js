import Coloris from "/app/js/vendor/coloris.min.js";
import { createBridge } from "/app/js/bridge/bridge-parent.js";
import { openViaDialog } from "/app/js/shell/file-controls.js";
import { createColorPopover } from "/app/js/shell/color-popover.js";
import { openComposer } from "/app/js/shell/comment-composer.js";
import { dialogSaveAs, save } from "/app/js/api-client.js";

let bridge = null;
let isDirty = false;
let isEditingNow = false;   // R3 edit-guard: cached from runtime 'edit-state' events

let undoBtn = null;
let redoBtn = null;

const AUTHOR_KEY = "hypresent-comment-author";

function setStatus(msg, type = "") {
  const el = document.getElementById("shell-status");
  if (!el) return;
  el.textContent = msg;
  el.className = "shell-status" + (type ? " " + type : "");
}

function getAuthorName() {
  let name = localStorage.getItem(AUTHOR_KEY);
  if (!name) {
    name = prompt("Enter your name for comments:");
    if (name && name.trim()) {
      name = name.trim();
      localStorage.setItem(AUTHOR_KEY, name);
    } else {
      name = "Anonymous";
    }
  }
  return name;
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function createThreadEl(thread, isUnanchored = false) {
  const div = document.createElement("div");
  div.className = "comment-thread" + (thread.resolved ? " comment-thread-resolved" : "");
  if (isUnanchored) div.classList.add("comment-thread-unanchored");
  div.dataset.commentId = thread.id;

  const header = document.createElement("div");
  header.className = "comment-thread-header";

  const authorSpan = document.createElement("span");
  authorSpan.className = "comment-author";
  authorSpan.textContent = thread.author;

  const timeSpan = document.createElement("span");
  timeSpan.className = "comment-time";
  timeSpan.textContent = formatTime(thread.createdAt);

  header.appendChild(authorSpan);
  header.appendChild(timeSpan);
  div.appendChild(header);

  const body = document.createElement("div");
  body.className = "comment-body";
  body.textContent = thread.body;
  div.appendChild(body);

  if (thread.contextText && isUnanchored) {
    const ctx = document.createElement("div");
    ctx.className = "comment-context";
    ctx.textContent = `“${thread.contextText}”`;
    div.appendChild(ctx);
  }

  if (thread.replies && thread.replies.length > 0) {
    const repliesDiv = document.createElement("div");
    repliesDiv.className = "comment-replies";
    for (const r of thread.replies) {
      const rDiv = document.createElement("div");
      rDiv.className = "comment-reply";

      const rHeader = document.createElement("div");
      const rAuthor = document.createElement("span");
      rAuthor.className = "comment-author";
      rAuthor.textContent = r.author;
      const rTime = document.createElement("span");
      rTime.className = "comment-time";
      rTime.textContent = formatTime(r.createdAt);
      rHeader.appendChild(rAuthor);
      rHeader.appendChild(rTime);
      rDiv.appendChild(rHeader);

      const rBody = document.createElement("div");
      rBody.className = "comment-reply-body";
      rBody.textContent = r.body;
      rDiv.appendChild(rBody);

      repliesDiv.appendChild(rDiv);
    }
    div.appendChild(repliesDiv);
  }

  const actions = document.createElement("div");
  actions.className = "comment-actions";

  const replyBtn = document.createElement("button");
  replyBtn.className = "comment-action-btn";
  replyBtn.textContent = "Reply";
  replyBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const author = getAuthorName();
    openComposer({
      rect: thread.rect || null,
      mode: "reply",
      commentId: thread.id,
      onSubmit: async (text) => {
        try {
          await bridge.command("reply-comment", {
            commentId: thread.id,
            body: text,
            author,
          });
          await refreshCommentPanel();
        } catch (err) {
          console.error("Reply failed:", err.message);
        }
      },
    });
  });
  actions.appendChild(replyBtn);

  const resolveBtn = document.createElement("button");
  resolveBtn.className = "comment-action-btn";
  resolveBtn.textContent = thread.resolved ? "Reopen" : "Resolve";
  resolveBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    try {
      await bridge.command("resolve-comment", {
        commentId: thread.id,
        resolved: !thread.resolved,
      });
      await refreshCommentPanel();
    } catch (err) {
      console.error("Resolve failed:", err.message);
    }
  });
  actions.appendChild(resolveBtn);

  const agentLabel = document.createElement("label");
  agentLabel.className = "comment-agent-toggle";
  const agentCb = document.createElement("input");
  agentCb.type = "checkbox";
  agentCb.checked = thread.agentInstruction === true;
  agentCb.addEventListener("click", (e) => e.stopPropagation());
  agentCb.addEventListener("change", async (e) => {
    e.stopPropagation();
    try {
      await bridge.command("tag-agent", {
        commentId: thread.id,
        agentInstruction: agentCb.checked,
      });
      await refreshCommentPanel();
    } catch (err) {
      console.error("tag-agent failed:", err.message);
    }
  });
  agentLabel.appendChild(agentCb);
  agentLabel.appendChild(document.createTextNode(" For agents"));
  actions.appendChild(agentLabel);

  div.appendChild(actions);

  if (!isUnanchored && thread.hypId) {
    div.addEventListener("click", () => {
      bridge.command("select", { hypId: thread.hypId }).catch((err) => {
        console.error("Select failed:", err.message);
      });
    });
  }

  return div;
}

function renderCommentPanel(threads) {
  const container = document.getElementById("comment-threads");
  const unanchoredContainer = document.getElementById("comment-unanchored");
  if (!container) return;

  container.innerHTML = "";
  if (unanchoredContainer) unanchoredContainer.innerHTML = "";

  const anchored = threads.filter((t) => !t.unanchored);
  const unanchored = threads.filter((t) => t.unanchored);

  for (const thread of anchored) {
    container.appendChild(createThreadEl(thread, false));
  }

  if (unanchored.length > 0 && unanchoredContainer) {
    const header = document.createElement("div");
    header.className = "comment-unanchored-header";
    header.textContent = "Unanchored";
    unanchoredContainer.appendChild(header);
    for (const thread of unanchored) {
      unanchoredContainer.appendChild(createThreadEl(thread, true));
    }
  }
}

async function refreshCommentPanel() {
  if (!bridge) return;
  try {
    const result = await bridge.command("comments-read");
    renderCommentPanel(result.threads || []);
  } catch (err) {
    console.error("Failed to read comments:", err.message);
  }
}

function ensureBridge(iframe) {
  if (bridge) bridge.destroy();
  bridge = createBridge(iframe);
  bridge.on("ready", async (payload) => {
    console.info("runtime ready");
    await refreshCommentPanel();
  });

  bridge.on("selection-changed", (payload) => {
    if (window.__hypUpdateAlignButtons) {
      window.__hypUpdateAlignButtons(payload && payload.alignCaps ? payload.alignCaps : null);
    }
  });

  bridge.on("dirty-changed", (payload) => {
    isDirty = payload && payload.dirty ? true : false;
    document.title = isDirty ? "hypresent *" : "hypresent";
  });

  bridge.on("edit-state", (payload) => {
    isEditingNow = !!(payload && payload.editing);
  });

  bridge.on("comment-anchor-clicked", (payload) => {
    const panel = document.getElementById("shell-panel");
    if (!panel) return;
    panel.querySelectorAll(".comment-thread").forEach((el) => {
      el.classList.remove("comment-thread-highlight");
    });
    const target = panel.querySelector(`[data-comment-id="${payload.commentId}"]`);
    if (target) {
      target.classList.add("comment-thread-highlight");
      target.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });

  bridge.on("history-changed", (payload) => {
    if (undoBtn) undoBtn.disabled = !(payload && payload.canUndo);
    if (redoBtn) redoBtn.disabled = !(payload && payload.canRedo);
  });

  const panel = document.getElementById("shell-panel");
  if (panel) {
    createColorPopover({ bridge, panelEl: panel });
  }

  return bridge;
}

document.addEventListener("DOMContentLoaded", () => {
  const toolbar = document.querySelector(".shell-toolbar");
  const main = document.querySelector(".shell-main");
  const mount = document.querySelector(".doc-frame-mount");
  const iframe = document.querySelector(".doc-frame");

  if (!toolbar || !main || !mount) {
    console.error("Shell DOM not fully mounted");
    return;
  }

  console.info("Shell DOM mounted");
  console.info("Moveable available:", typeof window.Moveable === "function");
  console.info("Coloris available:", typeof Coloris);

  // Initialize Coloris once. Dynamic inputs are wrapped later via Coloris.wrap().
  try {
    Coloris.init();
    Coloris({ el: ".hyp-coloris-input", alpha: true, format: "hex" });
  } catch (err) {
    console.warn("Coloris init failed (non-critical):", err.message);
  }

  (async () => {
    try {
      const { default: purify } = await import("/app/js/vendor/purify.min.js");
      console.info("DOMPurify available:", typeof purify);
    } catch {
      console.info("DOMPurify not loaded (optional)");
    }
  })();

  const openBtn = document.querySelector("#open-btn");
  if (!openBtn) {
    console.error("Open control not found");
  } else {
    openBtn.addEventListener("click", async () => {
      try {
        const result = await openViaDialog(iframe);
        if (!result) return; // cancelled
        ensureBridge(iframe);
        setStatus("");
      } catch (err) {
        console.error("Open failed:", err.message);
        setStatus("Open failed: " + err.message, "error");
      }
    });
  }

  async function serializeDoc() {
    if (!bridge) { setStatus("No document open.", "error"); return null; }
    let result;
    try {
      result = await bridge.command("serialize");
    } catch (err) {
      setStatus("Serialize failed: " + err.message, "error");
      return null;
    }
    if (!result || result.html == null) {
      setStatus("Document serialization returned null.", "error");
      return null;
    }
    return result.html;
  }

  const saveBtn = document.querySelector("#save-btn");
  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const html = await serializeDoc();
      if (html == null) return;
      try {
        const data = await save(html);
        if (data && data.no_open_file) {
          // No file open yet → fall back to Save As dialog.
          const sa = await dialogSaveAs(html);
          if (sa && sa.cancelled) return;
          isDirty = false; document.title = "hypresent";
          setStatus("Saved to " + (sa.path || ""), "success");
          return;
        }
        isDirty = false; document.title = "hypresent";
        setStatus("Saved to " + (data.path || ""), "success");
      } catch (err) {
        setStatus("Save failed: " + err.message, "error");
      }
    });
  }

  const saveAsBtn = document.querySelector("#save-as-btn");
  if (saveAsBtn) {
    saveAsBtn.addEventListener("click", async () => {
      const html = await serializeDoc();
      if (html == null) return;
      try {
        const data = await dialogSaveAs(html);
        if (data && data.cancelled) return; // user cancelled
        isDirty = false; document.title = "hypresent";
        setStatus("Saved to " + (data.path || ""), "success");
      } catch (err) {
        setStatus("Save failed: " + err.message, "error");
      }
    });
  }

  // Wire format toolbar buttons (T11)
  const formatButtons = [
    { id: "fmt-bold", op: "bold" },
    { id: "fmt-italic", op: "italic" },
    { id: "fmt-font-inc", op: "fontInc" },
    { id: "fmt-font-dec", op: "fontDec" },
  ];

  for (const { id, op } of formatButtons) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.addEventListener("mousedown", (e) => {
      e.preventDefault();
      // R8: snapshot the iframe selection BEFORE focus() collapses it, so
      // font-size can restore the word and bump one span on every press.
      if (bridge) {
        bridge.command("format-snapshot").catch(() => {});
      }
      iframe.contentWindow.focus();
    });
    btn.addEventListener("click", () => {
      if (!bridge) return;
      bridge.command("format", { op }).catch((err) => {
        console.error("Format failed:", err.message);
      });
    });
  }

  // Wire the 6 alignment buttons (R7). Horizontal: left/center/right. Vertical:
  // top/middle/bottom. Disabled state is set reactively from selection-changed.
  const alignButtons = [
    { id: "align-left", axis: "h", value: "left", vertical: false },
    { id: "align-center", axis: "h", value: "center", vertical: false },
    { id: "align-right", axis: "h", value: "right", vertical: false },
    { id: "align-top", axis: "v", value: "top", vertical: true },
    { id: "align-middle", axis: "v", value: "middle", vertical: true },
    { id: "align-bottom", axis: "v", value: "bottom", vertical: true },
  ];
  for (const { id, axis, value } of alignButtons) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.disabled = true; // disabled until something is selected
    btn.addEventListener("click", () => {
      if (!bridge) return;
      bridge.command("align", { axis, value }).catch((err) => {
        console.error("Align failed:", err.message);
      });
    });
  }

  function updateAlignButtons(caps) {
    for (const { id, vertical } of alignButtons) {
      const btn = document.getElementById(id);
      if (!btn) continue;
      if (!caps) {
        btn.disabled = true;
        btn.removeAttribute("title");
        continue;
      }
      if (vertical) {
        btn.disabled = !caps.vertical;
        if (!caps.vertical) {
          btn.title = "Vertical alignment needs a fixed-height, flex, grid, or table-cell element";
        }
      } else {
        btn.disabled = !caps.horizontal;
      }
    }
  }
  // expose to the selection-changed handler below via a window-scoped ref
  window.__hypUpdateAlignButtons = updateAlignButtons;

  // Wire toolbar delete button (R3): toolbar-only trigger (U14 — NO keyboard path).
  const deleteBtn = document.getElementById("delete-btn");
  if (deleteBtn) {
    // V3-S10 edit-active gate (shell-primary): snapshot editing state on mousedown,
    // BEFORE focus leaves the iframe and text-edit commits/exits on blur. The runtime
    // activeElement check cannot see this (blur fires first) — the mousedown snapshot can.
    let editingAtPress = false;
    deleteBtn.addEventListener("mousedown", () => {
      editingAtPress = isEditingNow;
    });
    deleteBtn.addEventListener("click", async () => {
      if (!bridge) return;
      if (editingAtPress) {
        editingAtPress = false;
        setStatus("Finish editing before deleting the element.", "error");
        return;
      }
      let sel;
      try {
        sel = await bridge.command("get-selection");
      } catch (err) {
        console.error("Get selection failed:", err.message);
        return;
      }
      if (!sel || !sel.hypId) {
        setStatus("Select an element to delete.", "error");
        return;
      }
      try {
        const res = await bridge.command("delete-element", { hypId: sel.hypId });
        if (res && res.blocked === "last-region") {
          setStatus("Cannot delete the last remaining region.", "error");
          return;
        }
        if (res && res.blocked === "editing") {
          setStatus("Finish editing before deleting the element.", "error");
          return;
        }
        if (res && res.blocked) {
          setStatus("Could not delete the selected element.", "error");
          return;
        }
        setStatus("Element deleted.", "success");
        await refreshCommentPanel(); // threads may have moved to Unanchored
      } catch (err) {
        setStatus("Delete failed: " + err.message, "error");
      }
    });
  }

  // Wire toolbar comment button → anchored composer popover (F5)
  const commentBtn = document.getElementById("comment-btn");
  if (commentBtn) {
    commentBtn.addEventListener("click", async () => {
      if (!bridge) return;
      let sel;
      try {
        sel = await bridge.command("get-selection");
      } catch (err) {
        console.error("Get selection failed:", err.message);
        return;
      }
      if (!sel || !sel.hypId) {
        alert("Select an element first to add a comment.");
        return;
      }
      const author = getAuthorName();
      openComposer({
        rect: sel.rect || null,
        mode: "new",
        onSubmit: async (text, agentInstruction) => {
          try {
            await bridge.command("add-comment", {
              hypId: sel.hypId,
              body: text,
              author,
              agentInstruction,
            });
            await refreshCommentPanel();
          } catch (err) {
            console.error("Add comment failed:", err.message);
          }
        },
      });
    });
  }

  // Wire Undo / Redo buttons (no IDs in HTML; select by label text)
  undoBtn = Array.from(document.querySelectorAll(".shell-toolbar button")).find(
    (b) => b.textContent.trim() === "Undo"
  );
  redoBtn = Array.from(document.querySelectorAll(".shell-toolbar button")).find(
    (b) => b.textContent.trim() === "Redo"
  );

  if (undoBtn) {
    undoBtn.addEventListener("click", async () => {
      if (!bridge) return;
      try {
        await bridge.command("undo");
        await refreshCommentPanel(); // undo may re-anchor threads (R3/V3-S8) → re-render panel
      } catch (err) {
        console.error("Undo failed:", err.message);
      }
    });
  }
  if (redoBtn) {
    redoBtn.addEventListener("click", () => {
      if (!bridge) return;
      bridge.command("redo").catch((err) => {
        console.error("Redo failed:", err.message);
      });
    });
  }
});
