---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
  - app/js/main.js
  - app/js/builder/builder-main.js
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
`--sandbox workspace-write` + `-c approval_policy="never"`. Edit ONLY the two allowlisted files. ASCII-only identifiers.

# Fix-round R5 — the Editor/Builder pill toggle should use the save-confirm modal (not discard work)

The top-left `.switcher` pills currently navigate away with only a "Unsaved … will be lost" confirm — discarding unsaved work. Route them through the SAME save-and-switch flow as the toolbar buttons (which already show the confirm-overwrite modal). One handler change per file.

## Allowed Paths
- `app/js/main.js`
- `app/js/builder/builder-main.js`

## Forbidden Paths
- Every other file. No commits.

---

## Step 1 — `app/js/main.js` (editor: the "Builder" pill → use the Open-in-builder flow)

Current handler:
```js
  const navBuilderLink = document.getElementById("nav-builder");
  if (navBuilderLink) {
    navBuilderLink.addEventListener("click", (e) => {
      const unsaved = bridge && (isDirty || historyCursor !== savedCursor);
      if (!unsaved) return;
      if (!confirm("Switch to the Builder? Unsaved changes will be lost.")) {
        e.preventDefault();
      }
    });
  }
```
Replace it with (delegate to the `#open-in-builder-btn`, which serializes + shows the confirm-overwrite modal + saves + navigates):
```js
  const navBuilderLink = document.getElementById("nav-builder");
  if (navBuilderLink) {
    navBuilderLink.addEventListener("click", (e) => {
      // Route the pill switch through the same save + confirm-overwrite modal as the
      // "Open in builder" button, so switching never silently discards unsaved work.
      const oib = document.getElementById("open-in-builder-btn");
      if (oib && !oib.disabled) {
        e.preventDefault();
        oib.click();
      }
      // else: no document open → allow the plain navigation
    });
  }
```

## Step 2 — `app/js/builder/builder-main.js` (builder: the "Editor" pill → use the Switch-to-editor flow)

`switchToEditorBtn` is already defined earlier in the same scope (`const switchToEditorBtn = document.getElementById('switch-to-editor-btn');`). Current handler:
```js
  const navEditorLink = document.getElementById('nav-editor');
  if (navEditorLink) {
    navEditorLink.addEventListener('click', (e) => {
      if (tray.getItems().length === 0) return;
      if (!confirm('Switch to the Editor? Unsaved builder work will be lost.')) {
        e.preventDefault();
      }
    });
  }
```
Replace it with (delegate to `switchToEditorBtn`, which saves + shows the confirm-overwrite modal + navigates):
```js
  const navEditorLink = document.getElementById('nav-editor');
  if (navEditorLink) {
    navEditorLink.addEventListener('click', (e) => {
      // Route the pill switch through the same save + confirm-overwrite modal as the
      // "Switch to editor" button, so switching never silently discards the tray.
      if (tray.getItems().length === 0) return;   // nothing to save → plain navigation
      e.preventDefault();
      if (switchToEditorBtn) switchToEditorBtn.click();
    });
  }
```

Change nothing else in either file.

## Validation (run before returning)
- `git --no-pager diff -- app/js/main.js app/js/builder/builder-main.js` → confirm ONLY the two handler replacements appear (no `confirm(...)` left in either pill handler; each now delegates to its button). No other change.
Report the command, output, and EXIT in `validation`.

## Commit Rule
Do NOT commit. Leave changes in the working tree; the conductor reviews and commits.

## Return Format (the five-field schema, exactly)
- `status` · `landed` · `validation` · `concerns` · `open_questions`
