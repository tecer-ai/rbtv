---
task_id: p3-checkpoint
status: pending
phase: validate
complexity_score: 6
human_review: required
orchestrator_executed: true
---

# Checkpoint p3-checkpoint: Copy / paste Review

## Goal

Evaluate Phase 3 against its review criteria, exercise C6/C7/C8/C9 at the fidelity floor (headed, with measured geometry), and present findings for human approval. Conductor-level — not delegated to a CLI executor.

---

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Constraints, the serializer guard, D1–D11 |
| `../specs/copypaste-spec.md` | C6–C9 + the fidelity floor (measured `getBoundingClientRect`) |
| `runtime/js/clipboard.js`, `runtime/js/commands.js`, `runtime/js/paste.js`, `runtime/js/shortcuts.js`, `runtime/js/runtime-main.js`, `docs/spec/03-module-map.md` | Phase 3 deliverables |

## Work to Evaluate

`p3-1` clipboard slot; `p3-2` paste command factory; `p3-3` `paste.js` (float + insert + grid fallback + whole-slide); `p3-4` keys + pointer + bridge commands + module map.

## Review Criteria

1. **C6 — Float paste, no reflow.** `Ctrl+C` then `Ctrl+V` over a slide drops a copy under the cursor; the OTHER components' measured `getBoundingClientRect` are unchanged before vs after.
2. **C7 — Insert paste + grid fallback.** In a flex row (`flow-grow.html`), `Ctrl+Shift+V` inserts a copy and siblings' measured positions change; on a grid (`grid-healthy.html`), `Ctrl+Shift+V` yields a floating (`position:absolute`) copy, not a broken grid.
3. **C8 — Whole-slide duplicate.** Copying a whole slide and pasting inserts a new slide (region), not a floating overlay.
4. **C9 — Undo + clean.** One Undo removes a pasted copy (Redo re-adds); pasted copies carry no comment threads; `serialize` after a paste succeeds (node-count guard passes) and the saved file re-opens.
5. **Guards (D4).** `Ctrl+C`/`Ctrl+V` while editing or with a real text selection do NOT hijack native copy/paste.
6. **Truthful module map** + **decisions.md audit** (entry-shape discipline).

## Execution Flow

### Phase: Evaluate
1. Read the Context Files and the executor/cold-verifier returns for `p3-1…p3-4`.
2. Launch the app headed; exercise C6/C7 on `flow-grow.html`/`grid-healthy.html` and C8/C9 on the real deck, with real mouse/keyboard, capturing screenshots AND measured `getBoundingClientRect` JSON before/after, plus the saved HTML for C9.
3. Append the C6, C7, C8, C9 rows to the evidence sheet `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste.md`; captures in the sibling folder.
4. Prepare a per-criterion PASS/FAIL summary.

### Phase: Gate
1. Present findings with PASS/FAIL per criterion + the evidence-sheet path.
2. **MUST** append the Human Review Presentation block; flag any `held-surprising`/`failed` row (e.g. a measured reflow where none was expected), else "None identified" + a one-line rationale.
3. **HALT for human approval** — do not advance to the final phase.
4. If rejected: document in `../decisions.md`, do not advance. If approved: mark `[x]` and flip the row to ✅ in `../deliverables.md`.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
