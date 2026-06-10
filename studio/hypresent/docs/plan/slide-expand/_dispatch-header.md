# DISPATCH — T1-slide-expand (kimi executor)

You are a NON-REASONING code executor. Implement EXACTLY what the task below specifies. Do NOT design, do NOT "fill in the blanks", do NOT interpret intent. Every interface and edge case is pre-resolved in the task. If anything is ambiguous or an anchor excerpt does not match the file on disk, HALT and return `DOUBT_ESCALATED` with the precise question — never guess.

## Binding obligations (you MUST obey)

- **Allowlist boundary:** Create/modify ONLY these 5 files. Nothing else.
  - ✚ create `app/js/builder/slide-stage.js`
  - ✚ create `tests/e2e/test_pb7_slide_expand.py`
  - ✎ modify `app/js/builder/browse-pane.js`
  - ✎ modify `app/js/builder/builder-main.js`
  - ✎ modify `app/css/builder.css`
- **No stray files:** NEVER write scratch/notes/log files into the repo root or anywhere outside the allowlist.
- **Validation before done:** Run the task's `test_command` and capture output. All checks EXIT 0 before you commit or claim DONE.
- **Commit:** local-only on `master`, subject MUST start with `[T1-slide-expand]`, stage ONLY the 5 allowlist files (NEVER `git add -A` — this repo has unrelated uncommitted files). NEVER push/amend/force-reset.
- **Halt on doubt:** doubt_policy is halt. Do not improvise past ambiguity.
- **No subagents:** swarm_policy is disabled — do NOT launch any kimi subagent.

## Required return — these five named fields, exactly (no renames, no prose-only)

- `status`: one of DONE · DONE_WITH_NOTES · BLOCKED · DOUBT_ESCALATED · NEEDS_CONTEXT
- `landed`: files created/modified + the commit hash (must match `git log`)
- `validation`: each command run + its EXIT code + WALL_MS; `SKIPPED_COUNT` and a reason per skip
- `concerns`: risks/smells/adjacent issues you noticed but did not fix
- `open_questions`: the precise blocker/doubt if you halted (else "none")

The return message is a HINT; your work on disk is the truth and will be reconciled against `git status` / `git log`. Capture validation output as evidence.

Decisions reference (already applied in the task; do not re-derive): `docs/plan/slide-expand/decisions.md`.

---

# TASK PAYLOAD (verbatim — implement this)

