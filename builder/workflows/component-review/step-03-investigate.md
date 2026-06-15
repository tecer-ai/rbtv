---
name: 'step-03-investigate'
description: 'Dispatch read-only investigator sub-agents per cost locus and fold returns into discoveries.'
nextStepFile: './step-04-synthesize.md'
workflowFile: './workflow.md'
dataFile: './data/efficiency-patterns.md'
---

# Step 3: Investigate

**Progress: Step 3 of 4** — Next: Synthesize

---

## STEP GOAL

Gather lane-by-lane evidence through read-only sub-agents so the conductor's context holds conclusions, never file dumps.

---

## MANDATORY EXECUTION RULES

- 📋 Read `./data/efficiency-patterns.md` before dispatching
- 🤖 Investigators are READ-ONLY sub-agents, default model `sonnet` — the conductor reads no target files itself in this step
- 📋 Sub-agents inherit NOTHING: every fact a lane needs (paths, pattern table, mandates) goes INTO its prompt
- 🛑 Honor the workspace's sub-agent dispatch rule if one is installed (e.g., `rbtv-sub-agents` pre-dispatch gate) before every dispatch

---

## MANDATORY SEQUENCE

### 1. Scale the Lane Plan

| Target size (from Measured Baseline) | Lanes |
|--------------------------------------|-------|
| ≤ 5 files or ≤ 3,000 words | 2 lanes: LOAD+DECIDE+THINK, RECORD+COORDINATE — earned-content hunting folded into both |
| Larger | 5 locus lanes (LOAD, DECIDE, THINK, RECORD, COORDINATE) + 1 earned-content lane |
| Owner hypotheses exist (H1..Hn) | +1 hypothesis-test lane, whatever the size |

Present the chosen lane plan to the owner in one line each, then dispatch without waiting (the owner interrupts if the plan is wrong).

### 2. Compose Each Lane Prompt

Every lane prompt MUST contain, in this order:

1. **Read-only mandate:** "You must NEVER create, write, edit, move, or delete any file. Your reply text is the deliverable. Local files only."
2. **Absolute target paths** from the diagnosis document's `target_paths`, plus the workspace root.
3. **Tooling caveat:** "Glob may return false negatives — verify any absence with Bash ls/find or Grep. All counts via wc/grep, never estimated."
4. **The lane's pattern table** — paste the relevant locus section(s) from `./data/efficiency-patterns.md` verbatim into the prompt. For any lane covering THINK, also paste that lane's per-file cognitive-load proxy columns (Conditional / Arbitration / Max prose run / Open-delib) from the Measured Baseline as the lane's starting point — directional figures the investigator confirms against the files (real load vs. earned), never a verdict.
5. **The mission:** find instances of the lane's patterns in the target; for each, cite file path + evidence + measured cost; AND mark earned content as KEEP rows (content whose removal would re-open a failure — name the failure).
6. **Anti-flattery clause:** "Report facts and measured costs. Do not flatter the hypothesis that this component is wasteful — disconfirming evidence is equally valuable."
7. **Return shape:** executive summary (3–6 bullets with totals) → evidence table (`pattern | file | evidence | measured cost`) → KEEP rows (`content | failure it guards`).

The hypothesis-test lane swaps item 5 for: "For each hypothesis below (verbatim), gather the evidence that confirms or rejects it; verdict each as confirmed / partially / rejected with the mechanism."

### 3. Dispatch and Fold

Dispatch lanes in parallel (background for 3+ lanes). As each returns, append its findings to the diagnosis document under `## Discoveries` as numbered entries (D1..Dn): conclusions and figures only — never paste raw file contents. KEEP rows are appended under a `### Counter-Evidence (KEEP)` subsection.

### 4. Saturation Check

If any lane's findings cite files OUTSIDE the Step 1 tree, the scope was wrong: re-enumerate, re-measure the missed files (Step 2 fallback recipe), and record the scope correction as a discovery.

### 5. Present Menu

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 4 — Synthesize |
| **[ML] More Lanes** | Dispatch an additional lane the evidence suggests |
| **[X] Exit** | Stop the review |

HALT and WAIT for user input (background lanes may still be returning — fold them as they land).

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected AND all dispatched lanes have returned and been folded:
1. Update the diagnosis document frontmatter: add `step-03-investigate` to `stepsCompleted`
2. Load `./step-04-synthesize.md` and follow its instructions

---

✅ **SUCCESS:** every lane returned, discoveries numbered and folded, KEEP rows present, conductor context free of file dumps.
❌ **FAILURE:** conductor reading target files directly; prompts missing the pasted pattern table; findings folded as raw dumps; synthesizing before all lanes returned.
