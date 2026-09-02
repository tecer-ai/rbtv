# 20260902-i-planning-drafter-never-calls-t — planning drafter never calls the envelope writer

kind: issue
component: meta-planning
date: 2026-09-02
commit: 94fe1f25da66ad21afadb26f329fc6d91fe08dff
deployed: not-applicable
pin: NONE

## Observed
`meta/planning/prompts/drafter.md` (the AI instructions guiding the plan-authoring step) already
told the drafter to write a "credential-name manifest" as prose inside the plan document, but never
told it to run `plan_envelope.py` (the tool that turns that prose into the real
`planning/envelope.json` file the birth process reads). Result: a plan that declared credentials
still birthed a goal with an empty `credentialNames` list and no working secret injection. This
exact gap was named as a known, unfixed consequence in the writer's own creation entry
(`planning/20260831-c-plan-envelope-artifact-writer.md`, commit `071687e7`: "Pipeline prompts are
not yet told to invoke the writer — a planning seat that never calls it still produces an empty name
list. That is a prompt gap, not a second writer.") and surfaced again in loose-ends.md (`redesign-
continue-1`, ~line 107, seat `planning-envelope-prompts`).

## Mechanism
The planning pipeline's step sequence had a producer (`plan_envelope.py`) with no caller.
`drafter.md` stopped at writing the manifest as prose; nothing after that step invoked the writer
before the leader took the bound commit. `verifier.md`'s existing checks never compared the plan's
declared credential names against the actual contents of `planning/envelope.json`, so a plan that
skipped the writer step passed verification anyway.

## Attempts
First attempt held — checked: `planning/20260831-c-plan-envelope-artifact-writer.md` (071687e7,
built the writer itself, explicitly left the prompt wiring undone) and
`envelope/20260831-i-declared-secrets-never-reached.md` (071687e7, fixed the launch-time consumer
side — `admitLaunch` calling `resolveCredentials` — but did not touch the planning-pipeline
prompts). Neither entry wired the drafter or verifier to the writer.

## Fix
`drafter.md` gains step 5b: where the credential-name manifest of step 5 names at least one name,
author `planning/envelope.json` now, before the leader binds, by running `plan-envelope --plan-
artifacts planning --credential-name <name>` once per declared name. `verifier.md` gains a new check
(c): every name in the revised plan's credential-name manifest must actually appear in
`planning/envelope.json`'s `credentialNames`; a manifest name missing from the file fails
verification.

## Consequences
Closes the prompt gap the writer's own entry (071687e7) flagged as known and unfixed. Does not touch
`plan_envelope.py`, `path_b.py`, or `admitLaunch` — those are unchanged. One disclosed narrow gap
remains: if the reviewer's revision pass changes the credential-name manifest, `verifier.md`'s on-
fail-relaunch re-fires `review+finalize` then `verify`, but `reviewer.md` (out of this fix's scope)
does not call `plan-envelope`, so a FAIL from the new check in that specific scenario cannot self-
heal and rides out the 2-pass cap to a red-flagged digest. In practice the reviewer's own scope
never invents new credential names, so this is currently inert.

## Verification
Proved end-to-end on a disposable test fixture (the daemon only runs deployed prompt files, not
uncommitted repo edits, so this could not be proven through a live goal): a fake plan declared
`TEST_FIXTURE_TOKEN`/`TEST_FIXTURE_SECRET`; following the drafter's new step 5b verbatim produced
`planning/envelope.json` matching the plan's declaration exactly; committing that fixture and
reading it back via `git show <bound-commit>:planning/envelope.json` confirmed the birth mechanism
sees the same file. Red/green on the new verifier check: before running the drafter step, check (c)
failed with `manifest names [...] missing from planning/envelope.json`; after running it, check (c)
passed. Not deployed — `meta/planning/` prompts become live only on the next deploy the orchestrator
runs.

## ATTENTION
1. A plan that declares credentials must run the drafter's step 5b BEFORE the leader takes the bound
   commit — writing `envelope.json` after `approve-package.json` names a commit does not put it
   in that tree (same trap named in `envelope/20260831-i-declared-secrets-never-reached.md`). 2.
   `reviewer.md` does NOT call `plan-envelope` — if a future change lets the reviewer alter the
   credential-name manifest, this gap reopens and needs its own fix. 3. This closes only the
   prompt-wiring gap; `plan_envelope.py` itself, `path_b.py`, and
   `admitLaunch`/`resolveCredentials` are unchanged and already covered by prior entries
   (071687e7).
- closest entries (071687e7 writer, envelope consumer) name the prompt-wiring as unfixed
