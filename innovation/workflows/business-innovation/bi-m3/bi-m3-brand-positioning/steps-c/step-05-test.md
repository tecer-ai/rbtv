---
name: 'step-05-test'
description: 'Run 4 validation tests: Uniqueness, Credibility, Relevance, Consistency'
nextStepFile: './step-06-synthesis.md'
outputFile: '{outputFolder}/brand-positioning.md'
---

# Step 5: Validation Tests

**Progress: Step 5 of 6** — Next: Synthesis

---

## STEP GOAL

Verify the positioning is unique, credible, relevant, and consistent through four systematic tests. Revise if any test fails.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Be rigorous. A failed test means revision, not rationalization. Position must pass ALL four tests.

### Step-Specific Rules
- ALL 4 tests are REQUIRED — no skipping
- If any test fails, MUST return to Step 3 for revision
- Document evidence for each test result
- Aspirational claims require gap-closing plan

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/brand-positioning.md` with Draft Statement and Perceptual Map
2. Read `{outputFolder}/golden-circle.md` for consistency check
3. Read `{outputFolder}/brand-prism.md` for consistency check (if exists)
4. Read `{outputFolder}/lean-canvas.md` for consistency check
5. Read `{outputFolder}/jobs-to-be-done.md` for relevance check

---

## MANDATORY SEQUENCE

### 1. Uniqueness Test

For each competitor on the perceptual map:

> "Read the positioning statement. Could [Competitor] credibly make the SAME claim?"

| Competitor | Could They Claim This? | Why/Why Not |
|------------|------------------------|-------------|
| [Name 1] | [Yes/No] | [Evidence] |
| [Name 2] | [Yes/No] | [Evidence] |
| [Name 3] | [Yes/No] | [Evidence] |
| ... | | |

**Result:**
- ✅ **PASS:** No competitor can credibly make the same claim
- ❌ **FAIL:** One or more competitors could make this claim

If FAIL:
> "The positioning is not unique. [Competitor] could make the same claim because [reason]. 
> Revision needed: [Specify which element to revise — benefit, alternative, or category frame]"

HALT — return to Step 3 with revision guidance.

### 2. Credibility Test

List evidence supporting the key benefit claim:

```markdown
### Credibility Evidence

| Evidence Type | Specific Evidence | Strength |
|---------------|-------------------|----------|
| Existing capability | [What you can do today] | [Strong/Moderate/Weak] |
| Customer testimonial | [Quote or reference] | [Strong/Moderate/Weak] |
| Technical architecture | [How it enables the benefit] | [Strong/Moderate/Weak] |
| Team expertise | [Relevant background] | [Strong/Moderate/Weak] |
| Partnership | [Supporting relationships] | [Strong/Moderate/Weak] |
```

Ask:
> "If a skeptical target customer investigated this claim, what would they find?"

**If claim is aspirational (not yet delivered):**

```markdown
### Aspirational Position Gap-Closing Plan

**Current state:** [What you can deliver today]
**Claimed position:** [What the statement promises]
**Gap:** [Difference between current and claimed]
**Plan to close gap:**
- [Action 1] by [timeframe]
- [Action 2] by [timeframe]
**Risk if gap not closed:** [Credibility damage]
```

**Result:**
- ✅ **PASS:** Evidence exists or credible gap-closing plan documented
- ❌ **FAIL:** No evidence and no credible plan

If FAIL:
> "The benefit claim '[benefit]' is not credible. No evidence exists and no path to deliver.
> Revision needed: Revise benefit to what you can credibly claim."

HALT — return to Step 3 with revision guidance.

### 3. Relevance Test

Compare positioning benefit to JTBD primary job:

```markdown
### Relevance Check

**Positioning benefit:** [Key benefit from statement]

**JTBD Primary Job:** [From jobs-to-be-done analysis]

**Alignment:**
- Does the benefit directly address the functional progress? [Yes/No — Evidence]
- Does the benefit address the emotional progress? [Yes/No — Evidence]
- Would the target immediately recognize their situation? [Yes/No — Evidence]
```

Ask:
> "If the target customer read this statement, would they immediately recognize their situation and need?"

**Result:**
- ✅ **PASS:** Benefit directly addresses JTBD, customer would recognize their situation
- ❌ **FAIL:** Benefit doesn't match job, customer wouldn't recognize themselves

If FAIL:
> "The positioning is accurate but irrelevant. The benefit '[benefit]' doesn't match the customer's job '[job]'.
> Revision needed: Revise benefit to connect to actual customer job."

HALT — return to Step 3 with revision guidance.

### 4. Consistency Test

Check alignment with upstream frameworks:

```markdown
### Consistency Check

**Golden Circle Alignment:**
- Why → Benefit: [Benefit connects to purpose?] [Yes/No — Evidence]
- How → Differentiation: [How principles visible in positioning?] [Yes/No — Evidence]
- What → Category: [Category matches What?] [Yes/No — Evidence]

**Brand Prism Alignment (if exists):**
- Physique → Category perception: [Aligned?] [Yes/No]
- Personality → Competitive tone: [Aligned?] [Yes/No]
- Relationship → Value delivery: [Aligned?] [Yes/No]

**Lean Canvas Alignment:**
- UVP → Positioning benefit: [Amplifies or contradicts?] [Amplifies/Contradicts]
```

**If inconsistencies found:**

| Inconsistency | Between | Resolution |
|---------------|---------|------------|
| [Description] | [Framework 1] vs [Framework 2] | [Update which framework] |

**Result:**
- ✅ **PASS:** All frameworks aligned, or inconsistencies resolved
- ❌ **FAIL:** Unresolved contradictions

If FAIL:
> "Positioning contradicts [framework]. [Specific contradiction].
> Resolution needed: Either update positioning or update [framework]."

Work with user to resolve before proceeding.

### 5. Document Test Results

Compile all test results:

```markdown
## Validation Tests

### Test Results Summary

| Test | Result | Key Evidence |
|------|--------|--------------|
| Uniqueness | ✅/❌ | [Summary] |
| Credibility | ✅/❌ | [Summary] |
| Relevance | ✅/❌ | [Summary] |
| Consistency | ✅/❌ | [Summary] |

### Detailed Results
[Full results from each test above]
```

### 6. Confirm All Tests Pass

If ALL 4 tests pass:
> "All validation tests passed. The positioning is unique, credible, relevant, and consistent. Ready for synthesis."

If ANY test failed:
> "Validation incomplete. [N] test(s) failed. Must revise positioning statement before proceeding."

HALT — return to Step 3.

### 7. Update Output Document

Add Validation Tests section to brand-positioning.md.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-inputs', 'step-03-draft', 'step-04-map', 'step-05-test']
```

### 8. Present Menu Options

**Select an Option:**
- **[R] Revise** — return to Step 3 to revise positioning statement
- **[C] Continue** — proceed to Synthesis (only if all tests pass)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected AND all 4 tests pass:
1. Verify all tests documented with evidence
2. Verify no failed tests
3. Load `./step-06-synthesis.md` and follow its instructions

If **[R] Revise** is selected:
1. Document which test(s) failed
2. Load `./step-03-draft.md` with revision guidance

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All 4 tests run with evidence, all passed, no contradictions unresolved

❌ **FAILURE:** Skipping tests, proceeding with failed tests, accepting "close enough" without revision
