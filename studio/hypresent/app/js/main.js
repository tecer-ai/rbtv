import Coloris from "/app/js/vendor/coloris.min.js";
import { createBridge } from "/app/js/bridge/bridge-parent.js";
import { openViaDialog, openFile } from "/app/js/shell/file-controls.js";
import { createColorPopover } from "/app/js/shell/color-popover.js";
import { openComposer } from "/app/js/shell/comment-composer.js";
import { createShortcutsHelp } from "/app/js/shell/shortcuts-help.js";
import { confirmSaveOverwrite } from "/app/js/shell/confirm-modal.js";
import { createThemeControls } from "/app/js/shell/theme-controls.js";
import { dialogSaveAs, save } from "/app/js/api-client.js";

let bridge = null;
let builderCrossReady = false;   // runtime live enough to serialize → the Builder tab may
                                 // save-then-switch. Reset per bridge; set on runtime 'ready'.
let isDirty = false;
let docDirty = false;       // authoritative "unsaved edits?" flag — mirrors the Saved/Unsaved
                            // chip via setDocState (the single choke point) and is read by the
                            // beforeunload close-guard. Kept separate from isDirty, which only
                            // tracks 'dirty-changed' events + the title and is NOT updated on the
                            // history-driven edit path.
let isEditingNow = false;   // R3 edit-guard: cached from runtime 'edit-state' events
let shortcutsHelp = null;
let lastSelection = null;   // cached from runtime 'selection-changed' (for the panel composer)
let historyCursor = -1;     // runtime history position (from 'history-changed'); -1 = empty stack
let savedCursor = -1;       // history position at the last save — chip shows Saved when equal.
                            // MUST start at -1: the runtime's empty-history cursor is -1 and the
                            // FIRST edit pushes cursor 0 — initializing these to 0 made the first
                            // edit compare equal and silently read as "Saved".

let undoBtn = null;
let redoBtn = null;
let currentDeckPath = "";
let themeControls = null;

const AUTHOR_KEY = "hypresent-comment-author";

function setStatus(msg, type = "") {
  const el = document.getElementById("shell-status");
  if (!el) return;
  el.textContent = msg;
  el.className = "shell-status" + (type ? " " + type : "");
}

// topbar doc-chip: filename + Saved/Unsaved state
function setDocChip(name, fullPath) {
  const chip = document.getElementById("doc-chip");
  const nameEl = document.getElementById("doc-name");
  if (!chip || !nameEl) return;
  if (name) nameEl.textContent = name;
  if (fullPath) chip.title = fullPath; else chip.removeAttribute("title");
  chip.hidden = false;
  const empty = document.getElementById("canvas-empty");
  if (empty) empty.hidden = true;
}

function joinPath(dir, name) {
  if (!dir || !name) return "";
  const sep = dir.includes("\\") ? "\\" : "/";
  return dir.replace(/[\\/]+$/, "") + sep + name;
}

function setCurrentDeckPath(path) {
  currentDeckPath = path || "";
}

