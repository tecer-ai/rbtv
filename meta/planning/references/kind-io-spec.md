---
description: decision procedure for authoring the io-spec section of a prompt file, including its input, outcome, and output sub-kinds
tags: [planning]
---

# `<io-spec>` — the declared contract

Records first: `sd-graph show "i/o spec"` · `sd-graph show outcome`. The records rule meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

An interface a stranger can consume: what this prompt (or capability) takes, what it stands for, what it hands back — declared up front, never discovered by reading the procedure.

## why it exists

Seats connect through their declared surfaces. Planning wires edges, staffs teams, and judges output against declarations — an undeclared contract makes every one of those acts a guess.

## when one exists at all

Every prompt and every capability carries one (`sd-graph show "cognitive unit"`, Requirement matrix). A task NEVER does: the run's concrete question, inputs, and output destination are instance data arriving with the seed — putting i/o fields on a task file is a defect, not a variant. On-disk home differs by carrier: a prompt's spec is its `<io-spec>` section; a capability's is frontmatter on its instruction file.

## what belongs — and what never does

Three sub-kinds, all inside this one section (input · outcome · output are indented sub-kinds of i/o spec in the requirement matrix — no top-level sections of their own, no separate guides):

- **input** — TWO separate parts: a SCHEMA (the format the material takes) and a DESCRIPTION (what that material carries).
- **outcome** — the standing objective the reusable prompt serves across every task. The outcome IS a done contract at the prompt radius: it must state observable done-criteria a verifier could judge against.
- **output** — schema and description again, two parts, for what is produced.

Never: one undifferentiated field per direction (the record calls that a defective spec) · run-instance values (seed-carried) · method steps (procedure) · quality prose that names no observable criterion.

## how to write an optimal one

1. Write each direction as schema + description, separately. If you cannot state the schema, you do not yet know the interface — stop and find out.
2. Write the three sub-kinds as three headings inside the section, and no other way: `## Inputs`, `## Outcome`, `## Outputs`. Inputs and Outputs carry one `- Schema: … Description: …` bullet per declared thing; Outcome carries prose. **The Outputs section IS READ BY MACHINE** — the edge runner takes EVERY backticked token carrying a `/` and an extension as a DECLARED ARTIFACT, verifies each one exists on disk before the seat is marked done, and reads routing-guard fields off the `.json` ones. A prose bullet the parser cannot read declares NOTHING, however clearly it reads to a human; and a seat that declares nothing satisfies no guard, so every fork over it stays unevaluable and blocks forever. Declare the artifact by its path, backticked, or it does not exist. **Paths are GOAL-RELATIVE** (`planning/current/findings-clarity.md`), the base both readers use; a seat-private file is written `./name.md`.
   - **You do NOT write the concrete destination here, and you must not** (rule 5: this spec serves every task the prompt will ever serve). The MATERIALIZER projects it: at render it reads the paired TASK's `<scope>` `Write:` clause and appends `- Destination (projected from the task's scope Write clause): \`<path>\`` into this section (D36, 2026-08-20). Your job is the schema + description bullet; the task's job is to name the file in its `Write:` clause, backticked, with a `/` and an extension — a slashless name (`task-dag.md`) projects NOTHING and the seat's `done` stays unverifiable.
   - **A seat that produces NO FILE declares `- Schema: chat …`** — the one typed non-file output (D36). It says the product is conversation: a verdict row on the bus, an answer, a `queue-request`. The check-out then admits that `done` (`none-declared`) and the render-time zero-token check stays quiet. It is SCHEMA POSITION ONLY: the word `chat` elsewhere in the prose declares nothing. Never write it on a seat that does produce a file — it turns off the one check that grades the seat's work.
3. Where an output is a `.json` artifact a downstream guard reads, NAME each of its top-level fields as a backticked bare token in the SAME bullet that declares the artifact — "a JSON object with exactly one top-level string field, `use-case`". The field surface is JSON top-level scalars only; that naming is what the fork-discharge lint checks the guard's key against.
4. Write the outcome as a falsifiable standing aim: "produce a cited answer to whatever is asked" passes; "be helpful and thorough" is a mood, not an outcome.
5. Keep it definition-side: the spec must hold for EVERY task this prompt will ever serve — anything true of only one run belongs in the seed.
6. Cross-check the procedure: every input the steps consume is declared; every declared output some step produces. An orphan on either side is a defect.
7. Keep it use-case-neutral — the same spec must serve an ad-hoc goal, an optimize, a port, or a scaffold run unmodified.
