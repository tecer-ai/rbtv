# 20260824-c-plan-sizing-law-measure-before — plan sizing law: measure before authoring

kind: change
component: meta-planning
date: 2026-08-24
commit: b1151618
deployed: no
pin: NONE

## Motivation
The plan format's 40%-of-context seat ceiling was a declared sentence, not a measured act: the 2026-08-24 redesign-implementation review found all ten impl seats over budget (typically 2–4×) even though every body carried the ceiling clause. The rule needed the discipline that makes it bind at authoring time.

## Design
Four bullets added to `meta/planning/references/plan.md` § Sizing and parallelism: (1) the ceiling is MEASURED before authoring — estimate the read set against the real tree (`wc -l` the files, count gate reads) plus writing plus verification; (2) one work stream per seat, split at the spec's own seams with explicit DoD-clause reallocation; (3) whole-suite verification once per chain, in the terminal seat; (4) a custody line for every file two sub-seats would both edit. Alternative rejected: lowering the percentage — the number was never the defect, the missing measurement was.

## How it works
A planner authoring a seat body now has a falsifiable pre-step: the workload estimate. The added text cites the measured 2026-08-24 failure so a future editor does not soften it back into advice.

## Consequences
Plans authored through the `plan` skill produce more, smaller seats (the redesign plan went 10 → 33). No code or installer surface changed.

## Verification
Text landed in commit b1151618 (single file, +4 lines); read back in place. Not a runnable surface — no probe.

## ATTENTION
- The ceiling percentage is unchanged on purpose: the defect was unmeasured authoring, not the number. Do not "fix" a future oversize by lowering the number without measurement discipline.
- The 40% number was never the defect; unmeasured authoring was
