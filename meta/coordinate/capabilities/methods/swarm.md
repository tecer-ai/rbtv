# Swarm

A swarm attacks one problem with structured waves of sub-agents: a wide base of cheap, fast models does the broad work, and each wave above it is smaller and stronger, building on the files the wave below wrote. It gives breadth and depth at low cost, with every agent's context kept small, and the coordinator reads one synthesis instead of the evidence.

A swarm is the wrong block when the problem is one question (one agent answers it) or when what is needed is a verdict over evidence already gathered (a [panel](panel.md)).

## Unit and lanes

- One swarm attacks one problem. Its base wave is one agent per independently answerable question of that problem, each with the material that question needs ([Building a scope](scope.md)). Several problems are several swarms, run in parallel when independent; never one swarm whose base agents each hold a whole problem.
- One lane is one facet, never one problem. A lane whose task names a problem ("investigate issue 3") is not a lane: decompose it into facets and those are the wave.
- The inverse failure: a question one file read or one command answers is one agent, or your own read. A run folder and a synthesis pass around it cost more than the answer.

## Waves

One to N waves. Within a wave, agents run in parallel, all working the same direction, each bounded. Waves run in sequence, each built on the previous wave's files. Shapes that fit most jobs:

- One wave of investigators, when their pages answer the problem directly.
- Investigators and a summarizer wave, when you would otherwise open more than one lane file.
- Wide cheap investigators, then fewer stronger investigators acting on their findings, then a summarizer, when the first wave's facts raise a second round of questions.

The coordinator never reads the wave's outputs to combine them. The moment you would open more than one lane's file to summarize, compare or judge across them, the next wave is a summarizer wave: dispatch it over those files and read its one page. A judgment across the wave (a diagnosis, a verdict, a recommendation) goes to a panel, not to you and not to a single agent.

## Model per wave

`cast route` names the model per wave from the job's class; the levels are its (`cast route -h`), and there is no swarm-special routing:

| Wave role | Route call |
|---|---|
| base investigators (wide, cheap) | `cast route --access … --type … --class mechanical --optimize price` |
| middle investigators | `--class bounded --optimize price` |
| summarizer / synthesis | `--class broad --optimize quality` |

Effort is the verdict's. A base lane on a mechanical-class model works only when its scope is tight and its read-set named; when the lane needs judgment, it is a middle lane.

## Depth

- **balanced** (default): the wave sizes you judge the problem needs; no spend on investigators beyond the questions you can name.
- **deep** (the user asks for it): investigator waves unbounded; the summarizer wave stays contained.

## Handoff between waves

One run folder per swarm (location as the coordinate skill says). Every agent writes its findings to a file there, and the next wave's tasks point at the previous wave's files: you compose tasks, you do not relay findings through your own context. Give same-wave agents task text with a shared prefix (same structure, the per-agent scope at the end), so the shared part is served from the model's cache.

The plan you show the user before the first launch (coordinate skill, rule 1) is the swarm's architecture: the waves, their sizes, the model per wave and the depth.
