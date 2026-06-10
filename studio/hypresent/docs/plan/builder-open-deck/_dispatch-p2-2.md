# DISPATCH — p2-2 (kimi executor) — builder-open-deck

You are a NON-REASONING code executor. Implement EXACTLY what the task below specifies. Do NOT design, do NOT "fill in the blanks", do NOT interpret intent. Every interface and edge case is pre-resolved in the task and its referenced specs. If anything is ambiguous or an anchor excerpt does not match the file on disk, HALT and return `DOUBT_ESCALATED` with the precise question — never guess.

## Binding obligations (you MUST obey)

- **Allowlist boundary (ADX-3-extended — authoritative over the frontmatter list):** touch ONLY these 5 files. Nothing else.
  - ✎ modify `app/js/builder/tray.js`
  - ✎ modify `app/js/builder/previews.js`
  - ✎ modify `app/js/builder/deck-load.js`
  - ✎ modify `tests/e2e/test_pb8_deck_open.py`
  - ✎ modify `app/js/builder/builder-main.js` — ONE purpose only, per the ADX-3 erratum at the bottom of the task: REMOVE the temporary post-`setFromPreset` srcdoc-injection block in `loadDeckIntoTray` once your per-row provider lands. No other change to this file.
- **Evidence capture (sanctioned write):** the task's Validate step 2 (headed spot-check screenshot) writes to `docs/plan/builder-open-deck/phase-2/evidence/` from your work-dir root — create the folder if absent, name the file `p2-2-headed-thumbnails.png`. This is the ONLY sanctioned write outside the 5-file allowlist. The spot-check driver script runs from the system temp dir or inline — NEVER left in the repo.
- **No stray files:** NEVER write scratch/notes/log files into the repo root or anywhere outside the allowlist + the sanctioned evidence path. Test temp files go through pytest `tmp_path` only.
- **READ-ONLY owner data:** the root decks `tecer-gsmm-introduction*.html` are the owner's real files. Tests and the spot-check copy them to temp locations — NEVER modify, move, or write to the originals.
- **Validation before done (ADX-3-extended):** run from your work-dir root: `node --check app/js/builder/tray.js && node --check app/js/builder/previews.js && node --check app/js/builder/builder-main.js && python -m pytest tests/e2e/test_pb8_deck_open.py -q`. All EXIT 0, no skips, before you commit or claim DONE.
- **Commit:** local-only on `master`, subject MUST start with `[p2-2]`, stage ONLY the allowlist files you changed (NEVER `git add -A` — this repo has unrelated uncommitted files). Do NOT stage the evidence screenshot. NEVER push/amend/force-reset.
- **Halt on doubt:** doubt_policy is halt. Do not improvise past ambiguity.
- **No subagents:** swarm_policy is disabled — do NOT launch any kimi subagent.

## Path mapping (the task body was authored in `docs/plan/builder-open-deck/phase-2/` — resolve its relative paths from your work-dir root as follows)

| Task-body path | Actual path from your work-dir root |
|----------------|--------------------------------------|
| `../specs/deck-ingest-spec.md` | `docs/plan/builder-open-deck/specs/deck-ingest-spec.md` |
| `../decisions.md` | `docs/plan/builder-open-deck/decisions.md` |
| `../deliverables.md` | `docs/plan/builder-open-deck/deliverables.md` (do not write — see ADX-1 in the task) |
| `phase-2/evidence/` | `docs/plan/builder-open-deck/phase-2/evidence/` (sanctioned screenshot path) |
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
task_id: p2-2
status: pending
phase: understand
complexity_score: 6
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
  - app/js/builder/previews.js
  - app/js/builder/deck-load.js
  - tests/e2e/test_pb8_deck_open.py
commit_policy: local-only
test_command: node --check app/js/builder/tray.js && node --check app/js/builder/previews.js && python -m pytest tests/e2e/test_pb8_deck_open.py -q
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - modifying root-level *.html decks
doubt_policy: halt
swarm_policy: disabled
max_kimi_subagents: 0
# Human-readable allowlist (✎ modify):
#   ✎ app/js/builder/tray.js
#   ✎ app/js/builder/previews.js
#   ✎ app/js/builder/deck-load.js
#   ✎ tests/e2e/test_pb8_deck_open.py
---

