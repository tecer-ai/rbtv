# Decisions - shortcuts-copypaste

> **Purpose:** This document captures shaping decisions, discoveries, constraints, and references that future agents need. The Original Shaping section is immutable. Other sections are append-only during routine execution.

---

## Original Shaping

### Scope Definition

**What this accomplishes:**
- Fix the bold/italic **repeat bug** — formatting only applied on the first click; the second press did nothing until the element was re-selected.
- **Whole-box formatting** — with a text box selected (not editing), bold/italic/A+/A− act on the whole box; A+/A− scale every text size proportionally.
- **Keyboard shortcuts** — bold, italic, comment, delete-component, copy, paste (float), paste (into layout), show-shortcuts — plus a clickable cheat-sheet overlay listing them.
- **Internal copy/paste of a component** — float-paste under the cursor (no reflow), insert-paste into the row/grid (reflow, grid falls back to float), whole-slide duplicate, all undoable and serializing cleanly.

**What this does NOT include:**
- OS / system-clipboard or cross-window / cross-file copy.
- Multi-select copy.
- New dedicated font-size keyboard shortcuts (A+/A− stay button-driven; only their whole-box behaviour changes).

### Key Decisions

Locked product decisions D1–D11 — full rationale in `./shortcuts-copypaste-design.md` §4 (the approved design). Carried here because they bind every backing task:

| # | Decision | Choice |
|---|----------|--------|
| D1 | Paste model | `Ctrl+V` floats a copy (no reflow); `Ctrl+Shift+V` inserts into the row/grid (reflows) |
| D2 | Clipboard scope | Internal, in-memory, this deck only |
| D3 | Float-paste position | Under the mouse cursor; fallback = centre of the slide in view |
| D4 | `Ctrl+C` while typing | Stays native text copy; copies the component only when a component is selected and NOT editing |
| D5 | Comments on a copy | Paste clean (fresh ids ⇒ no anchor matches) |
| D6 | Copying a whole slide | Paste duplicates the slide (always inserts; a slide cannot float) |
| D7 | Repeated paste | Cascades each copy by an offset |
| D8 | Comment shortcut key | `Ctrl+Alt+C` (NOT `Ctrl+Shift+C`, which is Chrome Inspect-Element) |
| D9 | Bold/italic/A± scope | Whole text box when selected; highlighted words when editing |
| D10 | Whole-box font size | Scale ALL text proportionally (one factor × every size) |
| D11 | Insert-paste into a grid | Fall back to float-paste (a fixed grid breaks instead of rebalancing) |

Planning-time decisions:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestration | `orchestrated: true`, **DEEP** pre-resolution | AFK fleet run; resolve executor/reviewer/allowlist/validation/batching up front so workers do not halt mid-run |
| Code work | Yes — specs authored per feature | each phase has a behavior+test-plan spec under `./specs/`; tasks reference, never restate |
| PR1 — Phase 1 `format` handler passes the selection into `text-format` | `runtime-main.js`'s `register("format")` calls `applyFormat(op, current())`; `text-format.apply(op, selInfo)` resolves the selected element via `byId(selInfo.hypId)` for the whole-box path | AVOIDS a `selection.js ↔ text-format.js` ES-module cycle (`selection.js` already imports `computeAlignCaps` from `text-format.js`; the codebase deliberately breaks such cycles — `interaction.js` R09). Cost: `runtime-main.js` joins Phase 1 → serialization `runtime-main.js: p1-1 → p2-1 → p3-4` (still linear; waves unchanged). **Supersedes** the earlier "leave `runtime-main.js` untouched" call. |
| PR2 — module map updated once | `docs/spec/03-module-map.md` updated only in `p3-4`, listing all four new modules | single owner of that file avoids a shared-file conflict; brief staleness between P2 and P3 within a run is accepted |
| PR3 — independent cold verifier | `p4-1` re-exercises C1–C9 given only the contract + running artifact | orchestrated done-gate: builder-graded sheets are insufficient (`rbtv-done-gate` § Orchestrated Dispatches) |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Compatibility regression set stays green | design §12 | `test_r3_delete.py` (esp. `test_no_keyboard_delete`), `test_r8_font_size_repeat.py`, `test_r7_alignment.py`, serializer unit tests in `tests/unit/` |
| Keyboard delete is `Ctrl+Del` ONLY | design §6.4, `test_r3_delete::test_no_keyboard_delete` | plain `Delete`/`Backspace` MUST stay inert |
| All injected DOM is `hyp-`/`data-hyp-*`; all mutations via command + history; serializer strips on save | design §1 (A2/A3/A6/A12) | new modules follow the prefix + command/history contract; floated copies' inline `position/left/top`/`translate` are real content styles → preserved |
| Whole-box bold/italic manage `contenteditable` LOCALLY | design §5.3 | MUST NOT route through `text-edit.enterEdit` (its blur listener + interaction-suspend are for user-driven edits); always restore prior `contenteditable`, keep the ring |
| Done-gate fidelity floor | `rbtv-done-gate` | headed browser + real mouse/keyboard, real deck (`tecer-gsmm-introduction.html`) + `flow-grow.html`/`grid-healthy.html`, measured `getBoundingClientRect`, captures on disk |
| Drivability | design §11, `rbtv-build-for-agent-testability` | all C1–C9 are `drivable` as-is (internal clipboard ⇒ no native OS dialog) → **no test seam to build** |

