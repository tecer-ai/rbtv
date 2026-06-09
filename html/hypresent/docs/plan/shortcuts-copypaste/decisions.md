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
