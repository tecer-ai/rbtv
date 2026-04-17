---
name: 'step-02-job-hypotheses'
description: 'Turn Working Backwards into 3-5 job hypotheses'
nextStepFile: './step-03-interview.md'
outputFile: '{outputFolder}/jobs-to-be-done.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: Job Hypotheses

**Progress: Step 2 of 5** — Next: Interview Design

---

## STEP GOAL

Transform the Working Backwards PR/FAQ into 3-5 explicit, testable job hypotheses using the "When / I want to / so I can" format.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Challenge job statements that are features in disguise. Push for situation specificity. Reject vague outcomes.

### Step-Specific Rules
- Each job must stand alone WITHOUT mentioning the product
- Jobs must have concrete situation triggers, not just demographics
- Tag each job with its dominant type (functional, emotional, social)
- Limit to 3-5 sharp hypotheses — more isn't better

---

## CONTEXT BOUNDARIES

**Available context:**
- working-backwards.md (Customer & Problem Brief, Press Release, FAQs)
- jobs-to-be-done.md from Step 1
- JTBD framework knowledge

**Out of scope:**
- Running actual interviews (that's Step 3)
- Synthesizing job stories (that's Step 4)

---

## MANDATORY SEQUENCE

### 1. Extract Progress Signals

Guide founder through Working Backwards with a JTBD lens:

> "Let's re-read your Press Release and FAQs looking for **progress signals** — phrases where customers are trying to achieve or avoid something."

Have founder identify phrases like:
- "ship faster", "avoid errors", "prove impact", "feel in control"
- Any statement about what changes for the customer

### 2. Situation Discovery

For each progress signal, ask:

> "When does this matter? What triggers this need?"

Capture:
- Specific time contexts (end-of-month, board meeting prep, feature launch)
- Event triggers (customer complaint, stakeholder request, deadline)
- Environmental factors (team size, tool stack, growth stage)

### 3. Progress Framing

For each situation, ask:

> "What progress are they trying to make? What's the 'before' state and 'after' state?"

Capture:
- Current state pain points
- Desired outcome (not features)
- What happens if they fail

### 4. Draft Job Statements

Help founder draft 3-7 raw job statements:

**Format:** "When [situation/trigger], I want to [progress], so I can [ultimate outcome]."

For each draft:
- Tag dominant type: Functional / Emotional / Social
- Check: Does this mention our product? (If yes, reframe)
- Check: Is the situation concrete? (If no, specify)

### 5. Filter and Prioritize

Remove or merge jobs that are:
- Features in disguise ("When I use the dashboard, I want to filter quickly")
- Too broad ("grow my business" without scope)
- Duplicates with different wording

Select 3-5 sharp hypotheses for stress-testing via interviews.

### 6. Update Output Document

Update jobs-to-be-done.md Job Hypotheses section:

```markdown
## Job Hypotheses

### Hypothesis 1: [Short Name]
**Type:** [Functional/Emotional/Social]

**Job Statement:** When [situation], I want to [progress], so I can [outcome].

**Validation Need:** [What would prove/disprove this hypothesis]

### Hypothesis 2: [Short Name]
...

### Hypothesis 3: [Short Name]
...
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-job-hypotheses']
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Interview Design

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify 3-5 job hypotheses documented
2. Verify each hypothesis has type tag and validation need
3. Verify `step-02-job-hypotheses` is in `stepsCompleted`
4. Load `./step-03-interview.md` and follow its instructions

- Dig deeper into specific hypotheses
- Challenge assumptions, explore edge cases
- Return to this menu after exploration

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 3-5 job hypotheses in correct format, each with situation trigger and type tag, none mention the product

❌ **FAILURE:** Jobs that are features in disguise, vague situations, more than 5 hypotheses, product mentioned in job statements
