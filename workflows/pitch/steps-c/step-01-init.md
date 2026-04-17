---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-context-gather.md
standaloneFallback: ./step-03-narrative.md
---

# Step 01: Initialize Pitch

**Progress: Step 1 of 10** — Next: Context Gathering

---

## STEP GOAL

**If pitch_type = investor:**
Detect project context, confirm investor pitch scope, and set output path.

**If pitch_type = client:**
Detect project context, understand the target client/audience, and set output path.

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

- Detect founder documents before asking questions
- Propose structured output path and HALT for user approval before creating any directories
- NEVER create folders before user explicitly approves the path

**If pitch_type = investor:**
- This workflow is exclusively for investor pitches (fundraising: VCs, angels, accelerators)

**If pitch_type = client:**
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
- Confirm: project detected message (see below)

**If no project-memo (standalone mode):**
- Set {mode}=standalone
- Ask: "What's the name of the project or company this pitch is for?"
- Set {project_name} from response

**If pitch_type = investor:**
- Confirm: "I see you're working on **{project_name}**. I'll pull content from your founder documents and then stress-test your pitch narrative before we build anything."

**If pitch_type = client:**
- Confirm: "I see you're working on **{project_name}**. I'll pull content from your founder documents and stress-test your pitch from the buyer's side of the table."

### 1b. Set Output Path

Propose a structured output folder path and HALT for user approval before creating any directories.

**Folder conventions:**

| pitch_type | Structure | Example |
|------------|-----------|---------|
| investor | `{output_path}/{project_name}/_fundraising/{round}/YYYY-MM-DD-{fund}/` | `_fundraising/seed/2026-03-17-sequoia/` |
| client | `{output_path}/{project_name}/_clients/{client}/presentations/YYYY-MM-DD-{objective}/` | `_clients/acme-corp/presentations/2026-03-17-initial-demo/` |

Subfolders created inside the output folder:

| Subfolder | Contents |
|-----------|----------|
| `artifacts/` | Workflow markdown outputs (narrative, research prompt, image prompts) |
| `assets/` | Images used in the pitch (replaces flat `images/` folder) |
| `research/` | Research outputs generated during or for the pitch workflow |
| `meeting-transcript/` | Meeting transcript and notes (**client pitches only** — not created for investor pitches) |

HTML and PDF files (`pitch-deck.html`, `pitch-deck.pdf`) are saved at the output folder root, not inside subfolders.

**If pitch_type = investor:**
- Ask for round context (e.g., "seed", "series-a", "pre-seed") and target fund name
- Propose: `{output_path}/{project_name}/_fundraising/{round}/YYYY-MM-DD-{fund}/`
- Use today's date for YYYY-MM-DD

**If pitch_type = client:**
- Use {target_client} from Section 2 (gathered below) — defer path proposal until after Section 2
- Ask for meeting objective (e.g., "initial-demo", "technical-deep-dive", "proposal")
- Propose: `{output_path}/{project_name}/_clients/{client}/presentations/YYYY-MM-DD-{objective}/`
- Use today's date for YYYY-MM-DD

Present the proposed full path and HALT:
- "Proposed output path: `{proposed_path}` — Approve, or provide an alternative path."
- Set {output_folder} from approved path
- Create the folder and all subfolders only AFTER user approval

### 2. Understand the Target Client (client pitch only)

**If pitch_type = investor:** Skip this section entirely.

**If pitch_type = client:**
Ask (only what's missing from conversation context):
- **Who is this pitch for?** A specific company? A segment? A type of buyer?
- **What's their role?** (CEO, CTO, procurement, department head, etc.)
- **What's the deal size?** (ballpark — this affects formality and detail level)
- **What do they use today?** (competitor, in-house solution, manual process, nothing)
- **What triggered this pitch?** (inbound interest, outbound prospecting, RFP, referral)
- **What language does the client operate in?** (pitch artifacts — narrative, deck, research prompt — must be written in the client's language, not the vendor's working language. Default: English.)

Set {target_client}, {deal_context}, and {artifact_language} from responses.

**After gathering client context:** Return to Section 1b to propose the output path using {target_client} and meeting objective. HALT for user approval before continuing.

### 3. Gather High-Level Context (Standalone Only)

**If {mode}=founder:** Skip — context will be gathered from documents in Step 02.

**If {mode}=standalone:**

**If pitch_type = investor:** Ask the following (only what's missing from conversation context):
- One-line description of what the company does
- Stage (pre-seed, seed, Series A, etc.)
- How much you're raising and what for
- Key differentiator or "why now"

**If pitch_type = client:** Ask the following (only what's missing):
- One-line description of what the company does
- Key differentiator vs. what the client uses today
- Price range or pricing model

### 4. Check for Existing Deck

Check if `{output_folder}/pitch-deck.html` exists (at the output folder root):
- If YES: "I found an existing pitch deck. Would you like to **[R] Replace** it with a fresh build, or **[E] Exit** and use Edit mode instead?"
- If NO: Continue normally.

### 5. Confirm Setup

**If pitch_type = investor:**
Present summary:
```
Investor Pitch Setup:
- Project: {project_name}
- Mode: {mode} (founder docs / standalone)
- Output: {output_folder}/
  ├── pitch-deck.html / .pdf
  ├── artifacts/    (narrative, research prompt, image prompts)
  ├── assets/       (images)
  └── research/     (research outputs)

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
- Mode: {mode} (founder docs / standalone)
- Output: {output_folder}/
  ├── pitch-deck.html / .pdf
  ├── artifacts/          (narrative, research prompt, image prompts)
  ├── assets/             (images)
  ├── research/           (research outputs)
  └── meeting-transcript/ (meeting notes)

Deliverables:
  1. artifacts/pitch-narrative.md        — The story, stress-tested slide by slide from buyer's perspective
  2. artifacts/pitch-research-prompt.md  — Research prompt for external AI (proof points + buyer objections)
  3. pitch-deck.html                     — The final HTML deck
  4. artifacts/pitch-image-prompts.md    — Image generation prompts

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
- Structured output path proposed and explicitly approved by user
- Output folder and subfolders created only after approval
- User understands the deliverables and sequence
- User proceeds to next step

**If pitch_type = client:** Additionally:
- Target client and deal context understood
- Artifact language confirmed (defaults to English if client language unknown)

❌ **FAILURE:**
- Generating content before setup complete
- Creating folders before user approves the path
- Using flat output path instead of structured conventions
- Proceeding without user confirmation

**If pitch_type = client:** Additionally:
- Not understanding who the pitch is FOR
