---
description: decision procedure for authoring the permissions section of a prompt file
tags: [planning]
---

# `<permissions>` — the grant

Record first: `sd-graph show permissions`. It rules meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

The smallest sufficient grant: everything the occupant's method actually needs, and not one surface more.

## why it exists

Permissions are enforced by machinery — the declaration is materialized into harness config, and it is the SOLE grant channel: an occupant's effective scope widens only by editing this declaration, never by a message's file link and never by dispatch-time packing. What is not granted here does not exist for the occupant.

## when one exists at all

Every prompt carries exactly one (`sd-graph show "cognitive unit"`, Requirement matrix). The judgment call is per GRANT: each row exists only because a procedure step needs it.

## what belongs — and what never does

Belongs:

- Read scope and write scope — the files and directories the occupant may touch, stated harness-agnostically (the machinery translates per harness).
- Command-line scope — which commands and tools the occupant may run.

Never:

- Prohibitions — "must not" rows are the `<restrictions>` kind, not negative grants here.
- Judgment-honored bounds — machinery cannot enforce them; they are the `<constraints>` kind.
- The tools themselves or how to use them — availability is the `<resources>` part; method is the `<procedure>`.
- Grants "to be safe", "for flexibility", or for work some future task might add. A grant no step needs is a defect now, whatever later needs.

## how to write an optimal one

1. Derive from the procedure, step by step: list what each step reads, writes, and runs. That list IS the grant — nothing enters it without a step to point at.
2. State write scope tighter than read scope; writing is where damage lives.
3. Ask, for every row: which step fails without this? No answer → delete the row.
4. Check the seat's agent type (`sd-graph show "agent type"`) — the type drives part of the permission set; do not contradict it.
5. Keep it use-case-neutral — the grant serves the prompt's method, not any one run; run-specific surfaces arrive via the task's `<scope>`, not by widening this grant.
