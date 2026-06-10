# DISPATCH — p4-1 (qwen executor) — builder-open-deck

You are a CODE EXECUTOR (qwen). This task is FULLY BOUNDED — every interface, edge case, and decision is pre-resolved in the task and its referenced spec (`bridge-spec.md`). Implement EXACTLY what is specified. Do NOT design, do NOT "fill in the blanks", do NOT interpret intent. If anything is ambiguous, or an anchor excerpt does not match the file on disk, HALT and return `DOUBT_ESCALATED` with the precise question — never guess (doubt_policy: halt).

## Runtime posture (qwen-specific)

- You run under `--approval-mode yolo` (all tool calls auto-approved, host privilege, no sandbox). Your confinement is the conductor's POST-RUN diff of every changed path against the allowlist — so you MUST stay strictly within the 6 allowlist files. Any write outside them is a flagged violation.
- Bound your own work: you have a wall-time budget; do not spin. If you cannot finish within budget, return `BLOCKED` with what remains, never a silent partial.
- Your work-dir has NO `.agents/behavior-rules/` directory and no `QWEN.md` — the generic rule-loading obligation is a silent no-op here. Proceed normally; do NOT hunt for rule files.

## Binding obligations (you MUST obey)

- **Allowlist boundary:** create/modify ONLY these 6 files. Nothing else.
  - ✎ modify `app/js/builder/builder-main.js`  (builder side — "Switch to editor" control + crossing)
  - ✎ modify `app/builder.html`  (builder topbar markup for the new control)
  - ✎ modify `app/js/main.js`  (editor `?file=` consumption — the percent-decode caution)
  - ✎ modify `app/index.html`  (editor topbar markup for "Open in builder")
  - ✎ modify `app/js/shell/file-controls.js`  (editor topbar controls + `apiClient.dialogSaveAs` idiom; where "Open in builder" mounts)
  - ✚ create `tests/e2e/test_pb12_bridge.py`
- **`app/js/builder/deck-save.js` is a CONTEXT file, NOT in your allowlist — REUSE it, do not modify it.** The builder→editor crossing reuses the save plumbing built in p3-3 (`saveDeck(...)` / `/api/deck-save`). Call its public surface; do NOT edit deck-save.js or reach into the server recompose path. The server's recompose is already ADX-2-correct (separator-preserving) — you do NOT touch it.
- **NEVER double-decode the `?file=` param.** `app/js/main.js` already carries a comment warning the URL param is ALREADY percent-decoded by `URLSearchParams.get`. Mirror the EXISTING assemble handoff line in `builder-main.js` (`window.location.href = '/app/?file=' + encodeURIComponent(result.output);`) for the builder→editor crossing, and `'/app/builder.html?file=' + encodeURIComponent(path)` for the editor→builder crossing. Encode on write; never decode on read.
- **D-asset-colocation (decisions.md, 2026-06-10) — IN-FORCE, do NOT try to fix it.** `/api/deck-save` co-locates ONLY assets referenced by added LIBRARY fragments; a saved deck's OWN `assets/*` refs (inherited from its source deck) are NOT copied to a new save directory. The bridge Save-As-es to a NEW path, so a saved deck whose own slides reference `assets/*` will have unresolved image refs when reopened in a different directory. This is **OUT OF p4-1 SCOPE and server-side anyway** (not in your allowlist). You MUST NOT add asset-copy logic, and your `test_pb12` MUST NOT assert that own-asset images resolve after a cross-directory crossing — assert only the spec's Test Plan rows 1-4 (crossing writes a NEW file · target view opens it · cancel leaves view intact · round-trip preserves order). Broken images in a cross-dir crossing are an EXPECTED, accepted limitation here, not a bug to fix.
- **OWNER DATA — root decks are READ-ONLY and SACRED.** The root decks `tecer-gsmm-introduction*.html` (in the work-dir root) are the owner's real files. Your e2e MUST copy any deck to pytest `tmp_path` BEFORE any save, point every injected save-dialog launcher at a `tmp_path` destination, and never let any crossing write to a root deck. A test that writes over an owner deck is a critical failure — HALT rather than risk it.
- **REGRESSION — prior behavior MUST stay green.** Your changes touch `builder-main.js` (shared file; deck lifecycle) and mirror the existing assemble handoff. AFTER your frontmatter `test_command` passes, you MUST ALSO run:
  `python -m pytest tests/e2e/test_pb5_assemble_handoff.py tests/e2e/test_pb8_deck_open.py tests/e2e/test_pb9_deck_tray.py tests/e2e/test_pb10_deck_add.py tests/e2e/test_pb11_deck_save.py -q`
  and include the result in `validation`. `pb5` guards the `/app/?file=` handoff you mirror; `pb8` guards the builder `?file=` arrival the editor→builder crossing navigates to; `pb9`/`pb10`/`pb11` guard the shared builder-main.js deck lifecycle. If ANY regresses, HALT (`DOUBT_ESCALATED`) — do not patch a regression you do not understand.
