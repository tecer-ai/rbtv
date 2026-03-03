---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-context-gather.md
standaloneFallback: ./step-03-narrative.md
---

# Step 01: Initialize Investor Pitch

**Progress: Step 1 of 9** — Next: Context Gathering

---

## STEP GOAL

Detect project context, confirm investor pitch scope, and set output path.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are The Investor. From this point forward, every question you ask is the question a VC partner would ask before writing a check. Start as you mean to continue.

### Step-Specific Rules

- Detect founder documents before asking questions
- Set output path based on project context
- This workflow is exclusively for investor pitches (fundraising: VCs, angels, accelerators)

---

## MANDATORY SEQUENCE

### 1. Detect Project Context

Check the conversation context:

**If project-memo was @-mentioned (founder mode):**
- Read project-memo frontmatter: extract projectName
- Set {mode}=founder
- Set {project_name} from projectName
- Set {output_folder}=`{project-root}/_bmad-output/{project_name}/_fundraising/pitch-deck`
- Confirm: "I see you're working on **{project_name}**. I'll pull content from your founder documents and then stress-test your pitch narrative before we build anything."

**If no project-memo (standalone mode):**
- Set {mode}=standalone
- Ask: "What's the name of the project or company this pitch is for?"
- Set {project_name} from response
- Ask: "Where should I save the pitch deck? Default: `_bmad-output/{project_name}/_fundraising/pitch-deck`"
- Set {output_folder} from response or default

### 2. Gather High-Level Context (Standalone Only)

**If {mode}=founder:** Skip — context will be gathered from documents in Step 02.

**If {mode}=standalone:** Ask the following (only what's missing from conversation context):
- One-line description of what the company does
- Stage (pre-seed, seed, Series A, etc.)
- How much you're raising and what for
- Key differentiator or "why now"

### 3. Check for Existing Deck

Check if `{output_folder}/pitch-deck.html` exists:
- If YES: "I found an existing pitch deck. Would you like to **[R] Replace** it with a fresh build, or **[E] Exit** and use Edit mode instead?"
- If NO: Continue normally.

### 4. Confirm Setup

Present summary:
```
Investor Pitch Setup:
- Project: {project_name}
- Mode: {mode} (founder docs / standalone)
- Output: {output_folder}/

Deliverables:
  1. pitch-narrative.md   — The story, stress-tested slide by slide
  2. pitch-research-prompt.md — Research prompt for external AI data gathering
  3. pitch-deck.html      — The final HTML deck
  4. pitch-image-prompts.md — Image generation prompts

Ready to proceed?
```

Wait for confirmation.

### 5. Present Menu

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
- Output path confirmed
- User understands the deliverables and sequence
- User proceeds to next step

❌ **FAILURE:**
- Generating content before setup complete
- Wrong output path
- Proceeding without user confirmation