function setDocState(dirty) {
  docDirty = !!dirty;        // mirror into the close-guard flag BEFORE the early return,
                             // so the guard never reads a stale value when the chip is absent
  const stateEl = document.getElementById("doc-state");
  if (!stateEl) return;
  stateEl.textContent = dirty ? "Unsaved" : "Saved";
  stateEl.classList.toggle("is-dirty", !!dirty);
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
  // Relative time ("2h ago"); falls back to a locale date for older items.
  try {
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return iso;
    const mins = Math.round((Date.now() - then) / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return mins + "m ago";
    const hours = Math.round(mins / 60);
    if (hours < 24) return hours + "h ago";
    const days = Math.round(hours / 24);
    if (days === 1) return "yesterday";
    if (days < 7) return days + "d ago";
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

const AVA_COLORS = ["#2B5EA7", "#2D7D6B", "#1B2B4B", "#B23E1D"];

function createAvatar(author) {
  const span = document.createElement("span");
  span.className = "cava";
  const name = (author || "?").trim() || "?";
  span.textContent = name[0].toUpperCase();
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  span.style.background = AVA_COLORS[hash % AVA_COLORS.length];
  return span;
}

function createThreadEl(thread, isUnanchored = false) {
  const div = document.createElement("div");
  div.className = "comment-thread" + (thread.resolved ? " comment-thread-resolved" : "");
  if (isUnanchored) div.classList.add("comment-thread-unanchored");
  div.dataset.commentId = thread.id;

  const header = document.createElement("div");
  header.className = "comment-thread-header comment-who";

  const authorSpan = document.createElement("span");
  authorSpan.className = "comment-author";
  authorSpan.textContent = thread.author;

  const timeSpan = document.createElement("span");
  timeSpan.className = "comment-time";
  timeSpan.textContent = formatTime(thread.createdAt);

  if (thread.number != null) {
    const numSpan = document.createElement("span");
    numSpan.className = "comment-number";
    numSpan.textContent = "#" + thread.number;
    numSpan.style.fontWeight = "700";
    numSpan.style.color = "var(--ink-mut)";
    numSpan.style.marginRight = "2px";
    header.appendChild(numSpan);
  }
  header.appendChild(createAvatar(thread.author));
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

  let repliesDiv = null;
  if (thread.replies && thread.replies.length > 0) {
    repliesDiv = document.createElement("div");
    repliesDiv.className = "comment-replies";
    for (let i = 0; i < thread.replies.length; i++) {
      const r = thread.replies[i];
      const rDiv = document.createElement("div");
      rDiv.className = "comment-reply";

      const rHeader = document.createElement("div");
      rHeader.className = "comment-who";
      const rAuthor = document.createElement("span");
      rAuthor.className = "comment-author";
      rAuthor.textContent = r.author;
      const rTime = document.createElement("span");
      rTime.className = "comment-time";
      rTime.textContent = formatTime(r.createdAt);
      rHeader.appendChild(createAvatar(r.author));
      rHeader.appendChild(rAuthor);
      rHeader.appendChild(rTime);
      rDiv.appendChild(rHeader);

      const rBody = document.createElement("div");
      rBody.className = "comment-reply-body";
      rBody.textContent = r.body;
      rDiv.appendChild(rBody);

      const rActions = document.createElement("div");
      rActions.className = "comment-actions";

      const rEditBtn = document.createElement("button");
      rEditBtn.className = "comment-action-btn comment-action-btn--mut";
      rEditBtn.textContent = "Edit";
      rEditBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        startInlineEdit(rBody, r.body, async (text) => {
          try {
            await bridge.command("edit-reply", { commentId: thread.id, replyIndex: i, body: text });
            await refreshCommentPanel();
          } catch (err) {
            console.error("Edit reply failed:", err.message);
          }
        });
      });
      rActions.appendChild(rEditBtn);

      const rDeleteBtn = document.createElement("button");
      rDeleteBtn.className = "comment-action-btn comment-action-btn--mut";
      rDeleteBtn.textContent = "Delete";
      rDeleteBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        try {
          await bridge.command("delete-reply", { commentId: thread.id, replyIndex: i });
          await refreshCommentPanel();
        } catch (err) {
          console.error("Delete reply failed:", err.message);
        }
      });
      rActions.appendChild(rDeleteBtn);

      rDiv.appendChild(rActions);

      repliesDiv.appendChild(rDiv);
    }
  }

  const actions = document.createElement("div");
  actions.className = "comment-actions";

  const resolveBtn = document.createElement("button");
  resolveBtn.className = "comment-action-btn comment-action-btn--mut";
  resolveBtn.textContent = thread.resolved ? "Reopen" : "Close";
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

  const editBtn = document.createElement("button");
  editBtn.className = "comment-action-btn comment-action-btn--mut";
  editBtn.textContent = "Edit";
  editBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    startInlineEdit(body, thread.body, async (text) => {
      try {
        await bridge.command("edit-comment", { commentId: thread.id, body: text });
        await refreshCommentPanel();
      } catch (err) {
        console.error("Edit failed:", err.message);
      }
    });
  });
  actions.appendChild(editBtn);

  const deleteBtn = document.createElement("button");
  deleteBtn.className = "comment-action-btn comment-action-btn--mut";
  deleteBtn.textContent = "Delete";
  deleteBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    try {
      await bridge.command("delete-comment", { commentId: thread.id });
      await refreshCommentPanel();
    } catch (err) {
      console.error("Delete failed:", err.message);
    }
  });
  actions.appendChild(deleteBtn);

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
  const agentIco = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  agentIco.setAttribute("viewBox", "0 0 24 24");
  agentIco.setAttribute("fill", "none");
  agentIco.setAttribute("stroke", "currentColor");
  agentIco.setAttribute("stroke-width", "2");
  agentIco.setAttribute("aria-hidden", "true");
  agentIco.style.width = "11px";
  agentIco.style.height = "11px";
  agentIco.innerHTML = '<rect x="5" y="8" width="14" height="11" rx="2"/><path d="M12 4v4M9 13h.01M15 13h.01"/>';
  agentLabel.appendChild(agentIco);
  agentLabel.appendChild(document.createTextNode(" For agents"));
  actions.appendChild(agentLabel);

  div.appendChild(actions);
  if (repliesDiv) {
    div.appendChild(repliesDiv);
  }

  if (!isUnanchored && !thread.resolved) {
    const replyForm = document.createElement("div");
    replyForm.className = "comment-reply-form";
    const replyInput = document.createElement("input");
    replyInput.type = "text";
    replyInput.className = "comment-reply-input";
    replyInput.placeholder = "Reply…";
    replyInput.style.cssText =
      "width:100%; margin-top:10px; height:32px; padding:0 12px; border:1px solid var(--line-2); border-radius:999px; background:var(--white); font-size:12.5px; color:var(--ink);";
    replyInput.addEventListener("click", (e) => e.stopPropagation());
    replyInput.addEventListener("keydown", async (e) => {
      e.stopPropagation();
      if (e.key === "Enter") {
        e.preventDefault();
        const text = replyInput.value.trim();
        if (!text) return;
        const author = getAuthorName();
        replyInput.disabled = true;
        try {
          await bridge.command("reply-comment", { commentId: thread.id, body: text, author });
          await refreshCommentPanel();
        } catch (err) {
          console.error("Reply failed:", err.message);
          replyInput.disabled = false;
        }
      }
    });
    replyForm.appendChild(replyInput);
    div.appendChild(replyForm);
  }

  if (!isUnanchored && thread.hypId) {
    div.addEventListener("click", () => {
      bridge.command("select", { hypId: thread.hypId }).catch((err) => {
        console.error("Select failed:", err.message);
      });
    });
  }

  return div;
}

