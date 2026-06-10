# Decisions-File Entry Discipline

The entry-shape discipline for the worker-facing `decisions.md` — the append-only file workers read (alongside their own task file) to pick up decisions, discoveries, and errata that affect future work. This file is the SOURCE of the discipline text; the three D13 surfaces carry it:

| Surface | Carries | Lands at (build artifact) |
|---------|---------|---------------------------|
| `decisions-template.md` hard text (`orchestration/workflows/_shared/templates/decisions-template.md`) | The full discipline below, as enforced template text | shipped at task p4-2 |
| Plan + task one-line reminder (in `planning/data/plan-creation-rules.md` § Decisions-File Discipline + generated task files) | The Reminder Line | shipped at task p4-3 |
| Reviewer audit step (the verification card references THIS file directly; planning checkpoints carry the Audit Checklist via `plan-creation-rules.md` § Decisions-File Discipline) | The Audit Checklist + size-floor enforcement | shipped at task p4-3 |

This file is the single source of the discipline; the three carrying surfaces above reference it.

Rationale (D13): the worker-facing decisions file exists to carry SIGNAL that changes future work, not an execution log. Two compounds confirmed routing confusion and rewrite-corruption when entries became narratives; this discipline is the prevention that replaced post-hoc compaction.

---

## Entry-shape rules

| Rule | Statement |
|------|-----------|
| Decision / rationale / scope only | Each entry carries exactly three things: the decision, its rationale, and its scope (which queued work it affects). Nothing else — plus the OPTIONAL `compoundable` marker below. |
| Never file-lists | An entry NEVER enumerates files changed. Files-changed is audit-log content, not decision content. |
| Never N→M narratives | An entry NEVER narrates a count change ("went from 4 files to 3", "merged 12 rows into 5"). The decision and its rationale carry the meaning; the arithmetic is noise. |
| UPDATE, not REWRITE | When a later decision changes an earlier one, APPEND an entry that supersedes it — never rewrite or delete the earlier entry. The append-only history is the audit trail. |
| Routine completions excluded | "Created file X", "updated config Y" never belong here. Ask: will this change future work in one month? If no, it does not go in `decisions.md`. |
| `compoundable` marker (optional) | An entry whose finding is harvest-worthy — a system-improvement pattern, a bug/discovery, a better approach that should compound into RBTV/sb-os later — carries the one-word marker `compoundable` (place it inline in the entry, e.g. a bolded `**compoundable:**` lead on the harvest-worthy sentence). This marker is the SINGLE harvesting home: there is no separate `learnings.md`. Most entries are NOT compoundable — mark only genuine system-improvement findings, never routine decisions. Correction-driven capture is `rbtv-compounding`'s job in the moment, not this marker's. |

## Size floor on rewrites

Routine maintenance of `decisions.md` is append-only — a full-file rewrite is NOT a routine operation (the old plan-shape-compact procedure that once owned it is dissolved under D13: prevention via this discipline replaces post-hoc compaction). If a rewrite is ever genuinely needed, it requires explicit user sanction AND MUST preserve at least 50% of the prior file's size. A rewrite that drops below the ≥50% floor is presumed to have discarded signal — it is rejected, and the original is kept. Decisions, findings, constraints, unresolved questions, and required references must all survive any rewrite.

## Reminder Line

The one-line discipline reminder that generated plans and task files carry verbatim:

> `decisions.md` entries: decision + rationale + scope ONLY (+ optional one-word `compoundable` marker for harvest-worthy findings) — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Audit Checklist

The reviewer runs this against every `decisions.md` it audits; any failure is a finding:

1. Every entry carries decision + rationale + scope, and nothing else.
2. No entry enumerates files changed.
3. No entry narrates a count change (N→M).
4. No earlier entry was rewritten or deleted (history is append-only).
5. If the file was rewritten this cycle, it retained ≥50% of its prior size and preserved all decisions, findings, constraints, open questions, and references.
6. No entry is a routine completion ("Created file X", "updated config Y") — every entry would change future work within one month (Rule 5). A `decisions.md` full of completion logs FAILS this check even when each line is decision-shaped.

## Checkpoint-ratification entry shape (ruling only)

A checkpoint or phase-gate that lands its verdict in `decisions.md` records the RULING ONLY — never the criterion-by-criterion narration. The entry carries:

| Element | Statement |
|---------|-----------|
| Ruling | `approved` or `rejected` — the gate's decision, stated as one word. |
| Scope | Which queued work the ruling unlocks, binds, or blocks. |
| Condition | Any condition attached to an `approved` ruling (e.g. "approved — fix F1 before phase 2"), or the blocking finding for a `rejected` ruling. |

BANNED in the entry: "all N criteria held", "8/8 PASS", per-criterion walk-throughs, and any count narration of the evaluation. The criteria evaluation belongs in the checkpoint's own findings artifact and the `run-log.md` event — NOT in the `decisions.md` ruling entry. A ruling that recites the criteria tally FAILS the entry-shape audit (it is N→M narration of the gate).
