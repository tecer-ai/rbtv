---
task_id: p1-checkpoint
status: pending
phase: validate
complexity_score: 5
human_review: required
orchestrator_executed: true
---

# Checkpoint p1-checkpoint: Formatting Review

## Goal

Evaluate Phase 1 (whole-box formatting + repeat-fix) against its review criteria, exercise C1/C2 at the done-gate fidelity floor, and present findings for human approval. This checkpoint runs at the conductor level (headed browser) — it is NOT delegated to a CLI executor.

---

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Prior decisions, constraints, the compat regression set |
| `../specs/formatting-spec.md` | C1, C2 + the fidelity floor for this phase |
| `runtime/js/text-format.js`, `runtime/js/runtime-main.js` | The Phase 1 deliverables to evaluate |

## Work to Evaluate

`p1-1` modified `runtime/js/text-format.js` (repeat-fix + whole-box + `scaleWholeBox`) and `runtime/js/runtime-main.js` (the `format` handler passes `current()`), and created `tests/e2e/test_format_repeat_wholebox.py`.

## Review Criteria

1. **C1 whole-box bold/italic** — selecting a text box (not editing) and pressing the Bold/Italic button toggles ALL its text and repeats without re-selecting; the `hyp-` ring stays; no edit session is entered (no `edit-state {editing:true}` emitted).
2. **C1 proportional A+/A−** — on a box with two differently-sized words, A+ multiplies both computed `font-size`s by the same factor (measured ratio unchanged).
3. **C2 editing-path repeat** — while editing, a selected word bolds then un-bolds on a second press with the selection preserved.
4. **Undo correctness** — a single Undo after whole-box A+ fully restores the box's own `font-size` AND descendant sizes (the inline command, not a `format`-only command).
5. **Compatibility** — `test_r8_font_size_repeat.py` passes; whole-box bold/italic never routes through `text-edit.enterEdit`; no `selection.js` import was added to `text-format.js` (no module cycle).
6. **decisions.md audit** — any new entry follows entry-shape discipline (decision + rationale + scope ONLY; never file-lists or N→M narratives; supersede by appending, never rewrite).

## Execution Flow

### Phase: Evaluate
1. Read the Context Files and the cold-verifier / executor returns for `p1-1`.
2. Launch the real app headed (`python server/server.py 127.0.0.1 8799`), open the real deck `tecer-gsmm-introduction.html`, and exercise C1 and C2 with real mouse/keyboard, capturing screenshots + measured `font-size` values.
3. Create the evidence sheet `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste.md` if absent (seed it with the C1–C9 contract from `../specs/`), and fill the C1, C2 rows (gesture / observed / evidence file / verdict). Captures go in the sibling `2026-06-08-shortcuts-copypaste/` folder.
4. Prepare a per-criterion PASS/FAIL summary.

### Phase: Gate
1. Present the findings with clear PASS/FAIL per criterion and the evidence-sheet path.
2. **MUST** append the Human Review Presentation block (checkpoints inherit `human_review: required`). Flag any `held-surprising`/`failed` row; if none, write "None identified" with a one-line rationale naming the checks that ran clean.
3. **HALT for human approval** — do not advance to Phase 2 regardless of findings.
4. If rejected: document feedback in `../decisions.md`, do not advance. If approved: mark `p1-checkpoint` `[x]` and flip its row to ✅ in `../deliverables.md`.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
