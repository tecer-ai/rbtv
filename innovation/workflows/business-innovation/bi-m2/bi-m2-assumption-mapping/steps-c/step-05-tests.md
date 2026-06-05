---
name: 'step-05-tests'
description: 'Design lightweight test cards for Test assumptions'
nextStepFile: './step-06-synthesis.md'
outputFile: '{outputFolder}/assumption-mapping.md'
---

# Step 5: Design Test Cards

**Progress: Step 5 of 6** — Next: Synthesis

---

## STEP GOAL

Create a test card for each "Test" assumption with a clear hypothesis, lightweight method, concrete success/failure signals, and timeline.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for lightweight tests. Reject vague signals like "seems interested." Connect failure signals to kill criteria.

### Step-Specific Rules
- Total test timeline should be 2-4 weeks max
- Use the lightest-weight method that produces credible evidence
- If > 10 Test assumptions, prioritize to top 5-7
- Group assumptions that can be tested together

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/assumption-mapping.md` for Test assumptions (ranked)
2. Read `{outputFolder}/leap-of-faith.md` for kill criteria and observable signals
3. Reference M2 downstream frameworks: TAM/SAM/SOM, Unit Economics, TRL, Pre-mortem

---

## MANDATORY SEQUENCE

### 1. Test Queue Review

If more than 10 Test assumptions:
> "You have [N] assumptions to test. That's too many for 2-4 weeks. Let's ruthlessly prioritize to the top 5-7 that:
> - Have the highest combined scores
> - Include all kill criteria
> - Can be grouped for efficient testing
>
> Which ones are truly essential to validate before proceeding?"

Otherwise:
> "You have [N] assumptions in the Test quadrant. Let's design tests for each, starting with the highest priority."

### 2. Test Method Options

Present available test methods:

| Method | Best For | Timeline |
|--------|----------|----------|
| Desk research | Market data, competitor analysis, public data | Days |
| Customer interviews (5-10) | Behavioural assumptions, pain validation | 1-2 weeks |
| Landing page / smoke test | Demand validation, willingness to engage | 1-2 weeks |
| Technical spike / PoC | Technical feasibility, performance | 1-2 weeks |
| Financial modeling | Economic assumptions, sensitivity analysis | Days |
| Expert consultation | Domain-specific unknowns | Days |

### 3. Design Test Cards

For each Test assumption (in rank order), create a test card:

**Prompt for each:**
> "For [AM-XX]: [Statement]
>
> **Hypothesis:** If this is true, what observable outcome would we see?
>
> **Method:** What's the lightest-weight test that produces credible evidence?
>
> **Success Signal:** What specific evidence validates this? Be concrete — not 'people seem interested.'
>
> **Failure Signal:** What evidence invalidates it? If this is a kill criterion, what triggers kill?
>
> **Timeline:** How long will this test take? (Prefer days or weeks, not months)
>
> **Owner:** Who runs this test?
>
> **Downstream:** Which M2 framework will consume this evidence?"

### 4. Grouping Opportunities

Identify assumptions that can be tested together:
> "I notice [AM-XX] and [AM-YY] could both be tested in a single interview round. Should we group them?
>
> Grouped tests are more efficient but need clear success/failure signals for each assumption within the group."

### 5. Timeline Validation

Sum all test timelines:
- **If > 4 weeks:** "The total timeline is [N] weeks. That's too long for this stage. Can we:
  - Run some tests in parallel?
  - Use faster methods for some?
  - Defer lower-priority tests?"

### 6. Document Test Cards

Update assumption-mapping.md:

```markdown
## Test Cards

### Test Card: AM-01

**Assumption:** We assume that [statement]

**Hypothesis:** If [assumption] is true, then [observable outcome]

**Test Method:** [Method]

**Success Signal:** [Concrete evidence that validates]

**Failure Signal:** [Concrete evidence that invalidates — connect to kill criteria]

**Timeline:** [X days/weeks]

**Owner:** [Who]

**Downstream Framework:** [TAM/SAM/SOM / Unit Economics / TRL / Pre-mortem]

---

### Test Card: AM-02

[Repeat for each Test assumption]

---

### Validation Backlog

| Priority | ID | Test Method | Timeline | Owner | Downstream |
|----------|-----|-------------|----------|-------|------------|
| 1 | AM-01 | [Method] | [Time] | [Who] | [Framework] |
| 2 | AM-02 | [Method] | [Time] | [Who] | [Framework] |
| ... | ... | ... | ... | ... | ... |

**Total Timeline:** [X weeks]

**Dependencies:**
- [Note any sequencing constraints between tests]
```

### 7. Kill Criteria Connection

Verify at least one test card connects to Leap of Faith kill criteria:
> "Which of these tests, if failed, would trigger a kill decision from Leap of Faith?"

Document this connection explicitly in the relevant test card's Failure Signal.

### 8. Update Frontmatter

Update stepsCompleted:
```yaml
stepsCompleted: ['step-01-init', 'step-02-collect', 'step-03-rate', 'step-04-matrix', 'step-05-tests']
```

### 9. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis
- **[R] Revise** — adjust test cards

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify every Test assumption has a test card
2. Verify success/failure signals are concrete
3. Verify total timeline ≤ 4 weeks
4. Verify at least one test connects to kill criteria
5. Verify `step-05-tests` is in `stepsCompleted`
6. Load `./step-06-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All Test assumptions have cards, concrete signals, timeline ≤ 4 weeks, kill criteria connected

❌ **FAILURE:** Vague signals, over-engineered tests, timeline > 4 weeks, no kill criteria connection
