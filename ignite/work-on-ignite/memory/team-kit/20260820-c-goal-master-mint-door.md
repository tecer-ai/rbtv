# 20260820-c-goal-master-mint-door — goal-master-mint-door

kind: creation
component: team-kit
date: 2026-08-20
commit: 1dd5d907,aa1920a8,61ce15d9,288de5d3,eda7e4c7
deployed: yes
pin: team-kit/probes/probe-staff-wiring.py;reconcile.selftest.js D24 arms
components: engine
seeded: true

## What it is
Closes the goal-master READY hole: a minted goal-master no longer counts ready-to-dispatch until summoned.

A summoned chair's row now closes silently instead of demanding verified outputs; D29's narrow "summoned seats only" exemption was widened by D30.

## Why
D24: a minted-but-not-yet-summoned `goal-master` was showing up as READY in `coord.py ready-seats`, which let the daemon fire a chair nobody had actually asked for. D29 then found that a summoned chair (one that only exists to answer, not to produce artifacts) was being held to the same verifiable-outputs done-check as a normal seat — wrongly, since it has no declared outputs to verify. D30 widened D29's fix from summoned-only to the broader `CONVERSATIONAL_CHAIRS` predicate, and folded in two more loose-end fixes (owed-answers-halts via a union of `open_escalations`, and delta-anchors).

## How to use & where wired
`ignite/team-kit/coord.py` (`CONVERSATIONAL_CHAIRS`, `close_staff_mail_arm`), `ignite/team-kit/materialize-seats.py` (D24 mint door — summoned seats join the first taskforce), `ignite/engine/reconcile.js` (a summoned seat is never counted as owed work). Commits: `1dd5d907` (D24 — minted goal-master reads IDLE, not READY), `aa1920a8` (materialize: summoned seats join first taskforce), `61ce15d9` (reconcile: a summoned seat is never owed work), `288de5d3` (a conversational chair may record done; a summoned chair's row closes silently — D24 second-enforcer fix, also D30's chair-closure), `eda7e4c7` (D29 — exempt summoned chairs from checkout outputs verification).

## commit
1dd5d907,aa1920a8,61ce15d9,288de5d3,eda7e4c7

## deployed
yes

## pin
team-kit/probes/probe-staff-wiring.py (D24/CONVERSATIONAL_CHAIRS-annotated); reconcile.selftest.js D24 arms (wrapped by probe-reconcile.js)

## ATTENTION
- D29's own narrow SUMMONED_SEATS-only exemption has no dedicated pin — it was almost immediately absorbed by D30's `CONVERSATIONAL_CHAIRS` predicate; check the D30/D24 pin for current behavior, not a D29-specific one.
- D30 also folds in owed-answers-halts (union of `open_escalations`) and delta-anchors — those live in different files (`owed-answers.py`; `.rbtv/mirror/meta/planning/capabilities/delta-anchors/`, vault-tracked with its own `test_delta_anchors.py`, not in rbtv probe-suite scope).
- D29's narrow exemption has no dedicated pin; check D30/D24 CONVERSATIONAL_CHAIRS pin instead
- D30 also folds in owed-answers-halts and delta-anchors, in different files/repos
