# Finalization Message Template

The orchestrator produces this message at the end of step-04 to close the orchestration session. Replace placeholders; preserve section structure. Each section is REQUIRED unless marked optional.

---

## Status line

`{plan-name}` plan **{COMPLETE | COMPLETE PENDING USER ACTION}**{ — brief reason if pending}. {N} commits added this session: {commit list — one line per commit, hash + short description}. {Phase status summary if applicable, e.g., "All Phase N plan checkboxes flipped except `pN-user-review` (left unchecked — bundle-accepted per E13)".}

---

## Batch summary

| Batch | Model | Status | Commit |
|---|---|---|---|
| {batch_id} — {short description} | {haiku\|sonnet\|opus} | {DONE \| DONE_WITH_NOTES \| FIXED \| CLEAN} | `{commit_hash}` |

One row per batch dispatched in this session. Include reviewer dispatches as their own rows.

---

## Next actions — in order

Each item MUST be self-explanatory. The user reads this with zero session context. If an item references a path, decision, or commit, name it inline. If skipping the item has consequences, state them. If prerequisites exist, list them.

1. {action — what to do, why, how, consequence of skipping}
2. {action}
3. ...

---

## Human Review

REQUIRED if any phase produced Human Review Presentation blocks (any task with `human_review: required` or any checkpoint). Omit entirely if no qualifying tasks ran.

Group by phase under `### Phase {N} — {phase name}` headers. Under each phase header, paste each finalized Human Review Presentation block (from that phase's reviewer return) VERBATIM. Block format: see `{rbtv_path}/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation. Do NOT collapse, summarize, paraphrase, or hide flags behind a wrapper.

If a task's reviewer flagged a 🔴 red flag, also list that task in the next section.

---

## Decisions worth your review (lowest confidence first)

REQUIRED if (a) mode was `autonomous` AND any decision logged with `confidence: medium` or `confidence: low`, OR (b) any Human Review block above contains a 🔴 red flag. If neither condition holds, replace this section with: "No low-confidence decisions logged."

Sort autonomous-mode entries by confidence ascending (`low` first, then `medium`). Red-flag tasks (regardless of mode) appear at the top of the list — they are the highest-priority review items. For each:

- **{Entry ID or task-id} — {short title}** (confidence: {low\|medium} OR red-flag: {one-line flag summary})
  - **Decided / Done:** {1-line summary}
  - **Alternatives:** {what the user could have chosen instead, if applicable}
  - **Why this one:** {orchestrator's or executor's rationale}
  - **Cost to change:** {effort + reversibility path}

Link to the full log: `{autonomous_run_log_path}` (only if autonomous mode was active)

---

## Artifacts

- Plan: `{plan_path}`
- Shape: `{shape_path}`
- Learnings: `{learnings_path}`
- Orchestration state: `{orchestration_state_path}`
- Autonomous run log: `{autonomous_run_log_path}` (include only if mode was `autonomous`)

---

## Working tree note (optional)

Include only if there is uncommitted/unstaged work the orchestrator deliberately did not touch. State the paths and why they were left alone.

---

## Post-merge / next-step commands (optional)

Include only if the user must run commands to land or follow up the work. Use a fenced bash block with a one-line comment per command explaining what it does.
