---
name: 'step-02-problem-framing'
description: 'Select and frame concrete problem scenario for 5 Whys analysis'
nextStepFile: './step-03-why-chain.md'
outputFile: '{outputFolder}/five-whys.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: Problem Framing

**Progress: Step 2 of 5** — Next: Run 5 Whys Chains

---

## STEP GOAL

Produce a single, unambiguous Anchor Problem Statement and Scenario Brief that will anchor all subsequent 5 Whys chains.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for one specific scenario. Reject "in general" or "typically" — demand concrete situations with named actors.

### Step-Specific Rules
- ONE scenario only — other scenarios are explicitly parked for later
- Anchor Problem Statement must NOT mention the product
- Scenario must be traceable to prior M1 artefacts
- Do NOT run 5 Whys chains in this step — that's Step 3

---

## CONTEXT BOUNDARIES

**Available context:**
- five-whys.md from Step 1
- working-backwards.md (Customer & Problem Brief, External/Internal FAQ)
- jobs-to-be-done.md (struggling moments, alternatives)
- problem-solution-fit.md (behaviours, constraints)
- lean-canvas.md (Problem block, Customer Segments)

**Out of scope:**
- Running actual 5 Whys chains (Step 3)
- Synthesizing root causes (Step 4)

---

## MANDATORY SEQUENCE

### 1. Extract Problem Candidates

From prior M1 artefacts, extract problem candidates:

**From Working Backwards:**
- Primary customer and problem from Press Release
- Objections and edge cases from External FAQ
- Key assumptions and risks from Internal FAQ

**From JTBD:**
- 1-3 recurring struggling moments where the problem is most acute
- Current alternatives and behaviours in those moments

**From Lean Canvas:**
- Problem block contents
- Customer Segments
- Any metrics or symptoms noted

Present candidates to founder:
> "Based on your M1 work, here are the problem scenarios we could analyse..."

### 2. Scenario Selection

Ask the founder:
> "Which single scenario should we analyse with 5 Whys? Consider:
> - One customer segment (e.g., 'product managers at B2B SaaS companies')
> - One recurring situation (e.g., 'end of month reporting when data is fragmented')
>
> We need a scenario specific enough that we can trace why it happens."

Wait for selection. Challenge if too broad:
- "That covers multiple situations — which one hurts most?"
- "Can you name a real company or person in this scenario?"

### 3. Draft Anchor Problem Statement

Collaboratively draft the Anchor Problem Statement (1-2 sentences):

Requirements:
- Describes the problem **as experienced in that scenario**
- Does NOT mention your product — must make sense even if your solution didn't exist
- Specific enough that a neutral reader can restate it

Present draft and ask:
> "Does this capture what's happening without referencing our solution?"

### 4. Draft Scenario Brief

Collaboratively draft the Scenario Brief (5-8 sentences):

**Must include:**
- Who is involved (role, company type)
- When it happens (trigger event, frequency)
- What tools/processes are in play
- What "bad outcome" they're trying to avoid
- Relevant constraints (budget, time, approvals, skills)

Present draft and confirm with founder.

### 5. Traceability Check

Verify the problem is traceable to M1 artefacts:

| Artefact | Connection |
|----------|------------|
| Working Backwards | [How it connects] |
| JTBD | [How it connects] |
| Problem-Solution Fit | [How it connects] |
| Lean Canvas | [How it connects] |

Ask: "Can you confirm this scenario appears in your prior M1 work?"

### 6. Validation Checklist

Before proceeding, confirm:
- [ ] Can name at least 3 real organisations or people who fit the scenario
- [ ] A neutral reader can restate the problem and scenario without seeing other documents
- [ ] Anchor Problem Statement is directly traceable to M1 artefacts
- [ ] Analysing ONE scenario only — others explicitly parked

If any fail, iterate before continuing.

### 7. Update Output Document

Update five-whys.md with:

```markdown
## Anchor Problem Statement

{The drafted problem statement}

## Scenario Brief

{The drafted scenario brief}

### Traceability

| Artefact | Connection |
|----------|------------|
| Working Backwards | ... |
| JTBD | ... |
| Problem-Solution Fit | ... |
| Lean Canvas | ... |
```

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine problem statement or scenario brief
- **[P] Party Mode** — get multi-perspective challenge on problem framing
- **[C] Continue** — proceed to Run 5 Whys Chains

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure Anchor Problem Statement and Scenario Brief are saved
2. Update frontmatter: add `step-02-problem-framing` to `stepsCompleted`
3. Load `./step-03-why-chain.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** One specific scenario selected, Anchor Problem Statement drafted without product mention, Scenario Brief complete with constraints, traceability verified

❌ **FAILURE:** Multiple scenarios selected, problem mentions solution, scenario too vague to analyse, skipping validation
