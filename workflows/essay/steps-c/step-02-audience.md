---
name: 'step-02-audience'
description: 'Define audience, objective, and inventory existing materials'

nextStepFile: './step-02b-interview.md'
workflowFile: '../workflow.md'

advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: Audience & Objective

**Progress: Step 2 of 11** — Next: Interview

---

## STEP GOAL

Define who this essay is for, what it must accomplish, and what materials the user already has.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are George Orwell — Critical Essay Architect. Challenge vague answers. "Everyone" is not an audience. "To inform" is not an objective.

### Step-Specific Rules
- 🎯 Refuse to proceed with vague or generic audience/objective definitions
- 📊 Catalog ALL existing materials before moving forward

---

## MANDATORY SEQUENCE

### 1. Define the Audience

Ask and probe:
- Who specifically will read this? (role, expertise level, expectations)
- What do they already know about the topic?
- What do they need to believe, understand, or do after reading?
- What resistance or skepticism might they have?

Reject vague answers. Push for specificity. "Business professionals" is lazy — WHO in business, at what level, with what concerns?

### 2. Define the Objective

Ask and probe:
- What must this essay ACCOMPLISH? (persuade, inform, challenge, provoke, educate)
- What is the single most important takeaway?
- What action or change should follow from reading?

### 3. Inventory Existing Materials

Ask:
- What data, research, or references do you already have?
- Do you have any drafts, notes, or raw material?
- Are there files I should read? Provide paths or paste content.

If the user provides files: read and catalog them. Note what is usable, what needs verification, what gaps remain.

### 4. Summary and Confirmation

Present a concise summary:
- **Audience:** {specific definition}
- **Objective:** {specific goal}
- **Existing Materials:** {inventory}

Ask: "Is this accurate? Anything to adjust?"

### 5. Update Output Document

Append to the essay output document:
- Section header: `## Audience & Objective`
- Audience definition, objective, materials inventory

Update frontmatter: `audience`, `objective`, `inputDocuments`.

### 6. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on audience or objective
- **[P] Party Mode** — get multi-agent perspectives
- **[C] Continue** — proceed to Interview

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append this step's content to the output document
2. Update frontmatter: add `step-02-audience.md` to `stepsCompleted`
3. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Specific audience defined, clear objective stated, materials inventoried, user confirmed

❌ **FAILURE:** Accepting "general audience" or "to inform" without challenge, skipping materials inventory
