# State Capsule — shortcuts-copypaste

The resume contract for `rbtv-orchestrating`. A fresh orchestrator rebuilds full state by reading, IN ORDER: **(1) this file → (2) `run-log.md` tail → (3) `decisions.md` → (4) `deliverables.md`**, then the plan (`shortcuts-copypaste-plan.md`) and the per-task files. This capsule is written to be self-contained; the others are the audit/detail backing it.

---

## Resume point
**PHASE 3 NOT STARTED — clean phase boundary, ready for a fresh orchestrator.** (2026-06-09)
Phases 1 and 2 are COMPLETE, reviewed, exercised headed, and approved. The owner asked to stop here and refresh to a new orchestrator before Phase 3. **Next action: run Phase 3 (copy/paste), starting with wave W3 (`p3-1 ∥ p3-2`).** First re-read this capsule + `run-log.md` + `decisions.md` fully before dispatching.

There is NO pending owner question. Phase 2 condition B (Esc fix) is done. Just begin Phase 3.

---

## What this run is
- **Goal:** add keyboard shortcuts + cheat-sheet, whole-box formatting w/ bold/italic repeat-fix, and internal component copy/paste to the hypresent editor. Plan: `shortcuts-copypaste-plan.md` (DEEP, `orchestrated: true`).
- **Door:** Plan ingest (the plan + specs + task files already existed on disk).
- **Workspace / repo:** `3-resources/tools/rbtv` (the rbtv repo, branch **`master`**). **Work-dir for all code: `html/hypresent`** (kimi `--work-dir` points here; absolute: `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/html/hypresent`).
- **Spine location:** this plan folder, `html/hypresent/docs/plan/shortcuts-copypaste/` (run-log, state-capsule, decisions, deliverables, learnings). UNTRACKED in git (readable from disk; a spine-protect commit may have been made — check `git log` for `[spine]`).

## Run configuration (owner-approved at intake)
- **Run mode: end-to-end** — run phases continuously; stop only at the 4 hard checkpoints, genuine worker doubts, or user-needed steps.
- **Context refresh: suggest** — this IS such a refresh, at a clean phase boundary.
- **Budget: default tiers** — no model swaps.
- **Code backend: CLI fleet.**

## Delegation map (FINAL)
| Role | Assigned |
|------|----------|
| Build (bounded code, every code task) | **kimi** (CLI, `--work-dir html/hypresent`, Shape B stdin, `--quiet`) |
| Review gate (ALL external-CLI code) | **claude-opus** (Agent-tool, `model: opus`) — non-overridable pin |
| Checkpoints, p4-1 cold-verify, p4-compound | **conductor** (orchestrator_executed) — exercised headed by the conductor itself |
| Cold verifier (p4-1) | independent Claude w/ chrome-devtools, contract-only |
| Conductor | opus |

---

## DONE so far (with commit hashes — all on `master`)
- **p1-1** (`0c70ed4`) — whole-box bold/italic + bold/italic repeat-fix + `scaleWholeBox` in `runtime/js/text-format.js` + `runtime-main.js` `format` handler passes `current()`. Reviewed (clean). 
- **p1-checkpoint** — C1/C2 exercised headed, all held, owner-approved.
- **p2-1 + p2-2** (wave `e7e482a`) — in-iframe keyboard router (`runtime/js/shortcuts.js` via `initShortcuts(handlers)` DI; `Ctrl+B/I` format, `Ctrl+Del` delete w/ guards, `Ctrl+Alt+C`/`Ctrl+/` forwarded to shell via `emit("shortcut",{action})`) + cheat-sheet (`app/js/shell/shortcuts-help.js`, `?` button in `app/index.html`, `app/css/shell.css`, shell listener + `bridge.on("shortcut")` in `app/js/main.js`).
- **p2-review** (`87144a5`) — removed an out-of-spec `window.__deleteComponentById` global; delete test now drives the real `delete-element` bridge command.
- **p2-fix** (`a3e217d`) — cheat-sheet `open()` sets scrim `tabindex=-1` + `scrim.focus()` so Esc closes regardless of prior focus. Reviewed clean, exercised headed.
- **p2-checkpoint** — C3/C4/C5 exercised headed, all held, owner-approved (option B).

Done-gate evidence sheet (C1–C5 filled, held): `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste.md` (captures in the sibling folder). **C6–C9 still pending** (Phase 3).

---

## ⚠️ RUN-SPECIFIC HAZARDS — a fresh orchestrator MUST honor these

1. **The rbtv repo has an ACTIVE PARALLEL WRITER.** During this run HEAD moved (`0c70ed4`→`ccb4332`→…) and the working tree carries many foreign uncommitted/edited files (`admin/install/*`, `orchestration/*`, `modules/*`, `core/rules/*`, etc.). A bare kimi self-commit ALREADY swept 5 foreign pre-staged files into `a3e217d` (see learnings.md L1).
   - **COMMIT DISCIPLINE (mandatory):** all commits MUST be **pathspec-limited** — `git commit -- <explicit paths>` — OR conductor-staged-then-committed with exactly the wave's files. NEVER bare `git commit` after `git add`; NEVER `git add -A`/`.`. For parallel waves, instruct kimi to NOT commit (leave uncommitted) and the CONDUCTOR wave-commits with explicit pathspec (this is the W2 pattern that worked). Before any commit, check `git diff --cached --name-only` is clean/only-yours.
   - NEVER rewrite history (no amend/reset) in this shared repo — fix forward only.

