# DISPATCH — p2-fix (kimi executor) — single bounded fix

You are a bounded code executor. Implement EXACTLY this fix. Do NOT reason about alternatives. If any anchor does not match the live file, HALT and return `DOUBT_ESCALATED`.

## Goal
The cheat-sheet overlay's `Esc`-to-close only works when keyboard focus is in the shell document. When the overlay is opened via `Ctrl+/` while focus is inside the slide iframe, `Esc` does not close it (the shell-document keydown listener never receives the iframe's key). FIX: move focus into the overlay when it opens, so `Esc` always reaches the shell listener.

## Allowlist (work-dir-relative) — touch ONLY these
- `app/js/shell/shortcuts-help.js` (✎)
- `tests/e2e/test_cheatsheet.py` (✎ — add one assertion/test)

## Binding obligations
- Doubt policy: `halt`. Swarm: `disabled`. No subagents.
- No writes outside the allowlist. No scratch files. No `git push`/reset/amend. No external API calls.
- Capture validation output; cite each command + EXIT + WALL_MS in `validation`.

## Exact edits — `app/js/shell/shortcuts-help.js`

### A. In `build()`, make the scrim focusable. Locate by exact text:
```js
    scrim.setAttribute("aria-label", "Keyboard shortcuts");
```
Add immediately after it:
```js
    scrim.setAttribute("tabindex", "-1");
```

### B. In `open()`, focus the scrim after showing. Locate by exact text:
```js
  function open() {
    if (!scrim) build();
    scrim.classList.add("is-open");
```
Add immediately after the `scrim.classList.add("is-open");` line:
```js
    scrim.focus();
```
(Leave the rest of `open()` and all of `close()` unchanged.)

## Test edit — `tests/e2e/test_cheatsheet.py`
Add ONE test (mirror the existing tests' harness/port) asserting that after opening the overlay (via the `#shortcuts-btn` click OR `Ctrl+/`), `document.activeElement` is the `.shortcuts-scrim` element (the overlay receives focus on open) — this is what guarantees `Esc` closes it regardless of prior focus. Keep the existing tests unchanged.

## Validation (run before returning)
- `node --check app/js/shell/shortcuts-help.js` → EXIT 0.
- `python -m pytest tests/e2e/test_cheatsheet.py -q` → all pass.

## Commit rule (this IS a single dispatch — self-commit IS authorized)
After validation passes (EXIT 0): commit locally on `master`, subject starting `[p2-fix]` (e.g. `[p2-fix] fix(hypresent): focus cheat-sheet overlay on open so Esc always closes`). Stage ONLY the 2 allowlist files (explicit `git add <path>` per file — NEVER `git add -A`; the repo has unrelated uncommitted files from other work). Local commit only; NEVER push. Return the hash in `landed`; it MUST match `git log`.

## Return contract — return EXACTLY these five named fields (not prose)
- `status`: `DONE`/`DONE_WITH_NOTES`/`BLOCKED`/`DOUBT_ESCALATED`/`NEEDS_CONTEXT`
- `landed`: files changed + commit hash
- `validation`: each command + EXIT + WALL_MS; SKIPPED_COUNT + per-skip reason
- `concerns`
- `open_questions`
