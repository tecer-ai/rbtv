# DISPATCH — p3-2 (kimi executor) — builder-open-deck

You are a NON-REASONING code executor. Implement EXACTLY what the task below specifies. Do NOT design, do NOT "fill in the blanks", do NOT interpret intent. Every interface and edge case is pre-resolved in the task and its referenced specs. If anything is ambiguous or an anchor excerpt does not match the file on disk, HALT and return `DOUBT_ESCALATED` with the precise question — never guess.

## Binding obligations (you MUST obey)

- **Allowlist boundary:** touch ONLY these 4 files. Nothing else.
  - ✎ modify `app/js/builder/builder-main.js`
  - ✎ modify `app/js/builder/browse-pane.js`
  - ✎ modify `app/builder.html`
  - ✚ create `tests/e2e/test_pb10_deck_add.py`
- **`tray.js` is NOT in your allowlist — use the tray's PUBLIC API only.** p3-1 (already landed) reworked the tray to uid identity with three row kinds (`existing` · `library` · `blank`), library-kind-only dedup on `add()`, a blank-add path, and `getItems()`. You wire `builder-main.js` to populate the deck tray through that existing public surface (create `library` rows carrying `libraryPath` per row; append `blank` rows). Do NOT reach into tray internals or modify `tray.js`. If the tray's public API is genuinely insufficient for the task, HALT and return `DOUBT_ESCALATED` — do NOT work around it by editing off-allowlist files.
- **REGRESSION — the deck-thumbnail provider + tray identity MUST stay green.** Your changes drive tray re-renders (adding library/blank rows). The p2-2 per-row srcdoc provider (deck-themed thumbnails) and the p3-1 uid identity are guarded by `tests/e2e/test_pb8_deck_open.py` and `tests/e2e/test_pb9_deck_tray.py`. AFTER your frontmatter `test_command` passes, you MUST ALSO run `python -m pytest tests/e2e/test_pb8_deck_open.py tests/e2e/test_pb9_deck_tray.py -q` and include the result in your `validation` field. If EITHER regresses, HALT and return `DOUBT_ESCALATED` — do not commit a regression.
- **No stray files:** NEVER write scratch/notes/log files into the repo root or anywhere outside the allowlist. Test temp files go through pytest `tmp_path` only.
- **READ-ONLY owner data:** the root decks `tecer-gsmm-introduction*.html` are the owner's real files. Tests copy them to `tmp_path` — NEVER modify, move, or write to the originals.
- **Validation before done:** run the full `test_command` from your work-dir root: `node --check app/js/builder/builder-main.js && node --check app/js/builder/browse-pane.js && python -m pytest tests/e2e/test_pb10_deck_add.py -q`. All EXIT 0, no skips. THEN run the regression pair above. All green before you commit or claim DONE.
- **Commit:** local-only on `master`, subject MUST start with `[p3-2]`, stage ONLY the 4 allowlist files (NEVER `git add -A` — this repo has unrelated uncommitted files from other sessions). NEVER push/amend/force-reset.
- **Halt on doubt:** doubt_policy is halt. Do not improvise past ambiguity.
- **No subagents:** swarm_policy is disabled — do NOT launch any kimi subagent.

## Path mapping (the task body was authored in `docs/plan/builder-open-deck/phase-3/` — resolve its relative paths from your work-dir root as follows)

| Task-body path | Actual path from your work-dir root |
|----------------|--------------------------------------|
| `../specs/tray-compose-spec.md` | `docs/plan/builder-open-deck/specs/tray-compose-spec.md` |
| `../decisions.md` | `docs/plan/builder-open-deck/decisions.md` |
| `../deliverables.md` | `docs/plan/builder-open-deck/deliverables.md` (do not write — see ADX-1 in the task) |
| `app/...`, `tests/e2e/...` | work-dir-relative as written |

## Required return — these five named fields, exactly (no renames, no prose-only)

- `status`: one of DONE · DONE_WITH_NOTES · BLOCKED · DOUBT_ESCALATED · NEEDS_CONTEXT
- `landed`: files created/modified + the commit hash (must match `git log`)
- `validation`: each command run + its EXIT code + WALL_MS; `SKIPPED_COUNT` and a reason per skip (INCLUDE the pb8+pb9 regression run)
- `concerns`: risks/smells/adjacent issues you noticed but did not fix
- `open_questions`: the precise blocker/doubt if you halted (else "none")

