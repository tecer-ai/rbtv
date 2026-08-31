# 20260831-c-plan-format-judge-seats-craft — plan format: judge seats, craft bindings, per-file custody

kind: change
component: meta-planning
date: 2026-08-31
commit: 719b1113,8f583178
deployed: no
pin: NONE

## Motivation
The plan format told a plan's author how builders are shaped and how the OWNER verifies (checkpoints), but carried no machine-side verification and no binding to the craft references. In a live 66-task plan the owner declined checkpoints and separately had to ask for (a) judge seats so checks run without him, (b) the coding/build references to bind every seat, and (c) more parallelism — all three should have come from the format itself.

## Design
Three additions to `meta/planning/references/plan.md`, owner-directed 2026-08-31. (1) A new § Judge seats: judges are ALWAYS CONSIDERED and created when the plan warrants (shared-surface clusters, high-stakes changes, go-live windows) — cluster judges at critical points, an optional go-live sweep judge per deploy window, and a final judge issuing plan ACCEPT/HOLD; never one judge per seat by default, never final-only on a deep plan. The judge bar: re-run every machine-checkable DoD command itself, probe untested edges, re-run stale-claims' reproductions, check diffs against the craft bindings, read-only, actionable FAIL findings; verdicts to `judgements/<judge>.md`. Orchestrator flow: reports saved to `seats/<name>/report.md`, light sanity only, judge FAIL → resume the builder with findings, two FAILs → owner ask. (2) The craft bindings live in read-first.md: code seats read `core/coding/references/coding.md` before the first edit; scaffolding seats route through `meta/planning/references/build.md` incl. its section-0 reads. (3) Custody lines are per-FILE and re-derived from the authored bodies' real edit sets before handover — pre-authoring subsystem-level custody is provisional. Rejected alternative: per-seat judges (2x cost, no cross-seat integration view) and a single final judge (foundation breakage found under later layers).

## How it works
`plan.md` § Judge seats carries the shape, bar, and orchestrator flow; § Owner checkpoints cross-references it as the machine-side counterpart (an owner declining checkpoints on a deep plan is offered judges); the plan-folder tree adds `judgements/`; the read-first section adds the craft-bindings bullet; the self-check gains items 10 (bindings present) and 11 (judges considered, or a one-line "none, because"); the sizing bullet's custody rule now mandates the per-file narrowing pass.

## Consequences
Replaces nothing; extends the format the 2026-08-24 sizing-law entry hardened. Plans authored from this reference now surface judge/craft/custody decisions without owner nudges. First consumer: the redesign-continue-1 plan (vault-side), which carries all three by hand and validated the shape (52 seats, 3 cluster judges + deploy sweep + final judge, per-file custody).

## Verification
No probe — a reference file. Verified by re-read of the four edited sections and by the consuming plan's `cast seat --dry-run` × 52 exit 0 (format unchanged for cast). Deployed: not a daemon surface — a meta/ reference read from the repo; it reaches consumers on the next plan-authoring read, no deploy or install step involved.

## ATTENTION
1. Judge CONSIDERATION is mandatory, creation is not — a small plan states "no judges" in one line beside the checkpoint statement; silently omitting the consideration is the defect this entry exists to prevent.
2. Judges verify seats against their OWN DoD — a judge that re-litigates settled rulings (canonical-source choices etc.) turns verification into re-planning; design disagreements are notes, not FAILs.
3. Custody drafted before seat bodies exist is a guess — the re-derivation pass from real edit sets is part of the format now; skipping it over-serializes (measured: 8 subsystem groups → per-file rows freed 5+ seats).
- Judge consideration is mandatory on every plan; creation is a judgment call recorded in one line when declined
