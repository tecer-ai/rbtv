# DISPATCH — p3-1 (kimi executor) — builder-open-deck

You are a NON-REASONING code executor. Implement EXACTLY what the task below specifies. Do NOT design, do NOT "fill in the blanks", do NOT interpret intent. Every interface and edge case is pre-resolved in the task and its referenced specs. If anything is ambiguous or an anchor excerpt does not match the file on disk, HALT and return `DOUBT_ESCALATED` with the precise question — never guess.

## Binding obligations (you MUST obey)

- **Allowlist boundary:** touch ONLY these 4 files. Nothing else.
  - ✎ modify `app/js/builder/tray.js`
  - ✎ modify `app/js/builder/tray-sorter.js`
  - ✎ modify `app/js/builder/builder-main.js`
  - ✚ create `tests/e2e/test_pb9_deck_tray.py`
- **PRESERVE THE p2-2 TRAY INVARIANT (load-bearing — do NOT break it):** `tray.js` already exposes `setSrcdocProvider(fn)` where `fn(rec, index) => Promise<string>`. In `render()`, this per-row srcdoc provider takes PRECEDENCE over `libraryPath`; and `setLibrary()` CLEARS the provider. Your row-manipulation changes (uid identity, three row kinds, duplicate, `getItems()`) MUST preserve BOTH: (a) the provider-precedes-`libraryPath` ordering in `render()`, and (b) `setLibrary()` clearing the provider. Reorder/remove already re-invoke the provider correctly (guarded by the PB8-2b e2e test `test_thumbnails_survive_rerender` in `tests/e2e/test_pb8_deck_open.py`) — keep that working. Breaking this silently wipes the deck-themed slide thumbnails. If your change cannot preserve it, HALT and escalate — do not work around it.
- **No stray files:** NEVER write scratch/notes/log files into the repo root or anywhere outside the allowlist. Test temp files go through pytest `tmp_path` only.
- **READ-ONLY owner data:** the root decks `tecer-gsmm-introduction*.html` are the owner's real files. Tests copy them to `tmp_path` — NEVER modify, move, or write to the originals.
- **Validation before done:** run the full `test_command` from your work-dir root: `node --check app/js/builder/tray.js && node --check app/js/builder/tray-sorter.js && node --check app/js/builder/builder-main.js && python -m pytest tests/e2e/test_pb9_deck_tray.py tests/e2e/test_pb4_tray_reorder.py -q`. ALL EXIT 0, no skips, before you commit or claim DONE. `test_pb4_tray_reorder.py` is the assemble-mode regression guard — it MUST stay green (proves `getOrder()` still returns library slide ids for `markTrayState`).
- **Commit:** local-only on `master`, subject MUST start with `[p3-1]`, stage ONLY the 4 allowlist files (NEVER `git add -A` — this repo has unrelated uncommitted files from other sessions). NEVER push/amend/force-reset.
- **Halt on doubt:** doubt_policy is halt. Do not improvise past ambiguity.
- **No subagents:** swarm_policy is disabled — do NOT launch any kimi subagent.

## Path mapping (the task body was authored in `docs/plan/builder-open-deck/phase-3/` — resolve its relative paths from your work-dir root as follows)

| Task-body path | Actual path from your work-dir root |
|----------------|--------------------------------------|
| `../specs/tray-compose-spec.md` | `docs/plan/builder-open-deck/specs/tray-compose-spec.md` |
| `../specs/deck-save-spec.md` | `docs/plan/builder-open-deck/specs/deck-save-spec.md` |
| `../decisions.md` | `docs/plan/builder-open-deck/decisions.md` |
| `../deliverables.md` | `docs/plan/builder-open-deck/deliverables.md` (do not write — see ADX-1 in the task) |
| `app/...`, `tests/e2e/...` | work-dir-relative as written |

## Required return — these five named fields, exactly (no renames, no prose-only)

- `status`: one of DONE · DONE_WITH_NOTES · BLOCKED · DOUBT_ESCALATED · NEEDS_CONTEXT
- `landed`: files created/modified + the commit hash (must match `git log`)
- `validation`: each command run + its EXIT code + WALL_MS; `SKIPPED_COUNT` and a reason per skip
- `concerns`: risks/smells/adjacent issues you noticed but did not fix
- `open_questions`: the precise blocker/doubt if you halted (else "none")

The return message is a HINT; your work on disk is the truth and will be reconciled against `git status` / `git log`. Capture validation output as evidence.

Decisions reference (already applied in the task; do not re-derive): `docs/plan/builder-open-deck/decisions.md`.

---

# TASK PAYLOAD (verbatim — implement this)

