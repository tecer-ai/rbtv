---
task_id: p2-checkpoint
status: pending
phase: validate
complexity_score: 5
human_review: required
orchestrator_executed: true
---

# Checkpoint p2-checkpoint: Shortcuts + cheat-sheet Review

## Goal

Evaluate Phase 2 against its review criteria, exercise C3/C4/C5 at the fidelity floor (headed), and present findings for human approval. Conductor-level — not delegated to a CLI executor.

---

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Constraints, the compat regression set |
| `../specs/shortcuts-spec.md` | C3, C4, C5 + the fidelity floor |
| `runtime/js/shortcuts.js`, `runtime/js/runtime-main.js`, `app/js/shell/shortcuts-help.js`, `app/index.html`, `app/css/shell.css`, `app/js/main.js` | Phase 2 deliverables |

## Work to Evaluate

`p2-1` created the in-iframe key router (`shortcuts.js`) and wired it in `runtime-main.js`; `p2-2` added the "?" button, the cheat-sheet overlay (`shortcuts-help.js` + `shell.css`), and the shell keydown listener + `bridge.on("shortcut")` in `main.js`.

## Review Criteria

1. **C3 — Comment shortcut.** With a component selected, `Ctrl+Alt+C` (focus in iframe AND focus in shell) opens the comment composer for it; Chrome's Inspect-Element does NOT open.
2. **C4 — Delete shortcut.** `Ctrl+Del` deletes a selected component; blocked while editing and on the last region; plain `Delete`/`Backspace` do nothing (`test_r3_delete::test_no_keyboard_delete` green).
3. **C5 — Cheat-sheet.** Clicking "?" or pressing `Ctrl+/` opens an overlay listing all shortcuts grouped Text/Components/Editing; `Esc` and outside-click close it.
4. **Focus split** — keys work whether focus is in the iframe (runtime listener) or shell chrome (shell listener); no double-firing; `Ctrl+B`/`Ctrl+I` apply whole-box formatting from p1-1.
5. **No regressions** — existing toolbar buttons (format, align, comment, delete, undo/redo) still work unchanged.
6. **decisions.md audit** — entry-shape discipline upheld.

## Execution Flow

### Phase: Evaluate
1. Read the Context Files and the executor/cold-verifier returns for `p2-1`, `p2-2`.
2. Launch the app headed, open the real deck, and exercise C3/C4/C5 with real mouse/keyboard from BOTH focus contexts (iframe and shell), capturing screenshots.
3. Append the C3, C4, C5 rows to the evidence sheet `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste.md`; captures in the sibling folder.
4. Prepare a per-criterion PASS/FAIL summary.

### Phase: Gate
1. Present findings with PASS/FAIL per criterion + the evidence-sheet path.
2. **MUST** append the Human Review Presentation block; flag any `held-surprising`/`failed` row, else "None identified" + a one-line rationale.
3. **HALT for human approval** — do not advance to Phase 3.
4. If rejected: document in `../decisions.md`, do not advance. If approved: mark `[x]` and flip the row to ✅ in `../deliverables.md`.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
