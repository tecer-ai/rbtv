---
description: "The coding component — the code-hygiene disciplines an agent applies whenever it writes, edits, fixes, or refactors code (the `coding` skill: no-dead-code, no-duplicate, no-monolith, no-patches), plus the on-demand architecture audit (`improve-codebase-architecture`)."
---

# coding

`coding/` holds the parts whose subject is the CODE an agent leaves behind — not how it thinks
(`core/behaviour`), not how it talks to the owner (`core/communication`). Everything here is
loaded at a moment, never always-on: the moment is "I am about to write, edit, fix, or refactor
code". That is why the four disciplines ship as ONE SKILL and not as rules — the owner's deciding
reason (2026-08-23): most turns in this vault are not coding turns, and a rule's always-on cost on
every non-coding turn is waste.

| Part | Answers |
|---|---|
| `coding` (skill; reads the four references beside it, all four on every load) | **How must code be left after ANY write/edit/fix/refactor?** Clean of leftovers (`no-dead-code`), one authored source per fact and behaviour (`no-duplicate`), one responsibility per file with size as a smell only (`no-monolith`), a fix that lands at the origin the root-cause statement named, the band-aid deleted, a default legal only where the contract permits absence (`no-patches`). Own-change violations are fixed in the same change; pre-existing ones are surfaced, never fixed unasked. |
| `improve-codebase-architecture` (skill) | **Where is this codebase shallow, and what would deepen it?** An on-demand scan → HTML report of deepening candidates → grill on the one picked; the deep-module vocabulary is inlined. |
| `commit` (skill; drives the `tool/commit.py` script) | **How are changes persisted to git?** The agent clusters changes and drafts messages; the deterministic script owns every git mechanic in one invocation per commit — remote sync, staging gate, pathspec-bounded commit, optional push. Carries the merge-conflict procedure inline. Subject note: commit persists changes of ANY kind, not only code — homed here by owner ruling (2026-08-23) as the closing act of leaving work behind, migrated from the rbtv repo's pre-component `core/` module root. |

Boundaries: `core/behaviour/kiss` decides WHETHER to build and how simply, BEFORE the work; the
`coding` skill governs the code AFTER. `core/behaviour/root-cause` (always-on) is the ONE home of
the written root-cause statement, the sibling sweep, and the origin test; `no-patches` carries only
the code PROCEDURE of the edit that follows. `_skills/ponytail` is an opt-in intensity mode, not a
discipline.

**Panel review 2026-08-23** (3 panelists, 3 providers; run folder kept in the authoring session's
scratchpad): convergent fixes applied — no size tripwire in `no-monolith`, the root-cause statement
has one home (owner-ruled: the always-on rule, not the skill), the occupant loopholes closed (origin
test, default-vs-masking, sameness test, no-touch deadlock), the architecture prompt carries
`human-interactive` + `exposes:`.

## Entry points

- `references/coding.md` — the `coding` skill's body; `references/no-dead-code.md`,
  `no-duplicate.md`, `no-monolith.md`, `no-patches.md` — the four disciplines it reads (no exposure
  rows of their own: reached only through `coding`); `references/architecture-report-format.md` —
  the HTML report format the architecture skill reads.
- `references/commit.md` — the `commit` skill's body (procedure + merge-conflict arm, one file);
  `tool/commit.py` — the deterministic commit script it drives (self-documents via `-h`;
  `tool/test_commit.py` is its test suite).
- `prompts/improve-codebase-architecture.md` — the architecture skill.
- `exposure.csv` — three `skill` rows plus the `rbtv-commit` tool inventory row.

**ORIGIN 2026-08-23.** Owner interview. `improve-codebase-architecture` is a FORK of
`github.com/mattpocock/skills` (`skills/engineering/improve-codebase-architecture` +
`codebase-design`, whose seven-term vocabulary is inlined), adapted to rbtv: the codebase's own
design sources (`component.md`, `decisions.md`, the knowledge graph) in place of `CONTEXT.md` /
`docs/adr/`, sub-agents through `cast route`, the `interview` skill for the grill, the HTML report
kept. Never re-synced — deliberately absent from `_skills/skills-repos.md`. The upstream siblings
(diagnosing-bugs, domain-modeling, code-review, tdd, implement, prototype, to-spec, to-tickets,
triage, wayfinder, wizard, research, resolving-merge-conflicts, grill-with-docs) were considered
and DROPPED by owner ruling the same day — not forked, not tracked.
