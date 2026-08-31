# 20260831-c-plan-envelope-artifact-writer — plan-envelope artifact writer

kind: creation
component: planning
date: 2026-08-31
commit: 071687e7
deployed: no
pin: ignite/planning/probes/probe-plan-envelope.py
components: envelope

## Motivation
Path-B birth (`path_b.bound_envelope_fillins`) reads `<plan-artifacts>/envelope.json` from the bound commit. Until this landing nothing in planning wrote that file, so every birth copied nothing and every caged seat compiled `credentialNames: []` (`G-plan-designer-0828-1815`).

## Design
A small writer next to `approve_package.py`, one responsibility: validate and atomically write the fill-ins object the compiler already reads. CLI `--credential-name` (repeatable) plus optional `--from-json` for the other fill-in keys. Shape-check only: env-var names, extraPaths `rw|ro`. Values are resolved at launch by `admitLaunch`/`resolveCredentials`, not here — a planning seat must be able to author the declaration before the store is consulted. Rejected: stuffing `credentialNames` into `approve_package.py` OPTIONAL_KEYS (second source; the birth already reads the bound artifact). Rejected: parsing plan prose.

## How it works
`write_plan_envelope(plan_artifacts, fillins)` validates via `build_fillins` and writes `<plan_artifacts>/envelope.json` through coord's `atomic_write`. A planning seat runs it before taking the bound commit. `path_b.bound_envelope_fillins` then `git show`s that path; `_land_envelope` copies it onto the born goal. A plan that needs no secrets writes nothing and births as before.

## Consequences
`path_b.py` and `approve_package.py` are byte-unchanged. Pipeline prompts are not yet told to invoke the writer — a planning seat that never calls it still produces an empty name list. That is a prompt gap, not a second writer.

## Verification
`python3 -B ignite/planning/probes/probe-plan-envelope.py` 5/5 PASS on `071687e7`: writer authors `["ELEVENLABS_API_KEY"]`, a scratch git commit carries it, `bound_envelope_fillins` reads it back, a bad name refuses `bad-credential-name`, an absent artifact returns None. Not deployed.

## ATTENTION
1. The file is read from the bound commit, never the working tree. Authoring it after `approve-package.json` names a SHA does not put it in that SHA.
2. Do not resolve store values in this writer — a missing key must still be declarable so `admitLaunch` can refuse at launch, which is the documented gate.
3. Empty fill-ins are refused (`empty-fillins`). A plan with no secrets should not write the file at all, matching `_land_envelope`'s absent-artifact no-op.
- The file is read from the bound commit, never the working tree
- Do not resolve store values in this writer
- Empty fill-ins are refused; a plan with no secrets should not write the file
