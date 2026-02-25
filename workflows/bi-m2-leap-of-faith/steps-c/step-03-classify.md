---
name: 'step-03-classify'
description: 'Sort assumptions into Value vs Growth hypotheses with sub-categories'
nextStepFile: './step-04-prioritize.md'
outputFile: '{outputFolder}/leap-of-faith.md'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 3: Classify Assumptions

**Progress: Step 3 of 5** — Next: Prioritize Assumptions

---

## STEP GOAL

Sort every assumption into Value Hypothesis or Growth Hypothesis with specific sub-categories, enabling targeted validation design.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. A product that solves a real problem but can't be sold profitably fails just as surely as one solving a non-existent problem. Force the founder to examine both sides.

### Step-Specific Rules
- Every assumption from the Inventory MUST be classified — none left unassigned
- MUST have assumptions in BOTH Value and Growth categories
- Boundary cases must be documented with reasoning, not silently shoved into one category
- Do NOT score or prioritize in this step — that's for Step 4

---

## CONTEXT BOUNDARIES

**Available context:**
- Consolidated Assumption Inventory from Step 2
- M1 artefacts for reference
- Framework methodology from data/leap-of-faith-framework.md

**Out of scope:**
- Impact/Uncertainty scoring (Step 4)
- Validation signal design (Step 5)

---

## MANDATORY SEQUENCE

### 1. Review Inventory

Load the Consolidated Assumption Inventory from leap-of-faith.md.

Count: [N] assumptions to classify.

### 2. Explain Classification Framework

Present to founder:

> "We'll classify each assumption into two fundamental types:
>
> **Value Hypothesis:** Beliefs about customers and the problem/solution
> - Problem Existence: Does this pain actually exist?
> - Problem Severity: Is it painful enough to motivate action?
> - Solution Fit: Does our solution address the pain?
> - Willingness to Switch: Will they switch from current workaround?
> - Retention & Habit: Will they keep using it?
>
> **Growth Hypothesis:** Beliefs about the business model and economics
> - Channel Effectiveness: Can we reach customers this way?
> - Acquisition Cost: Can we afford to acquire customers?
> - Conversion Rate: Will prospects convert at this rate?
> - Pricing & WTP: Will they pay this price?
> - Revenue Model: Will this revenue structure work?
> - Retention Economics: Will renewals sustain the business?
> - Referral & Virality: Will customers refer others?
> - Market Size: Is the market large enough?"

### 3. Classify Each Assumption

For each assumption in the Inventory:

1. Read the statement aloud
2. Ask: "Is this primarily about customer/problem/solution (Value) or business/economics (Growth)?"
3. Assign sub-category
4. Handle boundary cases explicitly:
   - Willingness to Pay: Growth if "will they pay X?"; Value if "is value large enough that any price is plausible?"
   - Retention: Value if "does product deliver ongoing value?"; Growth if "does pricing/engagement model sustain renewals?"
   - When in doubt: classify under BOTH with notes explaining different angles

Present classifications to founder for review after each batch of ~5 assumptions.

### 4. Build Classified Register

Reorganise assumptions into structured register:

```markdown
## Classified Assumption Register

### Value Hypotheses

#### Problem Existence
| ID | Statement | Sub-Category | Source |
|----|-----------|--------------|--------|
| LOF-003 | We assume that... | Problem Existence | JTBD > Job Story 1 |

**Summary Hypothesis:** We believe that [customer segment] experiences [specific pain] at [frequency/severity].

#### Problem Severity
...

#### Solution Fit
...

#### Willingness to Switch
...

#### Retention & Habit
...

---

### Growth Hypotheses

#### Channel Effectiveness
...

#### Acquisition Cost
...

[etc.]
```

### 5. Write Summary Hypotheses

For each sub-category with 2+ assumptions, write a one-sentence summary:

> "We believe that [specific belief about this sub-category] (based on LOF-003, LOF-007, LOF-012)."

These summary hypotheses should be specific enough that a stranger could design a validation test without reading the source artefacts.

### 6. Validation Check

Review with founder:

- [ ] Every assumption classified — **none left unassigned**
- [ ] Assumptions in **BOTH** Value and Growth categories
- [ ] Each sub-category has at least one assumption OR is marked "not applicable" with rationale
- [ ] Summary hypotheses are **specific and testable**
- [ ] Boundary cases documented with **explicit reasoning**

If all assumptions are in one category: "You've only examined [Value/Growth]. Let's review [the other] — what are you assuming about [customer behaviour / business economics]?"

### 7. Update Output Document

Update leap-of-faith.md with Classified Assumption Register.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-harvest', 'step-03-classify']
```

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — challenge classification of specific assumptions
- **[P] Party Mode** — get multi-agent perspectives on boundary cases
- **[C] Continue** — proceed to Prioritize Assumptions

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all assumptions are classified with no gaps
2. Verify assumptions exist in both Value and Growth categories
3. Update frontmatter with `step-03-classify` in `stepsCompleted`
4. Load `./step-04-prioritize.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All assumptions classified into Value/Growth with sub-categories, summary hypotheses written, boundary cases documented

❌ **FAILURE:** Leaving assumptions unclassified, all assumptions in one category, skipping summary hypotheses