### User Inputs

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Source + housekeeping | "plan …shortcuts-copypaste-design.md then move the design file to the plan folder (also, update the planning workflow…)" | This plan. Design already lives in this folder ⇒ no move needed. Workflow change handled separately, after the plan. |
| 2 | Run mode | DEEP orchestration | per-task executor/reviewer/allowlist/validation + plan-level serialization/hard-halts |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Plan layout | "move the design to the plan folder" | Design already in `docs/plan/shortcuts-copypaste/`; matches the `slide-expand` precedent (design+plan co-located) | Flat layout; no move — satisfied by placement |
| 2 | Phase-1 shared-file handling | (unset) | Read `selection.current()` inside `text-format.js` rather than pass a hint through `runtime-main.js` | Adopted (PR1) — simpler serialization |

---

<!-- BEGIN PLAN-SPECIFIC -->
## Standards Applied

### Authoring Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Task-file contract | every build task is zero-context: exact current-code anchors, explicit allowlist, self-verifiable acceptance, return contract |
| Dependency ordering + shared-file serialization | `runtime-main.js: p1-1 → p2-1 → p3-4`; `shortcuts.js: p2-1 → p3-4`; parallel waves built only from disjoint allowlists |
| `rbtv-done-gate` | C1–C9 are owner-observable; exercised headed at the fidelity floor; one evidence sheet; independent cold verifier at `p4-1` |
| `rbtv-build-for-agent-testability` | drivability checked at Contract — all criteria drivable as-is, no seam required (design §11) |
| Routing | bounded code → `kimi` executor; reviewer floor `claude-opus` (Opus reviews ALL external-CLI code) |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| No file outside a task's allowlist is touched | dispatcher diffs actual changes vs the task allowlist |
| Wave commits at each boundary | parallel uncommitted waves make per-task diffs inseparable; commit at wave end |
| Plain `Delete`/`Backspace` inert | `p2-checkpoint` runs `test_r3_delete::test_no_keyboard_delete` |

---

## Decisions and Discoveries

> **APPEND-ONLY RULES:**
> 1. Only capture decisions, discoveries, and unexpected constraints — NOT routine task completions
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Ask yourself: "Will this matter in one month?" If no, don't log it
>
> **What belongs here:** Decisions made during execution (with rationale), discoveries that change prior decisions, unexpected constraints
> **What does NOT belong:** Routine task completions ("created file X", "updated config Y")

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

<!-- Decisions and discovery entries will be appended below this line -->

### Decision (p1-checkpoint, 2026-06-09): Phase 1 APPROVED by owner
C1 (whole-box bold/italic/proportional-A±/undo) and C2 (editing-path repeat) all `held` at the done-gate fidelity floor (headed Chrome, real deck). Owner approved option A (proceed to Phase 2). The bold-on-CSS-bold-text `held-surprising` quirk was surfaced and accepted as standard rich-text behavior (no special-casing). Scope: unblocks Phase 2.

### Decision (p2-fix, 2026-06-09): cheat-sheet overlay focuses itself on open (Esc closes regardless of prior focus)
Owner approved p2-checkpoint with condition B. Fix: `createShortcutsHelp().open()` sets `tabindex=-1` on the scrim and calls `scrim.focus()`, so opening via `Ctrl+/` while focus is in the iframe still lets `Esc` close it. Commit `a3e217d` `[p2-fix]`. Re-exercised headed (focus moves to scrim on open; Esc closes). Scope: resolves the C5 held-surprising note.

