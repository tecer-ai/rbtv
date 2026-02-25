---
name: 'step-02-problem-space'
description: 'Map problem, triggers, emotions, behaviours, and constraints'
nextStepFile: './step-03-solution-space.md'
outputFile: '{outputFolder}/problem-solution-fit.md'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: Problem Space Mapping

**Progress: Step 2 of 5** — Next: Solution Articulation

---

## STEP GOAL

Build the problem-side of the canvas: Problem-Space Brief, Problem/Triggers/Emotions blocks, and Alternatives/Behaviours/Constraints blocks.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for specificity in situations and triggers. Reject generic language. If the founder says "sometimes" or "often," ask for concrete moments.

### Step-Specific Rules
- Problem-Space Brief MUST define exactly one segment and one situation
- Problem statement must NOT mention the solution
- Every trigger must be anchored in a specific observable context
- Do NOT articulate the solution in this step — that's Step 3

---

## CONTEXT TO LOAD

1. problem-solution-fit.md from step-01
2. working-backwards.md (Customer & Problem Brief, PR, FAQ)
3. jobs-to-be-done.md (job statements, struggling moments, alternatives)

---

## MANDATORY SEQUENCE

### 1. Problem-Space Brief

Extract from Working Backwards and JTBD:
- Primary customer archetype
- Problem description from Press Release
- Primary job statement from JTBD
- Current alternatives from JTBD

Ask founder to confirm scope:
> "Based on your prior work, let's define scope:
>
> **Customer segment:** [extracted description]
> **Situation:** [when this problem recurs]
>
> Is this the segment and situation we're focused on?"

If multiple segments exist:
> "You've identified multiple segments. This canvas must focus on ONE. Which is highest priority?"

Document:
- **In scope:** segment and situation this canvas covers
- **Out of scope:** segments or situations deliberately excluded and why

### 2. Problem, Triggers, and Emotions

**Problem situations (3-7):**
Ask: "Describe 3-5 concrete moments when this problem shows up. For each:
- Observable context (when, where, with whom, using which tools)
- Negative consequence if not handled"

Create table:

| Situation | Context | Consequence |
|-----------|---------|-------------|
| 1 | ... | ... |

**Triggers to act:**
For each situation, ask:
> "What makes the customer stop tolerating the status quo and do something?
> - Internal triggers: frustration, fear, pressure?
> - External triggers: deadlines, audits, incidents?"

**Emotional states:**
For each situation:
> "How does the customer feel BEFORE resolution? How do they want to feel AFTER?"

Synthesize into canvas blocks:
- **Problem:** 3-5 sentences describing recurring pain in situ
- **Triggers:** Bullet list of main triggers to action
- **Emotions:** Bullet list of before/after emotional states

### 3. Alternatives, Behaviours, and Constraints

**Current behaviours:**
Ask: "When this problem appears, what does the customer do? Walk me through their steps — include low-tech workarounds like spreadsheets, emails, manual processes."

**Available solutions:**
Ask: "What alternatives exist? Include:
- Direct competitors
- Adjacent tools
- Manual processes
- 'Do nothing' option

For each, what's unsatisfying about it for this segment?"

**Constraints and limitations:**
Ask: "What limits adoption of new solutions for this customer?
- Financial (budget, cost structure)?
- Time and attention (competing priorities)?
- Skills and tools (technical literacy)?
- Organisational (approvals, compliance, IT/security)?"

**Channels of behaviour:**
Ask: "Where do these behaviours happen? Which tools, systems, or communication channels are involved?"

Synthesize into canvas blocks:
- **Available Solutions:** List with one-line drawback per alternative
- **Behaviour:** Key patterns and coping strategies
- **Channels of Behaviour:** Where problem-related actions live
- **Customer Constraints:** Explicit limitations

### 4. Validation Checklist

Before proceeding, confirm:
- [ ] Problem-Space Brief names exactly one segment and one situation
- [ ] Can name at least 3 real organisations/people who fit
- [ ] Problem statement makes sense without mentioning product
- [ ] At least one situation describes customers who currently do nothing
- [ ] Constraints list is specific enough to invalidate certain solution ideas

If any fail, iterate before continuing.

### 5. Update Output Document

Update problem-solution-fit.md with:
- Problem-Space Brief (including in-scope/out-of-scope)
- Problem, Triggers, and Emotions blocks
- Alternatives, Behaviours, Channels, and Constraints blocks

### 6. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on problem situations or constraints
- **[P] Party Mode** — get multi-perspective challenge on problem mapping
- **[C] Continue** — proceed to Solution Articulation

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all problem-side canvas blocks are complete
2. Update frontmatter: add `step-02-problem-space` to `stepsCompleted`
3. Load `./step-03-solution-space.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Problem-Space Brief defines narrow scope, all problem-side blocks complete, validation checklist passed

❌ **FAILURE:** Multiple segments mixed in one canvas, problem mentions solution, skipping constraint analysis, accepting vague situations
