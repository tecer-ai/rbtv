---
name: 'refresh-workflow'
description: 'Update existing plan/PRD/CLAUDE.md with session outcomes — no new files'
---

# Refresh Workflow

**Goal:** Update existing documentation (plan, PRD, CLAUDE.md) in place with this session's outcomes so the next agent can pick up without guessing. Never creates new files.

**Your Role:** Silent doc-maintainer. Discover targets, extract outcomes, apply edits, guarantee a resume marker. Minimize questions. One shot.

---

## Hard Rules

| # | Rule |
|---|------|
| 1 | **Zero new files.** Ever. If a target doc doesn't exist, ASK — do not create. |
| 2 | **No duplicated content across docs.** For any fact, find the authoritative doc and update only that one. Cross-reference from others by path. |
| 3 | **Preserve structure.** Append/insert into existing sections; do NOT rewrite sections that are already there. |
| 4 | **Separate three flavors.** On-plan progress · scope changes · beyond-plan additions. Do not conflate. |
| 5 | **One question max.** Ask only if target docs are genuinely ambiguous. Otherwise proceed silently. |
| 6 | **End with a one-line audit.** List files touched and where the resume marker lives. |

---

## Execution (4 phases, one turn each where possible)

### Phase 1 — Discover targets

Scan the conversation for documentation candidates. Signals:

- Files read or edited during the session whose name matches a plan/PRD/requirements/CLAUDE.md pattern
- Files explicitly referenced by the user as "the plan", "the PRD", "the spec", "the docs"
- `CLAUDE.md` in the directory where most of the session's work landed

Build candidate set:

- **Lead plan** — the single file that tracks progress (required if any existed this session)
- **Structural docs** — CLAUDE.md / PRD / requirements — updated only if the session changed things they describe (routing, conventions, schema, data locations, file counts)

Decision rules:

| Situation | Action |
|---|---|
| Exactly one lead plan found + zero or more clearly-related structural docs | Proceed silently. Use that set. |
| Zero lead plans found | Ask one question: "What's the doc to update?" Use the answer as lead plan. If user says "just CLAUDE.md" or similar, treat that as the lead. |
| ≥2 candidate lead plans, none obviously authoritative | Ask one question with the candidates listed: "Which is the lead plan?" |
| A structural doc would need to be CREATED to describe new state | DO NOT create it. Log in audit line as "needs doc — not created per rule 1". |

### Phase 2 — Extract outcomes (5 buckets)

Walk the conversation from the last doc update (check frontmatter `last_updated` or `## Progress` date if present) to now. Categorize every concrete outcome:

| Bucket | What counts | Where it goes in the lead plan |
|---|---|---|
| **On-plan progress** | Work matching a unit/task/requirement already in the plan | Update the progress table / checklist in place |
| **Scope changes** | Work done differently than the plan described (narrowed, expanded, substituted) | Append to "Scope changes" section (create if missing, directly under Progress Summary) |
| **Beyond-plan additions** | Features, behaviors, or decisions NOT in the original plan | Append to "Features added beyond original plan" section (create if missing) |
| **Data operations** | Entity moves, renames, adds, field edits at scale | Append to "Data operations log" (create if missing). Date-stamp each entry. |
| **New followups** | TBDs, gaps, technical debt, deferred work surfaced this session | Append to "Known followups" section (create if missing) |

For structural docs (CLAUDE.md / PRD):

- Update routing tables, file lists, counts, or conventions ONLY where the session changed the underlying reality
- Add pointers to the lead plan for active work — never duplicate the plan's contents

### Phase 3 — Apply edits

Use Edit (preferred) or Write. Order:

1. Lead plan progress table — update status cells (✅ / ⏳ / pending) and the Progress Summary line
2. Lead plan scope-changes / beyond-plan / data-ops / followups sections — append new entries, never rewrite existing ones
3. Structural docs — surgical edits matching the new reality
4. Frontmatter: bump `last_updated` to today's date on any edited doc that has that field

### Phase 4 — Guarantee resume marker

The lead plan MUST have a visibly labeled resume block. Look for phrases like "Resume point", "Next session", "Start here", or a "How to resume" block.

- If present → verify it still points to the correct next step. Update if stale.
- If missing → insert a "Resume point for next session" line or a short "How to resume" block near the top of the lead plan (right after the progress table). Keep it 1-5 lines.

### Phase 5 — Audit output

End the turn with one compact line:

```
Refresh complete. Updated: {file1}, {file2}. Resume: {plan-file}#{marker-heading-or-line}.
```

If any structural doc was flagged as "needs doc — not created per rule 1", list it separately so the user can decide manually.

---

## Skipped by design

This workflow intentionally does NOT:

- Present menus or ask for approval between phases
- Create new files (including new handoff files)
- Generate summary artifacts for others — the lead plan IS the artifact
- Validate completeness — the user invokes this because they already know what changed; don't second-guess

If the user wants a comprehensive transfer artifact, they invoke `/session-close handoff` instead.
