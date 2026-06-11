---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
  - runtime/js/comments.js
  - app/js/main.js
sandbox: workspace-write
commit_policy: none
test_command: NONE (conductor runs the e2e gate)
forbidden_ops:
  - git commit
  - git push
  - git reset
  - writes outside allowlist
  - external production API calls
  - --dangerously-bypass-approvals-and-sandbox
doubt_policy: halt
reviewer: claude-opus
---

## Sandbox + Approval
`--sandbox workspace-write` + `-c approval_policy="never"`. Edit ONLY `runtime/js/comments.js` and `app/js/main.js`. Make ONLY the enumerated changes. Use ASCII-only identifiers. Preserve the existing `"✓"` (U+2713 check mark) characters exactly where shown.

# Fix bug-2 — every comment marker shows "1"; give each a sequential number by document order

## Goal
Replace the in-deck marker badge text (currently `1 + replies.length`, which is `1` for every reply-less comment) with a sequential comment NUMBER assigned by document order (top-to-bottom), and show that same number in the side panel, with the panel sorted to match. Resolved comments keep the `"✓"` badge and are excluded from numbering, so unresolved comments number contiguously 1,2,3…

## Allowed Paths
- `runtime/js/comments.js`
- `app/js/main.js`

## Forbidden Paths
- Every other file. No new files. No commits.

---

## Part A — `runtime/js/comments.js`

**(A1) Add three helper functions** immediately BEFORE the line `function renderMarkerFor(thread, el) {`:
```js
// --- Numbering (document order; resolved excluded so unresolved number 1..N) ---
function documentOrderedIds() {
  const arr = [];
  for (const t of threadStore) {
    if (t.resolved === true) continue;
    const el = matchAnchor(t.anchor);
    if (el) arr.push({ id: t.id, el });
  }
  arr.sort((a, b) => {
    const p = a.el.compareDocumentPosition(b.el);
    if (p & Node.DOCUMENT_POSITION_FOLLOWING) return -1;
    if (p & Node.DOCUMENT_POSITION_PRECEDING) return 1;
    return 0;
  });
  return arr.map((x) => x.id);
}

function commentNumber(commentId, order) {
  const list = order || documentOrderedIds();
  const i = list.indexOf(commentId);
  return i >= 0 ? i + 1 : null;
}

function renumberMarkers() {
  const order = documentOrderedIds();
  for (const [commentId, marker] of markers) {
    const t = threadStore.find((x) => x.id === commentId);
    if (!t) continue;
    if (t.resolved) { marker.textContent = "✓"; continue; }
    const n = commentNumber(commentId, order);
    marker.textContent = n != null ? String(n) : "";
  }
}
```

**(A2) In `renderMarkerFor`**, replace:
```js
  marker.textContent = thread.resolved
    ? "✓"
    : String(1 + thread.replies.length);
```
with:
```js
  marker.textContent = thread.resolved ? "✓" : "";
```

**(A3) In `updateMarkerState`**, replace:
```js
  marker.textContent = thread.resolved
    ? "✓"
    : String(1 + thread.replies.length);
```
with:
```js
  renumberMarkers();
```

**(A4) In `add()`'s `doFn`**, replace:
```js
  const doFn = () => {
    threadStore.push(thread);
    writeIsland();
    const resolvedEl = matchAnchor(anchor);
    renderMarkerFor(thread, resolvedEl);
    emit("dirty-changed", { dirty: true });
  };
```
with (add `renumberMarkers()` after the render):
```js
  const doFn = () => {
    threadStore.push(thread);
    writeIsland();
    const resolvedEl = matchAnchor(anchor);
    renderMarkerFor(thread, resolvedEl);
    renumberMarkers();
    emit("dirty-changed", { dirty: true });
  };
```

**(A5) In `deleteComment()`'s `doFn`**, replace:
```js
  const doFn = () => {
    removeMarker(commentId);
    threadStore.splice(idx, 1);
    writeIsland();
    emit("dirty-changed", { dirty: true });
  };
```
with:
```js
  const doFn = () => {
    removeMarker(commentId);
    threadStore.splice(idx, 1);
    writeIsland();
    renumberMarkers();
    emit("dirty-changed", { dirty: true });
  };
```

**(A6) At the END of `reanchorAll()`**, add a `renumberMarkers()` call. Replace:
```js
  for (const thread of threadStore) {
    const el = matchAnchor(thread.anchor);
    if (el) {
      renderMarkerFor(thread, el);
    }
  }
}
```
with:
```js
  for (const thread of threadStore) {
    const el = matchAnchor(thread.anchor);
    if (el) {
      renderMarkerFor(thread, el);
    }
  }
  renumberMarkers();
}
```
(This is the `reanchorAll` function specifically — the one that clears `markers` and re-renders from `threadStore`. Do NOT modify the similarly-shaped `updateAllMarkers`.)

**(A7) In the exported `threads()` function**, add a `number` field. Replace:
```js
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
```
with:
```js
export function threads() {
  const order = documentOrderedIds();
  return threadStore.map((t) => {
    const el = matchAnchor(t.anchor);
    const hypId = el ? idOf(el) : null;
    const rect = el ? domRectToPlain(el.getBoundingClientRect()) : null;
    return {
      ...t,
      unanchored: !el,
      hypId,
      rect,
      number: commentNumber(t.id, order),
    };
  });
}
```

---

## Part B — `app/js/main.js`

**(B1) In `createThreadEl`**, show the number in the thread header. Find this block:
```js
  header.appendChild(createAvatar(thread.author));
  header.appendChild(authorSpan);
  header.appendChild(timeSpan);
  div.appendChild(header);
```
and insert a number badge as the header's FIRST child — replace the block with:
```js
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
```

**(B2) In `renderCommentPanel`**, sort the anchored threads by number so the panel reads top-to-bottom in the same order as the deck. Replace:
```js
  const anchored = threads.filter((t) => !t.unanchored);
```
with:
```js
  const anchored = threads
    .filter((t) => !t.unanchored)
    .sort((a, b) => (a.number || 0) - (b.number || 0));
```

---

## Validation (run before returning)
- `git --no-pager diff -- runtime/js/comments.js app/js/main.js` → confirm ONLY the A1–A7 and B1–B2 changes appear; no stray edits; no non-ASCII identifiers; the `"✓"` check marks preserved.
Report the command, output, and EXIT in `validation`.

## Commit Rule
Do NOT commit. Leave the files modified; the conductor reviews and commits.

## Return Format (the five-field schema, exactly)
- `status` · `landed` · `validation` · `concerns` · `open_questions`
