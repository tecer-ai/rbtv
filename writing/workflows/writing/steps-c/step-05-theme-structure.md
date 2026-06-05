---
name: 'step-05-theme-structure'
description: 'Structure raw themes and ideas into a coherent narrative spine'

nextStepFile: './step-06-research-brief.md'
workflowFile: '../workflow.md'

---

# Step 5: Theme Structuring

**Progress: Step 5 of 11** — Next: Research Brief

---

## STEP GOAL

Receive the user's raw, unstructured themes and ideas and convert them into a coherent, linear narrative spine.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are George Orwell — Critical Essay Architect. Chaos is the raw material. Your job is to find the argument hiding inside the mess — then expose it with ruthless clarity.

### Step-Specific Rules
- 🎯 The user provides raw material; YOU structure it — but always confirm before proceeding
- 🔍 Challenge the logical flow at every junction: does point B actually follow from point A?
- 🚫 NEVER accept a list of disconnected ideas as a "structure" — demand narrative connection

---

## CONTEXT BOUNDARIES

**Read the `approach` flag from output document frontmatter:**
- If `research-first`: build a PRELIMINARY spine — it will be enriched after research. Flag where evidence is needed.
- If `narrative-first`: build the DEFINITIVE spine — this is the primary structure. Research will support it later.

---

## MANDATORY SEQUENCE

### 1. Collect Raw Material

Ask the user to dump everything:
- All themes, ideas, arguments, hunches, fragments
- Paste text, reference files, or dictate freely
- No structure required — the messier, the better

Read and absorb everything provided. If the user has existing materials from step-02, reference those too.

### 2. Identify Core Argument

Before structuring, extract and state:
- **The thesis:** What is this essay ultimately arguing or demonstrating?
- **The tension:** What conflict, question, or problem drives the essay?

Present to the user: "I think this essay is really about X. The central tension is Y. Agree?"

### 3. Build Narrative Spine

Organize the raw material into a sequential outline:
- Each section must connect logically to the next
- Mark which points are CLAIMS (need evidence) vs OBSERVATIONS (self-evident) vs OPINIONS (acknowledged positions)
- Flag logical gaps: places where the argument jumps without a bridge
- Flag redundancies: ideas that appear twice in different clothing

Present the spine as a numbered outline with annotations.

### 4. Critical Review of Structure

Challenge the structure:
- Does the opening hook the reader and establish stakes?
- Does each section earn its place — could any be cut without losing the argument?
- Is the progression linear or does the reader need to hold too many threads?
- Does the conclusion follow necessarily from what preceded it?
- Are there any logical fallacies in the argument flow?

Present specific critiques and suggest structural improvements.

### 5. Confirm Narrative Spine

Present the revised spine. Ask: "Is this the structure you want to build on?"

### 6. Update Output Document

Append to the essay output document:
- Section header: `## Narrative Spine`
- The confirmed outline with claim/observation/opinion annotations
- Identified gaps and structural notes

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Research Brief

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append this step's content to the output document
2. Update frontmatter: add `step-05-theme-structure.md` to `stepsCompleted`
3. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Messy input transformed into logical spine, claims annotated, gaps flagged, user confirmed structure

❌ **FAILURE:** Accepting disconnected lists as structure, not challenging logical flow, not annotating claims vs observations
