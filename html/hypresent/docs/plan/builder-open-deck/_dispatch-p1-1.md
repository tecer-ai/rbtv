# DISPATCH — p1-1 (kimi executor) — builder-open-deck

You are a NON-REASONING code executor. Implement EXACTLY what the task below specifies. Do NOT design, do NOT "fill in the blanks", do NOT interpret intent. Every interface and edge case is pre-resolved in the task and its referenced spec. If anything is ambiguous or an anchor excerpt does not match the file on disk, HALT and return `DOUBT_ESCALATED` with the precise question — never guess.

## Binding obligations (you MUST obey)

- **Allowlist boundary:** Create ONLY these 2 files. Nothing else.
  - ✚ create `server/recompose.py`
  - ✚ create `tests/test_recompose.py`
- **No stray files:** NEVER write scratch/notes/log files into the repo root or anywhere outside the allowlist. Test temp files go through pytest `tmp_path` only.
- **READ-ONLY owner data:** the root decks `tecer-gsmm-introduction*.html` are the owner's real files. Tests `shutil.copy` them to `tmp_path` — NEVER modify, move, or write to the originals.
- **Validation before done:** Run `python -m pytest tests/test_recompose.py -q` and capture output. All checks EXIT 0, no skips, before you commit or claim DONE.
- **Commit:** local-only on `master`, subject MUST start with `[p1-1]`, stage ONLY the 2 allowlist files (NEVER `git add -A` — this repo has unrelated uncommitted files). NEVER push/amend/force-reset.
- **Halt on doubt:** doubt_policy is halt. Do not improvise past ambiguity.
- **No subagents:** swarm_policy is disabled — do NOT launch any kimi subagent.

## Path mapping (the task body was authored in `docs/plan/builder-open-deck/phase-1/` — resolve its relative paths from your work-dir root as follows)

| Task-body path | Actual path from your work-dir root |
|----------------|--------------------------------------|
| `../specs/deck-save-spec.md` | `docs/plan/builder-open-deck/specs/deck-save-spec.md` |
| `../decisions.md` | `docs/plan/builder-open-deck/decisions.md` |
| `../deliverables.md` | `docs/plan/builder-open-deck/deliverables.md` (do not write — see ADX-1 in the task) |
| `server/api.py` | `server/api.py` (as written) |
| `tecer-gsmm-introduction-test-v3.html` | `tecer-gsmm-introduction-test-v3.html` (work-dir root, READ-ONLY) |

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
task_id: p1-1
status: pending
phase: understand
complexity_score: 8
human_review: required
execution_kind: code
executor: kimi
reviewer: claude-opus
workspace: 3-resources/tools/rbtv
work_dir: html/hypresent
allowed_workdir: html/hypresent
branch: master
allowlist:
  - server/recompose.py
  - tests/test_recompose.py
commit_policy: local-only
test_command: python -m pytest tests/test_recompose.py -q
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - modifying root-level *.html decks
doubt_policy: halt
swarm_policy: disabled
max_kimi_subagents: 0
# Human-readable allowlist (✚ create):
#   ✚ server/recompose.py
#   ✚ tests/test_recompose.py
---

# Task p1-1: Recompose engine — byte-range section splicing

## Goal

CREATE `server/recompose.py` containing the pure recompose engine — `split_sections(html)` and `recompose(html, items)` per `../specs/deck-save-spec.md` Context Snapshot — plus CREATE `tests/test_recompose.py` unit-testing it against a copy of a real deck.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../specs/deck-save-spec.md` | Behavior source of truth: function contracts, item kinds, edge cases (comments, nesting, zero sections) |
| `../decisions.md` | Architectural constraint: byte-range splicing ONLY — never parse-and-re-serialize the document |
| `server/api.py` | House style for stdlib-only pure handler modules |
| `tecer-gsmm-introduction-test-v3.html` | A real deck — READ-ONLY; tests copy it to a temp path |

## Execution Flow

### Phase: Understand
1. Read every Context File. Mark this task in progress in the plan file, this frontmatter, and `../deliverables.md` (same turn).
2. Confirm the real deck's top-level `<section>` count by inspection — your tests assert against this ground truth.

### Phase: Execute
1. CREATE `server/recompose.py` — stdlib only, no HTTP, no imports from `server.py`. Implement `split_sections` (depth-counted top-level `<section>` spans, comment-aware) and `recompose` (prefix + ordered item markup + suffix). The blank `<section>` placeholder markup lives here as a module constant — plain markup, NO `hyp-`/`data-hyp-*` tokens.
2. CREATE `tests/test_recompose.py` covering: spec Behavior rows 1-3 and 6 (reorder byte-identity outside moved spans, remove, duplicate, blank purity) and EVERY Edge Cases row (zero sections, commented tags, nested sections, out-of-range index). Use the real deck via `shutil.copy` to `tmp_path`; assert untouched spans byte-identical (slice comparison, not parsed comparison).

### Phase: Validate
1. Run `python -m pytest tests/test_recompose.py -q` — expected EXIT 0, no skips.
2. Self-check: grep your module for `html.parser`/`BeautifulSoup`/`lxml` — any hit violates the splicing constraint.

### Phase: Close
Follow the standard close (orchestrated): flip plan checkbox, frontmatter status, `../deliverables.md` row. `human_review: required` → emit the Human Review Presentation block in your return.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Recompose engine | `server/recompose.py` | Pure-function Python module |
| Unit tests | `tests/test_recompose.py` | pytest |

## Return Contract

Return `status` · `landed` · `validation` (commands + EXIT + WALL_MS + skips with reasons) · `concerns` · `open_questions`.

## Revolving Plan Rules

Simple discovery (<5 min): resolve, document in `../decisions.md`. Complex: add a task, notify. State `PLAN MODIFIED:` lines in your return when tasks change.

---

> **ADX-1 (run erratum, 2026-06-09):** The status-flip bookkeeping steps in this task (marking the task in progress / done in the plan file, this file's frontmatter, and `../deliverables.md`) are performed by the ORCHESTRATOR at verified return — NOT by the executor. Executor: skip those steps; write ONLY within your allowlist. All other instructions unchanged.

