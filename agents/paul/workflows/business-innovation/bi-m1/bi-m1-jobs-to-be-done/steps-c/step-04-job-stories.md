---
name: 'step-04-job-stories'
description: 'Synthesize job stories, forces analysis, and job map'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/jobs-to-be-done.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Job Stories & Forces

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

Convert job hypotheses and interview data into refined job stories, forces analysis, and a job map showing how customers try to get the job done today.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Job stories must be grounded in real behavior. Push for specificity. Reject stories that mirror product UI structure.

### Step-Specific Rules
- Job stories must be in customer language, not product language
- Forces must explain both why people switch AND why they stay
- Job map describes current state, not your future solution
- If interviews not yet done, synthesize from founder knowledge (note limitation)

---

## CONTEXT BOUNDARIES

**Available context:**
- Job hypotheses from Step 2
- Interview guide and data from Step 3
- Working Backwards insights

**Out of scope:**
- Final prioritization (that's Step 5)
- Solution design
- Product features

---

## MANDATORY SEQUENCE

### 1. Cluster Interview Insights

If interview data exists, cluster episodes by:
- Situation trigger (board meeting prep, month-end close, feature launch)
- Customer type (role, company size, environment)
- Progress sought (what "better" looked like)

If no interviews yet:
- Use founder knowledge and Working Backwards insights
- Note explicitly: "Based on founder knowledge, pending interview validation"

### 2. Refine Job Stories

For each cluster, write a refined job story:

**Format:** "When [specific situation], I want to [progress], so I can [ultimate outcome]."

Distinguish between:
- **Main job:** Core progress they hire a solution for
- **Related jobs:** Upstream/downstream tasks (may be out of scope)
- **Emotional job:** How they want to feel
- **Social job:** How they want to be perceived

### 3. Forces Analysis

For each main job, document the four forces:

| Force | Description | Evidence |
|-------|-------------|----------|
| **Push of Present** | Pains with current way | [Quotes/observations] |
| **Pull of New** | Attractions of alternatives | [What draws them] |
| **Anxieties** | Fears about change | [What holds them back] |
| **Habits** | Comfort with status quo | [What they're used to] |

Ask founder:
- "What's so painful about the current way that they'd seek change?"
- "What would make them nervous about adopting something new?"
- "What habits would they have to break?"

### 4. Build Job Map

Create a job map showing stages of getting the job done:

| Stage | Customer Actions | Pain Points | Current Workarounds |
|-------|------------------|-------------|---------------------|
| Define | How they recognize/frame the problem | [Pains] | [What they do] |
| Locate | How they find options/information | [Pains] | [What they do] |
| Prepare | How they set up for the work | [Pains] | [What they do] |
| Execute | How they do the core work | [Pains] | [What they do] |
| Confirm | How they verify/share results | [Pains] | [What they do] |
| Evolve | How they refine over time | [Pains] | [What they do] |

**Important:** Write in customer language, not product UI structure.

### 5. Compare to Original Hypotheses

Document where reality diverged from initial hypotheses:

| Original Hypothesis | Validated? | What Changed |
|---------------------|------------|--------------|
| [Hypothesis 1] | Yes/No/Partial | [Explanation] |
| [Hypothesis 2] | Yes/No/Partial | [Explanation] |
| [Hypothesis 3] | Yes/No/Partial | [Explanation] |

### 6. Update Output Document

Update jobs-to-be-done.md Job Stories & Forces section:

```markdown
## Job Stories & Forces

### Main Job Story

**When** [specific situation],
**I want to** [progress],
**so I can** [ultimate outcome].

**Type:** [Functional]

### Related Jobs

- **Related:** [Job statement]
- **Emotional:** [How they want to feel]
- **Social:** [How they want to be perceived]

### Forces Analysis

| Force | Description | Evidence |
|-------|-------------|----------|
| Push of Present | [Description] | [Quote/observation] |
| Pull of New | [Description] | [What attracts] |
| Anxieties | [Description] | [What worries] |
| Habits | [Description] | [What's comfortable] |

### Job Map

| Stage | Customer Actions | Pain Points | Workarounds |
|-------|------------------|-------------|-------------|
| Define | [Actions] | [Pains] | [Workarounds] |
| Locate | [Actions] | [Pains] | [Workarounds] |
| Prepare | [Actions] | [Pains] | [Workarounds] |
| Execute | [Actions] | [Pains] | [Workarounds] |
| Confirm | [Actions] | [Pains] | [Workarounds] |
| Evolve | [Actions] | [Pains] | [Workarounds] |

### Hypothesis Validation

| Hypothesis | Validated | Notes |
|------------|-----------|-------|
| [H1] | [Yes/No/Partial] | [Notes] |
| [H2] | [Yes/No/Partial] | [Notes] |
| [H3] | [Yes/No/Partial] | [Notes] |

### Data Source

[Interview-based / Founder knowledge / Hybrid — note limitations if applicable]
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-job-hypotheses', 'step-03-interview', 'step-04-job-stories']
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify main job story documented
2. Verify forces analysis complete (all 4 forces)
3. Verify job map has at least 3 stages populated
4. Verify `step-04-job-stories` is in `stepsCompleted`
5. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Main job story in correct format, forces analysis explains adoption and non-adoption, job map in customer language

❌ **FAILURE:** Job story mirrors product UI, forces only explain adoption (not resistance), job map is product-centric
