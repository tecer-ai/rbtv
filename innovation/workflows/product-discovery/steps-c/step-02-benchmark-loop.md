---
stepNumber: 2
stepName: benchmark-loop
description: 'Process each benchmark through sub-agent extraction with founder review'
nextStepFile: './step-03-comparative-synthesis.md'
subAgentPrompts: '../data/sub-agent-prompts.md'
profileTemplate: '../templates/profile-template.md'
---

# Step 2: Benchmark Loop

**Progress: Step 2 of 5** — Next: Comparative Synthesis

---

## STEP GOAL

Process each benchmark file through a sub-agent that extracts a structured profile using the approved taxonomy. The founder reviews each profile and its residual interactively. Residual information is preserved in `residual.md` — nothing is silently discarded.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input
- CRITICAL: Read the complete step file before taking any action
- YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are a product strategist peer. Present each profile clearly, flag anything surprising in the residual.

### Step-Specific Rules
- NEVER load raw benchmark files in the main conversation — ALWAYS delegate to sub-agents
- ALWAYS present BOTH the structured profile AND the residual to the founder
- If the founder identifies a new taxonomy category from residual, update `taxonomy.md` BEFORE processing the next benchmark
- Update the state document after EVERY benchmark — never batch updates
- The sub-agent produces TWO outputs: structured profile + residual. Read `{subAgentPrompts}` for the exact prompt template.

---

## MANDATORY SEQUENCE

### 1. Load State

Read the state document. Identify:
- `processedBenchmarks` — which are done
- `benchmarkSourceFolder` — where raw files live
- `taxonomyFile` — path to current taxonomy

Read `taxonomy.md` to know the current categories.

### 2. Identify Next Benchmark

List all `.md` files in the benchmark source folder. Exclude already-processed ones.

Present: "**{N} benchmarks remaining:** {list}. Processing next: **{name}**."

If all are processed → present only the [C] option to continue to synthesis.

### 3. Spawn Extraction Sub-Agent

Read `{subAgentPrompts}` — section **"Benchmark Extraction Prompt"**.

Spawn **1 sub-agent**:
- Input: raw benchmark file path + full taxonomy.md content
- Task: extract structured profile + list ALL residual information
- Output: two clearly labeled sections — PROFILE and RESIDUAL

### 4. Present Results to Founder

When the sub-agent returns:

**Profile highlights** — present a summary per taxonomy module: key features found, notable absences, anything unusual. Do NOT dump the full profile — highlight what matters.

**Residual items** — list everything the sub-agent flagged as not fitting the taxonomy.

Ask: "Review this profile. Any adjustments needed?"

### 5. Founder Decision on Residual

For each residual item, the founder decides:

| Decision | Action |
|----------|--------|
| **Add to taxonomy** | Update `taxonomy.md` with the new category. Note: subsequent benchmarks will use the updated taxonomy. |
| **Keep as company note** | Add to the profile's "Additional Notes" section |
| **Store in residual file** | Append to `residual.md` under the company's heading — preserved for potential future taxonomy expansion |

### 6. Save Outputs

1. Save the finalized profile to the structured output folder as `{company-name}.md`
2. Append any residual items (that the founder chose to store) to `residual.md` under the company heading
3. Update state document: add company name to `processedBenchmarks`

### 7. Loop or Pause Menu

**Select an Option:**
- **[N] Next Benchmark** — process the next one (return to step 2)
- **[X] Pause** — save state and stop (resume later via step-01b-continue)
- **[C] Continue to Synthesis** — proceed to comparative synthesis (only available if 5+ benchmarks processed)

On **[N]**: return to sequence step 2.
On **[X]**: confirm state is saved, inform user to invoke the workflow again to resume.
On **[C]**: warn about any skipped benchmarks, confirm, then proceed.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue to Synthesis** is selected:
1. Update state document: add `step-02-benchmark-loop` to `stepsCompleted`
2. Record total benchmarks processed and skipped in state document
3. Load `{nextStepFile}` and follow its instructions
