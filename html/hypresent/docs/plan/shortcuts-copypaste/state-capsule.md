# State Capsule — shortcuts-copypaste

The resume contract for `rbtv-orchestrating`. A fresh orchestrator rebuilds full state by reading, IN ORDER: **(1) this file → (2) `run-log.md` tail → (3) `decisions.md` → (4) `deliverables.md`**, then the plan (`shortcuts-copypaste-plan.md`) and the per-task files. This capsule is written to be self-contained; the others are the audit/detail backing it.

---

## Resume point
**FINAL PHASE — `p4-1` + `p4-refs` + `p4-compound` ALL DONE (2026-06-09). NEXT: `p4-checkpoint` (HARD halt) — awaiting owner approval to complete the plan. NO code/work pending; the only open items are owner DECISIONS (below).**
Phase 3 done/approved earlier: p3-1+p3-2 (`d66021c`), p3-3 (`92a0423`+`6c7a129`), p3-4 (`3aca3f6`), p3-fix (`a27c401`); C6–C9 held headed (C9 after p3-fix).
**`p4-1` DONE:** independent cold verifier (opus, chrome-devtools, contract-only) re-exercised C1–C9 → C1-C4/C6-C9 held; **C5 it graded `failed` was a FALSE NEGATIVE** (its visibility boolean read the opacity:0/pointer-events:none/inset:0 hidden-but-present scrim as "visible"). Reconciled to **held** on the verifier's OWN screenshots (overlay closed) + conductor measured re-exercise (opacity 1→0 both open routes). Compat regression **39 passed / EXIT 0**. Conductor exit probes E1 (C5 close) + E2 (cross-feature C1+C6+C9 integration) held. Consolidated sheet updated. Deck file byte-identical (never saved). **C1–C9 ALL held.**

