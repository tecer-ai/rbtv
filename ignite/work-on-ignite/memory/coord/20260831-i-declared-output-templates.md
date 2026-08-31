# 20260831-i-declared-output-templates — declared-output-templates

kind: issue
component: coord
date: 2026-08-31
commit: 4796a716
deployed: no
pin: ignite/coord/probes/probe-outputs-template.py
components: planning,envelope,meta-planning

## Observed

Four ignite-engine register filings (G-plan-planner-0822-1713, G-plan-2-plan-planner-0822-2053, G-plan-4-plan-resource-definer-0822-2338, G-console-master-0822-1613) were one class: a seat that had produced its real files could not check out `done`. The planner that wrote all six `findings-{edges,resources,permissions,scope,clarity,consistency}.md` was refused for a missing file literally named `findings-<dimension>.md`. A resource-definer that wrote `deltas-plan-4-plan-resource-definer-round-1.md` was refused for the unexpanded `deltas-<seat-id>-round-<n>.md`. Completeness-reviewer and dag-structurer materialized with `outputs-undeclarable` because `goal.md` / `milestones.csv` carry no slash. Confirmed on disk 2026-08-23 as a workaround file `findings-<dimension>.md` in ignite-engine's planning archive. Rolling-planning seats were later retired (6318207d); the grammar class still reproduced on fixtures at HEAD 4796a716, deploy copy untouched.

## Mechanism

`iospec_outputs` / `PATHISH` accept any backticked token with a `/` and an extension, including ones that still contain `<placeholder>`. D36 projects that literal string into `## Outputs`. `declared_outputs` then asks the filesystem for that exact path. No expansion, no conditionality. Zero matches of a slashless backtick (`forge-spec.md`) is a different spelling of the same rule: `_IOSPEC_PATHISH` demands a `/`, so materialize warns `outputs-undeclarable` and checkout records unverified. D90 already made `./name.md` the sanctioned goal-root form; live forge Write clauses had not adopted it.

## Attempts

D36 (`ee64adde`, memory `engine/20260820-c-outputs-declared-at-gate`) projected Write: tokens into Outputs but left PATHISH unchanged, so placeholders still projected as filenames and slashless names still projected nothing. D90 (`ffdf2dc2`, memory `team-kit/20260822-c-goal-root-relative-outputs`) added a goal-root candidate for `./name.md` only; `_IOSPEC_PATHISH` still demanded a `/`, and `<dimension>` was still a literal. D41 accepted leftover undeclarable seats as authoring-side. First attempt that holds: treat `<…>` as a template at the grade, and refuse it at materialize so a new descriptor cannot project one.

## Fix

Grammar side, not a six-name list in the checker. `is_output_template` (one helper in `outputs.py`) is true when a declared path still carries `<…>`. `declared_outputs` skips those tokens in the missing list; `stamp_checkout_ending` does not hand the literal string to the ending store (empty declared_outputs is ok). Materialize raises `outputs-placeholder` after D36 projection so the class is loud at the cheap moment. Rejected: expanding `<dimension>` to a hardcoded six-file list (planner-domain knowledge in the path grammar). Rejected: widening PATHISH to slashless names (the `backticked-but-slashless` fixture exists so prose `exposure.csv` does not become an output). Live forge tasks/prompts spell `./forge-spec.md` and `./forge-build.md`, the D90 form.

## Consequences

Already-rendered descriptors that still declare a template can check out `done` without minting a placeholder file. A new materialize of such a declaration refuses. Two archive workaround files named `findings-<dimension>.md` were deleted (ignite-engine m2-pass, granted; stools-canvas-audio-elevenlabs archive, found by glob). PATHISH itself is unchanged; both parsers still extract the placeholder as a token (shared fixture `placeholder-path-is-still-a-token`).

## Verification

`python3 -B ignite/coord/probes/probe-outputs-template.py` 5/5 (six real findings files + no literal → done; deltas template with no file → done; deltas template with the real round-1 file → done; mutant that restores the literal demand → failed/outputs-missing). `node ignite/deploy/probe-suite.js --only probe-outputs-resolver --only probe-outputs-template` GREEN. Materialize `--selftest` arm `outputs-placeholder` ok (suite later aborted on a pre-existing EndingStoreError in staff-mint, not this arm). Coord selftest: the three tmplhit/tmplmiss/tmpldelta rows ok; suite exit 1 is 25 pre-existing FAILs none of which name those arms. Deployed no.

## ATTENTION

- PATHISH still matches a `<placeholder>` token. Checkout skips it; materialize refuses a new one. Changing only one of those two leaves the class half-fixed.
- Never mint a file whose name is the unexpanded template (`findings-<dimension>.md`). The six real files, or a `./name.md` declaration, are the product.
- Slashless backticks (`forge-spec.md`) are still not tokens. The sanctioned goal-root spelling is `./name.md` (D90). Do not widen PATHISH to admit them — that would harvest prose filenames.
- PATHISH still matches <placeholder>; checkout skips, materialize refuses — change only one and the class is half-fixed
- Never mint findings-<dimension>.md; six real files or ./name.md are the product
- Slashless backticks are not tokens; use ./name.md. Do not widen PATHISH
