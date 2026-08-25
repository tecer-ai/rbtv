---
description: "Five Whys — trace one concrete problem down a causal chain to a structural root cause, labelling every link as fact or hypothesis, and separating what will be targeted from what will not."
tags: [conception]
---

# Five Whys

Five Whys traces a visible problem to its structural root cause by asking "why is this
happening?" repeatedly and recording each answer as a link in a causal chain. Use it as the
final conception framework, after the customer, job, solution fit, and business model exist:
it takes the problem statement they produced and finds the cause underneath it, which is what
determines whether the solution attacks the problem or its symptom.

## The chain

Every chain starts from a concrete **anchor problem statement** and iterates.

| Level | Element | Worked example |
|---|---|---|
| 0 | Anchor problem statement | "Trial users from segment X don't complete onboarding within 7 days" |
| 1 | First why | "They abandon during the data import step" |
| 2 | Second why | "Import requires manual formatting they don't have time for" |
| 3 | Third why | "Our import expects clean CSV but their data is fragmented across 4 tools" |
| 4 | Fourth why | "Nobody in their organization owns data consolidation — it is everyone's problem and no one's job" |
| 5 | Root cause | "Organizational structure treats data consolidation as overhead, not value creation" |

Each level records the why question, the answer, a **Fact / Hypothesis** label, the evidence,
and notes. A Fact is supported by data or observation; a Hypothesis goes to the validation
backlog.

**Stop when** the chain reaches a structural cause (incentives, processes, constraints) that
explains the symptoms above it; or further whys only restate the same idea in different
words; or the chain hits a knowledge frontier where every further answer is untestable.

## Session rules

State these at the start of every session: focus on THIS scenario only and park other
scenarios for their own chains; blame processes, structures, incentives, and assumptions —
never individuals; each answer must be a direct cause of the previous answer, not a different
problem; label every answer Fact or Hypothesis; stop at a structural cause that can be acted
on.

## Root-cause categories

Cluster the chain endpoints: customer behaviour and context (habits, incentives, skills,
workflows); product and user experience (discovery, onboarding, feedback loops); business
model and pricing (misaligned incentives, long approvals); go-to-market and channels (wrong
decision-maker, weak trust signals); organization and operations (internal bottlenecks
slowing iteration); external constraints (regulation, vendor lock-in, platform risk).

## What a good output contains

- **Problem framing:** three or more real organizations or people who fit the scenario can be
  named; the anchor problem statement is traceable to the press release, the job statement,
  the fit canvas, or the business-model canvas; exactly one scenario is being analyzed and
  the others are explicitly parked.
- **Chain quality:** each chain is a linear sequence of causes with no topic jumps; every
  answer is labelled Fact or Hypothesis with its evidence noted; at least one chain reaches a
  structural cause — "users don't care" and "the team is slow" are not structural causes.
- **Synthesis:** at least one root-cause statement that is non-obvious compared to the
  starting problem; each targeted root-cause hypothesis linked to the specific behaviour or
  metric it would change; and at least one **non-targeted** root cause documented — what is
  deliberately not being tackled in the first version.

## Pitfalls

Stopping at three whys — push at least one chain to a structural cause uncomfortable enough
to be worth writing down. Blaming people instead of systems, policies, and incentives. Mixing
problems instead of forking a new chain. Ignoring evidence: prioritize the chains supported
by real behaviour or metrics. Treating the analysis as a one-off ritual rather than a living
document updated as assumptions get validated. Starting from an unbounded topic instead of
narrowing to a specific scenario, metric, or segment.

## Builds on / feeds

Builds on Working Backwards, Jobs-to-be-Done, and a first Lean Canvas draft, and takes its
anchor problem from Problem-Solution Fit. Owns the root-cause structure and is the terminal
framework for causal analysis. It refines the Lean Canvas Problem block and Key Metrics, and
its targeted root-cause hypotheses seed the validation milestone's Leap of Faith and
Assumption Mapping.

## Sources

Distilled from `3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m1/bi-m1-five-whys/`
— `data/five-whys-framework.md` and `steps-c/step-05-synthesis.md`.
