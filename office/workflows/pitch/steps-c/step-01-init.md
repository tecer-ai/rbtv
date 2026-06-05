---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-context-gather.md
---

# Step 01: Initialize Pitch

**Progress: Step 1 of 10** — Next: Context Gathering

---

## STEP GOAL

Detect pitch context, resolve the output path via File Routing, and confirm scope.

**If pitch_type = client:** Also gather target client/audience details to inform routing and context discovery.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

**If pitch_type = investor:**
You are The Investor. From this point forward, every question you ask is the question a VC partner would ask before writing a check. Start as you mean to continue.

**If pitch_type = client:**
You are The Buyer. From this point forward, every question you ask is the question a procurement VP would ask before signing a contract. Start as you mean to continue.

### Step-Specific Rules

- Resolve output path via the `rbtv-output-resolution` rule — NEVER hardcode folder conventions
- Propose the resolved path and HALT for user approval before creating any directories

---

## MANDATORY SEQUENCE

### 1. Identify the Project

Check the conversation context:

**If project-memo was @-mentioned:**
- Read project-memo frontmatter: extract projectName
- Set {project_name} from projectName
- Confirm: "I see you're working on **{project_name}**."

**If no project-memo:**
- Ask: "What's the name of the project or company this pitch is for?"
- Set {project_name} from response

### 2. Understand the Target (client pitch only)

**If pitch_type = investor:** Skip this section.

**If pitch_type = client:**
Ask (only what's missing from conversation context):
- **Who is this pitch for?** A specific company? A segment? A type of buyer?
- **What's their role?** (CEO, CTO, procurement, department head, etc.)
- **What's the deal size?** (ballpark — this affects formality and detail level)
- **What do they use today?** (competitor, in-house solution, manual process, nothing)
- **What triggered this pitch?** (inbound interest, outbound prospecting, RFP, referral)
- **What language does the client operate in?** (pitch artifacts must be written in the client's language. Default: English.)

Set {target_client}, {deal_context}, and {artifact_language} from responses.

### 3. Resolve Output Path

Follow the `rbtv-output-resolution` rule:
1. Read the workspace CLAUDE.md for a `## File Routing` block
2. Match the output type (`pitch`) to a route
3. Resolve any variables from conversation context ({project_name}, {target_client}, round, fund, objective, date)
4. If the route has further CLAUDE.md refinement, follow it
5. Present the resolved path to the user and HALT for approval

Create these subfolders inside the approved output directory:

| Subfolder | Contents |
|-----------|----------|
| `artifacts/` | Workflow markdown outputs (narrative, research prompt, image prompts) |
| `assets/` | Images used in the pitch |
| `research/` | Research outputs generated during or for the pitch |

**If pitch_type = client:** Also create:

| Subfolder | Contents |
|-----------|----------|
| `meeting-transcript/` | Meeting transcript and notes |

HTML and PDF files (`pitch-deck.html`, `pitch-deck.pdf`) are saved at the output folder root.

Create folders ONLY after user approval.

### 4. Check for Existing Deck

Check if `{output_folder}/pitch-deck.html` exists:
- If YES: "I found an existing pitch deck. Would you like to **[R] Replace** it with a fresh build, or **[E] Exit** and use Edit mode instead?"
- If NO: Continue normally.

### 5. Confirm Setup

**If pitch_type = investor:**
Present summary:
```
Investor Pitch Setup:
- Project: {project_name}
- Output: {output_folder}/

Deliverables:
  1. artifacts/pitch-narrative.md        — The story, stress-tested slide by slide
  2. artifacts/pitch-research-prompt.md  — Research prompt for external AI data gathering
  3. pitch-deck.html                     — The final HTML deck
  4. artifacts/pitch-image-prompts.md    — Image generation prompts

Ready to proceed?
```

**If pitch_type = client:**
Present summary:
```
Client Pitch Setup:
- Project: {project_name}
- Target: {target_client}
- Deal context: {deal_context}
- Artifact language: {artifact_language}
- Output: {output_folder}/

Deliverables:
  1. artifacts/pitch-narrative.md        — The story, stress-tested from buyer's perspective
  2. artifacts/pitch-research-prompt.md  — Research prompt for external AI (proof points + buyer objections)
  3. pitch-deck.html                     — The final HTML deck
  4. artifacts/pitch-image-prompts.md    — Image generation prompts

Ready to proceed?
```

Wait for confirmation.

### 6. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to context gathering
- **[X] Exit** — exit workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
- Load `{nextStepFile}` (step-02-context-gather)

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Output path resolved via File Routing and explicitly approved by user
- Output folder and subfolders created only after approval
- User understands the deliverables and sequence

**If pitch_type = client:** Additionally:
- Target client and deal context understood
- Artifact language confirmed

❌ **FAILURE:**
- Hardcoding folder conventions instead of using File Routing
- Creating folders before user approves the path
- Proceeding without user confirmation
