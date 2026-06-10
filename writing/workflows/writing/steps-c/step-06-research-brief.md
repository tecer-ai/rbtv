---
name: 'step-06-research-brief'
description: 'Generate research document with specific questions for external AI tools'

nextStepFile: './step-07-research-integration.md'
workflowFile: '../workflow.md'
researchBriefTemplate: '../templates/research-brief.md'
researchDispatchSkill: 'rbtv-orchestrating'

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

Create the research brief document from `{researchBriefTemplate}` at `{essaySlug}/research-brief.md`.

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
- **[R] Run Research Now (in-session)** — dispatch the brief to the orchestration skill's research leaf (`{researchDispatchSkill}`) so a web-capable worker runs it here, instead of hand-carrying it to an external AI
- **[C] Continue** — proceed to Research Integration (do this AFTER completing external research)

**IMPORTANT:** Tell the user: "Take the research brief to your chosen AI tool. When you have results, return here and select [C] to integrate them — or select [R] to run it in-session now."

ALWAYS halt and wait for user selection.

**Menu handling — [R] in-session research dispatch:**

The `{researchDispatchSkill}` skill (installed invocation; its loader ships with the orchestration install) owns worker routing — its research leaf sends the brief to a web-capable worker (or, absent one, an Agent-tool sub-agent carrying the `rbtv-web-searching` directive). When [R] is selected:

1. Invoke `{researchDispatchSkill}` and route the research brief as a research-leaf dispatch.
2. The dispatch carries: the full brief (it is self-contained — usable without essay context), an OPTIONAL sources-manifest pointer if the user named a preferred/banned-sources file (the `rbtv-web-searching` sources-manifest convention — graceful skip when none), and the mandatory directive "invoke `rbtv-web-searching` before any web work and follow it exactly."
3. The worker returns cited findings keyed to the brief's research topics.
4. Hand those findings to **[C] Continue** — step-07 ingests dispatched results through the same path as hand-carried results (its § Collect Research Results maps either back to the brief topics).

If `{researchDispatchSkill}` is not installed in this workspace, [R] is unavailable — fall back to [C] (hand-carry to an external AI). Redisplay this menu after the dispatch returns.

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