// Per-session collapse state for the two comment groups.
// Default: Anchored expanded, Unanchored collapsed.
const commentGroupCollapsed = { anchored: false, unanchored: true };

// Per-session status filter (All / Open / Closed). Open = unresolved,
// Closed = resolved — the only status the comment system tracks. Resets on
// reload, like the collapse state above. Applied to BOTH groups.
let commentStatusFilter = "all";
// Last threads rendered, so a filter change re-renders without a bridge read.
let _lastCommentThreads = [];

function statusMatchesFilter(thread) {
  if (commentStatusFilter === "open") return !thread.resolved;
  if (commentStatusFilter === "closed") return !!thread.resolved;
  return true;
}

function renderCommentPanel(threads) {
  _lastCommentThreads = threads;
  const container = document.getElementById("comment-threads");
  const unanchoredContainer = document.getElementById("comment-unanchored");
  if (!container) return;

  container.innerHTML = "";
  if (unanchoredContainer) unanchoredContainer.innerHTML = "";

  const anchored = threads
    .filter((t) => !t.unanchored)
    .filter(statusMatchesFilter)
    .sort((a, b) => (a.number || 0) - (b.number || 0));
  const unanchored = threads.filter((t) => t.unanchored).filter(statusMatchesFilter);

  for (const thread of anchored) {
    container.appendChild(createThreadEl(thread, false));
  }
  if (unanchoredContainer) {
    for (const thread of unanchored) {
      unanchoredContainer.appendChild(createThreadEl(thread, true));
    }
  }

  updateCommentGroup("anchored", anchored.length);
  updateCommentGroup("unanchored", unanchored.length);
  applyCommentGroupSizing();
}