---
task_id: p3-1
status: pending
phase: understand
complexity_score: 8
human_review: optional
execution_kind: code
executor: kimi
reviewer: claude-opus
workspace: 3-resources/tools/rbtv
work_dir: html/hypresent
allowed_workdir: html/hypresent
branch: master
allowlist:
  - app/js/builder/tray.js
  - app/js/builder/tray-sorter.js
  - app/js/builder/builder-main.js
  - tests/e2e/test_pb9_deck_tray.py
commit_policy: local-only
test_command: node --check app/js/builder/tray.js && node --check app/js/builder/tray-sorter.js && node --check app/js/builder/builder-main.js && python -m pytest tests/e2e/test_pb9_deck_tray.py tests/e2e/test_pb4_tray_reorder.py -q
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - modifying root-level *.html decks
doubt_policy: halt
swarm_policy: disabled
max_kimi_subagents: 0
# Human-readable allowlist (✚ create · ✎ modify):
#   ✎ app/js/builder/tray.js
#   ✎ app/js/builder/tray-sorter.js
#   ✎ app/js/builder/builder-main.js
#   ✚ tests/e2e/test_pb9_deck_tray.py
---

# Task p3-1: Heterogeneous tray — uid identity, three row kinds, duplicate

## Goal

Rework tray row identity to unique `uid`s carrying three row kinds (`existing` · `library` · `blank`) with reorder/remove/duplicate across kinds and a `getItems()` mapping to the deck-save items contract. Behavior source of truth: `../specs/tray-compose-spec.md` (rows 1-4, 8 + Edge Cases; row kinds table).

Serialization notes: `app/js/builder/tray.js` order is `p2-2 → p3-1` (p2-2 landed; build on current). `app/js/builder/builder-main.js` order is `p2-1 → p3-1 → p3-2 → p3-3 → p4-1`.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../specs/tray-compose-spec.md` | Row-kind model, uid identity, duplicate semantics, dedup rules, `getItems()` contract |
| `../specs/deck-save-spec.md` § Context Snapshot | The items contract `getItems()` must emit |
| `app/js/builder/tray.js` | The model you rework — the dedup line `if (model.some(m => m.id === rec.id)) return;` becomes library-kind-only; `dataset.slideId` keying moves to uid |
| `app/js/builder/tray-sorter.js` | Sorter round-trips row identity through the DOM — must use uid |
| `app/js/builder/builder-main.js` | `onChange` wiring, `markTrayState(order)` (receives library slide ids only after this change) |
| `tests/e2e/test_pb4_tray_reorder.py` | Regression suite that MUST stay green (assemble mode untouched) |

## Execution Flow

### Phase: Understand
1. Read every Context File. Mark this task in progress in the plan file, this frontmatter, and `../deliverables.md` (same turn).

### Phase: Execute
1. UPDATE `tray.js` — uid identity; kind-aware add/remove/duplicate; per-kind dedup per spec; kind badge on rows; duplicate control (mirror the remove-button idiom); `getItems()`; `getOrder()` keeps returning library slide ids for `markTrayState` compatibility in assemble mode.
2. UPDATE `tray-sorter.js` — reorder round-trip keyed by uid.
3. UPDATE `builder-main.js` — wire duplicate/badges; deck-mode `onChange` drives the save-enabled state (button itself lands in p3-3).
4. CREATE `tests/e2e/test_pb9_deck_tray.py` — spec Test Plan rows 1 (reorder via real mouse drag), 2 (duplicate), plus duplicate-then-remove-original edge case.

### Phase: Validate
1. Run the frontmatter `test_command` — expected EXIT 0 (includes the assemble-mode regression suite).

### Phase: Close
Standard orchestrated close: flip plan checkbox, frontmatter status, `../deliverables.md` row.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Heterogeneous tray | `app/js/builder/tray.js`, `tray-sorter.js`, `builder-main.js` | edits |
| e2e | `tests/e2e/test_pb9_deck_tray.py` | Playwright pytest |

## Return Contract

Return `status` · `landed` · `validation` (commands + EXIT + WALL_MS + skips with reasons) · `concerns` · `open_questions`.

## Revolving Plan Rules

Simple discovery (<5 min): resolve, document in `../decisions.md`. Complex: add a task, notify. State `PLAN MODIFIED:` lines in your return when tasks change.

---

> **ADX-1 (run erratum, 2026-06-09):** The status-flip bookkeeping steps in this task (marking the task in progress / done in the plan file, this file's frontmatter, and `../deliverables.md`) are performed by the ORCHESTRATOR at verified return — NOT by the executor. Executor: skip those steps; write ONLY within your allowlist. All other instructions unchanged.