- **No stray files:** NEVER write scratch/notes/log/summary files into the repo root or anywhere outside the allowlist. Test temp files go through pytest `tmp_path` only. (Your own `.qwen/` session/cache dir is qwen-internal and exempt.)
- **Validation before done:** run the full frontmatter `test_command` (all EXIT 0, no skips); THEN the 5-file regression set above. All green before commit or DONE.
- **Commit (you ARE authorized — local-only self-commit):** after ALL validation passes, commit LOCALLY on `master` with a subject starting EXACTLY `[p4-1]`. Stage ONLY the 6 allowlist files by explicit path (`git add <each file>`) — NEVER `git add -A` / `git add .` (this repo has unrelated uncommitted files from OTHER sessions; staging them is a violation). NEVER push, amend, force-reset, or rebase. The returned commit hash MUST match `git log`.
- **Halt on doubt:** doubt_policy is halt. Do not improvise past ambiguity.
- **No subagents:** swarm_policy is disabled (`max_qwen_subagents: 0`) — do NOT dispatch any qwen sub-agent/agent-tool task.

## Path mapping (the task body was authored in `docs/plan/builder-open-deck/phase-4/`; your CWD is the work-dir root `studio/hypresent` — resolve its relative paths as follows)

| Task-body path | Actual path from your CWD root |
|----------------|--------------------------------|
| `../specs/bridge-spec.md` | `docs/plan/builder-open-deck/specs/bridge-spec.md` (the behavior source of truth — read ALL rows + Edge Cases) |
| `../decisions.md` | `docs/plan/builder-open-deck/decisions.md` (D-asset-colocation entry is in force — see binding note above) |
| `../deliverables.md` | `docs/plan/builder-open-deck/deliverables.md` (do not write — see ADX-1 in the task) |
| `app/...`, `tests/e2e/...` | CWD-relative as written |

## Required return — these five named fields, exactly (no renames, no prose-only)

- `status`: one of DONE · DONE_WITH_NOTES · BLOCKED · DOUBT_ESCALATED · NEEDS_CONTEXT
- `landed`: files created/modified + the commit hash (must match `git log`)
- `validation`: each command run + its EXIT code + WALL_MS; `SKIPPED_COUNT` and a reason per skip (INCLUDE the pb5+pb8+pb9+pb10+pb11 regression run)
- `concerns`: risks/smells/adjacent issues you noticed but did not fix
- `open_questions`: the precise blocker/doubt if you halted (else "none")

Your final message is a HINT; your work on disk is the truth and will be reconciled against `git status` / `git log`. Capture validation output as evidence.

