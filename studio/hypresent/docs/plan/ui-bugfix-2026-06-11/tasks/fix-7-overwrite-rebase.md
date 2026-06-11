---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
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
`--sandbox workspace-write` + `-c approval_policy="never"`. Edit ONLY `app/js/builder/builder-main.js`.

# Fix bug-7 — adding a blank slide then overwriting deletes a neighbor slide

## Goal
Make the deck-save rebase run after BOTH save modes, not only `new-file`. One bounded change: move ONE line out of an `if` block.

## Context Snapshot
In `app/js/builder/builder-main.js`, the `doSave(mode)` function (around lines 514-554) does, on a successful save:

```js
        if (mode === 'new-file') {
          state.deck.path = result.path;
          state.deck.name = result.path.split(/[\\/]/).pop() || result.path;
          if (deckChipName) deckChipName.textContent = state.deck.name;
          await rebaseDeckToSavedFile(result.path);
        }
```

`rebaseDeckToSavedFile()` re-syncs the tray model's `existing`-section indices to the freshly written file. It is gated to `new-file` ONLY. But an **overwrite** save also rewrites the deck's section layout (add/remove/reorder, including blank insertion), so after an overwrite the model's section indices go STALE and the NEXT save resolves `sections[staleIdx]` to the WRONG section — a blank "takes the place of" and deletes a real slide. (The new-file equivalent of this bug was already fixed by adding this rebase; the overwrite branch was missed.)

## Allowed Paths
- `app/js/builder/builder-main.js`

## Forbidden Paths
- Every other file. No new files. No commits.

## Implementation Requirements (exact)
Change the block shown above so the path/name/chip update stays gated to `new-file`, but `rebaseDeckToSavedFile(result.path)` runs after BOTH modes. The result MUST be exactly:

```js
        if (mode === 'new-file') {
          state.deck.path = result.path;
          state.deck.name = result.path.split(/[\\/]/).pop() || result.path;
          if (deckChipName) deckChipName.textContent = state.deck.name;
        }
        // Rebase after BOTH modes: an overwrite also restructures the saved file's
        // sections, so the tray model's existing-indices must be re-synced or the
        // next save resolves stale indices to the wrong sections.
        await rebaseDeckToSavedFile(result.path);
```

Change NOTHING else in the file. Do not rename, reorder, or "improve" adjacent code.

## Validation (run before returning)
- `git --no-pager diff -- app/js/builder/builder-main.js` → MUST show ONLY the `await rebaseDeckToSavedFile(result.path);` line moving out of the `if (mode === 'new-file')` block (plus the explanatory comment). No other change.
Report the command, output, and EXIT in `validation`.

## Commit Rule
Do NOT commit. Leave the file modified; the conductor reviews and commits.

## Return Format (the five-field schema, exactly)
- `status` · `landed` · `validation` · `concerns` · `open_questions`
