---
stepNumber: 1
stepName: init-taxonomy
description: 'Discover product taxonomy from seed benchmarks using sub-agents, validated by the founder'
nextStepFile: './step-02-benchmark-loop.md'
continueStepFile: './step-01b-continue.md'
stateFile: 'discovery-state.md'
stateTemplate: '../templates/discovery-state-template.md'
taxonomyTemplate: '../templates/taxonomy-template.md'
subAgentPrompts: '../data/sub-agent-prompts.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 1: Init + Taxonomy Discovery

**Progress: Step 1 of 5** — Next: Benchmark Loop

---

## STEP GOAL

Discover a product taxonomy (modules and features framework) from 2 seed benchmarks, validated by the founder. This taxonomy becomes the template for structuring all remaining benchmarks.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input
- CRITICAL: Read the complete step file before taking any action
- CRITICAL: When loading next step with 'C', ensure entire file is read
- YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are a product strategist peer. Provocative, structured, focused on decisions.

### Step-Specific Rules
- NEVER load raw benchmark files in the main conversation — ALWAYS delegate to sub-agents
- The founder validates the taxonomy — NEVER finalize without explicit approval
- Seed benchmarks are chosen for representativeness, not completeness

---

## MANDATORY SEQUENCE

### 1. Check for Existing State

Search for an existing `discovery-state.md` file in likely output locations.
- If found with `stepsCompleted` entries → load `{continueStepFile}` immediately. STOP this sequence.
- If not found → proceed.

### 2. Gather Configuration

Ask the user:
1. **Benchmark source folder** — where are the raw benchmark files?
2. **Output base folder** — where should all outputs go? Suggest: profiles and synthesis in a `structured/` subfolder near the benchmarks; product map and V1 scope in a separate `product/` folder.
3. **Seed benchmarks** — which 2 benchmarks to start with? Suggest the most comprehensive or representative ones.

### 3. Create State Document

Create `discovery-state.md` from `{stateTemplate}` in the output folder. Populate frontmatter with configuration.

### 4. Spawn Taxonomy Discovery Sub-Agents

Read `{subAgentPrompts}` — section **"Taxonomy Discovery Prompt"**.

Spawn **2 sub-agents in parallel** (one per seed benchmark):
- Input: the raw benchmark file path
- Task: identify product structure — modules, feature groupings, flow patterns
- Output: structured observations (NOT a profile — structural patterns only)

### 5. Synthesize Taxonomy Proposal

When both sub-agents return:
1. Cross-reference their observations — identify common modules and features
2. Merge into a unified taxonomy proposal: modules with descriptions and expected features
3. Present to the founder as a table

### 6. Founder Validates Taxonomy

Present the proposed taxonomy. Ask:
- "Are these categories right? Anything missing?"
- "Any categories that don't make sense for your domain?"
- "Should any be split or merged?"

Iterate until the founder explicitly approves.

### 7. Save Taxonomy

Create `taxonomy.md` from `{taxonomyTemplate}` in the output folder. Record seed benchmark names, version number, and all approved categories.

### 8. Present Menu

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on taxonomy categories
- **[P] Party Mode** — multi-agent perspectives on the taxonomy
- **[C] Continue** — proceed to Benchmark Loop

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update state document: add `step-01-init-taxonomy` to `stepsCompleted`
2. Record taxonomy file path in state document frontmatter (`taxonomyFile`)
3. Load `{nextStepFile}` and follow its instructions