**FRESH CONDUCTOR — resume procedure:** read THIS capsule → `run-log.md` tail → `decisions.md` → `deliverables.md`, then reconcile disk (`git -C 3-resources/tools/rbtv log` — confirm the 5 build commits + `a490b89` are ancestors; the parallel writer keeps advancing HEAD with foreign commits — expected). Then run the REMAINING final steps in order:
1. ✅ **`p4-1`** — DONE (above). Cold-verify sheet `1-projects/.../hypresent/2026-06-09-shortcuts-copypaste-coldverify.md`; consolidation in `…/2026-06-08-shortcuts-copypaste.md` § p4-1.
2. ✅ **`p4-refs`** — DONE. Link audit CLEAN (live docs use `./`/`../` + root-relative externals; dispatch-file paths correctly work-dir-relative; no fixes).
3. ✅ **`p4-compound`** — DRAFTED (write-gated). 2 proposals from `learnings.md`: **L1** → `rbtv-orchestrating` pathspec-commit discipline (PRD `.user/compounds/rbtv-orchestrating/cp-rbtv-orchestrating-pathspec-commit-shared-repo.md`); **L2** → done-gate/cold-verifier user-perceived-visibility check (PRD folder owner-routed: `rbtv-done-gate/` new vs `rbtv-orchestrating/`). NOT written — owner approves at p4-checkpoint, THEN write PRDs + add eval task in `2-areas/compounds/compounds-tasks.md`.
4. **`p4-checkpoint`** (HARD halt — NEXT) — final owner approval to complete the plan. Owner-decision items: (a) accept the **C5 reconciliation** (verifier false-negative → held); (b) the **C1 held-surprising** (bold on CSS-bold text — pre-existing quirk); (c) the known **out-of-scope orphan-UI-tag** hardening flag; (d) approve **writing the 2 compound PRDs** (+ route L2's folder); (e) approve **completing the plan**.

There is NO code work pending and NO open owner question. Run mode is end-to-end — the per-task HALTs of p4-1/p4-compound roll up into the single p4-checkpoint halt; nothing is WRITTEN as a system change until owner approval.

---

## What this run is
- **Goal:** add keyboard shortcuts + cheat-sheet, whole-box formatting w/ bold/italic repeat-fix, and internal component copy/paste to the hypresent editor. Plan: `shortcuts-copypaste-plan.md` (DEEP, `orchestrated: true`).
- **Door:** Plan ingest (the plan + specs + task files already existed on disk).
- **Workspace / repo:** `3-resources/tools/rbtv` (the rbtv repo, branch **`master`**). **Work-dir for all code: `html/hypresent`** (kimi `--work-dir` points here; absolute: `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/html/hypresent`).
- **Spine location:** this plan folder, `html/hypresent/docs/plan/shortcuts-copypaste/` (run-log, state-capsule, decisions, deliverables, learnings). The CODE commits land in the rbtv repo on `master`; the spine itself is loosely tracked (a `[spine]` commit `a490b89` protected it at the phase-3 boundary).

## Run configuration (owner-approved at intake)
- **Run mode: end-to-end** — run phases continuously; stop only at the 4 hard checkpoints, genuine worker doubts, or user-needed steps.
- **Context refresh: suggest.**
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
- **p1-1** (`0c70ed4`) — whole-box bold/italic + repeat-fix + `scaleWholeBox` (`text-format.js`, `runtime-main.js`). Reviewed clean.
- **p1-checkpoint** — C1/C2 exercised headed, held, owner-approved.
- **p2-1 + p2-2** (wave `e7e482a`) — in-iframe keyboard router (`shortcuts.js` via `initShortcuts` DI) + cheat-sheet (`shortcuts-help.js`, `?` button, shell listener).
- **p2-review** (`87144a5`) — removed out-of-spec `window.__deleteComponentById`; delete test drives the real `delete-element` bridge command.
- **p2-fix** (`a3e217d`) — cheat-sheet focuses scrim on open so Esc always closes. Reviewed clean, exercised headed.
- **p2-checkpoint** — C3/C4/C5 exercised headed, held, owner-approved (option B).
- **p3-1 + p3-2** (wave `d66021c`) — `runtime/js/clipboard.js` (in-memory slot: deep clone + full `data-hyp-*` strip via `stripAllHyp`, `wasRegion`, `cascade`, `copy/get/hasContent/bumpCascade`) + `runtime/js/commands.js` `paste(node,parentHypId,nextHypId)` factory (inverse of `deleteElement`; `parentHypId===null`→`document.body`). Opus review CLEAN (0 defects); 3 forward bindings for p3-3 logged → decisions.md.

Done-gate evidence sheet (C1–C5 filled, held): `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste.md`. **C6–C9 still pending** (exercised at p3-checkpoint).

---

## ⚠️ RUN-SPECIFIC HAZARDS — a fresh orchestrator MUST honor these

1. **The rbtv repo has an ACTIVE PARALLEL WRITER.** HEAD has moved repeatedly during this run and the working tree carries many foreign uncommitted/untracked files (`orchestration/*`, `admin/install/*`, `modules/*`, `core/rules/*`, `how-it-works.html`, the `slide-expand` plan spine, etc.). A bare kimi self-commit ALREADY swept 5 foreign pre-staged files into `a3e217d` once (learnings.md L1). **W3 `d66021c` was committed clean by EXPLICIT PATHSPEC — the discipline works; keep using it.**
   - **COMMIT DISCIPLINE (mandatory):** all commits MUST be **pathspec-limited** — conductor `git add <exact paths>` then `git commit -- <exact paths>` (the `-- <paths>` commits ONLY those paths even if the index holds foreign staged files). NEVER bare `git commit` after `git add`; NEVER `git add -A`/`.`. For parallel waves AND single tasks while the foreign writer is active: instruct kimi to NOT commit (leave uncommitted); the CONDUCTOR pathspec-commits. Before any commit, check `git diff --cached --name-only` is only-yours.
   - NEVER rewrite history (no amend/reset) in this shared repo — fix forward only.

2. **Synthetic keydown does NOT cross into the slide iframe under automation** (Windows/Chromium). `Ctrl+B` crosses; `Ctrl+Delete`/`Ctrl+C`/`Ctrl+V` likely do NOT. **Phase 3 copy/paste e2e (p3-4) MUST drive the production path** (the real bridge command / genuine clipboard API), NEVER a `window.*` test hook (review WILL reject those). Each new key combo gets its own drivability check at Contract. For headed checkpoint exercises, drive keyboard actions from **shell focus** (shell listener → real path) when the iframe boundary blocks the key.

3. **Shared-file serialization (build waves strictly from this):**
   - `runtime/js/shortcuts.js`: `p2-1 → p3-4` (p3-4 adds copy/paste keys to it — build on the current file).
   - `runtime/js/runtime-main.js`: `p1-1 → p2-1 → p3-4`.
   - Never parallelize two tasks that write the same file. (W3's two files — clipboard.js/commands.js — were disjoint; W4 `p3-3` is a single new file `paste.js`; W5 `p3-4` touches the shared shortcuts.js + runtime-main.js, so it is SERIAL after everything.)

---

## NEXT: Phase 3 plan (copy/paste) — waves + checkpoints
Read `shortcuts-copypaste-plan.md` §Orchestration + each task file before dispatch. Spec: `specs/copypaste-spec.md` (C6–C9 + clipboard-slot shape + paste-command signature).
- ✅ **W3: `p3-1 ∥ p3-2`** — clipboard slot + paste command. DONE (`d66021c`), reviewed clean.
- ⏳ **W4: `p3-3`** — float-paste + insert-paste + grid fallback + whole-slide (`runtime/js/paste.js`). DISPATCHED (in-flight). Single new file; conductor pathspec-commits on return; Opus reviews.
- **W5: `p3-4`** — copy/paste keys + pointer + bridge commands + module map (`runtime/js/shortcuts.js`, `runtime/js/runtime-main.js`, `docs/spec/03-module-map.md`, `tests/e2e/test_copy_paste.py`). SERIAL (shared files); its e2e MUST drive the production path (hazard #2).
- **p3-checkpoint** (HARD halt) — exercise C6/C7/C8/C9 headed, then owner approval.
- **Final:** `p4-1` (independent cold-verifier, re-exercise C1–C9 from contract + compat regression) → `p4-refs` (plan-link audit) → `p4-compound` (process `learnings.md` — ALREADY 1 entry: the commit-collision) → **p4-checkpoint** (final owner approval).

W4 `p3-3` dispatch is composed at `phase-3/p3-3.dispatch.md` (header: commit-override + binding addendum + 5-field schema + 3 inherited p3-3 bindings + inlined copypaste-spec rows 3–11 + verbatim task). Launch: `cat phase-3/p3-3.dispatch.md | kimi --work-dir <abs html/hypresent> --input-format text --quiet > phase-3/_p3-3-kimi.log 2>&1`.

---

## HOW-TO recipes (validated this run)

### Dispatch kimi (background)
```
cat "<plan>/phaseN/pX.dispatch.md" | kimi --work-dir "C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/html/hypresent" --input-format text --quiet > "<plan>/phaseN/_pX-kimi.log" 2>&1
```
kimi at `C:\Users\henri\.local\bin\kimi.exe` v1.41.0. Pre-flight each dispatch: `kimi --version` + grep `kimi --help` for pinned flags (PASS this session). Returns may be PROSE (drift) — RECONCILE against `git log`/`git status`/disk; disk = truth. Reconcile EVERY return: hash in `git log`, diff = only allowlist files, re-run `node --check` yourself. Session ids captured this run: p3-1 `44f5cdcc-fa1b-4611-80fb-bb6ded331cf5`, p3-2 `52c97600-b8ac-49c0-9998-9649bdea6ccc` (resume via `kimi -r <id>`).

### Conductor pathspec wave-commit (the discipline that works)
```
git -C <rbtv> add <exact work-dir-relative paths>
git -C <rbtv> diff --cached --name-only      # MUST be only-yours
git -C <rbtv> commit -m "[<ids>] <subject>" -m "Co-Authored-By: …" -- <exact paths>
git -C <rbtv> log -1 --stat                  # confirm exactly your files
```

### Headed checkpoint exercise (chrome-devtools MCP) — for p3-checkpoint
1. Start server: `cd html/hypresent && HYP_TEST_DIALOG=1 python server/server.py 127.0.0.1 8799` (background). Stop after via `Get-NetTCPConnection -LocalPort 8799 | Stop-Process`.
2. `new_page http://127.0.0.1:8799/app/`.
3. Arm the file-open seam + seed author via `evaluate_script`: `localStorage.setItem('hypresent-comment-author','Tester')` then `fetch('/api/_test/set-dialog',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:'<abs deck path>'})})`. Real deck: `…/html/hypresent/tecer-gsmm-introduction.html`. Fixtures for C7 flex/grid: `tests/e2e/fixtures/flow-grow.html` (flex row) + `grid-healthy.html` (CSS grid).
4. `take_snapshot` → click the **Open…** button (real click) → poll `iframe.doc-frame`.contentWindow.hyp for ready.
5. Select a component by clicking its in-iframe uid (real click) — selection shows as `.hyp-selection-ring`. Copy/paste e2e/exercise MUST drive the production path (hazard #2): for keys that don't cross the iframe, drive the bridge command from shell focus / the real clipboard path. Measure `getBoundingClientRect` for C6 (siblings unchanged) and C7 (siblings moved).
6. Capture screenshots to `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste/`. (Screenshot occasionally times out — retry once.)

### Deck specifics
- `.slide-title` is CSS-bold (`font-weight:700`) → use `.slide-subtitle` (weight 400) for bold tests, `.slide-title` for italic.
- Elements carry `data-hyp-id` (e.g. `hyp-13`). Runtime API on `iframe.contentWindow.hyp` exposes `command`/`version`/`comments` (NOT selection).

---

## Active red-sets
_none_

## Active doubts / open questions
_none blocking._ The entire build + final verification phase is DONE; the run sits at the `p4-checkpoint` HARD halt awaiting owner approval. The open items are owner DECISIONS, not blockers (see Resume point: C5 reconciliation, C1 held-surprising, orphan-UI-tag flag, writing the 2 compound PRDs, completing the plan). Consolidated evidence sheet (C1–C9 all `held` after reconciliation): `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste.md` (§ p4-1 consolidation); independent cold-verify sheet: `…/2026-06-09-shortcuts-copypaste-coldverify.md`.

_RESOLVED 2026-06-09:_ (1) C9 whole-slide-redo defect → `p3-fix` `a27c401`; (2) kimi-quota 429 block on p3-4 (re-dispatched after reset, clean). _Flagged future hardening (out of scope):_ `element-registry.js` `tag()`/`shouldTag` could skip `hyp-`-classed editor artifacts so UI elements never count as regions. _Non-blocking polish:_ cheat-sheet `close()` focus-restore (modal a11y nicety).

_Non-blocking future polish (owner not yet asked):_ cheat-sheet `close()` does not restore focus to the opener (standard modal a11y) — tiny follow-up if desired.
