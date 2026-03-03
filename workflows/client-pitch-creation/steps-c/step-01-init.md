---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-context-gather.md
standaloneFallback: ./step-03-narrative.md
---

# Step 01: Initialize Client Pitch

**Progress: Step 1 of 9** — Next: Context Gathering

---

## STEP GOAL

Detect project context, understand the target client/audience, and set output path.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are The Buyer. From this point forward, every question you ask is the question a procurement VP would ask before signing a contract. Start as you mean to continue.

### Step-Specific Rules

- Detect founder documents before asking questions
- Set output path based on project context
- This workflow is exclusively for client/sales pitches (winning customers or partnerships)
- Understanding the TARGET CLIENT is critical — the pitch must be tailored to their world, not yours

---

## MANDATORY SEQUENCE

### 1. Detect Project Context

Check the conversation context:

**If project-memo was @-mentioned (founder mode):**
- Read project-memo frontmatter: extract projectName
- Set {mode}=founder
- Set {project_name} from projectName
- Set {output_folder}=`{project-root}/_bmad-output/{project_name}/_clients/pitch-deck`
- Confirm: "I see you're working on **{project_name}**. I'll pull content from your founder documents and stress-test your pitch from the buyer's side of the table."

**If no project-memo (standalone mode):**
- Set {mode}=standalone
- Ask: "What's the name of the project or company this pitch is for?"
- Set {project_name} from response
- Ask: "Where should I save the pitch deck? Default: `_bmad-output/{project_name}/_clients/pitch-deck`"
- Set {output_folder} from response or default

### 2. Understand the Target Client

Ask (only what's missing from conversation context):
- **Who is this pitch for?** A specific company? A segment? A type of buyer?
- **What's their role?** (CEO, CTO, procurement, department head, etc.)
- **What's the deal size?** (ballpark — this affects formality and detail level)
- **What do they use today?** (competitor, in-house solution, manual process, nothing)
- **What triggered this pitch?** (inbound interest, outbound prospecting, RFP, referral)

Set {target_client} and {deal_context} from responses.

### 3. Gather High-Level Context (Standalone Only)

**If {mode}=founder:** Skip — context will be gathered from documents in Step 02.

**If {mode}=standalone:** Ask the following (only what's missing):
- One-line description of what the company does
- Key differentiator vs. what the client uses today
- Price range or pricing model

### 4. Check for Existing Deck

Check if `{output_folder}/pitch-deck.html` exists:
- If YES: "I found an existing pitch deck. Would you like to **[R] Replace** it with a fresh build, or **[E] Exit** and use Edit mode instead?"
- If NO: Continue normally.

### 5. Confirm Setup

Present summary:
```
Client Pitch Setup:
- Project: {project_name}
- Target: {target_client}
- Deal context: {deal_context}
- Mode: {mode} (founder docs / standalone)
- Output: {output_folder}/

Deliverables:
  1. pitch-narrative.md        — The story, stress-tested slide by slide from buyer's perspective
  2. pitch-research-prompt.md  — Research prompt for external AI (proof points + buyer objections)
  3. pitch-deck.html           — The final HTML deck
  4. pitch-image-prompts.md    — Image generation prompts

Ready to proceed?
```

Wait for confirmation.

### 6. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to content gathering
- **[X] Exit** — exit workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
- If {mode}=founder: Load `{nextStepFile}` (step-02-context-gather)
- If {mode}=standalone: Load `{standaloneFallback}` (step-03-narrative — skip context-gather)

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Mode detected (founder or standalone)
- Target client and deal context understood
- Output path confirmed
- User understands the deliverables and sequence

❌ **FAILURE:**
- Generating content before setup complete
- Not understanding who the pitch is FOR
- Proceeding without user confirmation
