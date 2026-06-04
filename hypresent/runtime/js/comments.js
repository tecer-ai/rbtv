/**
 * runtime/js/comments.js
 *
 * Comment store, anchors, JSON island read/write (D4).
 *
 * Public contract (module-map 03 §4):
 *   load(islandJson), toJson(), add(hypId,body,author), reply(commentId,body,author),
 *   resolve(commentId,resolved), threads(), anchorRect(commentId),
 *   buildAnchorKey(el), matchAnchor(anchor)→Element|null
 *
 * Emits (via bridge-iframe.js):
 *   comment-anchor-clicked {commentId, rect}
 *   dirty-changed {dirty}
 */

import { byId, idOf } from "./element-registry.js";
import { push as historyPush } from "./history.js";
import { comment as makeCommentCommand } from "./commands.js";
import { emit } from "./bridge-iframe.js";

// --- State ---

let threadStore = [];
let nextId = 1;
const markers = new Map(); // commentId -> marker element

// --- Helpers: text / hash ---

function normalizeText(str) {
  return (str || "").replace(/\s+/g, " ").trim();
}

function fnv1a32(input) {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function computeContentHash(el) {
  const text = normalizeText(el.textContent).slice(0, 32);
  return fnv1a32(text);
}

function domRectToPlain(rect) {
  return {
    x: rect.x,
    y: rect.y,
    width: rect.width,
    height: rect.height,
    top: rect.top,
    right: rect.right,
    bottom: rect.bottom,
    left: rect.left,
  };
}

// --- Helpers: class signature ---

function getPrimaryClassSignature(el) {
  const cls = el.getAttribute("class") || "";
  const tokens = cls
    .trim()
    .split(/\s+/)
    .filter((t) => t && !t.startsWith("hyp-"));
  return tokens.join(" ");
}

function computeSiblingIndex(el) {
  const parent = el.parentElement;
  if (!parent) return 0;
  const tag = el.tagName.toLowerCase();
  const sig = getPrimaryClassSignature(el);
  let idx = 0;
  for (const sibling of parent.children) {
    if (sibling === el) return idx;
    if (
      sibling.tagName.toLowerCase() === tag &&
      getPrimaryClassSignature(sibling) === sig
    ) {
      idx++;
    }
  }
  return 0;
}

function getSameKeySiblings(el) {
  const parent = el.parentElement;
  if (!parent) return [];
  const tag = el.tagName.toLowerCase();
  const sig = getPrimaryClassSignature(el);
  return Array.from(parent.children).filter(
    (c) => c.tagName.toLowerCase() === tag && getPrimaryClassSignature(c) === sig
  );
}

// --- Helpers: path ---

function buildPath(el) {
  // base = nearest ancestor with native id, or documentElement
  let base = null;
  let p = el.parentElement;
  while (p) {
    if (p.id && !p.id.startsWith("hyp-")) {
      base = p;
      break;
    }
    p = p.parentElement;
  }
  if (!base) base = document.documentElement;

  const segments = [];
  let cur = el;
  while (cur && cur !== base) {
    const parent = cur.parentElement;
    if (!parent) break;
    const tag = cur.tagName.toLowerCase();
    let nth = 1;
    for (const sibling of parent.children) {
      if (sibling === cur) break;
      if (sibling.tagName.toLowerCase() === tag) nth++;
    }
    segments.unshift(`${tag}:${nth}`);
    cur = parent;
  }

  return segments.join("/");
}

function walkPath(base, pathStr) {
  if (!pathStr) return base;
  const segments = pathStr.split("/");
  let cur = base;
  for (const seg of segments) {
    const [tag, nthStr] = seg.split(":");
    const nth = parseInt(nthStr, 10);
    if (!cur) return null;
    let count = 0;
    let found = null;
    for (const child of cur.children) {
      if (child.tagName.toLowerCase() === tag) {
        count++;
        if (count === nth) {
          found = child;
          break;
        }
      }
    }
    if (!found) return null;
    cur = found;
  }
  return cur;
}

// --- Anchor key: build ---

export function buildAnchorKey(el) {
  const hook = el.getAttribute("data-hyp-hook") || null;
  const path = buildPath(el);

  let nativeIdEl = null;
  let cur = el;
  while (cur) {
    if (cur.id && !cur.id.startsWith("hyp-")) {
      nativeIdEl = cur;
      break;
    }
    cur = cur.parentElement;
  }
  const nativeId = nativeIdEl ? nativeIdEl.id : null;
  const contentHash = computeContentHash(el);
  const siblingIndex = computeSiblingIndex(el);

  return { hook, path, nativeId, contentHash, siblingIndex };
}

// --- Anchor key: match ---

export function matchAnchor(anchor) {
  // 1. Hook match (unique only)
  if (anchor.hook) {
    const matches = document.querySelectorAll(
      `[data-hyp-hook="${CSS.escape(anchor.hook)}"]`
    );
    if (matches.length === 1) return matches[0];
  }

  // 2. Base + path walk, then hash check
  const base = anchor.nativeId
    ? document.getElementById(anchor.nativeId)
    : document.documentElement;
  if (!base) return null;

  const el = walkPath(base, anchor.path);
  if (el && computeContentHash(el) === anchor.contentHash) {
    return el;
  }

  // 3. Same-key sibling check
  if (el && el.parentElement) {
    const siblings = getSameKeySiblings(el);
    const candidate = siblings[anchor.siblingIndex];
    if (candidate && computeContentHash(candidate) === anchor.contentHash) {
      return candidate;
    }
  }

  // 4. Relaxed fallback: tail tag (+ class sig if known) under base
  if (anchor.path) {
    const tailSeg = anchor.path.split("/").pop();
    const tailTag = tailSeg.split(":")[0];
    const classSig = el ? getPrimaryClassSignature(el) : "";
    const all = base.getElementsByTagName(tailTag);
    let match = null;
    for (const candidate of all) {
      if (classSig && getPrimaryClassSignature(candidate) !== classSig) continue;
      if (computeContentHash(candidate) === anchor.contentHash) {
        if (match) return null; // ambiguous
        match = candidate;
      }
    }
    if (match) return match;
  }

  // 5. Unanchored
  return null;
}

// --- Island read/write ---

function readIsland() {
  const island = document.getElementById("hyp-comments");
  if (!island) return [];
  try {
    const data = JSON.parse(island.textContent.trim());
    if (Array.isArray(data)) return data;
  } catch {
    // ignore parse errors
  }
  return [];
}

function writeIsland() {
  let island = document.getElementById("hyp-comments");
  if (!island) {
    island = document.createElement("script");
    island.type = "application/json";
    island.id = "hyp-comments";
    document.body.appendChild(island);
  }
  // Persist only stable fields (no runtime-only flags like unanchored)
  const clean = threadStore.map((t) => ({
    id: t.id,
    anchor: t.anchor,
    contextText: t.contextText,
    author: t.author,
    createdAt: t.createdAt,
    body: t.body,
    resolved: t.resolved,
    replies: t.replies,
    agentInstruction: t.agentInstruction === true,
  }));
  island.textContent = JSON.stringify(clean);
}

// --- Markers ---

function positionMarker(marker, el) {
  const rect = el.getBoundingClientRect();
  const sx = window.scrollX || window.pageXOffset || 0;
  const sy = window.scrollY || window.pageYOffset || 0;
  marker.style.top = `${rect.top + sy - 8}px`;
  marker.style.left = `${rect.right + sx - 8}px`;
}

function renderMarkerFor(thread, el) {
  removeMarker(thread.id);
  if (!el) return;

  const marker = document.createElement("div");
  marker.className = "hyp-comment-marker";
  marker.style.position = "absolute";
  marker.style.pointerEvents = "auto";
  marker.style.zIndex = "999998";
  marker.style.width = "20px";
  marker.style.height = "20px";
  marker.style.borderRadius = "50%";
  marker.style.background = thread.resolved ? "#9ca3af" : "#fbbf24";
  marker.style.border = "2px solid " + (thread.resolved ? "#6b7280" : "#f59e0b");
  marker.style.cursor = "pointer";
  marker.style.display = "flex";
  marker.style.alignItems = "center";
  marker.style.justifyContent = "center";
  marker.style.fontSize = "10px";
  marker.style.lineHeight = "1";
  marker.textContent = thread.resolved
    ? "✓"
    : String(1 + thread.replies.length);
  marker.title = `Comment by ${thread.author}`;

  marker.addEventListener("click", (e) => {
    e.stopPropagation();
    const rect = el.getBoundingClientRect();
    emit("comment-anchor-clicked", {
      commentId: thread.id,
      rect: domRectToPlain(rect),
    });
  });

  document.body.appendChild(marker);
  markers.set(thread.id, marker);
  positionMarker(marker, el);
}

function removeMarker(commentId) {
  const marker = markers.get(commentId);
  if (marker && marker.parentNode) {
    marker.parentNode.removeChild(marker);
  }
  markers.delete(commentId);
}

function updateMarkerState(commentId) {
  const thread = threadStore.find((t) => t.id === commentId);
  const marker = markers.get(commentId);
  if (!thread || !marker) return;
  marker.style.background = thread.resolved ? "#9ca3af" : "#fbbf24";
  marker.style.borderColor = thread.resolved ? "#6b7280" : "#f59e0b";
  marker.textContent = thread.resolved
    ? "✓"
    : String(1 + thread.replies.length);
}

function updateAllMarkers() {
  for (const [commentId, marker] of markers) {
    const thread = threadStore.find((t) => t.id === commentId);
    if (!thread) continue;
    const el = matchAnchor(thread.anchor);
    if (el) {
      marker.style.display = "flex";
      positionMarker(marker, el);
    } else {
      marker.style.display = "none";
    }
  }
}

window.addEventListener("resize", updateAllMarkers);
window.addEventListener("scroll", updateAllMarkers, { passive: true });

function reanchorAll() {
  for (const [, marker] of markers) {
    if (marker.parentNode) marker.parentNode.removeChild(marker);
  }
  markers.clear();

  for (const thread of threadStore) {
    const el = matchAnchor(thread.anchor);
    if (el) {
      renderMarkerFor(thread, el);
    }
  }
}

// --- Public API ---

export function load(islandJson) {
  if (Array.isArray(islandJson)) {
    threadStore = islandJson.map((t) => ({ ...t }));
  } else {
    threadStore = [];
  }
  nextId =
    threadStore.reduce((max, t) => Math.max(max, parseInt(t.id, 10) || 0), 0) + 1;
  reanchorAll();
}

export function toJson() {
  return threadStore.map((t) => ({
    id: t.id,
    anchor: t.anchor,
    contextText: t.contextText,
    author: t.author,
    createdAt: t.createdAt,
    body: t.body,
    resolved: t.resolved,
    replies: t.replies,
    agentInstruction: t.agentInstruction === true,
  }));
}

export function add(hypId, body, author, agentInstruction = false) {
  const el = byId(hypId);
  if (!el) throw new Error("add-comment: element not found");

  const anchor = buildAnchorKey(el);
  const contextText = normalizeText(el.textContent).slice(0, 80);
  const id = String(nextId++);
  const createdAt = new Date().toISOString();

  const thread = {
    id,
    anchor,
    contextText,
    author,
    createdAt,
    body,
    resolved: false,
    replies: [],
    agentInstruction: !!agentInstruction,
  };

  const doFn = () => {
    threadStore.push(thread);
    writeIsland();
    const resolvedEl = matchAnchor(anchor);
    renderMarkerFor(thread, resolvedEl);
    emit("dirty-changed", { dirty: true });
  };

  const undoFn = () => {
    const idx = threadStore.findIndex((t) => t.id === id);
    if (idx !== -1) {
      threadStore.splice(idx, 1);
      writeIsland();
      removeMarker(id);
      emit("dirty-changed", { dirty: true });
    }
  };

  historyPush(makeCommentCommand("add-comment", doFn, undoFn));
  return { commentId: id };
}

export function reply(commentId, body, author) {
  const thread = threadStore.find((t) => t.id === commentId);
  if (!thread) throw new Error("reply-comment: thread not found");

  const createdAt = new Date().toISOString();
  const replyObj = { author, body, createdAt };

  const doFn = () => {
    thread.replies.push(replyObj);
    writeIsland();
    updateMarkerState(commentId);
    emit("dirty-changed", { dirty: true });
  };

  const undoFn = () => {
    thread.replies.pop();
    writeIsland();
    updateMarkerState(commentId);
    emit("dirty-changed", { dirty: true });
  };

  historyPush(makeCommentCommand("reply-comment", doFn, undoFn));
  return { commentId };
}

export function resolve(commentId, resolved = true) {
  const thread = threadStore.find((t) => t.id === commentId);
  if (!thread) throw new Error("resolve-comment: thread not found");

  const before = thread.resolved;

  const doFn = () => {
    thread.resolved = resolved;
    writeIsland();
    updateMarkerState(commentId);
    emit("dirty-changed", { dirty: true });
  };

  const undoFn = () => {
    thread.resolved = before;
    writeIsland();
    updateMarkerState(commentId);
    emit("dirty-changed", { dirty: true });
  };

  historyPush(
    makeCommentCommand(
      resolved ? "resolve-comment" : "reopen-comment",
      doFn,
      undoFn
    )
  );
  return { commentId };
}

export function setAgentInstruction(commentId, agentInstruction) {
  const thread = threadStore.find((t) => t.id === commentId);
  if (!thread) throw new Error("tag-agent: thread not found");
  const before = thread.agentInstruction === true;
  const next = !!agentInstruction;
  const doFn = () => {
    thread.agentInstruction = next;
    writeIsland();
    emit("dirty-changed", { dirty: true });
  };
  const undoFn = () => {
    thread.agentInstruction = before;
    writeIsland();
    emit("dirty-changed", { dirty: true });
  };
  historyPush(makeCommentCommand(next ? "tag-agent" : "untag-agent", doFn, undoFn));
  return { commentId, agentInstruction: next };
}

// THE single escape function for the agent block (R06): HTML comments cannot
// contain '-->'. Every interpolated value MUST pass through this.
function escapeAgentBlock(s) {
  return String(s == null ? "" : s).replace(/-->/g, "--&gt;");
}

export function buildAgentBlock() {
  const agentThreads = threadStore.filter(
    (t) => t.agentInstruction === true && t.resolved !== true
  );
  if (agentThreads.length === 0) return null;

  const lines = [];
  lines.push("<!-- ===== HYPRESENT AGENT INSTRUCTIONS =====");
  lines.push(
    "This block is auto-generated from agent-tagged review comments in this file. Each entry describes a change an AI coding agent should make to the element identified by its anchor."
  );
  lines.push(
    "Do not edit this block manually — it is regenerated on every save and removed when no agent comments remain."
  );
  for (const t of agentThreads) {
    lines.push("");
    lines.push(`[agent:${escapeAgentBlock(t.id)}]`);
    const path = escapeAgentBlock((t.anchor && t.anchor.path) || "(root)");
    const nid = escapeAgentBlock((t.anchor && t.anchor.nativeId) || "");
    const ctx = escapeAgentBlock((t.contextText || "").slice(0, 80));
    lines.push(`anchor: ${path} | id="${nid}" | "${ctx}"`);
    lines.push(`instruction: ${escapeAgentBlock(t.body)}`);
    for (const r of t.replies || []) {
      lines.push(`reply: ${escapeAgentBlock(r.body)} — ${escapeAgentBlock(r.author)}`);
    }
    lines.push(`author: ${escapeAgentBlock(t.author)}`);
    lines.push(`date: ${t.createdAt}`);   // ISO-8601 from new Date().toISOString(); cannot contain '-->'
  }
  lines.push("===== END HYPRESENT AGENT INSTRUCTIONS ===== -->");
  return lines.join("\n");
}

export function reanchorAfterMove() {
  // Recompute anchors for ALL threads after a DOM move (R14).
  for (const t of threadStore) {
    const el = matchAnchor(t.anchor);          // multi-signal resolution (partial-match fallbacks)
    if (el) {
      t.anchor = buildAnchorKey(el);           // regenerate path + siblingIndex from CURRENT position
    }
    // else: unresolved → keep the old anchor; the thread shows as unanchored, never deleted.
  }
  writeIsland();
  reanchorAll();
}

export function threads() {
  return threadStore.map((t) => {
    const el = matchAnchor(t.anchor);
    const hypId = el ? idOf(el) : null;
    const rect = el ? domRectToPlain(el.getBoundingClientRect()) : null;
    return {
      ...t,
      unanchored: !el,
      hypId,
      rect,
    };
  });
}

export function anchorRect(commentId) {
  const thread = threadStore.find((t) => t.id === commentId);
  if (!thread) return null;
  const el = matchAnchor(thread.anchor);
  if (!el) return null;
  return domRectToPlain(el.getBoundingClientRect());
}
