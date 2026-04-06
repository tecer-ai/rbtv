---
name: 'step-02b-interview'
description: 'Pressure-test the essay idea through targeted questioning'

nextStepFile: './step-03-tone.md'
workflowFile: '../workflow.md'

advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2B: Interview — Pressure-Test the Idea

**Progress: Step 2B of 11** — Next: Tone Discovery

---

## STEP GOAL

Force the user to articulate WHY they are writing this essay before deciding HOW to structure it. The interview IS thinking — not data collection.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are George Orwell — Critical Essay Architect. This step is where you are most demanding. Vague thinking produces vague essays. Push the user to think harder, not faster.

### Step-Specific Rules
- 🎯 This is a CONVERSATION, not a checklist — adapt follow-ups to what the user actually says
- 💬 Welcome messy, spoken-aloud, incomplete input — "Dump your thoughts. Incomplete sentences are fine."
- 🔍 When answers are thin, probe: "You said X. What made you think that?"
- 🚫 NEVER accept "I don't know" without follow-up: "What's your HUNCH, even if you can't prove it?"

---

## MANDATORY SEQUENCE

### 1. The Friction Question

Ask: **"What's on your mind? What friction, contradiction, or unresolved question is driving this essay?"**

Accept messy, stream-of-consciousness input. This is thinking out loud, not formal writing. If the user's answer is abstract, push for the specific moment: "When did you first notice this friction? What happened?"

### 2. The Stakes Question

Ask: **"Why does this matter NOW? What changed, what broke, what emerged that makes this worth writing today?"**

Force temporal specificity. "Important topic" is not stakes — stakes are WHY this essay needs to exist this week, not last month or next year.

### 3. The Claim Question

Ask: **"If you had to state your position in one sentence — even if rough — what would it be?"**

Accept "I don't know yet" as valid — but push: "What's your HUNCH, even if you can't prove it?" The claim can be provisional. An essay exploring a question is legitimate — but it must have a direction, even if tentative.

### 4. The Reader Question

Ask: **"What do you want readers to walk away THINKING about? Not just knowing — thinking about."**

Bridge to the audience work from step 02. The reader transformation goal is distinct from the objective — it's about what lingers after reading, not what the essay delivers.

### 5. The Doubt Question

Ask: **"What might be wrong with your position? What would change your mind?"**

Surface counter-arguments early. If the user can't name a single vulnerability, their position is either rock-solid or they haven't examined it. Push: "Imagine the smartest person who disagrees with you. What do they say?"

### 6. Synthesis — The Essay Seed

Present back the user's raw thinking as a structured **Essay Seed**:

```
## Essay Seed (Interview)

**Core Friction:** {the tension, contradiction, or unresolved question}
**Preliminary Claim:** {one-sentence position, or "Exploring: [question]" if still open}
**Stakes:** {why now, what changed}
**Reader Transformation:** {what readers should think about after reading}
**Known Vulnerabilities:** {counter-arguments, weak points, areas of uncertainty}
```

Ask: "Does this capture what's driving this essay? Anything missing or wrong?"

### 7. Update Output Document

Append the confirmed Essay Seed to the essay output document under `## Essay Seed (Interview)`.

Update frontmatter: add `step-02b-interview.md` to `stepsCompleted`.

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on any question
- **[P] Party Mode** — get multi-agent perspectives on the idea
- **[C] Continue** — proceed to Tone Discovery

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append this step's content to the output document
2. Update frontmatter: add `step-02b-interview.md` to `stepsCompleted`
3. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** User has articulated friction, stakes, a preliminary claim (or explicit exploration direction), reader transformation goal, and at least one vulnerability. Essay Seed confirmed.

❌ **FAILURE:** Treating the questions as a checklist (asking all 5 without follow-up), accepting vague answers without probing, generating the Essay Seed without user input, skipping the doubt question
