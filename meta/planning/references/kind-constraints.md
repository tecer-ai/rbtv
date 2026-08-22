---
description: decision procedure for authoring the constraints section of a prompt file, including the shared-ethos carry
tags: [planning]
---

# `<constraints>` — the judgment-honored bounds

Record first: `sd-graph show constraints`. It rules meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

Conduct: standing invariants that shape HOW the occupant works, across every step, without prescribing any step — honored by the model's judgment, because no machinery can enforce them.

## why it exists

Some bounds cannot be enforced ("preserve the author's voice"; "never create information, only transcribe") yet must hold everywhere. The constraints section is their one home in the prompt; they reach the occupant as prose, never as config.

## when one exists at all

The ONE optional bound-kind: the requirement matrix (`sd-graph show "cognitive unit"`, Requirement matrix) permits it, never demands it. Author it only when a real judgment-honored invariant exists — an empty constraints section is correct for a seat with none, and padding one with restated rules is context tax. Exception: a prompt designated as an ethos carrier ALWAYS has one (below).

## what belongs — and what never does

Belongs:

- Invariants on conduct that hold across every step and prescribe none.
- **The shared ethos, for carrier prompts:** the block between `<!-- ethos:start -->` and `<!-- ethos:end -->` in `references/ethos.md`, copied VERBATIM into a section opened exactly as `<constraints source="references/ethos.md">` — the `source` attribute marks the carried copy, and a deterministic drift check diffs every copy against the source and fails loud on mismatch. Which prompts carry it, and which are excluded, is stated in `references/ethos.md` — check there, never from memory.

Never:

- Machine-enforceable bans (the `<restrictions>` kind — enforcement locus is the whole test) · grants (permissions) · ordered steps (procedure) · heuristics and how-to guidance (procedure) · outcome-quality bars (the outcome, under the i/o spec).
- A reworded or trimmed ethos copy — verbatim or absent; the drift check makes anything else a loud failure.

## how to write an optimal one

1. Test each candidate: does honoring it take the model's judgment? If machinery could enforce it, move it to `<restrictions>`.
2. Test its reach: does it hold across every step? A bound tied to one step belongs in that step.
3. Write each as a direct instruction in the seat's own words — never as a KG citation the occupant must look up.
4. Keep the set small: every constraint rides in context on every act of the occupant's work.
5. For ethos carriers, paste the block verbatim BETWEEN its `<!-- ethos:start -->` / `<!-- ethos:end -->` marker lines inside the section opened with the `source` attribute — the drift check diffs exactly the marker-delimited region, and a carrier without the markers fails it. Seat-specific constraints, if any, go BELOW the end marker inside that SAME section — never a second `<constraints>` section (one section per kind).
