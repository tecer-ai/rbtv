---
description: decision procedure for authoring the restrictions section of a prompt file
tags: [planning]
---

# `<restrictions>` — the enforced prohibitions

Record first: `sd-graph show restrictions`. It rules meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

Bounds that leave nothing to judgment: prohibitions machinery enforces and the occupant cannot override, however the session goes.

## why it exists

Some acts must be impossible, not discouraged. A prohibition carried as prose depends on the model honoring it; a restriction is materialized into enforcing machinery (harness config for the prompt part), so violation is blocked, not resisted.

## when one exists at all

Every prompt carries exactly one section (`sd-graph show "cognitive unit"`, Requirement matrix). The judgment call is per PROHIBITION — each row earns its place by naming an act that (a) the occupant could otherwise perform under its grants and (b) must never happen.

## what belongs — and what never does

Belongs:

- Prohibitions machinery can enforce without the model's judgment: never push, never write outside the stated allowlist, no destructive resets, no external production calls.
- Bans on acts the permissions grant would otherwise allow — restrictions carve the granted surface, they do not restate its edges.

Never:

- Grants — what MAY be done is the `<permissions>` kind.
- Bounds only judgment can honor ("preserve the author's voice", "reorganize, never rewrite") — those are the `<constraints>` kind. This is the enforcement-locus test, and it is the whole classification.
- Prohibitions of acts the occupant could never perform anyway — a ban on the ungrantable is ceremony.
- Method or sequencing — an ordered "do X before Y" is procedure, not a prohibition.

## how to write an optimal one

1. Sort every candidate bound with the enforcement-locus test: can machinery enforce it with no judgment? Yes → here. No → move it to `<constraints>`. Never let one bound sit in both.
2. Phrase each as a flat prohibition of a concrete act — enforceable means checkable: name the act, not the attitude.
3. Cross-check against `<permissions>`: each restriction should bound something actually granted; prune the rest.
4. Keep the list short and absolute. A restriction with an exception clause is either two bounds or a constraint in disguise.
5. Keep it use-case-neutral — the same prohibitions must hold for an ad-hoc goal, an optimize, a port, or a scaffold run unmodified.
