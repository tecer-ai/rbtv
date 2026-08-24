---
description: Use when asked to swarm, or when a task benefits from waves of parallel sub-agents — a large cheap base layer feeding smaller layers of stronger models.
tags: [sub-agents]
---

# Swarm

A swarm dispatches structured WAVES of sub-agents at one task: a wide base of cheap, fast
models does the broad work, and each wave above it is smaller and stronger, building on the
wave below. The point: optimal breadth and depth at lower cost, with every agent's context
kept small.

A swarm saves the coordinator's context (it reads one synthesis, not the evidence), gets better
results (a fresh focused context per question), and costs less (cheap models on the wide base,
strong ones only at the top) — all three at once, or the shape is wrong.

Staffing and launch mechanics are the sub-agents skill's (`references/sub-agents.md` — seats,
`cast` launches, output schemas, output location). This reference adds only what is
swarm-specific.

## Quick interview — always

Before dispatching, propose ONE architecture to the user and get a confirm/adjust:
waves (count and size), `cast route` model suggestion for each wave, and depth. One short round, then go.

## Architecture

- Unit: ONE swarm attacks ONE problem. Its base wave is one agent per independently-answerable
  question of that problem (the small-scope test — sub-agents skill § Staffing). Several
  problems are several swarms (run in parallel when independent) — never one swarm whose base
  agents each hold a whole problem.
- Lane membership: **ONE LANE = ONE FACET, never one problem.** A lane's scope is a single
  independently-answerable question about the problem — where a value is written, what a reader
  parses, which callers exist. If a lane's prompt names a problem ("investigate issue 3"),
  it is not a lane; decompose it into facets and those ARE the wave. Inverse guard: a question
  one file read or one command answers is ONE agent — do not build a wave, a run folder and a
  synthesis pass around it.
- **The coordinator never reads the wave's outputs to combine them.** The moment you would open
  more than one lane's output file to summarize, compare or judge across them, the next wave IS
  a summarizer wave — dispatch it over those files and read its ONE page. A judgment across the
  wave (diagnosis, verdict, recommendation) goes to a panel (`panel.md`), not to the coordinator
  and not to a single agent.
- 1..N waves. Within a wave, agents run in PARALLEL, each with a bounded, small scope,
  all working the same direction. Waves run in sequence: each builds on the previous wave's
  outputs. Shape the pyramid to the job — examples:
  - A: one wave of investigators
  - B: investigators + a summarizer wave
  - C: wide cheap investigators → fewer stronger investigators acting on their findings → summarizer
- Model per wave comes from `cast route` — the existing classes, no swarm-special routing:

  | Wave role | Route call |
  |---|---|
  | base investigators (wide, cheap) | `cast route --access … --type … --class mechanical --optimize price` |
  | middle investigators | `--class bounded --optimize price` |
  | summarizer / synthesis | `--class broad --optimize quality` |

  Effort is the route verdict's — no override.

## Depth

- **balanced** (default): the wave sizes you judge necessary — no overspend on investigators.
- **deep** (user asks for it): investigator waves unbounded; the summarizer wave stays contained.

## Handoff between waves

One run folder per swarm (location per the sub-agents skill's output-location rule). Every
agent writes its findings to a file there; the next wave's prompts point at the previous
wave's files — the coordinator composes prompts, it does not relay findings through its own
context. Give same-wave agents a shared prompt prefix (same seat structure, per-agent scope
at the end) to optimize KV cache.
