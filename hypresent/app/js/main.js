import Coloris from "/app/js/vendor/coloris.min.js";
import { createBridge } from "/app/js/bridge/bridge-parent.js";
import { openFile } from "/app/js/shell/file-controls.js";
import { createColorPopover } from "/app/js/shell/color-popover.js";
import { saveAs } from "/app/js/api-client.js";

let bridge = null;
let isDirty = false;
let lastOpenedPath = "";
let outlineRegions = [];
let activeOutlineHypId = null;
let undoBtn = null;
let redoBtn = null;

const AUTHOR_KEY = "hypresent-comment-author";

function setStatus(msg, type = "") {
  const el = document.getElementById("shell-status");
  if (!el) return;
  el.textContent = msg;
  el.className = "shell-status" + (type ? " " + type : "");
}

function deriveSaveDefault(openPath) {
  if (!openPath) return "";
  const sep = openPath.lastIndexOf("\\") >= 0 ? "\\" : "/";
  const idx = openPath.lastIndexOf(sep);
  const dir = idx >= 0 ? openPath.slice(0, idx) : "";
  const name = idx >= 0 ? openPath.slice(idx + 1) : openPath;
  let defaultName;
  if (/\.html$/i.test(name)) {
    defaultName = name.replace(/\.html$/i, "-edited.html");
  } else {
    defaultName = name + "-edited.html";
  }
  return dir ? dir + sep + defaultName : defaultName;
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
  replyBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    const text = prompt("Reply:");
    if (!text || !text.trim()) return;
    const author = getAuthorName();
    try {
      await bridge.command("reply-comment", {
        commentId: thread.id,
        body: text.trim(),
        author,
      });
      await refreshCommentPanel();
    } catch (err) {
      console.error("Reply failed:", err.message);
    }
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

function renderOutline(regions) {
  outlineRegions = regions || [];
  activeOutlineHypId = null;
  const container = document.getElementById("outline-list");
  if (!container) return;
  container.innerHTML = "";

  if (outlineRegions.length === 0) {
    const empty = document.createElement("div");
    empty.className = "outline-empty";
    empty.textContent = "No regions detected";
    container.appendChild(empty);
    return;
  }

  for (const region of outlineRegions) {
    const item = document.createElement("div");
    item.className = "outline-item";
    item.textContent = region.label || region.hypId;
    item.dataset.hypId = region.hypId;
    item.addEventListener("click", () => {
      if (!bridge) return;
      bridge.command("select", { hypId: region.hypId }).catch((err) => {
        console.error("Select failed:", err.message);
      });
    });
    container.appendChild(item);
  }
}

function setActiveOutline(hypId) {
  activeOutlineHypId = hypId || null;
  const container = document.getElementById("outline-list");
  if (!container) return;
  container.querySelectorAll(".outline-item").forEach((el) => {
    el.classList.toggle("outline-item-active", el.dataset.hypId === activeOutlineHypId);
  });
}

function ensureBridge(iframe) {
  if (bridge) bridge.destroy();
  bridge = createBridge(iframe);
  bridge.on("ready", async (payload) => {
    console.info("runtime ready");
    renderOutline(payload && payload.sections ? payload.sections : []);
    await refreshCommentPanel();
  });

  bridge.on("selection-changed", (payload) => {
    setActiveOutline(payload && payload.hypId ? payload.hypId : null);
  });

  bridge.on("dirty-changed", (payload) => {
    isDirty = payload && payload.dirty ? true : false;
    document.title = isDirty ? "hypresent *" : "hypresent";
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
  const pathInput = document.querySelector("#open-path-input");
  const saveAsInput = document.querySelector("#save-as-path-input");
  if (!openBtn || !pathInput) {
    console.error("Open control not found");
  } else {
    openBtn.addEventListener("click", async () => {
      const path = pathInput.value.trim();
      if (!path) return;
      lastOpenedPath = path;
      if (saveAsInput) {
        saveAsInput.value = deriveSaveDefault(path);
      }
      try {
        await openFile(path, iframe);
        ensureBridge(iframe);
        setStatus("");
      } catch (err) {
        console.error("Open failed:", err.message);
        setStatus("Open failed: " + err.message, "error");
      }
    });
  }

  const saveAsBtn = document.querySelector("#save-as-btn");
  if (saveAsBtn && saveAsInput) {
    saveAsBtn.addEventListener("click", async () => {
      if (!bridge) {
        setStatus("No document open.", "error");
        return;
      }
      const path = saveAsInput.value.trim();
      if (!path) {
        setStatus("Please enter a save path.", "error");
        return;
      }
      let result;
      try {
        result = await bridge.command("serialize");
      } catch (err) {
        setStatus("Serialize failed: " + err.message, "error");
        return;
      }
      if (!result || result.html == null) {
        setStatus("Document serialization returned null.", "error");
        return;
      }
      try {
        const data = await saveAs(path, result.html);
        isDirty = false;
        document.title = "hypresent";
        setStatus("Saved to " + (data.path || path), "success");
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
      iframe.contentWindow.focus();
    });
    btn.addEventListener("click", () => {
      if (!bridge) return;
      bridge.command("format", { op }).catch((err) => {
        console.error("Format failed:", err.message);
      });
    });
  }

  // Wire toolbar color button
  const colorBtn = document.getElementById("color-btn");
  if (colorBtn) {
    colorBtn.addEventListener("click", () => {
      const panel = document.querySelector(".shell-panel");
      if (!panel) return;
      // Open the first color input in the panel (triggers Coloris)
      const firstInput = panel.querySelector(".hyp-coloris-input");
      if (firstInput) {
        firstInput.click();
        firstInput.focus();
      }
    });
  }

  // Wire toolbar comment button
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
      const body = prompt("Comment:");
      if (!body || !body.trim()) return;
      const author = getAuthorName();
      try {
        await bridge.command("add-comment", {
          hypId: sel.hypId,
          body: body.trim(),
          author,
        });
        await refreshCommentPanel();
      } catch (err) {
        console.error("Add comment failed:", err.message);
      }
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
    undoBtn.addEventListener("click", () => {
      if (!bridge) return;
      bridge.command("undo").catch((err) => {
        console.error("Undo failed:", err.message);
      });
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
