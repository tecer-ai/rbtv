---
name: 'step-04-optimization-plan'
description: 'Prioritize hypotheses and create testing roadmap'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/conversion-optimization.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Optimization Plan

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

Prioritize optimization hypotheses using an Impact vs. Effort matrix and create a phased testing roadmap with clear success criteria for each experiment.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for ruthless prioritization. Founders want to fix everything at once. Force them to pick the highest-impact, lowest-effort changes first. Perfect is the enemy of shipped.

### Step-Specific Rules
- Quick wins (high impact, low effort) come first
- Every experiment needs measurable success criteria
- F&F testing phase = qualitative feedback, not statistical significance
- Maximum 5 changes per testing batch to isolate variables

---

## CONTEXT BOUNDARIES

**Available context:**
- conversion-optimization.md with all hypotheses
- data/conversion-framework.md for prioritization framework

**Out of scope:**
- A/B testing infrastructure setup
- Statistical analysis methodology
- Post-F&F scaling strategies

---

## MANDATORY SEQUENCE

### 1. Impact vs. Effort Assessment

For each hypothesis, assess:

**Impact (1-5):**
- 5: Addresses Critical friction, high expected conversion lift
- 4: Addresses Major friction, moderate conversion lift
- 3: Addresses Moderate friction, incremental improvement
- 2: Minor polish, small improvement
- 1: Cosmetic, negligible conversion impact

**Effort (1-5):**
- 1: Minutes to implement (copy change, color tweak)
- 2: Hours (layout adjustment, new section)
- 3: Half-day (significant redesign of a section)
- 4: Full day+ (structural changes, new functionality)
- 5: Multiple days (major rebuild)

Present assessment for each hypothesis:
> "**Hypothesis [N]: [Name]**
> - Impact: [1-5] — [rationale]
> - Effort: [1-5] — [rationale]
> 
> Do you agree with this assessment?"

### 2. Prioritization Matrix

Plot hypotheses on the matrix:

```
                    HIGH IMPACT
                         │
    ┌────────────────────┼────────────────────┐
    │   PLAN & SCHEDULE  │   DO FIRST         │
    │   (High Impact,    │   (High Impact,    │
    │    High Effort)    │    Low Effort)     │
    │                    │   ★ QUICK WINS ★   │
LOW ├────────────────────┼────────────────────┤ LOW
EFFORT                   │                      EFFORT
    │   DEPRIORITIZE     │   DO IF TIME        │
    │   (Low Impact,     │   (Low Impact,      │
    │    High Effort)    │    Low Effort)      │
    │                    │                      │
    └────────────────────┼────────────────────┘
                         │
                    LOW IMPACT
```

Present prioritized list:
> "**Priority Order:**
> 
> **Batch 1 — Quick Wins (Do First):**
> 1. [Hypothesis] — Impact: [5], Effort: [1]
> 2. [Hypothesis] — Impact: [4], Effort: [2]
> 
> **Batch 2 — Plan & Schedule:**
> 3. [Hypothesis] — Impact: [5], Effort: [4]
> 
> **Batch 3 — If Time Permits:**
> 4. [Hypothesis] — Impact: [2], Effort: [1]
> 
> **Deprioritized:**
> - [Hypothesis] — Low impact, high effort. Skip unless fundamentals change."

### 3. Success Criteria Definition

For each Batch 1 hypothesis, define:

**Qualitative Success (F&F Testing):**
- What questions will testers answer?
- What observed behaviors indicate success?
- What feedback themes indicate success?

**Quantitative Proxy (if measurable):**
- Scroll depth
- Time on page
- Click-through to CTA
- Form completion rate

Example:
> "**Hypothesis 1: Simplified Hero Headline**
> 
> **Qualitative Success:**
> - 4/5 testers can explain product value within 5 seconds
> - No tester asks 'What is this?' in first 10 seconds
> - Zero confusion comments about purpose
> 
> **Quantitative Proxy:**
> - Time-to-scroll decreases (users engage faster)
> - Bounce rate proxy: testers proceed past hero"

### 4. Testing Roadmap

Create phased roadmap:

**Phase 1: Pre-F&F Implementation (Before Testing)**
- [ ] Implement Batch 1 quick wins
- [ ] Document baseline state (screenshots, current copy)
- Timeline: [X hours/days]

**Phase 2: F&F Testing Round 1**
- Test Batch 1 changes with 3-5 testers
- Gather qualitative feedback
- Success criteria: [list]

**Phase 3: Iterate**
- If success criteria met: Move to Batch 2
- If not met: Revise hypotheses based on feedback

**Phase 4: F&F Testing Round 2 (Optional)**
- Test Batch 2 changes if time permits

### 5. Implementation Checklist

For Batch 1 quick wins, create specific action items:

| # | Hypothesis | Action | File/Element | Before | After |
|---|------------|--------|--------------|--------|-------|
| 1 | [Name] | [Change X] | [hero section] | [current] | [new] |

### 6. Update Output Document

Add to conversion-optimization.md:

```markdown
## Prioritization Matrix

### Impact/Effort Assessment

| # | Hypothesis | Impact | Effort | Quadrant |
|---|------------|--------|--------|----------|
| 1 | [Name] | [5] | [1] | Quick Win |
| 2 | ... | ... | ... | ... |

### Priority Batches

#### Batch 1: Quick Wins (Implement Now)
1. **[Hypothesis Name]** — [Brief description]
   - Impact: [5], Effort: [1]
   - Success Criteria: [qualitative + quantitative]

#### Batch 2: Plan & Schedule
[List]

#### Batch 3: If Time Permits
[List]

#### Deprioritized
[List with rationale]

## Testing Roadmap

### Phase 1: Pre-F&F Implementation
- [ ] [Action item]
- Timeline: [estimate]

### Phase 2: F&F Testing Round 1
- Testers: [3-5]
- Test Batch 1 changes
- Success criteria: [list]

### Phase 3: Iterate
- If met: Proceed to Batch 2
- If not: Revise based on feedback

### Implementation Checklist

| # | Action | Element | Before | After | Status |
|---|--------|---------|--------|-------|--------|
| 1 | ... | ... | ... | ... | [ ] |
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-funnel-mapping', 'step-03-hypothesis-generation', 'step-04-optimization-plan']
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify Prioritization Matrix and Testing Roadmap sections are complete
2. Verify Batch 1 has specific success criteria
3. Verify frontmatter updated with `step-04-optimization-plan`
4. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All hypotheses assessed for impact/effort, clear batch prioritization, Batch 1 has measurable success criteria, founder agreed on priority order

❌ **FAILURE:** No prioritization (trying to do everything), missing success criteria, vague timeline, not getting founder buy-in on priorities
