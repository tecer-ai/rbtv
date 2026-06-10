---
name: 'step-04-synthesize'
description: 'Build the four-branch problem tree, verdict hypotheses, rank fix directions, finalize the diagnosis.'
nextStepFile: null
workflowFile: './workflow.md'
dataFile: './data/efficiency-patterns.md'
---

# Step 4: Synthesize

**Progress: Step 4 of 4** — Final step

---

## STEP GOAL

Convert discoveries into a decision-ready diagnosis: tree, verdicts, and prioritized fix directions that preserve every protection.

---

## MANDATORY EXECUTION RULES

- 🌳 Every tree leaf cites a discovery (D#) — no leaf stands on impression
- 🛡️ Every fix direction names the protection it preserves and the format that preserves it (Diagnostic Method Requirement 2)
- ⚖️ A diagnosis with zero KEEP rows is incomplete — return to Step 3 and run the earned-content hunt

---

## MANDATORY SEQUENCE

### 1. Build the Problem Tree

Root: "Why does {component} cost tokens that don't buy quality?" Branches: the four cost loci (LOAD / DECIDE / RECORD / COORDINATE). Leaves: pattern instances, each citing D#. Each branch carries its counter-evidence line(s) — "(KEEP: …)" — where the earned-content hunt found them. Validate MECE at each level: no leaf in two branches (file by fix locus); no discovery unmapped.

### 2. Verdict the Hypotheses

One row per owner hypothesis: `H# | verdict (confirmed / partially / rejected) | mechanism | evidence (D#)`. A rejected hypothesis is stated as plainly as a confirmed one — that result redirects the owner's attention from felt waste to measured waste, which is the diagnosis's core value.

### 3. Rank Fix Directions

Order by measured mass × how often the cost is paid. Each entry: `fix | waste removed (measured) | protection preserved + new format | sized as (direct edit / plan-sized)`. Plan-sized fixes are flagged for handoff to a planning workflow; direct edits are listed as immediately actionable.

### 4. Finalize the Document

1. Compute the completion timestamp with a shell call (`date` / `Get-Date`) — never invent it.
2. Frontmatter: `status: complete`, add `step-04-synthesize` to `stepsCompleted`, add `completed: {timestamp}`.
3. Append the tree, verdict table, and ranked fixes under `## Problem Tree` and `## Verdicts & Priorities`.

### 5. Present the Result

Present to the owner: the document path, the 30-second version (one main-message sentence + top 3 fix directions), and every rejected hypothesis surfaced explicitly.

| Option | Action |
|--------|--------|
| **[P] Plan** | Hand the diagnosis to the planning workflow (the diagnosis document is the plan input) |
| **[R] Revise** | Adjust tree, verdicts, or priorities |
| **[D] Done** | Close the review |

HALT and WAIT for user input.

---

## CRITICAL STEP COMPLETION NOTE

Terminal step — no next step file. On **[D] Done**, confirm the document is saved and `status: complete`. On **[P] Plan**, follow the workspace's planning entry point with the diagnosis document as input.

---

✅ **SUCCESS:** tree with D-cited leaves and KEEP rows, every hypothesis verdicted, fixes ranked with protections named, document complete.
❌ **FAILURE:** leaves without discovery citations; hypotheses left unverdicted; a fix that drops a protection instead of reformatting it; invented timestamps.
