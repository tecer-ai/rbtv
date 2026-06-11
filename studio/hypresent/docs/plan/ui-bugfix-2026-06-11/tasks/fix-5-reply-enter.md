---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
  - app/js/shell/comment-composer.js
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
`--sandbox workspace-write` + `-c approval_policy="never"`. Edit ONLY `app/js/shell/comment-composer.js`.

# Fix bug-5 — comment/reply composer: plain Enter does nothing (must submit)

## Goal
In the anchored comment composer popover, make plain **Enter submit** the comment/reply and **Shift+Enter insert a newline**, matching the inspector's bottom composer. One bounded change to the textarea keydown handler.

## Context Snapshot
Live repro confirmed: in the popover composer, plain Enter inserts a newline (textarea value became `"...\n"`) and never submits; only Ctrl/Cmd+Enter or the Save button submits — so users think reply is broken. The data path is fine. The bottom panel composer already submits on plain Enter, so this makes the two consistent.

In `app/js/shell/comment-composer.js`, the textarea keydown handler is (around lines 96-100):

```js
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { e.stopPropagation(); e.preventDefault(); closeActive(); return; }
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.stopPropagation(); e.preventDefault(); submit(); return; }
    // plain Enter falls through → inserts a newline (default textarea behavior)
  });
```

`submit()` and `closeActive()` are already defined in the same module; do not redefine them.

## Allowed Paths
- `app/js/shell/comment-composer.js`

## Forbidden Paths
- Every other file. No new files. No commits.

## Implementation Requirements (exact)
Replace the handler above with the version below — add ONE branch so plain Enter (no Shift) submits, and Shift+Enter falls through to a newline:

```js
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { e.stopPropagation(); e.preventDefault(); closeActive(); return; }
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.stopPropagation(); e.preventDefault(); submit(); return; }
    if (e.key === "Enter" && !e.shiftKey) { e.stopPropagation(); e.preventDefault(); submit(); return; }
    // Shift+Enter falls through → inserts a newline (default textarea behavior)
  });
```

Change NOTHING else (the pop-level keydown that also handles Ctrl/Cmd+Enter stays as-is). Do not touch other handlers, styles, or the composer structure.

## Validation (run before returning)
- `git --no-pager diff -- app/js/shell/comment-composer.js` → MUST show ONLY the added plain-Enter branch + the updated trailing comment. No other change.
Report the command, output, and EXIT in `validation`.

## Commit Rule
Do NOT commit. Leave the file modified; the conductor reviews and commits.

## Return Format (the five-field schema, exactly)
- `status` · `landed` · `validation` · `concerns` · `open_questions`