Decisions reference (already applied where relevant; do not re-derive): `docs/plan/builder-open-deck/decisions.md` (ADX-1 status-flip = orchestrator's; D-asset-colocation = in force, do not fix).

---

# TASK PAYLOAD (verbatim — implement this)

---
task_id: p4-1
status: pending
phase: understand
complexity_score: 7
human_review: optional
execution_kind: code
executor: qwen
reviewer: claude-opus
workspace: 3-resources/tools/rbtv
work_dir: studio/hypresent
allowed_workdir: studio/hypresent
branch: master
allowlist:
  - app/js/builder/builder-main.js
  - app/builder.html
  - app/js/main.js
  - app/index.html
  - app/js/shell/file-controls.js
  - tests/e2e/test_pb12_bridge.py
commit_policy: local-only
approval_mode: yolo
test_command: node --check app/js/builder/builder-main.js && node --check app/js/main.js && node --check app/js/shell/file-controls.js && python -m pytest tests/e2e/test_pb12_bridge.py -q
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - modifying root-level *.html decks
doubt_policy: halt
swarm_policy: disabled
max_qwen_subagents: 0
# Human-readable allowlist (✚ create · ✎ modify):
#   ✎ app/js/builder/builder-main.js
#   ✎ app/builder.html
#   ✎ app/js/main.js
#   ✎ app/index.html
#   ✎ app/js/shell/file-controls.js
#   ✚ tests/e2e/test_pb12_bridge.py
---

# Task p4-1: Save-and-switch bridge, both directions

## Goal

"Switch to editor" in the builder (deck mode) and "Open in builder" in the editor — each crossing Save-As-es to a NEW file then opens it in the target view via the existing `?file=` handoff. Behavior source of truth: `../specs/bridge-spec.md` (all rows + Edge Cases).

Serialization note: `app/js/builder/builder-main.js` order is `p2-1 → p3-1 → p3-2 → p3-3 → p4-1`. You are last; build on the current file.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../specs/bridge-spec.md` | Crossing gestures, cancel semantics, disabled states, fresh-filename proposal |
| `app/js/builder/builder-main.js` | Deck mode state, the assemble handoff line `window.location.href = '/app/?file=' + encodeURIComponent(result.output);` you mirror |
| `app/js/builder/deck-save.js` | Save plumbing the builder crossing reuses (built in p3-3) |
| `app/js/main.js` | Editor `?file=` consumption (the percent-decoding caution comment) and `serializeDoc()` |
| `app/js/shell/file-controls.js` | Editor topbar controls + `apiClient.dialogSaveAs` idiom; where "Open in builder" mounts |
| `app/index.html`, `app/builder.html` | Topbar markup for the two new controls |

## Execution Flow

### Phase: Understand
1. Read every Context File. Mark this task in progress in the plan file, this frontmatter, and `../deliverables.md` (same turn).

### Phase: Execute
1. Builder side: "Switch to editor" (deck mode, tray non-empty) — `/api/dialog-save-path` proposing `{name}-restructured.html`, `/api/deck-save`, then navigate `/app/?file=<path>`. Cancel/error → stay, status-bar message, no navigation.
2. Editor side: "Open in builder" (disabled when no doc open) — `serializeDoc()`, `/api/dialog-save-as`, then navigate `/app/builder.html?file=<path>` (the p2-1 arrival). NEVER double-decode the param.
3. CREATE `tests/e2e/test_pb12_bridge.py` — spec Test Plan rows 1-4 (both crossings, cancel, round trip) with injected dialog launchers and temp paths.

### Phase: Validate
1. Run the frontmatter `test_command` — expected EXIT 0.

### Phase: Close
Standard orchestrated close: flip plan checkbox, frontmatter status, `../deliverables.md` row.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Bridge controls + crossings | `builder-main.js`, `app/builder.html`, `app/js/main.js`, `app/index.html`, `file-controls.js` | edits |
| e2e | `tests/e2e/test_pb12_bridge.py` | Playwright pytest |

## Return Contract

Return `status` · `landed` · `validation` (commands + EXIT + WALL_MS + skips with reasons) · `concerns` · `open_questions`.

## Revolving Plan Rules

Simple discovery (<5 min): resolve, document in `../decisions.md`. Complex: add a task, notify. State `PLAN MODIFIED:` lines in your return when tasks change.

---

> **ADX-1 (run erratum, 2026-06-09):** The status-flip bookkeeping steps in this task (marking the task in progress / done in the plan file, this file's frontmatter, and `../deliverables.md`) are performed by the ORCHESTRATOR at verified return — NOT by the executor. Executor: skip those steps; write ONLY within your allowlist. All other instructions unchanged.
