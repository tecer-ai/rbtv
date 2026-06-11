---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
  - app/js/shell/file-controls.js
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
`--sandbox workspace-write` + `-c approval_policy="never"`. Edit ONLY the two allowlisted files.

# Fix bug-6 — Editor↔Builder switch pops a save dialog with no context (looks like "open", overwrite risk)

## Goal
When the user crosses Editor↔Builder, surface a clear one-line message BEFORE the native save dialog appears, so it is obvious the dialog is a SAVE/choose-destination step and that the deck then opens automatically on the other page. Scope per owner decision D2: clarify only — do NOT change the dialog architecture (auto-open via `?file=` already works). Two tiny JS additions.

## Context Snapshot
- The native dialog shown on both crossings is already a real `SaveFileDialog` (Save button, OverwritePrompt=true) — but it appears unexpectedly after the user clicks "switch", reading as a surprise file picker.
- **Editor→Builder** crossing is `setupOpenInBuilder()` in `app/js/shell/file-controls.js`. After `serializeDoc()` succeeds it calls `apiClient.dialogSaveAs(html)` (around line 52-56). `setStatusSetter()` returns the status setter (signature `(msg, type)`).
- **Builder→Editor** crossing is the `switchToEditorBtn` click handler in `app/js/builder/builder-main.js` (around lines 564-577). After the empty-tray guard it calls `saveDeck({ deck: state.deck, items, mode: 'new-file' })`. `setStatus(msg, type)` is in scope in that file.

## Allowed Paths
- `app/js/shell/file-controls.js`
- `app/js/builder/builder-main.js`

## Forbidden Paths
- Every other file (no server changes, no api-client changes). No new files. No commits.

## Implementation Requirements (exact)
1. In `app/js/shell/file-controls.js`, inside `setupOpenInBuilder`'s click handler, immediately BEFORE the `const result = await apiClient.dialogSaveAs(html);` line, insert:
   ```js
       setStatusSetter()('Choose where to save the presentation — it then opens in the Builder.', '');
   ```
   (Use the existing `setStatusSetter()` accessor; do not refactor the surrounding code.)

2. In `app/js/builder/builder-main.js`, inside the `switchToEditorBtn` click handler, immediately BEFORE the `const result = await saveDeck({ deck: state.deck, items, mode: 'new-file' });` line, insert:
   ```js
        setStatus('Choose where to save the deck — it then opens in the Editor.', '');
   ```
   (Match the indentation of the surrounding lines.)

Change NOTHING else — no dialog-title changes, no server edits, no new behavior.

## Validation (run before returning)
- `git --no-pager diff -- app/js/shell/file-controls.js app/js/builder/builder-main.js` → MUST show exactly the two inserted `setStatus...` lines and nothing else.
Report the command, output, and EXIT in `validation`.

## Commit Rule
Do NOT commit. Leave the files modified; the conductor reviews and commits.

## Return Format (the five-field schema, exactly)
- `status` · `landed` · `validation` · `concerns` · `open_questions`