// Sync one group's header (count, collapsed class, aria) and hide it entirely
// when empty so the other group takes the whole list area.
function updateCommentGroup(group, count) {
  const section = document.querySelector(`.comment-group[data-group="${group}"]`);
  if (!section) return;
  section.style.display = count > 0 ? "" : "none";
  const countEl = section.querySelector(`.comment-group-count[data-group="${group}"]`);
  if (countEl) countEl.textContent = String(count);
  const collapsed = commentGroupCollapsed[group];
  section.classList.toggle("collapsed", collapsed);
  const header = section.querySelector(".comment-group-header");
  if (header) header.setAttribute("aria-expanded", String(!collapsed));
}

// Size the two group bodies: each sizes to its content; when both are expanded
// and would overflow, the busy group borrows the idle group's unused space,
// capped so neither exceeds half the list area (→ 50/50 only when both overflow).
function applyCommentGroupSizing() {
  const wrap = document.getElementById("comment-groups");
  if (!wrap) return;
  const groups = ["anchored", "unanchored"]
    .map((g) => ({
      sec: document.querySelector(`.comment-group[data-group="${g}"]`),
      body: document.getElementById(g === "anchored" ? "comment-threads" : "comment-unanchored"),
    }))
    .filter((x) => x.sec && x.body && x.sec.style.display !== "none");

  // Reset to natural height so scrollHeight reflects true content height.
  for (const x of groups) x.body.style.maxHeight = "none";

  const open = groups.filter((x) => !x.sec.classList.contains("collapsed"));
  if (open.length === 0) return;

  let headersH = 0;
  for (const x of groups) {
    const header = x.sec.querySelector(".comment-group-header");
    headersH += header ? header.offsetHeight : 0;
  }
  const avail = wrap.clientHeight - headersH;
  if (avail <= 0) return;

  if (open.length === 1) {
    open[0].body.style.maxHeight = avail + "px";
    return;
  }
  const half = avail / 2;
  const n0 = open[0].body.scrollHeight;
  const n1 = open[1].body.scrollHeight;
  let h0, h1;
  if (n0 + n1 <= avail) { h0 = n0; h1 = n1; }            // both fit
  else if (n0 <= half) { h0 = n0; h1 = avail - n0; }     // group 0 small → group 1 borrows
  else if (n1 <= half) { h1 = n1; h0 = avail - n1; }     // group 1 small → group 0 borrows
  else { h0 = half; h1 = half; }                          // both overflow → 50/50
  open[0].body.style.maxHeight = Math.floor(h0) + "px";
  open[1].body.style.maxHeight = Math.floor(h1) + "px";
}

// Collapse/expand a group on header click, then re-size both.
function toggleCommentGroup(group) {
  if (!(group in commentGroupCollapsed)) return;
  commentGroupCollapsed[group] = !commentGroupCollapsed[group];
  const section = document.querySelector(`.comment-group[data-group="${group}"]`);
  if (section) {
    const collapsed = commentGroupCollapsed[group];
    section.classList.toggle("collapsed", collapsed);
    const header = section.querySelector(".comment-group-header");
    if (header) header.setAttribute("aria-expanded", String(!collapsed));
  }
  applyCommentGroupSizing();
}