### Discovery (p2-fix commit, 2026-06-09): bare CLI self-commit swept a contaminated shared index — use pathspec commits
Commit `a3e217d` unintentionally included 5 foreign files a parallel session had pre-staged in the shared rbtv index (`git commit` commits the whole index, not just the worker's `git add`). History NOT rewritten (parallel-session discipline). **Scope — all remaining waves (incl. Phase 3):** commits MUST be pathspec-limited (`git commit -- <paths>`) or conductor-staged-and-committed; CLI workers must NOT bare-self-commit while a parallel writer is active in this repo. Full learning in `./learnings.md` (Learning 1).

### Discovery (p2 review, 2026-06-09): synthetic keydown does not cross into the iframe (Windows headless Chromium) — affects P3
A real `Ctrl+Delete` key event does NOT reach the iframe document under headless Chromium/Windows (the component survives), while `Ctrl+B` DOES cross. p2-1's first attempt exposed a `window.__deleteComponentById` global to work around this; review REMOVED it and rewrote the test to drive the real `delete-element` bridge command (the production path). **Scope — P3 (`p3-4` copy/paste keys):** synthetic `Ctrl+C`/`Ctrl+V`/`Ctrl+Shift+V` likely won't cross into the iframe either; P3 e2e must drive the production clipboard/paste path (real bridge command or genuine clipboard API), NEVER a `window.*` test hook. Each new combo needs its own drivability check at Contract (`rbtv-build-for-agent-testability`).

### Decision (W2 dispatch, 2026-06-09): parallel-wave commit handled by conductor, not kimi self-commit
For the first PARALLEL wave (`p2-1 ∥ p2-2`), both kimi workers run validation but leave their (disjoint) allowlisted changes UNCOMMITTED; the conductor commits at the wave boundary after return + Opus review. Rationale: two concurrent kimi self-commits on the same repo race on `.git/index.lock`; deferring to a conductor wave-commit removes the race AND aligns with the routing commit-pin (commits via a commit worker, CLI workers off commits). Overrides the per-task `Commit Rule` for this wave only. Scope: W2 (and any future parallel wave).

### Discovery (p1-1 review, 2026-06-09): editing-path repeat-fix depends on the format-snapshot being primed
The editing-path bold/italic repeat-fix reuses the pre-existing R8 `format-snapshot`/`savedRange` mechanism (toolbar `mousedown` primes the snapshot) to restore the toolbar-collapsed selection before capturing char offsets. **Scope:** `p2-1` must ensure its `Ctrl+B`/`Ctrl+I` keyboard handlers also prime that snapshot (or the editing-path restore falls back to the live selection and the keyboard repeat-fix won't hold). Rationale: keys bypass the toolbar `mousedown` that buttons trigger. Verified clean for the button path in p1-1.

### Decision (p3-checkpoint, 2026-06-09): Phase 3 APPROVED by owner
C6–C9 all `held` at the done-gate fidelity floor (headed Chrome; real `Ctrl+C/V/Shift+V` for C6/C7-flex — keys DO cross the iframe under chrome-devtools CDP; production bridge command for C7-grid/C8/C9; measured `getBoundingClientRect`). The C9 whole-slide-redo defect was found at the checkpoint and FIXED (`p3-fix` `a27c401`) BEFORE approval, then re-exercised headed → clean round-trip. Owner approved p3-checkpoint and requested a context refresh at this clean phase boundary. Scope: Phase 3 COMPLETE; unblocks the final phase (`p4-1` cold-verifier C1–C9 + compat regression → `p4-refs` → `p4-compound` → `p4-checkpoint`).

### Decision (p3-fix, 2026-06-09): C9 whole-slide-redo defect FIXED; root cause = `tag()` re-run on redo stamping editor artifacts
Owner chose to fix before Phase 3 approval. Top-tier Opus debug agent root-caused it (CORRECTING the initial node-spawn hypothesis): the paste command's `do(){ cmd.do(); tag(); }` re-runs `tag()` on REDO; `tag()` walks `document.body` and stamps the editor's OWN untagged UI artifacts (selection ring + Moveable interaction wrapper appended by `select()`/`mount()`, plus `color.js`'s persistent `_hexProbe` span) with `data-hyp-id` — and since `runtime-main` counts body-children-carrying-`data-hyp-id` as regions, those artifacts register as orphan "regions" the command's `undo()` never removes. Fix (`a27c401`): a one-time `let tagged=false` guard so `tag()` runs only on the FIRST paste, applied to all three paste paths (`pasteRegion`, `pasteFloat`, `pasteIntoLayout` — all shared the latent bug; the prior 4 e2e tests missed float/layout because they never asserted body-count after a redo). Regression `test_region_paste_undo_redo_roundtrip` + `two-regions.html` fixture added (fails-before/passes-after; e2e 5 passed). C9 re-exercised headed → clean round-trip (baseline 10→paste 11→undo 10→redo 11 no-orphans→undo 10) → `held`. **Candidate future hardening (out of scope, flagged):** make `element-registry.js` `tag()`/`shouldTag` skip `hyp-`-classed editor artifacts so UI elements never count as regions. Scope: resolves C9; unblocks Phase 3 approval.

### Discovery (p3-checkpoint, 2026-06-09): C6/C7/C8 HELD headed; C9 whole-slide REDO defect → p3-fix needed
Conductor headed exercise (chrome-devtools MCP; **real keys** for C6 + C7-flex, production bridge command for C7-grid/C8/C9): **C6** (float, no-reflow — originals moved 0.00px), **C7** (flex insert reflow — `hyp-4` +197.8px/`hyp-5` +82.4px; grid → float fallback, grid intact 3 children), **C8** (whole-slide copy → new `SECTION` region, count 11→12) all HELD with measured geometry. **C9:** undo-removes-paste, serialize (100,106 chars, node-count guard passes), and no-comment-threads (0 anchors) all HELD — BUT **whole-slide REDO is DEFECTIVE**: redo of a region paste over-adds untracked orphan regions (paste 11→12, undo →11, redo →14, one undo →13 leaving `hyp-411`/`hyp-412`). Component undo/redo is clean (e2e `test_copy_paste` 4 passed). **Root cause:** `pasteRegion()`'s command `do(){ cmd.do(); tag(); }` re-runs `tag()` on redo, spawning untracked duplicates of the re-inserted slide clone outside the command's `undo()` scope. **Scope — NEW `p3-fix` on `runtime/js/paste.js`:** tag the clone ONCE at initial paste (before the `historyPush`, or guard tag to first-run) so redo only re-inserts the already-tagged node; audit `pasteFloat`'s do()-tag() the same way; add a C9 whole-slide-redo e2e case; re-exercise C9 headed. **Also NEW (testability):** real `Ctrl+C`/`Ctrl+V`/`Ctrl+Shift+V` DO cross into the slide iframe under chrome-devtools CDP `press_key` (the "synthetic keydown doesn't cross" limit was Playwright-`dispatchEvent`-specific) — the real-keystroke gesture is headed-provable.

### Discovery (p3-4 review, 2026-06-09): Phase 3 build complete; p3-checkpoint headed-exercise requirements
Opus review of p3-4 (keys + bridge commands + module map + e2e) → DONE clean (commit `3aca3f6`; no fixes). All imports resolve (`pasteRegion` correctly NOT imported); D4 guards correct; existing shortcuts cases byte-intact (regression `test_shortcuts` 5 passed); the e2e drives the real bridge `postMessage` protocol (no `window.*` hook, no synthetic keys). **Scope p3-checkpoint (conductor headed exercise of C6–C9):** (1) the build-phase e2e runs HEADLESS — the done-gate fidelity floor requires C6 (no-reflow) and C7 (reflow / grid-fallback) geometry RE-MEASURED in a HEADED visible browser via `getBoundingClientRect`; (2) synthetic Ctrl+C/V do NOT cross into the slide iframe, so a REAL `Ctrl+C`/`Ctrl+V`/`Ctrl+Shift+V` keystroke into the slide is provable ONLY headed (drive from the slide/iframe focus) — this is the owner-UAT-grade gesture the automated e2e structurally cannot reach (the e2e proves the shared `copy`/`pasteFloat`/`pasteLayout` engine via the bridge, not the key path); (3) the C7-grid e2e asserts "any absolute element exists" broadly (passes on the controlled fixture) — at the checkpoint confirm the PASTED node specifically is the absolute/float one. Scope: p3-checkpoint exercise + owner UAT.

### Discovery (p3-3 review, 2026-06-09): paste.js public surface = 2 exports; bindings for p3-4 wiring + p3-checkpoint
Opus review of p3-3 (`paste.js`) → DONE_WITH_NOTES with one fix: `pasteRegion` un-exported (commit `6c7a129`) so the module's public surface is exactly `pasteFloat`/`pasteIntoLayout` (a `wasRegion` clipboard reaches the whole-slide path via internal delegation inside both). All 7 cross-module imports confirmed against real exports; `history.push` confirmed synchronous (FLIP snapshot/play timing correct). **Scope p3-4 (wiring):** import ONLY `pasteFloat`/`pasteIntoLayout` from `paste.js` (NOT `pasteRegion`); wire `Ctrl+V`→`pasteFloat(x,y)`, `Ctrl+Shift+V`→`pasteIntoLayout(x,y)` passing LIVE cursor client-coords (paste resolves the target slide via `document.elementFromPoint(x,y)`; stale coords misplace the copy); `Ctrl+C` copies a component ONLY when one is selected and NOT editing (D4). **Scope p3-checkpoint (exercise watch-items):** (a) on a slide whose container has a visible border, float-paste lands shifted by the border width (left/top from border-box origin vs absolute's padding-edge origin) — benign on current borderless decks; (b) inserting after a sole child plays no FLIP (only displaced siblings animate — expected, not a bug).

### Discovery (W3 review, 2026-06-09): three bindings for p3-3 `paste.js` from the clipboard/paste-command seam
The Opus review of p3-1 (`clipboard.js`) + p3-2 (`commands.js` `paste` factory) confirmed both clean (committed `d66021c`) and surfaced three constraints that bind `p3-3`'s `paste.js`: (1) **Re-tag after insert** — the clipboard slot's clone is intentionally id-less (`copy()` strips EVERY `data-hyp-*`), so `paste.js` MUST call `tag()` on the inserted node AFTER insertion and BEFORE any `byId`-based `select()`/`mount()`; `byId` cannot resolve the clone until it carries a fresh `data-hyp-id`. (2) **`parentHypId` is "hyp-N"|null ONLY** — `commands.paste` resolves the parent with a truthy check (`parentHypId ? byId(parentHypId) : document.body`, mirroring `deleteElement`), so `paste.js` must pass a real `"hyp-N"` string or `null`/`undefined` for the body/region case — never `""` or `0` (would wrongly route to `document.body`). (3) **The `data-hyp-*` strip is load-bearing** — clipboard's completeness rests on its own `stripHypAttributes` sweep over clone root + all descendants, NOT on `stripIds` (a `TreeWalker` that skips the clone root and removes only `data-hyp-id`); must not be "simplified" to `stripIds`-only or paste would silently reattach comment anchors (D5 violation). Scope: `p3-3` `paste.js` construction.

---

## References

> **Path format:** External files (outside this plan folder) use project-root-relative paths. Internal files (within this plan folder) use file-relative paths (`./`, `../`).

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|------------------------|
| `./shortcuts-copypaste-design.md` | The approved design + the done-gate Contract (§11 = C1–C9). Architecture primer, reuse table, locked decisions, edge cases, phases. |
| `html/hypresent/runtime/js/text-format.js` | `apply(op)` no-ops outside an active edit; font-size survives the `innerHTML` round-trip via a `data-hyp-fontspan` marker; bold/italic have no such fallback (the repeat bug, §5.1). |
| `html/hypresent/runtime/js/commands.js` | `format`/`deleteElement` factories; `deleteElement` captures parent+next-sibling+node ref for undo — the pattern the paste/insert factory mirrors. |
| `html/hypresent/runtime/js/interaction.js` | `commitDrop` FLIP block (snapshot displaced siblings → reorder → play) to reuse for insert-paste; `lastPointer` tracking. |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `./specs/formatting-spec.md` | behavior + test plan for whole-box + repeat-fix | p1-1, p1-checkpoint |
| `./specs/shortcuts-spec.md` | behavior + test plan + the `"shortcut"` bridge-event contract | p2-1, p2-2, p2-checkpoint |
| `./specs/copypaste-spec.md` | behavior + test plan + clipboard-slot shape + paste-command signature | p3-1 … p3-checkpoint |
