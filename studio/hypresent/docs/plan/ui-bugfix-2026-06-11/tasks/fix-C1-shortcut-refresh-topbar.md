---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
  - runtime/js/shortcuts.js
  - app/js/shell/shortcuts-help.js
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
`--sandbox workspace-write` + `-c approval_policy="never"`. Edit ONLY the three allowlisted files. Make ONLY the changes enumerated below — do not refactor, rename, or "improve" anything else.

# Fix bugs 1, 3, 4 — comment shortcut, comment-panel double-refresh, topbar path

This task carries THREE independent fixes. Apply all three exactly.

## Allowed Paths
- `runtime/js/shortcuts.js`
- `app/js/shell/shortcuts-help.js`
- `app/js/main.js`

## Forbidden Paths
- Every other file. No new files. No commits.

---

## Fix bug-1 — comment shortcut Ctrl+Alt+C → Ctrl+M (Ctrl+Alt = AltGr on the owner's keyboard)

**(1a) `runtime/js/shortcuts.js`** — the comment branch currently reads:
```js
    // Comment
    if ((e.key === "c" || e.key === "C") && e.altKey && !e.shiftKey) {
      e.preventDefault();
      handlers.requestComment();
      return;
    }
```
Replace the condition so it fires on Ctrl+M (no Alt):
```js
    // Comment
    if ((e.key === "m" || e.key === "M") && !e.altKey && !e.shiftKey) {
      e.preventDefault();
      handlers.requestComment();
      return;
    }
```

**(1b) `app/js/main.js`** — in the document `keydown` listener (near the end of the file) this line:
```js
    if (e.altKey && k === "c") { e.preventDefault(); document.getElementById("comment-btn")?.click(); return; }
```
becomes:
```js
    if (!e.altKey && k === "m") { e.preventDefault(); document.getElementById("comment-btn")?.click(); return; }
```

**(1c) `app/js/shell/shortcuts-help.js`** — in the help table, this row:
```js
          { keys: ["Ctrl", "Alt", "C"], label: "Comment" },
```
becomes:
```js
          { keys: ["Ctrl", "M"], label: "Comment" },
```

---

## Fix bug-3 — comment panel refreshes twice per op (coalesce, do not remove any trigger)

**`app/js/main.js`** — the function currently reads:
```js
async function refreshCommentPanel() {
  if (!bridge) return;
  try {
    const result = await bridge.command("comments-read");
    renderCommentPanel(result.threads || []);
  } catch (err) {
    console.error("Failed to read comments:", err.message);
  }
}
```
Replace it with a re-entrancy-coalescing version (add the two module-level flags immediately above it):
```js
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
```
(Use ASCII identifiers `_commentRefreshInFlight` / `_commentRefreshQueued` exactly — do NOT introduce non-ASCII characters.) Do not change any caller of `refreshCommentPanel`.

---

## Fix bug-4 — topbar shows the full path twice; show basename + Saved/Unsaved, full path on hover

Owner decision: show only the filename in the doc chip, expose the full path as a hover tooltip, and stop printing "Saved to <full path>" in the status line. Three sub-changes, all in `app/js/main.js`:

**(4a)** `setDocChip` currently:
```js
function setDocChip(name) {
  const chip = document.getElementById("doc-chip");
  const nameEl = document.getElementById("doc-name");
  if (!chip || !nameEl) return;
  if (name) nameEl.textContent = name;
  chip.hidden = false;
  const empty = document.getElementById("canvas-empty");
  if (empty) empty.hidden = true;
}
```
becomes (adds an optional `fullPath` that sets the chip's hover title):
```js
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
```

**(4b)** Fix the basename split (it uses `/[\/]/`, forward-slash only, so Windows backslash paths render whole) AND pass the full path for the tooltip, AND drop the path from the status line, at the THREE save/handoff call sites:

- In the `?file=` handoff branch, the line `setDocChip((result && result.name) || fileParam.split(/[\\/]/).pop() || "");` becomes:
  `setDocChip((result && result.name) || fileParam.split(/[\\/]/).pop() || "", fileParam);`

- In the Save button handler's no-open-file fallback, the two lines
  ```js
          setDocChip((sa.path || "").split(/[\/]/).pop() || "");
          setStatus("Saved to " + (sa.path || ""), "success");
  ```
  become:
  ```js
          setDocChip((sa.path || "").split(/[\\/]/).pop() || "", sa.path || "");
          setStatus("Saved", "success");
  ```

- In the Save button handler's normal path, the line `setStatus("Saved to " + (data.path || ""), "success");` becomes `setStatus("Saved", "success");`

- In the Save As button handler, the two lines
  ```js
        setDocChip((data.path || "").split(/[\/]/).pop() || "");
        setStatus("Saved to " + (data.path || ""), "success");
  ```
  become:
  ```js
        setDocChip((data.path || "").split(/[\\/]/).pop() || "", data.path || "");
        setStatus("Saved", "success");
  ```

Leave the Open-button call `setDocChip(result.name || "")` unchanged. Change nothing else.

## Validation (run before returning)
- `git --no-pager diff -- runtime/js/shortcuts.js app/js/shell/shortcuts-help.js app/js/main.js` → confirm ONLY the changes above appear (bug-1 shortcut rebind ×3, bug-3 coalesce, bug-4 chip/status ×the sites listed). No stray edits, no non-ASCII identifiers.
Report the command, output, and EXIT in `validation`.

## Commit Rule
Do NOT commit. Leave the files modified; the conductor reviews and commits.

## Return Format (the five-field schema, exactly)
- `status` · `landed` · `validation` · `concerns` · `open_questions`