// One-time wiring: header clicks toggle collapse; window resize re-sizes groups.
(function wireCommentGroups() {
  const wrap = document.getElementById("comment-groups");
  if (wrap) {
    wrap.addEventListener("click", (e) => {
      const header = e.target.closest(".comment-group-header");
      if (header) toggleCommentGroup(header.getAttribute("data-group"));
    });
  }
  window.addEventListener("resize", applyCommentGroupSizing);

  const filterSel = document.getElementById("comment-filter");
  if (filterSel) {
    filterSel.addEventListener("change", () => {
      commentStatusFilter = filterSel.value;
      renderCommentPanel(_lastCommentThreads);
    });
  }
})();

let _commentRefreshInFlight = false;
let _commentRefreshQueued = false;
async function refreshCommentPanel() {
  if (!bridge) return;
  if (_commentRefreshInFlight) { _commentRefreshQueued = true; return; }
  _commentRefreshInFlight = true;
  try {
    const result = await bridge.command("comments-read");
    renderCommentPanel(result.threads || []);
  } catch (err) {
    console.error("Failed to read comments:", err.message);
  } finally {
    _commentRefreshInFlight = false;
    if (_commentRefreshQueued) { _commentRefreshQueued = false; refreshCommentPanel(); }
  }
}

// Open the anchored composer for a NEW comment on the current selection.
// agentDefault=true pre-checks "For agents" (Ctrl+Shift+M path). Shared by the
// toolbar button, the keyboard shortcuts, and the iframe-origin shortcut events.
async function openCommentFlow(agentDefault = false) {
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
    agentDefault,
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
}

// Edit a comment/reply body INLINE inside the right comments pane (not over the
// document). `anchorEl` is the .comment-body / .comment-reply-body element being
// edited; it is hidden and an editor is inserted right after it. onSave(text) runs
// the bridge edit command; both Save and Cancel re-render the panel afterward.
function startInlineEdit(anchorEl, currentText, onSave) {
  // Guard against a second editor on the same body.
  if (anchorEl.nextElementSibling && anchorEl.nextElementSibling.classList.contains("comment-inline-edit")) {
    anchorEl.nextElementSibling.querySelector("textarea")?.focus();
    return;
  }

  const editor = document.createElement("div");
  editor.className = "comment-inline-edit";
  editor.addEventListener("click", (e) => e.stopPropagation());

  const ta = document.createElement("textarea");
  ta.className = "comment-inline-textarea";
  ta.rows = 3;
  ta.value = currentText;

  const acts = document.createElement("div");
  acts.className = "comment-inline-actions";
  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.className = "comment-inline-save";
  saveBtn.textContent = "Save";
  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "comment-inline-cancel";
  cancelBtn.textContent = "Cancel";
  acts.appendChild(saveBtn);
  acts.appendChild(cancelBtn);

  editor.appendChild(ta);
  editor.appendChild(acts);

  anchorEl.style.display = "none";
  anchorEl.insertAdjacentElement("afterend", editor);

  function commit() {
    const text = ta.value.trim();
    if (!text) { refreshCommentPanel(); return; } // empty → discard edit, restore view
    onSave(text);                                  // onSave runs the bridge command + refresh
  }

  saveBtn.addEventListener("click", (e) => { e.stopPropagation(); commit(); });
  cancelBtn.addEventListener("click", (e) => { e.stopPropagation(); refreshCommentPanel(); });
  ta.addEventListener("click", (e) => e.stopPropagation());
  ta.addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.key === "Escape") { e.preventDefault(); refreshCommentPanel(); return; }
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); commit(); return; }
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); commit(); return; }
    // Shift+Enter → newline (default)
  });

  ta.focus();
  ta.setSelectionRange(ta.value.length, ta.value.length);
}

