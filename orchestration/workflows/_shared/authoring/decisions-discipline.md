# Decisions-File Entry Discipline

The entry-shape discipline for the worker-facing `decisions.md` — the append-only file workers read (alongside their own task file) to pick up decisions, discoveries, and errata that affect future work. This file is the SOURCE of the discipline text; the three D13 surfaces carry it:

| Surface | Carries | Lands at |
|---------|---------|----------|
| `decisions-template.md` hard text | The full discipline below, as enforced template text | p4-2 |
| Plan + task one-line reminder | The Reminder Line | p4-3 |
| Reviewer audit step | The Audit Checklist + size-floor enforcement | p4-3 |

Rationale (D13): the worker-facing decisions file exists to carry SIGNAL that changes future work, not an execution log. Two compounds confirmed routing confusion and rewrite-corruption when entries became narratives; this discipline is the prevention that replaced post-hoc compaction.

---

## Entry-shape rules

| Rule | Statement |
|------|-----------|
| Decision / rationale / scope only | Each entry carries exactly three things: the decision, its rationale, and its scope (which queued work it affects). Nothing else. |
| Never file-lists | An entry NEVER enumerates files changed. Files-changed is audit-log content, not decision content. |
| Never N→M narratives | An entry NEVER narrates a count change ("went from 4 files to 3", "merged 12 rows into 5"). The decision and its rationale carry the meaning; the arithmetic is noise. |
| UPDATE, not REWRITE | When a later decision changes an earlier one, APPEND an entry that supersedes it — never rewrite or delete the earlier entry. The append-only history is the audit trail. |
| Routine completions excluded | "Created file X", "updated config Y" never belong here. Ask: will this change future work in one month? If no, it does not go in `decisions.md`. |

## Size floor on rewrites

Routine maintenance of `decisions.md` is append-only. A full-file rewrite (the only sanctioned exception, via the maintenance-compaction path) MUST preserve at least 50% of the prior file's size. A rewrite that drops below the ≥50% floor is presumed to have discarded signal — it is rejected, and the original is kept. Decisions, findings, constraints, unresolved questions, and required references must all survive any compaction.

## Reminder Line

The one-line discipline reminder that generated plans and task files carry verbatim:

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Audit Checklist

The reviewer runs this against every `decisions.md` it audits; any failure is a finding:

1. Every entry carries decision + rationale + scope, and nothing else.
2. No entry enumerates files changed.
3. No entry narrates a count change (N→M).
4. No earlier entry was rewritten or deleted (history is append-only).
5. If the file was compacted this cycle, it retained ≥50% of its prior size and preserved all decisions, findings, constraints, open questions, and references.
