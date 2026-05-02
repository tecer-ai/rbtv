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

## Decisions worth your review (lowest confidence first)

REQUIRED if mode was `autonomous` AND any decision logged with `confidence: medium` or `confidence: low`. If neither condition holds, replace this section with: "No low-confidence decisions logged."

Sort entries by confidence ascending (`low` first, then `medium`). For each:

- **{Entry ID} — {short title}** (confidence: {low\|medium})
  - **Decided:** {1-line summary}
  - **Alternatives:** {what the user could have chosen instead}
  - **Why this one:** {orchestrator's rationale}
  - **Cost to change:** {effort + reversibility path}

Link to the full log: `{autonomous_run_log_path}`

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
