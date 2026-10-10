# Panel

A panel sends N sub-agents at the same subject, each contributing an independent point of view, and a synthesis that keeps their disagreements visible. Where a swarm layers waves to cover breadth, a panel is flat: one round of peers whose value is diversity, of perspective, of model, or both. It surfaces what any single viewpoint misses, and makes disagreement a finding instead of averaging it away.

## When a panel pays

A judgment is in front of you: a diagnosis, a verdict, a review, a recommendation, or a design, over more than a trivial evidence base. The test: does answering require weighing evidence that no single file read settles? Then a panel, never one agent and never you. A judgment over N reports handed to one agent both overloads its scope and throws away the independence that makes the answer trustworthy.

A fact that one read settles is one agent, or your own read. Four lenses convened to confirm a value spend four agents on nothing.

## Composition

- Panelists are always sub-agents. A viewpoint produced inside your own context is not independent, and you are the one who must judge the synthesis.
- Each panelist gets the same subject, a bounded scope, and one viewpoint stated in its task. An output format is required: panel outputs are always piped into a synthesis.
- Diversity axes:
  - **Perspective**: same model, different roles or angles.
  - **Model**: same task, different models, from different providers where the catalog has them.
  - **Both**: the strongest form, when the subject warrants the spend.

A generative panel (one that produces solutions, designs or drafts rather than reviews) needs the problem pinned first: interview the user until the problem statement and the desired functioning are settled, because every panelist inherits that statement and a vague one wastes the whole panel.

## Models

One `cast route` call for the task sets the class and effort for the whole panel. Only the model is chosen differently: the rule that a job launches the verdict's top worker is relaxed for a panel, because its point is to hear several models, not the best one. On the model axis the roster is built from the installation's model catalog, `cast models list --catalog --json`, in this order:

1. Take every row at the class's level and every row at the level directly below it. `mechanical` has no level below, so its panel is `L3` only.

   | Class (its level) | Panel levels |
   |---|---|
   | planner (SOTA) | SOTA + L1 |
   | broad (L1) | L1 + L2 |
   | bounded (L2) | L2 + L3 |
   | mechanical (L3) | L3 |

2. Drop every row that cannot run this job: an image model (`image` is `Y`; it has no level and never sits on a panel), a row whose `launchable` is not `yes` or whose `available` is not `true`, and a row the job itself rules out, such as an api row when the panelists must discover files (`--access open`).
3. Seat each model once: a model the catalog lists at both levels takes one seat.

Every model the installation selects is eligible; the catalog has no setting that reserves a model for panels or keeps one off them. Name each drop of step 2 in the synthesis. Never seat a model above the class's own level. The verdict's effort applies to every panelist.

The full roster is the default because a hand-picked panel drifts toward the models the coordinator already trusts, and an agreement among two models of one provider is weaker than it looks. Show the roster in the plan you present before launching (coordinate skill, rule 1); the user's budget answer is where it narrows. When you narrow it yourself, say which models were left out and why in the synthesis.

## Synthesis

One run folder per panel; every panelist's raw output file is kept there, because the synthesis condenses and the raw files preserve. A synthesis task goes to a sub-agent when the panel has more than two panelists; you synthesize a two-panelist panel yourself only when both outputs fit one page. Either way the synthesis carries:

- **Convergence**: what several viewpoints independently agree on, the strongest findings.
- **Divergence**: where viewpoints conflict, with each side's argument. Never silently merged: a disagreement between independent viewpoints is signal.
- **Recommendation**: your call, with its reason.

A rebuttal round (each panelist reads the others' pages and answers) is worth its cost when the divergence is the finding; propose it in the plan when you expect one.

## Shapes

Compose viewpoints freely; two shapes recur:

- **Review panel**: panelists review one artifact, each through a different lens. Lenses that have served: adversarial (try to break it), consistency, bug hunt, design quality, root cause, first principles, customer or user, investor, completeness (edge cases, states), references (do the cited things exist and say what is claimed). When the subject is a plan folder, the checks in [Reviewing a plan](../../../plan/capabilities/methods/planning-a-workflow/reviewing-a-plan.md) (structure, hand-offs, context ceiling, Needs edges, shared writes, descriptions) are ready-made lenses.
- **Design panel**: after the problem is pinned, two or more panelists each produce an independent solution to the same problem, on strong models (class planner or broad), each with a small bounded scope and one output format. The synthesis compares the designs and recommends one, grafting the best ideas from the others.
