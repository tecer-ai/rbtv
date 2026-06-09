# Deliverables Map - shortcuts-copypaste

> **Single index of every artifact this plan produces.**
>
> **Every agent working on this plan MUST:**
> 1. Read this file BEFORE starting any task — it tells you the exact path your output must land at.
> 2. UPDATE this file AFTER delivering — flip the Status to ✅ and confirm the Path matches what you produced.
>
> The synthesis tasks (`p4-1`, `p4-compound`) read this map to find every input they need. If an artifact lands somewhere this map doesn't list, the synthesis agent will miss it. The index being accurate is a hard dependency, not a courtesy.

---

## Phase 1 deliverables — Formatting

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p1-1 | Whole-box formatting + bold/italic repeat-fix + `scaleWholeBox` (+ e2e) | `runtime/js/text-format.js`, `runtime/js/runtime-main.js`, `tests/e2e/test_format_repeat_wholebox.py` | ✅ (commit 0c70ed4) |
| p1-checkpoint | Phase 1 evaluation + C1/C2 evidence rows + approval | `./decisions.md` (Decision entry) + the done-gate sheet | ✅ (approved 2026-06-09) |

## Phase 2 deliverables — Shortcuts + cheat-sheet

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p2-1 | In-iframe keyboard router + runtime wiring (+ e2e) | `runtime/js/shortcuts.js`, `runtime/js/runtime-main.js`, `tests/e2e/test_shortcuts.py` | ✅ (wave `e7e482a`; review `87144a5`) |
| p2-2 | "?" button + cheat-sheet overlay + shell listener (+ e2e) | `app/js/shell/shortcuts-help.js`, `app/index.html`, `app/css/shell.css`, `app/js/main.js`, `tests/e2e/test_cheatsheet.py` | ✅ (wave `e7e482a`) |
| p2-fix | Cheat-sheet focuses on open so Esc closes regardless of focus (+ e2e) | `app/js/shell/shortcuts-help.js`, `tests/e2e/test_cheatsheet.py` | ✅ (`a3e217d`; review `p2-fix-review` clean) |
| p2-checkpoint | Phase 2 evaluation + C3/C4/C5 evidence rows + approval | `./decisions.md` (Decision entry) + the done-gate sheet | ✅ (approved B 2026-06-09) |

## Phase 3 deliverables — Copy / paste

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p3-1 | In-memory clipboard slot | `runtime/js/clipboard.js` | pending |
| p3-2 | Paste / insert command factory | `runtime/js/commands.js` | pending |
| p3-3 | Float-paste + insert-paste + grid fallback + whole-slide | `runtime/js/paste.js` | pending |
| p3-4 | Copy/paste keys + pointer + bridge commands + module map (+ e2e) | `runtime/js/shortcuts.js`, `runtime/js/runtime-main.js`, `docs/spec/03-module-map.md`, `tests/e2e/test_copy_paste.py` | pending |
| p3-checkpoint | Phase 3 evaluation + C6/C7/C8/C9 evidence rows + approval | `./decisions.md` (Decision entry) + the done-gate sheet | pending |

## Final phase deliverables — Verify & close

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p4-1 | Independent cold-verifier sheet + consolidated C1–C9 + compat result | `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste.md` | pending |
| p4-refs | Plan-artifact link audit result | `./decisions.md` (Discovery entry only if fixes were needed) | pending |
| p4-compound | Compound learnings → system improvements (or "none") | `.user/compounds/{component}/cp-…` if any; else `./learnings.md` (marked) | pending |
| p4-checkpoint | Final owner approval to complete the plan | `./decisions.md` (Decision entry) | pending |

**Status values:** `pending` | `in-progress` | `✅` | `⏸ deferred` — deferrals carry a parenthetical reason in the cell.

---

## How the synthesis tasks consume this index

A fresh agent at `p4-1` / `p4-compound` reads, in order:

1. **This file (`deliverables.md`)** — the artifact index.
2. `./decisions.md` end-to-end — every Decision and Discovery; the running rationale (D1–D11, the pre-resolutions, the compat set).
3. The three `./specs/*-spec.md` — the C1–C9 contract `p4-1` re-exercises.
4. `./learnings.md` — meta-observations `p4-compound` folds into system changes.

`p4-1` folds the per-phase checkpoint rows + an independent cold-verifier pass into ONE C1–C9 evidence sheet; `p4-compound` folds `learnings.md` into compound system changes.

---

## Sub-folder creation

The plan uses `specs/`, `phase-1/`, `phase-2/`, `phase-3/`, `phase-final/` (all created at plan creation). Done-gate captures land OUTSIDE the plan folder at `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste/` — created on demand by the first checkpoint that captures evidence.