function ensureBridge(iframe) {
  if (bridge) bridge.destroy();
  bridge = createBridge(iframe);
  // New bridge: the runtime in the freshly (re)loaded iframe has NOT booted yet, so
  // serialize() will not answer until it emits 'ready'. Hold the Builder-tab crossing
  // until then — crossing on bridge-object-existence alone lets a click race ahead of
  // the runtime and silently no-op (the suite-load flake). Mirror the flag onto window
  // so tests can wait on the true readiness signal.
  builderCrossReady = false;
  window.__hypBuilderCrossReady = false;
  bridge.on("ready", async (payload) => {
    console.info("runtime ready");
    historyCursor = -1;
    savedCursor = -1;
    // Runtime is now live and serialize() will answer → the crossing can never hit an
    // unready runtime. Open the gate on the TRUE readiness signal, identically for both
    // open paths (dialog open and ?file= handoff arrival).
    builderCrossReady = true;
    window.__hypBuilderCrossReady = true;
    await refreshCommentPanel();
  });

  bridge.on("theme-stamp", (payload) => {
    if (themeControls) themeControls.handleThemeStamp(payload);
  });

  bridge.on("selection-changed", (payload) => {
    lastSelection = payload && payload.hypId ? payload : null;
    if (window.__hypUpdateAlignButtons) {
      window.__hypUpdateAlignButtons(payload && payload.alignCaps ? payload.alignCaps : null);
    }
  });

  bridge.on("dirty-changed", (payload) => {
    isDirty = payload && payload.dirty ? true : false;
    document.title = isDirty ? "hypresent *" : "hypresent";
    setDocState(isDirty);
    refreshCommentPanel();
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
    // Saved/Unsaved chip: any history movement away from the saved position
    // means the document differs from disk; moving back to it means it matches.
    if (payload && typeof payload.cursor === "number") {
      historyCursor = payload.cursor;
      setDocState(historyCursor !== savedCursor);
    }
  });

  bridge.on("shortcut", (payload) => {
    const action = payload && payload.action;
    if (action === "comment") openCommentFlow(false);
    else if (action === "comment-agent") openCommentFlow(true);
    else if (action === "save") document.getElementById("save-btn")?.click();
    else if (action === "save-as") document.getElementById("save-as-btn")?.click();
    else if (action === "show-shortcuts") { if (shortcutsHelp) shortcutsHelp.open(); }
  });

  const panel = document.getElementById("shell-panel");
  if (panel) {
    createColorPopover({ bridge, panelEl: panel });
  }

  return bridge;
}

