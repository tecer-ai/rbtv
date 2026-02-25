---
name: 'step-04-assumptions'
description: 'Extract and tag critical assumptions for validation'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/problem-solution-fit.md'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Critical Assumptions

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

Turn implicit beliefs embedded in the canvas into explicit, tagged assumptions that will drive M2 validation work.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for uncomfortable assumptions — the ones that would collapse the entire canvas if wrong. Comfortable assumptions don't need validation.

### Step-Specific Rules
- Every assumption must be tagged with category (behavioural, technical, economic)
- Priority 5-10 assumptions that, if wrong, destroy problem-solution fit
- Cross-reference Internal FAQ assumptions from Working Backwards
- Assumptions must be falsifiable — if you can't imagine a test, it's not an assumption

---

## CONTEXT TO LOAD

1. problem-solution-fit.md with Steps 2-3 content
2. working-backwards.md (Internal FAQ, especially economics and feasibility sections)

---

## MANDATORY SEQUENCE

### 1. Systematic Extraction

Work through each canvas area, asking for assumptions:

**Problem assumptions:**
> "Looking at your problem mapping, what must be true for this to be a real problem?
> - Frequency: How often does this problem occur?
> - Intensity: How painful is it when it happens?
> - Awareness: Do customers recognize they have this problem?"

**Behaviour assumptions:**
> "For your behaviour mapping, what must be true for customers to change?
> - Willingness: Are customers motivated to change current behaviour?
> - Ability: Can they actually adopt a new approach?"

**Constraint assumptions:**
> "For your constraint mapping, what must be true about limits?
> - Are budget constraints real or assumed?
> - Are approval processes as rigid as described?"

**Solution assumptions:**
> "For your solution to work, what must be true?
> - Will customers accept this new workflow?
> - Does the core mechanism actually deliver value?"

### 2. Write Assumption Statements

For each assumption, write as "This assumes that..." statement:

| ID | Assumption | Category |
|----|------------|----------|
| PSF-1 | This assumes that [customer] experiences [problem] at least [frequency] | Behavioural |
| PSF-2 | This assumes that [customer] is willing to [change behaviour] | Behavioural |
| PSF-3 | This assumes that [technical capability] is feasible | Technical |
| PSF-4 | This assumes that [customer] can afford [price point] | Economic |

### 3. Categorize Assumptions

Apply categories:
- **Behavioural:** About customers and their context (frequency, willingness, ability)
- **Technical:** About feasibility and performance (can we build it, will it work)
- **Economic:** About pricing, costs, market size, buying process

For each assumption:
> "Is this about customer behaviour, technical feasibility, or economics?"

### 4. Prioritize Critical Assumptions

From all assumptions, identify 5-10 most critical:
> "Which assumptions would collapse your entire canvas if wrong?
>
> Rate each:
> - **Impact if wrong:** Does the problem disappear? Does the solution fail?
> - **Confidence level:** How certain are you it's true?"

Create priority list:

| Rank | ID | Assumption | Impact if Wrong | Confidence |
|------|-----|------------|-----------------|------------|
| 1 | PSF-X | ... | Problem disappears | Low |
| 2 | PSF-Y | ... | Solution fails | Medium |

### 5. Cross-Reference Internal FAQ

From Working Backwards Internal FAQ:
> "Your Internal FAQ raised assumptions about economics and feasibility. Let's check if they're captured:
>
> - [List assumptions from Internal FAQ]
>
> Are these already in our list? Any we missed?"

Maintain consistent IDs/labels so M2 Leap of Faith mapping can reuse them.

### 6. Falsifiability Check

For each critical assumption:
> "How would you know this assumption is WRONG? What evidence would falsify it?"

If no test is imaginable:
> "This isn't really an assumption — it's a hope. Can we make it more specific?"

### 7. Draft Assumptions Block

Collaboratively draft "Critical Assumptions" canvas block:

**Category: Behavioural**
- PSF-1: [Assumption] — Priority: [High/Medium] — Test: [How to falsify]
- PSF-2: [Assumption] — Priority: [High/Medium] — Test: [How to falsify]

**Category: Technical**
- PSF-3: [Assumption] — Priority: [High/Medium] — Test: [How to falsify]

**Category: Economic**
- PSF-4: [Assumption] — Priority: [High/Medium] — Test: [How to falsify]

### 8. Validation Checklist

Before proceeding, confirm:
- [ ] At least one assumption for each canvas area (problem, behaviours, solution, constraints)
- [ ] At least 5 assumptions tagged and categorized
- [ ] Top 3-5 assumptions feel uncomfortable (if wrong, canvas collapses)
- [ ] Each assumption has a falsifiable test

If any fail, iterate before continuing.

### 9. Update Output Document

Update problem-solution-fit.md with "Critical Assumptions" section.

### 10. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — go deeper on specific assumptions
- **[P] Party Mode** — get multi-perspective challenge on assumptions
- **[C] Continue** — proceed to Synthesis

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify "Critical Assumptions" block is complete with categories and priorities
2. Update frontmatter: add `step-04-assumptions` to `stepsCompleted`
3. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 5-10 assumptions extracted, categorized, prioritized, and tagged with falsifiable tests

❌ **FAILURE:** Only comfortable assumptions listed, missing categories, no falsifiability check, missing cross-reference to Internal FAQ
