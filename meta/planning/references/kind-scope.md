---
description: decision procedure for authoring the scope section of a task file
tags: [planning]
---

# `<scope>` — the task's surfaces

Record first: `sd-graph show scope`. It rules meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

The smallest context slice that lets the task complete: exactly the surfaces the work needs — read and write named separately — and nothing more.

## why it exists

The scope is what selects the context a session receives. Every surface it grants rides in the occupant's attention for the whole run, and every write surface is exposure. Unnamed surfaces get improvised; over-named ones get paid for on every step.

## when one exists at all

Every task carries exactly one (`sd-graph show "cognitive unit"`, Requirement matrix). The judgment call is per SURFACE: a surface exists in the scope only because reaching the done contract needs it.

## what belongs — and what never does

Belongs — the two halves, always stated separately:

- **Read surfaces** — the references and locations this task may consult.
- **Write surfaces** — the workbench this task may change.

Never:

- The role's standing remit — that is the role-level scope facet, on the prompt side; THIS scope is one task's radius.
- Grants and bans of acts — permissions and restrictions are prompt-serving, installed into harness config; scope selects surfaces per task.
- Run-instance paths — the concrete destinations of one run arrive with the seed; the scope names surface KINDS reusable across runs ("the goal folder", "the subject workflow's folder").
- Instructions or method — nothing in a scope tells the occupant what to do.

## how to write an optimal one

1. Derive from the done contract: list what must be read to produce the outputs, and where the outputs land. That list is the scope — start from need, never from availability.
2. State write surfaces tightest: a task that writes one file names one file's home, not its directory tree.
3. Ask, per surface: what in the contract fails without it? No answer → cut it. A "for context" surface is context tax.
4. Phrase surfaces by role, not by run, so the same task file serves every use case — ad-hoc goal, optimize, port, scaffold — unmodified.
5. Cross-check the paired prompt's permissions: a scope surface outside the prompt's grant is a seat that cannot run — fix the pairing, not the occupant.
