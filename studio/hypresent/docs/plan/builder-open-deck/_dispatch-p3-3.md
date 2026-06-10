# DISPATCH — p3-3 (kimi executor) — builder-open-deck

You are a NON-REASONING code executor. Implement EXACTLY what the task below specifies. Do NOT design, do NOT "fill in the blanks", do NOT interpret intent. Every interface and edge case is pre-resolved in the task and its referenced specs. If anything is ambiguous or an anchor excerpt does not match the file on disk, HALT and return `DOUBT_ESCALATED` with the precise question — never guess.

## Binding obligations (you MUST obey)

- **Allowlist boundary:** touch ONLY these 4 files. Nothing else.
  - ✚ create `app/js/builder/deck-save.js`
  - ✎ modify `app/js/builder/builder-main.js`
  - ✎ modify `app/builder.html`
  - ✚ create `tests/e2e/test_pb11_deck_save.py`
- **`tray.js` is NOT in your allowlist — use its PUBLIC API.** `getItems()` was built in p3-1 (it emits the deck-save items contract). You call `tray.getItems()` and POST it; do NOT modify or reach into tray.js.
- **ADX-2 ERRATUM — the authoritative recompose contract (deck-save-spec consumer obligation).** `docs/plan/builder-open-deck/specs/deck-save-spec.md` carries an **ADX-2 erratum at its BOTTOM** that SUPERSEDES the "Context Snapshot" recompose sketch earlier in the same spec. The erratum: `recompose` rebuilds the doc as `prefix + item₀ + sep(item₀) + … + itemₙ₋₁ + suffix` — inter-slide separators PRESERVED (an `existing` item carries its own trailing separator; a last-section/`fragment`/`blank` item uses the deck's DEFAULT separator). The server (`/api/deck-save`, built in phase 1) already implements this — you do NOT implement recompose; you build the UI that POSTs `getItems()` and the server recomposes. BUT your `test_pb11` "reopen intact" assertions MUST align with separator-preserving recompose (a reopened saved deck keeps its inter-slide structure) — follow the erratum, never the superseded sketch.
- **OWNER DATA — root decks are READ-ONLY and SACRED (this is the SAVE task — highest risk).** The root decks `studio/hypresent/tecer-gsmm-introduction*.html` are the owner's real files. Your e2e test MUST copy a deck to pytest `tmp_path` BEFORE any save, point the injected save-dialog at a `tmp_path` destination, and ASSERT the original root deck is byte-unchanged after the save. NEVER let any save (new-file OR overwrite) write to a root deck. A test that saves over an owner deck is a critical failure — HALT rather than risk it.
- **REGRESSION — prior behavior MUST stay green.** Your changes touch `builder-main.js` (deck-mode Save replaces the assemble button) and the tray's save path. AFTER your frontmatter `test_command` passes, you MUST ALSO run `python -m pytest tests/e2e/test_pb8_deck_open.py tests/e2e/test_pb9_deck_tray.py tests/e2e/test_pb10_deck_add.py -q` and include the result in `validation`. If ANY regresses, HALT (`DOUBT_ESCALATED`) — do not commit a regression.
- **No stray files:** NEVER write scratch/notes/log files into the repo root or anywhere outside the allowlist. Test temp files go through pytest `tmp_path` only.
- **Validation before done:** run the full frontmatter `test_command` (`node --check app/js/builder/deck-save.js && node --check app/js/builder/builder-main.js && python -m pytest tests/e2e/test_pb11_deck_save.py -q`), all EXIT 0 no skips; THEN the regression trio above. All green before commit or DONE.
- **Commit:** local-only on `master`, subject MUST start with `[p3-3]`, stage ONLY the 4 allowlist files (NEVER `git add -A` — this repo has unrelated uncommitted files from other sessions). NEVER push/amend/force-reset.
- **Halt on doubt:** doubt_policy is halt. Do not improvise past ambiguity.
- **No subagents:** swarm_policy is disabled — do NOT launch any kimi subagent.

## Path mapping (the task body was authored in `docs/plan/builder-open-deck/phase-3/` — resolve its relative paths from your work-dir root as follows)

| Task-body path | Actual path from your work-dir root |
|----------------|--------------------------------------|
| `../specs/deck-save-spec.md` | `docs/plan/builder-open-deck/specs/deck-save-spec.md` (READ THE ADX-2 ERRATUM AT THE BOTTOM) |
| `../decisions.md` | `docs/plan/builder-open-deck/decisions.md` |
| `../deliverables.md` | `docs/plan/builder-open-deck/deliverables.md` (do not write — see ADX-1 in the task) |
| `app/...`, `tests/e2e/...` | work-dir-relative as written |

## Required return — these five named fields, exactly (no renames, no prose-only)

- `status`: one of DONE · DONE_WITH_NOTES · BLOCKED · DOUBT_ESCALATED · NEEDS_CONTEXT
- `landed`: files created/modified + the commit hash (must match `git log`)
- `validation`: each command run + its EXIT code + WALL_MS; `SKIPPED_COUNT` and a reason per skip (INCLUDE the pb8+pb9+pb10 regression run)
- `concerns`: risks/smells/adjacent issues you noticed but did not fix
- `open_questions`: the precise blocker/doubt if you halted (else "none")

The return message is a HINT; your work on disk is the truth and will be reconciled against `git status` / `git log`. Capture validation output as evidence.

Decisions reference (already applied in the task; do not re-derive): `docs/plan/builder-open-deck/decisions.md`.

---

# TASK PAYLOAD (verbatim — implement this)

---
task_id: p3-3
status: in-progress
phase: understand
complexity_score: 7
human_review: optional
execution_kind: code
executor: kimi
reviewer: claude-opus
workspace: 3-resources/tools/rbtv
work_dir: studio/hypresent
allowed_workdir: studio/hypresent
branch: master
allowlist:
  - app/js/builder/deck-save.js
  - app/js/builder/builder-main.js
  - app/builder.html
  - tests/e2e/test_pb11_deck_save.py
commit_policy: local-only
test_command: node --check app/js/builder/deck-save.js && node --check app/js/builder/builder-main.js && python -m pytest tests/e2e/test_pb11_deck_save.py -q
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - modifying root-level *.html decks
doubt_policy: halt
swarm_policy: disabled
max_kimi_subagents: 0
# Human-readable allowlist (✚ create · ✎ modify):
#   ✚ app/js/builder/deck-save.js
#   ✎ app/js/builder/builder-main.js
#   ✎ app/builder.html
#   ✚ tests/e2e/test_pb11_deck_save.py
---

# Task p3-3: Save deck UI — new-file vs overwrite, every time

## Goal

A "Save deck…" control in deck mode asks new-file vs overwrite on every explicit save, then posts `getItems()` to `/api/deck-save` (new-file path via `/api/dialog-save-path`; overwrite path uses `state.deck.path`) and reports the result in the status bar. In deck mode the assemble button is hidden — Save replaces it. Behavior source of truth: `../specs/deck-save-spec.md` (the UI exercises its API rows 1-8).

Serialization note: `app/js/builder/builder-main.js` order is `p2-1 → p3-1 → p3-2 → p3-3 → p4-1`. p3-2 has landed; build on the current file.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../specs/deck-save-spec.md` | `/api/deck-save` payload (`source_path`, `out_path`, `items`), response (`assets_copied`/`assets_skipped`), error behavior |
| `../decisions.md` | "Ask each time" save semantics (Key Decisions) |
| `app/js/builder/builder-main.js` | Assemble-button wiring you mirror/replace in deck mode; `setStatus` reporting idiom |
| `app/js/builder/tray.js` | `getItems()` (built in p3-1) |
| `app/js/api-client.js` | Fetch idiom for the new endpoints |
| `app/builder.html` | Where the Save control and the new-file/overwrite chooser mount |

## Execution Flow

### Phase: Understand
1. Read every Context File. Mark this task in progress in the plan file, this frontmatter, and `../deliverables.md` (same turn).

### Phase: Execute
1. CREATE `app/js/builder/deck-save.js` — `saveDeck({deck, items, mode})` posting to `/api/deck-save`; the new-file path first fetches `/api/dialog-save-path`. Cancel → no write, no error.
2. UPDATE `app/builder.html` + `builder-main.js` — deck-mode Save control with an in-page two-button chooser ("New file…" / "Overwrite") shown on EVERY explicit save; assemble button hidden in deck mode, restored in assemble mode; empty-tray → Save disabled; success/error → `setStatus` (include `assets_copied` count, surface `assets_skipped`).
3. After a successful new-file save, `state.deck.path` re-points to the new file (subsequent Overwrite writes there).
4. CREATE `tests/e2e/test_pb11_deck_save.py` — full loop at the floor: open real deck copy → reorder/remove/duplicate/add blank + fixture-library slide → Save (both modes, injected dialog) → reopen the saved file → tray reflects the restructure; assert the original root deck untouched.

### Phase: Validate
1. Run the frontmatter `test_command` — expected EXIT 0.

### Phase: Close
Standard orchestrated close: flip plan checkbox, frontmatter status, `../deliverables.md` row.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Save module + UI | `app/js/builder/deck-save.js`, `builder-main.js`, `app/builder.html` | ES module + edits |
| e2e | `tests/e2e/test_pb11_deck_save.py` | Playwright pytest |

## Return Contract

Return `status` · `landed` · `validation` (commands + EXIT + WALL_MS + skips with reasons) · `concerns` · `open_questions`.

## Revolving Plan Rules

Simple discovery (<5 min): resolve, document in `../decisions.md`. Complex: add a task, notify. State `PLAN MODIFIED:` lines in your return when tasks change.

---

> **ADX-1 (run erratum, 2026-06-09):** The status-flip bookkeeping steps in this task (marking the task in progress / done in the plan file, this file's frontmatter, and `../deliverables.md`) are performed by the ORCHESTRATOR at verified return — NOT by the executor. Executor: skip those steps; write ONLY within your allowlist. All other instructions unchanged.
