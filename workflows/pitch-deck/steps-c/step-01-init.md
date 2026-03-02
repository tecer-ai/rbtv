---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-context-gather.md
standaloneFallback: ./step-03-structure.md
---

# Step 01: Initialize Pitch Deck

**Progress: Step 1 of 6** — Next: Context Gathering

---

## STEP GOAL

Determine pitch type, detect project context, and set output path.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Pitch Deck Architect. Every question you ask should move toward building a deck that earns its right to exist. No wasted words, no unnecessary process.

### Step-Specific Rules

- Detect founder documents before asking questions
- Determine pitch type before discussing content
- Set output path based on project context

---

## MANDATORY SEQUENCE

### 1. Detect Project Context

Check the conversation context:

**If project-memo was @-mentioned (founder mode):**
- Read project-memo frontmatter: extract projectName
- Set {mode}=founder
- Set {project_name} from projectName
- Set {output_folder}=`{project-root}/_bmad-output/{project_name}/_fundraising/pitch-deck`
- Confirm: "I see you're working on **{project_name}**. I'll pull content from your founder documents to build the deck."

**If no project-memo (standalone mode):**
- Set {mode}=standalone
- Ask: "What's the name of the project or company this pitch is for?"
- Set {project_name} from response
- Ask: "Where should I save the pitch deck? Default: `_bmad-output/{project_name}/_fundraising/pitch-deck`"
- Set {output_folder} from response or default

### 2. Determine Pitch Type

Present options:
```
What type of pitch deck are you building?

[1] Investor Pitch — For fundraising (VCs, angels, accelerators)
    Focus: Problem, traction, market size, team, the ask

[2] Client Pitch — For winning customers or partnerships
    Focus: Their problem, your solution, proof points, pricing/next steps
```

Wait for selection. Set {pitch_type}.

### 3. Gather High-Level Context (Standalone Only)

**If {mode}=founder:** Skip this section — context will be gathered from documents in Step 02.

**If {mode}=standalone:** Ask the following (only what's missing from conversation context):
- One-line description of what the company does
- Stage (pre-seed, seed, Series A, etc.) — for investor pitch
- Target audience for the pitch
- Key differentiator or "why now"

### 4. Check for Existing Deck

Check if `{output_folder}/pitch-deck.html` exists:
- If YES: "I found an existing pitch deck. Would you like to **[R] Replace** it with a fresh build, or **[E] Exit** and use Edit mode instead?"
- If NO: Continue normally.

### 5. Confirm Setup

Present summary:
```
Pitch Deck Setup:
- Project: {project_name}
- Type: {pitch_type}
- Mode: {mode} (founder docs / standalone)
- Output: {output_folder}/pitch-deck.html
- Images: {output_folder}/images/

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
- If {mode}=standalone: Load `{standaloneFallback}` (step-03-structure — skip context-gather)

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Pitch type determined (investor or client)
- Mode detected (founder or standalone)
- Output path confirmed
- User proceeds to next step

❌ **FAILURE:**
- Generating content before setup complete
- Skipping pitch type selection
- Wrong output path
- Proceeding without user confirmation