# Task p2-2: Deck-themed thumbnails for existing-section rows

## Goal

Tray rows for the open deck's sections render thumbnails composed from the deck's own `head` styles + each section's html (srcdoc), per `../specs/deck-ingest-spec.md` gesture 3 and Edge Cases (lazy render, decorative-failure rule).

Serialization note: `app/js/builder/tray.js` is shared — its order is `p2-2 → p3-1`. You are first; build on the current file.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../specs/deck-ingest-spec.md` | Thumbnail contract (deck head + section srcdoc, scripts stripped server-side) |
| `app/js/builder/previews.js` | `buildSrcdoc(theme, fragment)` to reuse; caching + IntersectionObserver idiom for lazy render |
| `app/js/builder/tray.js` | Row render: the `getSlideSrcdoc(libraryPath, rec.id)` call you generalize — rows need a per-row srcdoc source (library rows keep today's path; deck rows compose locally) |
| `app/js/builder/deck-load.js` | Where the loaded deck's `head` + `sections` live (built in p2-1) |

## Execution Flow

### Phase: Understand
1. Read every Context File. Mark this task in progress in the plan file, this frontmatter, and `../deliverables.md` (same turn).

### Phase: Execute
1. UPDATE `app/js/builder/previews.js` — export a deck-srcdoc builder (deck `head` markup + section html; `buildSrcdoc` only wraps a `<style>` string, so add a variant accepting raw head markup).
2. UPDATE `app/js/builder/tray.js` — rows obtain their srcdoc from a kind-appropriate provider instead of hardcoding `getSlideSrcdoc(libraryPath, rec.id)`; thumbnail failure stays decorative (keep the `catch(() => {})` rule).
3. UPDATE `app/js/builder/deck-load.js` and/or the wiring so deck rows carry what the provider needs.
4. UPDATE `tests/e2e/test_pb8_deck_open.py` — add spec Test Plan row 2 (each row's iframe srcdoc contains its section markup and the deck head styles).

### Phase: Validate
1. Run the frontmatter `test_command` — expected EXIT 0.
2. Headed spot-check: open a real deck copy; thumbnails visibly render slide content (capture a screenshot to `phase-2/evidence/`).

### Phase: Close
Standard orchestrated close: flip plan checkbox, frontmatter status, `../deliverables.md` row.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Deck thumbnail rendering | `app/js/builder/previews.js`, `app/js/builder/tray.js`, `app/js/builder/deck-load.js` | edits |
| e2e extension | `tests/e2e/test_pb8_deck_open.py` | Playwright pytest |

## Return Contract

Return `status` · `landed` · `validation` (commands + EXIT + WALL_MS + skips with reasons) · `concerns` · `open_questions`.

## Revolving Plan Rules

Simple discovery (<5 min): resolve, document in `../decisions.md`. Complex: add a task, notify. State `PLAN MODIFIED:` lines in your return when tasks change.

---

> **ADX-1 (run erratum, 2026-06-09):** The status-flip bookkeeping steps in this task (marking the task in progress / done in the plan file, this file's frontmatter, and `../deliverables.md`) are performed by the ORCHESTRATOR at verified return — NOT by the executor. Executor: skip those steps; write ONLY within your allowlist. All other instructions unchanged.

> **ADX-3 (run erratum, 2026-06-09):** Your allowlist is EXTENDED with `app/js/builder/builder-main.js` (✎ modify) for ONE purpose only: p2-1 shipped a TEMPORARY stopgap in `loadDeckIntoTray` (builder-main.js, the block that manually injects each section's srcdoc into tray iframes immediately after `tray.setFromPreset(...)` — because tray.js was off-allowlist for p2-1). Once your per-row srcdoc provider lands in `tray.js` (Execute step 2), that injection is redundant and conflicting (tray re-render would wipe and the provider re-fill the same iframes): REMOVE the injection block so deck rows obtain srcdoc EXCLUSIVELY through the provider. Make no other change to `builder-main.js`. Your `test_command` gains `node --check app/js/builder/builder-main.js`. The full validation is now: `node --check app/js/builder/tray.js && node --check app/js/builder/previews.js && node --check app/js/builder/builder-main.js && python -m pytest tests/e2e/test_pb8_deck_open.py -q`.
