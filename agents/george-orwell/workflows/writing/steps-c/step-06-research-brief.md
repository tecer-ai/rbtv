---
name: 'step-06-research-brief'
description: 'Generate research document with specific questions for external AI tools'

nextStepFile: './step-07-research-integration.md'
workflowFile: '../workflow.md'
researchBriefTemplate: '../templates/research-brief.md'
webResearchTask: '{bmad_rbtv}/tasks/web-research.xml'

advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 6: Research Brief

**Progress: Step 6 of 11** — Next: Research Integration

---

## STEP GOAL

Analyze the narrative spine to identify what needs evidence, then generate a research document the user can take to any external AI for deep research.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are George Orwell — Critical Essay Architect. An unsupported claim is a liability. Every factual assertion must have a research question behind it.

### Step-Specific Rules
- 🎯 Every CLAIM annotation from the narrative spine MUST have a corresponding research topic
- 📎 The research document must be SELF-CONTAINED — usable without the essay context
- 🔗 Explicitly instruct the research AI to include direct source links

---

## CONTEXT BOUNDARIES

**Read the `approach` flag from output document frontmatter:**
- If `research-first`: generate COMPREHENSIVE research brief covering all claims plus exploratory questions that could reshape the argument
- If `narrative-first`: generate TARGETED research brief — only claims that need substantiation, plus counter-argument research

---

## MANDATORY SEQUENCE

### 1. Analyze the Narrative Spine

Read the essay output document. For each section of the spine:
- Identify every CLAIM that needs evidence
- Identify knowledge gaps where the argument assumes facts not yet verified
- Identify potential counter-arguments that research should preemptively address
- Note existing materials from the user's inventory that partially cover a topic

### 2. Categorize Research Needs

Present a categorized list:

| Category | Description |
|----------|-------------|
| **Must-have** | Claims that are central to the argument — essay fails without evidence |
| **Should-have** | Supporting data that strengthens but isn't structurally essential |
| **Counter-arguments** | Opposing positions the essay should acknowledge or refute |
| **Exploratory** | Questions that could reveal new angles (research-first approach only) |

Ask: "Does this capture what we need? Anything to add or deprioritize?"

### 3. Ask Target AI Preference

Ask: "Which AI tool will you use for this research? (e.g., ChatGPT, Perplexity, Claude, Gemini, other)"

This affects how the research brief is formatted — some tools work better with different prompt structures.

### 4. Generate Research Brief

Create the research brief document from `{researchBriefTemplate}` at `{bmad_output}/{essaySlug}/research-brief.md`.

For each research topic, include:
- **Topic title and priority** (must-have / should-have / counter-argument / exploratory)
- **Specific question** — not vague, but precise enough to get actionable results
- **What constitutes a good answer** — data type, recency requirements, source quality expectations
- **Context** — enough background for the research AI to understand why this matters
- **Existing partial data** — what the user already has, so research can fill gaps rather than duplicate

Update `{researchBriefTemplate}` frontmatter: `targetAI`, `status: 'ready'`.

### 5. Present Research Brief

Show the user the complete research brief. Ask: "Ready to take this to {targetAI}? Any adjustments?"

### 6. Update Essay Output Document

Append to the essay output document:
- Section header: `## Research Brief`
- Summary of research topics by category and priority
- Path to the full research brief document

### 7. Present Menu Options

**Select an Option:**
- **[R] Run Research Now** — execute web research using the built-in RBTV research task ({webResearchTask}) instead of external AI
- **[C] Continue** — proceed to Research Integration (do this AFTER completing external research)

**IMPORTANT:** Tell the user: "Take the research brief to your chosen AI tool. When you have results, return here and select [C] to integrate them."

ALWAYS halt and wait for user selection.

**Menu handling:** When [R] is selected, load and execute `{webResearchTask}` for each must-have topic, then redisplay this menu.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append this step's content to the output document
2. Update frontmatter: add `step-06-research-brief.md` to `stepsCompleted`
3. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Every claim has a research question, brief is self-contained and actionable, user knows how to proceed with external research

❌ **FAILURE:** Vague research questions, missing counter-argument research, brief that requires essay context to understand