document.addEventListener("DOMContentLoaded", () => {
  const toolbar = document.querySelector(".ed-toolbar");
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

  themeControls = createThemeControls({
    bridge: () => bridge,
    getDeckPath: () => currentDeckPath,
    setStatus,
    markDirty: () => {
      isDirty = true;
      document.title = "hypresent *";
      setDocState(true);
    },
    els: {
      container: document.getElementById("theme-switcher"),
      select: document.getElementById("theme-select"),
      library: document.getElementById("theme-library"),
      pickLibrary: document.getElementById("theme-library-pick"),
      message: document.getElementById("theme-message"),
    },
  });

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

  // Mode-switch guard: the Builder link is a plain navigation that discards
  // unsaved edits. Confirm before leaving when the open document is dirty.
  const navBuilderLink = document.getElementById("nav-builder");
  if (navBuilderLink) {
    navBuilderLink.addEventListener("click", (e) => {
      // When a document is open AND the runtime is ready, save (with a confirm-overwrite
      // prompt) before switching — the save-first safety the removed "Open in builder"
      // button used to carry. Otherwise fall through to plain navigation (nothing to lose).
      if (!bridge || !builderCrossReady) return;
      e.preventDefault();
      saveThenSwitchToBuilder();
    });
  }

  // Unsaved-changes close-guard: when the open document has unsaved edits, ask the
  // browser to confirm before the tab is closed (Ctrl+W / window X), refreshed, or
  // navigated away. The browser shows its own generic "Leave site? Changes you made
  // may not be saved" dialog — we only opt in by preventing default + setting
  // returnValue. A clean document (freshly opened or just saved) never prompts.
  // Intentional in-app navigation (the Builder-tab save-then-switch crossing, which
  // saves first) sets window.__hypSuppressUnloadPrompt to skip this prompt.
  window.addEventListener("beforeunload", (e) => {
    if (window.__hypSuppressUnloadPrompt) return;
    if (!docDirty) return;
    e.preventDefault();
    e.returnValue = "";   // Chrome requires returnValue to be set to raise the prompt
  });

  const openBtn = document.querySelector("#open-btn");
  if (!openBtn) {
    console.error("Open control not found");
  } else {
    openBtn.addEventListener("click", async () => {
      try {
        const result = await openViaDialog(iframe);
        if (!result) return; // cancelled
        setCurrentDeckPath(joinPath(result.dir, result.name));
        if (themeControls) themeControls.resetForOpen();
        ensureBridge(iframe);
        setStatus("");
        setDocChip(result.name || "", currentDeckPath);
        setDocState(false);
        // The Builder-tab crossing is gated by the runtime-ready flag set in the
        // bridge 'ready' handler — NOT here. Opening the gate on open would re-introduce
        // the ready-before-serialize window the crossing races against.
      } catch (err) {
        console.error("Open failed:", err.message);
        setStatus("Open failed: " + err.message, "error");
      }
    });
  }

  // canvas empty-state Open button proxies the topbar one
  const canvasOpenBtn = document.getElementById("canvas-open-btn");
  if (canvasOpenBtn && openBtn) {
    canvasOpenBtn.addEventListener("click", () => openBtn.click());
  }

  // prez-builder handoff: open a deck passed via ?file= (set by the builder page).
  // Absent the param, the editor boot is unchanged (this branch is skipped).
  // URLSearchParams.get() ALREADY returns the percent-decoded value — do NOT decode again
  // (a second decodeURIComponent would throw URIError / corrupt a path bearing a literal '%').
  const fileParam = new URLSearchParams(location.search).get("file");
  if (fileParam) {
    (async () => {
      try {
        const result = await openFile(fileParam, iframe);
        setCurrentDeckPath(fileParam);
        if (themeControls) themeControls.resetForOpen();
        ensureBridge(iframe);
        setStatus("");
        setDocChip((result && result.name) || fileParam.split(/[\\/]/).pop() || "", fileParam);
        setDocState(false);
        // Readiness flag is set by the bridge 'ready' handler, not here — see the
        // dialog-open path above. Same readiness gate on both crossings into the builder.
      } catch (err) {
        console.error("Handoff open failed:", err.message);
        setStatus("Open failed: " + err.message, "error");
      }
    })();
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

  // Save-then-switch crossing (editor → builder), invoked by the Builder tab. Saves the
  // current document (confirm-overwrite when a file is open; Save As for a never-saved
  // deck), then navigates to the builder with ?file=. Suppresses the unsaved-changes
  // close-guard for this intentional in-app navigation. The caller gates on readiness.
  async function saveThenSwitchToBuilder() {
    if (!bridge) { setStatus("No document open.", "error"); return; }
    const html = await serializeDoc();
    if (html == null) return; // serialization failed — status already set
    try {
      const docChip = document.getElementById("doc-chip");
      const docNameEl = document.getElementById("doc-name");
      const hasOpenFile = !!(docChip && !docChip.hidden && docNameEl && docNameEl.textContent);
      let result;
      if (hasOpenFile) {
        const choice = await confirmSaveOverwrite(docNameEl.textContent);
        if (choice === "cancel") return;                  // stay in the editor
        if (choice === "proceed") {
          result = await save(html);                      // overwrite the opened file
          if (result && result.no_open_file) result = await dialogSaveAs(html);
        } else {
          result = await dialogSaveAs(html);              // Save As — keep the original
        }
      } else {
        result = await dialogSaveAs(html);                // never-saved deck → pick a path
      }
      if (result && result.cancelled) return;
      if (!result || !result.ok) { setStatus("Save failed.", "error"); return; }
      window.__hypSuppressUnloadPrompt = true;
      window.location.href = "/app/builder.html?file=" + encodeURIComponent(result.path);
    } catch (err) {
      setStatus("Save failed: " + err.message, "error");
    }
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
          savedCursor = historyCursor;
          setDocState(false);
          setDocChip((sa.path || "").split(/[\\/]/).pop() || "", sa.path || "");
          setCurrentDeckPath(sa.path || "");
          setStatus("");
          return;
        }
        isDirty = false; document.title = "hypresent";
        savedCursor = historyCursor;
        setDocState(false);
        setStatus("");
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
        savedCursor = historyCursor;
        setDocState(false);
        setDocChip((data.path || "").split(/[\\/]/).pop() || "", data.path || "");
        setCurrentDeckPath(data.path || "");
        setStatus("");
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
    commentBtn.addEventListener("click", () => openCommentFlow(false));
  }

  // Wire Undo / Redo buttons (topbar icon buttons)
  undoBtn = document.getElementById("undo-btn");
  redoBtn = document.getElementById("redo-btn");

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

  shortcutsHelp = createShortcutsHelp();
  document.getElementById("shortcuts-btn")?.addEventListener("click", () => shortcutsHelp.open());

  document.addEventListener("keydown", (e) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    const t = e.target;
    const inField = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA");
    const k = e.key.toLowerCase();
    if (k === "/") { e.preventDefault(); shortcutsHelp.open(); return; }
    // Save / Save As — global (fire even while a field/composer is focused).
    if (k === "q" && e.shiftKey) { e.preventDefault(); document.getElementById("save-btn")?.click(); return; }
    if (k === "q" && !e.shiftKey) { e.preventDefault(); document.getElementById("save-as-btn")?.click(); return; }
    if (inField) return;
    if (!e.altKey && k === "m" && e.shiftKey) { e.preventDefault(); openCommentFlow(true); return; }
    if (!e.altKey && k === "m" && !e.shiftKey) { e.preventDefault(); openCommentFlow(false); return; }
    if (e.key === "Delete") { e.preventDefault(); document.getElementById("delete-btn")?.click(); return; }
    if (!e.altKey && k === "b") { e.preventDefault(); if (bridge) bridge.command("format", { op: "bold" }).catch(() => {}); return; }
    if (!e.altKey && k === "i") { e.preventDefault(); if (bridge) bridge.command("format", { op: "italic" }).catch(() => {}); return; }
  });

  // Panel composer (inspector bottom): comments the currently selected element.
  const composerInput = document.getElementById("composer-input");
  const composerSend = document.getElementById("composer-send");
  async function submitPanelComment() {
    if (!composerInput) return;
    const text = composerInput.value.trim();
    if (!text) return;
    if (!bridge) { setStatus("Open a document first.", "error"); return; }
    if (!lastSelection || !lastSelection.hypId) {
      setStatus("Select an element to comment.", "error");
      return;
    }
    const author = getAuthorName();
    try {
      await bridge.command("add-comment", {
        hypId: lastSelection.hypId,
        body: text,
        author,
        agentInstruction: false,
      });
      composerInput.value = "";
      await refreshCommentPanel();
    } catch (err) {
      setStatus("Add comment failed: " + err.message, "error");
    }
  }
  if (composerSend) composerSend.addEventListener("click", submitPanelComment);
  if (composerInput) {
    composerInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); submitPanelComment(); }
    });
  }
});
