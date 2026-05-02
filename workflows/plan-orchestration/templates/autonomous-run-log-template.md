---
plan: {plan-name}
purpose: Audit trail for autonomous orchestration — captures halt-skips, unilateral decisions, and risk-acceptance for user review.
---

# Autonomous Run Log — {plan-name}

> **Why this log exists.** The user authorized continuous orchestration in autonomous mode with these constraints: skip all routine plan-mandated halts (checkpoint AND doubt AND USER-EXECUTED-ONLY tasks), do NOT destroy user content, free to edit project source files and managed scaffolds. Plan-marked HARD halts (irreversibility gates, e.g., pre-cutover) are NEVER overridden. In exchange, every halt skipped AND every decision the user normally would have approved MUST be appended to this log so the user can review and challenge it. The log is the audit trail that makes autonomous execution accountable. **Never modify entries above the "Append-only" line.**

---

## Always-log categories

The orchestrator MUST append an entry whenever it makes a decision that falls into ANY of these categories — even if the decision feels routine in the moment:

| Category | Why it matters |
|----------|---------------|
| Change to user content (rule files, CLAUDE.md, glossary, profile) | User-owned; reverting requires explicit user knowledge |
| Change to a convention default (naming, path format, marker semantics) | Propagates beyond the immediate edit |
| Decision under ambiguous spec (plan/shape silent on the case) | User would have wanted to disambiguate |
| Decision where 2+ valid alternatives existed | The unchosen alternative may have been preferred |
| Decision that constrains future choices (cross-batch coupling) | Downstream batches inherit the constraint |
| USER-EXECUTED-ONLY task accepted with defaults | User reserved this; orchestrator overrode the reservation |
| Doubt-escalation skipped | Sub-agent flagged uncertainty; orchestrator decided unilaterally |
| Risk-acceptance with mitigation (rather than user approval) | Risk is the user's to weigh, not the orchestrator's |

If the decision does not fall into any category, no log entry is required. Routine successful task completions are never logged.

---

## Entry Schema

Every entry uses this shape:

```
### EN — <short title> · <commit-hash-or-batch-id> · <date>

- **Confidence:** high | medium | low
- **Decision:** what the orchestrator decided.
- **Why decided unilaterally:** why no user halt fired (or which halt was skipped).
- **User might have decided differently:** the realistic alternative the user could pick if asked.
- **Risk accepted:** what the orchestrator chose to live with, and what mitigation exists.
- **Reversibility:** how the user can undo this if challenged (commit revert, file edit, rollback tag, etc.).
```

**Confidence rubric:**

| Level | When to assign |
|-------|----------------|
| `high` | Decision is mechanical OR the unchosen alternative would have produced an equivalent outcome |
| `medium` | Multiple valid alternatives existed; orchestrator picked one with clear rationale; user might prefer another but the impact is contained |
| `low` | Orchestrator resolved real ambiguity; user judgment was the right path and was overridden; the choice may not be what the user would have made |

The finalization message surfaces medium and low confidence entries explicitly — high-confidence entries remain in the log for completeness but do not gate user review.

---

## Append-only

(All entries below this line are append-only. Do not edit prior entries. Append new ones at the bottom in chronological order, numbered sequentially.)

---
