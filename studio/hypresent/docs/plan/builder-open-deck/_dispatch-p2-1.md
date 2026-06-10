# DISPATCH — p2-1 (kimi executor) — builder-open-deck

You are a NON-REASONING code executor. Implement EXACTLY what the task below specifies. Do NOT design, do NOT "fill in the blanks", do NOT interpret intent. Every interface and edge case is pre-resolved in the task and its referenced specs. If anything is ambiguous or an anchor excerpt does not match the file on disk, HALT and return `DOUBT_ESCALATED` with the precise question — never guess.

## Binding obligations (you MUST obey)

- **Allowlist boundary:** touch ONLY these 4 files. Nothing else.
  - ✚ create `app/js/builder/deck-load.js`
  - ✎ modify `app/js/builder/builder-main.js`
  - ✎ modify `app/builder.html`
  - ✚ create `tests/e2e/test_pb8_deck_open.py`
- **No stray files:** NEVER write scratch/notes/log files into the repo root or anywhere outside the allowlist. Test temp files go through pytest `tmp_path` only.
- **READ-ONLY owner data:** the root decks `tecer-gsmm-introduction*.html` are the owner's real files. Tests copy them to `tmp_path` — NEVER modify, move, or write to the originals.
- **Validation before done:** run the full `test_command` from your work-dir root: `node --check app/js/builder/deck-load.js && node --check app/js/builder/builder-main.js && python -m pytest tests/e2e/test_pb8_deck_open.py -q`. All EXIT 0, no skips, before you commit or claim DONE.
- **Commit:** local-only on `master`, subject MUST start with `[p2-1]`, stage ONLY the 4 allowlist files (NEVER `git add -A` — this repo has unrelated uncommitted files). NEVER push/amend/force-reset.
- **Halt on doubt:** doubt_policy is halt. Do not improvise past ambiguity.
- **No subagents:** swarm_policy is disabled — do NOT launch any kimi subagent.

## Path mapping (the task body was authored in `docs/plan/builder-open-deck/phase-2/` — resolve its relative paths from your work-dir root as follows)

| Task-body path | Actual path from your work-dir root |
|----------------|--------------------------------------|
| `../specs/deck-ingest-spec.md` | `docs/plan/builder-open-deck/specs/deck-ingest-spec.md` |
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
task_id: p2-1
status: pending
phase: understand
complexity_score: 7
human_review: optional
execution_kind: code
executor: kimi
reviewer: claude-opus
workspace: 3-resources/tools/rbtv
work_dir: html/hypresent
allowed_workdir: html/hypresent
branch: master
allowlist:
  - app/js/builder/deck-load.js
  - app/js/builder/builder-main.js
  - app/builder.html
  - tests/e2e/test_pb8_deck_open.py
commit_policy: local-only
test_command: node --check app/js/builder/deck-load.js && node --check app/js/builder/builder-main.js && python -m pytest tests/e2e/test_pb8_deck_open.py -q
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - modifying root-level *.html decks
doubt_policy: halt
swarm_policy: disabled
max_kimi_subagents: 0
# Human-readable allowlist (✚ create · ✎ modify):
#   ✚ app/js/builder/deck-load.js
#   ✎ app/js/builder/builder-main.js
#   ✎ app/builder.html
#   ✚ tests/e2e/test_pb8_deck_open.py
---

# Task p2-1: "Open deck…" — deck mode entry + deck model

## Goal

Add deck-open to the builder: an "Open deck…" topbar control and `?file=` arrival, both loading the deck via `/api/deck-load` into `state.deck = {path, name, dir, head, sections}` and filling the tray with `existing` rows. Behavior source of truth: `../specs/deck-ingest-spec.md` (gestures 1, 2, 4-7).

Serialization note: `app/js/builder/builder-main.js` is shared — its order is `p2-1 → p3-1 → p3-2 → p3-3 → p4-1`. You are first; build on the current file.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../specs/deck-ingest-spec.md` | The behavior contract, builder-mode model, endpoint shapes |
| `app/js/builder/builder-main.js` | Entry point you extend: `state`, `handlePickLibrary` idiom, `setStatus`, tray creation |
| `app/js/builder/tray.js` | Current tray API — add deck rows through its public surface (thumbnails refined in p2-2) |
| `app/js/api-client.js` | Fetch idiom for `/api/*` endpoints |
| `app/builder.html` | Topbar markup where the "Open deck…" control mounts |
| `tests/e2e/test_pb2_library_load.py`, `tests/e2e/builder_helpers.py` | e2e idiom: server fixture, dialog-launcher injection, headed Playwright |

## Execution Flow

### Phase: Understand
1. Read every Context File. Mark this task in progress in the plan file, this frontmatter, and `../deliverables.md` (same turn).

### Phase: Execute
1. CREATE `app/js/builder/deck-load.js` — `pickAndLoadDeck()` (calls `/api/dialog-open-path`, then `/api/deck-load`) and `loadDeck(path)` (deck-load only), mirroring the `library-load.js` module shape.
2. UPDATE `app/builder.html` — "Open deck…" topbar button + a deck-name chip (mirror the lib-chip pattern).
3. UPDATE `app/js/builder/builder-main.js` — wire the button and the `?file=` boot branch (copy the editor's percent-decoding caution: `URLSearchParams.get()` already decodes). On load: set `state.deck`, fill the tray with one row per section in order, show errors via `setStatus(msg, 'error')`. Unsaved-tray replace guard per spec gesture 7.
4. CREATE `tests/e2e/test_pb8_deck_open.py` — spec Test Plan rows 1, 3, 4 (full tray, non-conforming rejection, `?file=` arrival) on a temp copy of `tecer-gsmm-introduction-test-v3.html`.

### Phase: Validate
1. Run the frontmatter `test_command` — expected EXIT 0.

### Phase: Close
Standard orchestrated close: flip plan checkbox, frontmatter status, `../deliverables.md` row.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Deck-open module | `app/js/builder/deck-load.js` | ES module |
| Wiring + UI | `app/js/builder/builder-main.js`, `app/builder.html` | edits |
| e2e | `tests/e2e/test_pb8_deck_open.py` | Playwright pytest |

## Return Contract

Return `status` · `landed` · `validation` (commands + EXIT + WALL_MS + skips with reasons) · `concerns` · `open_questions`.

## Revolving Plan Rules

Simple discovery (<5 min): resolve, document in `../decisions.md`. Complex: add a task, notify. State `PLAN MODIFIED:` lines in your return when tasks change.

---

> **ADX-1 (run erratum, 2026-06-09):** The status-flip bookkeeping steps in this task (marking the task in progress / done in the plan file, this file's frontmatter, and `../deliverables.md`) are performed by the ORCHESTRATOR at verified return — NOT by the executor. Executor: skip those steps; write ONLY within your allowlist. All other instructions unchanged.
