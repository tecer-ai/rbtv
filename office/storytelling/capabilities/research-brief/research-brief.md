---
id: research-brief
description: Author self-contained research briefs that storytelling roles emit; consume keyed findings. Reached only through narrative-lock and visual-strategist.
inputs: the emitting role's current lock-in-progress or locked spine, plus any findings already returned for earlier briefs
outcome: a research worker can execute each brief without the parent narrative, and storytelling can consume keyed findings without executing the search
outputs: one or more self-contained briefs, each carrying the six-field schema; findings return keyed to the brief's return key — this capability NEVER produces the findings
---

# research-brief

Storytelling **requests** research. It does not own research seats, web-search tools, or design-extraction tools. It authors self-contained briefs; non-interactive seats elsewhere execute them; findings return keyed to the brief's topics.

This capability is tier 3 with no exposure row, no skill, and no part-id an agent can invoke on its own. It is reached through `narrative-lock` and `visual-strategist`. An agent MUST NEVER invoke this capability on its own.

## Four purpose types

### `audience-intel`

When: before or during lock. A good answer is who they are, their vocabulary, prior beliefs, and objections — enough to sit in their seat.

### `content-facts`

When: after lock, parallel per-beat. A good answer is owner-facing evidence for a named claim, with source, recency, and what would falsify it.

### `competitive-context`

When: decision-time and/or fill. A good answer is alternatives, market frame, and positioning tensions. MUST NEVER relabel third-party research to fit.

### `visual-references`

When: visual-strategist needs exemplars before design extraction. A good answer is exemplar URLs or images for a named form or emphasis, NEVER a vibe dump. Wired to design's extraction, but storytelling only writes the ask and MUST NEVER execute it.

## Decision-research spine

Research that decides before research that fills. Sequential, pre-lock, feeding the narrative, in this exact order: themes → options → segments → implications → insights → connections.

Each stage is a brief (or a short chain) whose output is an insight artifact the narrative role consumes before freezing thesis and spine. It is not a parallel scrape and not a substitute for owner excavation — owner excavation still happens; this spine pressure-tests it and supplies the field it sits in.

- **themes** — what themes exist in the field the piece will enter.
- **options** — what alternatives a decision-maker actually considers.
- **segments** — how the audience splits, and which split this piece addresses.
- **implications** — what follows if a theme or option is true.
- **insights** — load-bearing takeaways the thesis MUST survive.
- **connections** — how those insights attach to the owner's claim.

Wait for each stage's insight artifact before emitting the next. fill-research MUST wait until after lock.

## Fill-research (after lock)

After lock: parallel per-beat `content-facts` briefs, plus remaining `competitive-context` and `visual-references` asks. Context-rot ceiling: briefs MUST chunk the ask; they MUST NEVER dump a corpus into one worker.

## Brief schema

Every brief of any type MUST carry all six fields:

1. `type` plus `priority` in {must-have, should-have, counter-argument, exploratory}.
2. A specific question, NEVER a topic label.
3. What constitutes a good answer — data type, recency, source bar.
4. Enough context to run without the parent narrative.
5. Existing partial data, so nothing is duplicated.
6. The return key — the beat id, claim id, or form id the finding maps to.

A brief missing any field is incomplete and MUST NOT be dispatched.

## Procedure

1. Confirm the caller is `narrative-lock` or `visual-strategist`. If an agent reached this file on its own, stop — do not author briefs.
2. Classify the sitting: pre-lock → decision-research spine, sequential. Post-lock → fill-research, parallel per-beat.
3. For each needed ask, author one brief using the six-field schema. Pick the purpose type from the four above. Chunk large asks.
4. Hand the brief to a non-interactive research seat elsewhere. MUST NOT execute the search, MUST NOT run web-search tools, MUST NOT run design-extraction tools.
5. When findings return, run Findings integration below.

## Findings integration

Storytelling consumes findings; it MUST NEVER execute the search.

1. Map each finding back to its return key (beat id, claim id, or form id).
2. Flag weak or conflicting sources. MUST NOT hide a conflict. MUST NOT treat an unsourced finding as evidence.
3. Remaining gaps become **Open data gaps** on the narrative lock. An unsourced external-facing claim stays blocked — NEVER invented.
4. Hand mapped, flagged findings to the calling role. `narrative-lock` consumes decision-research and `content-facts`; `visual-strategist` consumes `visual-references` findings as input, not as asks.
