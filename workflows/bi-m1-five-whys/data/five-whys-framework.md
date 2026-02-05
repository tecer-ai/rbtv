# Five Whys Framework Knowledge

**Purpose:** Reference knowledge for the Five Whys (Root Cause Analysis) framework methodology.

---

## Framework Overview

Five Whys traces visible problems to structural root causes by iteratively asking "Why?" and recording each answer as a causal chain link.

### Core Principles

1. **Anchor on one concrete scenario** — Never analyse abstract problem categories
2. **Surface structural causes** — Blame incentives, processes, constraints — never individuals
3. **Separate facts from hypotheses** — Label each chain link and attach evidence where available
4. **Mark validation requirements** — Hypotheses feed M2/M5 validation backlog

---

## Chain Structure

A 5 Whys chain starts from a concrete **Anchor Problem Statement** and iteratively asks "Why is this happening?"

| Level | Element | Example |
|-------|---------|---------|
| 0 | Anchor Problem Statement | "Trial users from segment X don't complete onboarding within 7 days" |
| 1 | First Why | "They abandon during data import step" |
| 2 | Second Why | "Data import requires manual formatting they don't have time for" |
| 3 | Third Why | "Our import expects clean CSV but their data is fragmented across 4 tools" |
| 4 | Fourth Why | "Nobody in their org owns data consolidation — it's everyone's problem and no one's job" |
| 5 | Root Cause | "Organisational structure treats data consolidation as overhead, not value creation" |

**Stop when you reach:**
- A structural cause (incentives, processes, constraints) that explains upstream symptoms
- Additional whys only repeat the same idea with different words
- A knowledge frontier where all further answers are untestable hypotheses

---

## Session Rules

Display at the top of every 5 Whys session:

1. Focus on THIS scenario only — park other scenarios for separate chains
2. Blame processes, structures, incentives, assumptions — NEVER individuals
3. Each answer must be a direct cause of the previous answer, not a different problem
4. Label every answer as **Fact** (supported by data/observation) or **Hypothesis** (to validate)
5. Stop when you reach a structural cause that is actionable

---

## Chain Template

| Level | Why Question | Answer | Fact/Hypothesis | Evidence | Notes |
|-------|--------------|--------|-----------------|----------|-------|
| 0 | — | Anchor Problem Statement | — | — | — |
| 1 | Why is this problem happening? | ... | F/H | ... | ... |
| 2 | Why is [level 1 answer] true? | ... | F/H | ... | ... |
| 3 | Why is [level 2 answer] true? | ... | F/H | ... | ... |
| 4 | Why is [level 3 answer] true? | ... | F/H | ... | ... |
| 5 | Why is [level 4 answer] true? | ... | F/H | ... | ... |

---

## Root Cause Categories

Cluster chain endpoints into structural categories:

| Category | Examples |
|----------|----------|
| Customer behaviour and context | Habits, incentives, skills, workflows |
| Product and UX | Discovery, onboarding, feedback loops |
| Business model and pricing | Misaligned incentives, long approvals |
| Go-to-market and channels | Wrong decision-maker, weak trust signals |
| Organisation and operations | Internal bottlenecks slowing iteration |
| External constraints | Regulation, vendor lock-in, platform risk |

---

## Validation Checklist

**Problem Framing:**
- [ ] Can name at least 3 real organisations or people who fit the scenario
- [ ] Anchor Problem Statement is traceable to PR/FAQ, JTBD, Problem-Solution Fit, Lean Canvas
- [ ] Analysing one scenario only — others explicitly parked

**Chain Quality:**
- [ ] Each chain is a linear sequence of causes — no topic jumps
- [ ] Every answer labelled Fact or Hypothesis with evidence noted
- [ ] At least one chain reaches a structural cause (not "users don't care" or "team is slow")

**Root Cause Synthesis:**
- [ ] At least one Root Cause Statement is non-obvious compared to initial problem
- [ ] Each Targeted Root Cause Hypothesis links to specific behaviours/metrics to change
- [ ] At least one Non-Targeted Root Cause documented (what you're NOT tackling in v1)

---

## Pitfalls to Avoid

1. **Stopping at three whys** — Push at least one chain to a structural cause you're uncomfortable writing down
2. **Blaming people** — Force every answer to be about systems, policies, incentives, not character
3. **Mixing problems** — When a different problem appears, fork a new chain
4. **Ignoring evidence** — Prioritise chains supported by real user behaviour or metrics
5. **One-off ritual** — Treat five_whys.md as living document; update when assumptions are validated
6. **Unbounded topics** — Always narrow to specific scenario/metric/segment before starting

---

## Integration

**Prerequisites:**
- Working Backwards, JTBD, and Lean Canvas (draft) should be completed before starting

**Feeds Into:**
- Project memo (refined problem narrative, explicit root causes)
- Lean Canvas (refined Problem block, Key Metrics)
- M2 Validation (Targeted Root Cause Hypotheses seed experiments)
- M5 Market Validation (hypotheses about adoption/retention drivers)

**Workflow Position:**
5 Whys sits after Working Backwards, JTBD, Problem-Solution Fit, and alongside or just after the first Lean Canvas draft. It is typically the final M1 framework.