2. **Synthetic keydown does NOT cross into the slide iframe under automation** (Windows/Chromium). `Ctrl+B` crosses; `Ctrl+Delete`/`Ctrl+C`/`Ctrl+V` likely do NOT. **Phase 3 copy/paste e2e MUST drive the production path** (the real bridge command, e.g. the `paste`/clipboard commands, or the genuine clipboard API) — NEVER a `window.*` test hook (the review will reject those). Each new key combo gets its own drivability check at Contract (`rbtv-build-for-agent-testability`). For headed checkpoint exercises, drive keyboard actions from **shell focus** (shell listener → real path) when the iframe boundary blocks the key.

3. **Shared-file serialization (build waves strictly from this):**
   - `runtime/js/shortcuts.js`: `p2-1 → p3-4` (p3-4 adds copy/paste keys to it — build on the current file).
   - `runtime/js/runtime-main.js`: `p1-1 → p2-1 → p3-4`.
   - Never parallelize two tasks that write the same file.

---

## NEXT: Phase 3 plan (copy/paste) — waves + checkpoints
Read `shortcuts-copypaste-plan.md` §Orchestration + each task file before dispatch. Spec: `specs/copypaste-spec.md` (C6–C9 + clipboard-slot shape + paste-command signature).
- **W3: `p3-1 ∥ p3-2`** (parallel, disjoint allowlists) — `p3-1` in-memory clipboard slot (`runtime/js/clipboard.js`); `p3-2` paste/insert command factory (`runtime/js/commands.js`).
- **W4: `p3-3`** — float-paste + insert-paste + grid fallback + whole-slide (`runtime/js/paste.js`).
- **W5: `p3-4`** — copy/paste keys + pointer + bridge commands + module map (`runtime/js/shortcuts.js`, `runtime/js/runtime-main.js`, `docs/spec/03-module-map.md`, `tests/e2e/test_copy_paste.py`).
- **p3-checkpoint** (HARD halt) — exercise C6/C7/C8/C9 headed, then owner approval.
- **Final:** `p4-1` (independent cold-verifier, re-exercise C1–C9 from contract + compat regression) → `p4-refs` (plan-link audit) → `p4-compound` (process `learnings.md` — there is ALREADY 1 entry: the commit-collision → a real rbtv orchestration improvement) → **p4-checkpoint** (final owner approval).

For W3 parallel: same as W2 — kimi builds both UNCOMMITTED, conductor pathspec-wave-commits at the boundary, then Opus reviews. Each kimi dispatch = compose a `phaseN/pX.dispatch.md` (header: binding addendum + 5-field return schema + inlined `copypaste-spec.md` + verbatim task payload), launch `cat dispatch.md | kimi --work-dir <abs html/hypresent> --input-format text --quiet` in background.

---

## HOW-TO recipes (validated this run)

### Dispatch kimi (background)
```
cd 3-resources/tools/rbtv
cat "<plan>/phaseN/pX.dispatch.md" | kimi --work-dir "C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/html/hypresent" --input-format text --quiet > "<plan>/phaseN/_pX-kimi.log" 2>&1
```
kimi at `C:\Users\henri\.local\bin\kimi.exe` v1.41.0. Pre-flight each dispatch: `kimi --version` + grep `kimi --help` for pinned flags. Returns may be PROSE (drift) — RECONCILE against `git log`/`git status`/disk; disk = truth. Reconcile EVERY return: hash in `git log`, diff = only allowlist files, re-run validations yourself.

### Headed checkpoint exercise (chrome-devtools MCP)
1. Start server: `cd html/hypresent && HYP_TEST_DIALOG=1 python server/server.py 127.0.0.1 8799` (background). Stop it after via PowerShell `Get-NetTCPConnection -LocalPort 8799 | Stop-Process`.
2. `new_page http://127.0.0.1:8799/app/`.
3. Arm the file-open seam + seed author via `evaluate_script`: `localStorage.setItem('hypresent-comment-author','Tester')` then `fetch('/api/_test/set-dialog',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:'<abs deck path>'})})`. Real deck: `…/html/hypresent/tecer-gsmm-introduction.html`.
4. `take_snapshot` → click the **Open…** button (real click) → poll `iframe.doc-frame`.contentWindow.hyp for ready.
5. Doc renders in `iframe.doc-frame`; its content appears in the (non-verbose) snapshot with uids. Toolbar buttons are in the shell (stable uids: Bold/Italic/Font−/Font+/Delete; the `?` button = "Keyboard shortcuts"). Select a component by clicking its in-iframe uid (real click) — selection shows as `.hyp-selection-ring`; verify via `evaluate_script` comparing ring rect to the element rect.
6. Keyboard via `press_key` (e.g. `Control+Alt+c`, `Control+Delete`, `Control+/`, `Escape`, `Control+Home`, `Control+Shift+ArrowRight`). Note: keys may not cross into the iframe — drive from shell focus when needed.
7. Capture screenshots to `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste/`. (Screenshot occasionally times out — just retry once.)

### Deck specifics
- `.slide-title` is CSS-bold (`font-weight:700`) → `execCommand("bold")` on it toggles OFF first; use `.slide-subtitle` (weight 400) for bold tests, `.slide-title` for italic.
- Elements carry `data-hyp-id` (e.g. `hyp-13`). Runtime API on `iframe.contentWindow.hyp` exposes `command`/`version`/`comments` (NOT selection).

---

## Active red-sets
_none_

## Active doubts / open questions
_none blocking._ Optional future polish (NOT blocking, owner not yet asked): cheat-sheet `close()` does not restore focus to the opener (standard modal a11y) — could be a tiny follow-up if desired.