The return message is a HINT; your work on disk is the truth and will be reconciled against `git status` / `git log`. Capture validation output as evidence.

Decisions reference (already applied in the task; do not re-derive): `docs/plan/builder-open-deck/decisions.md`.

---

# TASK PAYLOAD (verbatim — implement this)

---
task_id: p3-2
status: in-progress
phase: understand
complexity_score: 6
human_review: optional
execution_kind: code
executor: kimi
reviewer: claude-opus
workspace: 3-resources/tools/rbtv
work_dir: studio/hypresent
allowed_workdir: studio/hypresent
branch: master
allowlist:
  - app/js/builder/builder-main.js
  - app/js/builder/browse-pane.js
  - app/builder.html
  - tests/e2e/test_pb10_deck_add.py
commit_policy: local-only
test_command: node --check app/js/builder/builder-main.js && node --check app/js/builder/browse-pane.js && python -m pytest tests/e2e/test_pb10_deck_add.py -q
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - modifying root-level *.html decks
doubt_policy: halt
swarm_policy: disabled
max_kimi_subagents: 0
# Human-readable allowlist (✚ create · ✎ modify):
#   ✎ app/js/builder/builder-main.js
#   ✎ app/js/builder/browse-pane.js
#   ✎ app/builder.html
#   ✚ tests/e2e/test_pb10_deck_add.py
---

# Task p3-2: Add from library + add blank, in deck mode

## Goal

With a deck open, the existing library browse feeds the deck tray (`library` rows, toggle + badges working), and an "Add blank slide" button appends `blank` rows. Behavior source of truth: `../specs/tray-compose-spec.md` (rows 4-7 + Edge Cases: library-change, no-deck regression).

Serialization note: `app/js/builder/builder-main.js` order is `p2-1 → p3-1 → p3-2 → p3-3 → p4-1`. p3-1 has landed; build on the current file.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../specs/tray-compose-spec.md` | Library-row dedup/toggle semantics, blank-add gesture, library-change edge case |
| `app/js/builder/builder-main.js` | `handlePickLibrary`, `onTag` toggle, slide-stage `onAdd`, `markTrayState` — the wiring you extend to deck mode |
| `app/js/builder/browse-pane.js` | Card render + badge mechanics (`markTrayState`) |
| `app/builder.html` | Where the "Add blank slide" control mounts (near the tray) |
| `tests/e2e/test_pb2_library_load.py`, `tests/e2e/builder_helpers.py` | Fixture-library loading idiom for e2e (`tests/e2e/fixtures/builder-lib/`) |

## Execution Flow

### Phase: Understand
1. Read every Context File. Mark this task in progress in the plan file, this frontmatter, and `../deliverables.md` (same turn).

### Phase: Execute
1. UPDATE `builder-main.js` — in deck mode, browse-card `onTag` and stage `onAdd` create `library` rows (storing `libraryPath` per row so a later library change keeps them valid); badges reflect deck-tray membership.
2. UPDATE `app/builder.html` + `builder-main.js` — "Add blank slide" button appending a `blank` row (the approved sibling feature).
3. UPDATE `browse-pane.js` only if badge mechanics need the kind-aware order (prefer no change).
4. CREATE `tests/e2e/test_pb10_deck_add.py` — spec Test Plan rows 1 (mixed add) and 3 (toggle in deck mode) using the fixture library + a real deck copy.

### Phase: Validate
1. Run the frontmatter `test_command` — expected EXIT 0.

### Phase: Close
Standard orchestrated close: flip plan checkbox, frontmatter status, `../deliverables.md` row.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Deck-mode library add + blank add | `app/js/builder/builder-main.js`, `browse-pane.js`, `app/builder.html` | edits |
| e2e | `tests/e2e/test_pb10_deck_add.py` | Playwright pytest |

## Return Contract

Return `status` · `landed` · `validation` (commands + EXIT + WALL_MS + skips with reasons) · `concerns` · `open_questions`.

## Revolving Plan Rules

Simple discovery (<5 min): resolve, document in `../decisions.md`. Complex: add a task, notify. State `PLAN MODIFIED:` lines in your return when tasks change.

---

> **ADX-1 (run erratum, 2026-06-09):** The status-flip bookkeeping steps in this task (marking the task in progress / done in the plan file, this file's frontmatter, and `../deliverables.md`) are performed by the ORCHESTRATOR at verified return — NOT by the executor. Executor: skip those steps; write ONLY within your allowlist. All other instructions unchanged.
