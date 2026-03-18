---
name: 'step-05-synthesis'
description: 'Model break-even, run sensitivity analysis, update project-memo'
nextStepFile: null
outputFile: '{outputFolder}/unit-economics.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Model break-even analysis, run sensitivity analysis to identify critical assumptions, consolidate findings, and update project-memo.md with Unit Economics synthesis.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Identify which single assumption, if wrong, kills the business. Wire critical assumptions into other M2 frameworks.

### Step-Specific Rules
- MUST model break-even with realistic fixed costs (including founder salaries)
- MUST identify top 3-5 critical assumptions by impact
- MUST define validation/invalidation criteria for each
- MUST update project-memo.md with synthesis

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/unit-economics.md` for all assumptions
2. Review Lean Canvas Cost Structure for fixed costs
3. Read `{outputFolder}/project-memo.md` for update location

---

## MANDATORY SEQUENCE

### 1. Model Break-Even Analysis

#### Fixed Costs Inventory

List all monthly fixed costs:

| Category | Monthly Cost | Notes |
|----------|--------------|-------|
| Founder salaries (imputed) | $[X] | Don't use $0 |
| Team salaries | $[X] | |
| Office/workspace | $[X] | |
| Tools/software | $[X] | |
| Infrastructure (fixed) | $[X] | |
| Legal/accounting | $[X] | |
| Other | $[X] | |
| **Total Monthly Fixed Costs** | $[X] | |

#### Break-Even Calculation

```
Monthly Contribution Per Customer = Monthly ARPU × Gross Margin %
Break-Even Customers = Monthly Fixed Costs / Monthly Contribution
```

| Scenario | Fixed Costs | Contribution/Customer | Break-Even Customers |
|----------|-------------|----------------------|---------------------|
| Pessimistic | $[X] | $[X] | [X] customers |
| Base | $[X] | $[X] | [X] customers |
| Optimistic | $[X] | $[X] | [X] customers |

#### Reality Check

Compare break-even to SOM:
> "Break-even requires [X] customers. Your Year 1 SOM is [Y] customers. This represents [Z]% of SOM.
> 
> [If >30% of SOM]: ⚠️ Break-even requires capturing >30% of your addressable market in Year 1. This is aggressive."

#### Break-Even Timeline

Model the path with growth and churn:

| Month | New Customers | Churned | Net Customers | Revenue | Costs | Cash Position |
|-------|---------------|---------|---------------|---------|-------|---------------|
| 1 | [X] | 0 | [X] | $[X] | $[X] | $[X] |
| ... | | | | | | |
| [N] | | | **Break-even** | | | |

Identify:
- **Operating break-even month:** [X]
- **Total capital required to reach break-even:** $[X]

### 2. Run Sensitivity Analysis

#### One-at-a-Time Sensitivity

For each key assumption, vary from pessimistic to optimistic while holding others at base:

| Assumption | Pessimistic | Base | Optimistic | Impact on LTV:CAC |
|------------|-------------|------|------------|-------------------|
| Monthly Churn | X% → Y:1 | X% → Y:1 | X% → Y:1 | [High/Med/Low] |
| ARPU | $X → Y:1 | $X → Y:1 | $X → Y:1 | [High/Med/Low] |
| CAC | $X → Y:1 | $X → Y:1 | $X → Y:1 | [High/Med/Low] |
| Gross Margin | X% → Y:1 | X% → Y:1 | X% → Y:1 | [High/Med/Low] |
| Growth Rate | X → Y mo BE | X → Y mo BE | X → Y mo BE | [High/Med/Low] |

#### Identify Critical Assumptions

Rank by impact magnitude:

> "Your top 3-5 critical economic assumptions are:
> 1. **[Assumption]** — If wrong, [impact]. Because [reasoning].
> 2. **[Assumption]** — If wrong, [impact]. Because [reasoning].
> 3. **[Assumption]** — If wrong, [impact]. Because [reasoning]."

### 3. Define Validation Criteria

For each critical assumption:

| Assumption | Validation Evidence | Invalidation Evidence | Test Method | Timeline |
|------------|--------------------|-----------------------|-------------|----------|
| [Assumption 1] | [What would validate] | [What would kill] | [Method] | [When] |
| [Assumption 2] | [What would validate] | [What would kill] | [Method] | [When] |
| [Assumption 3] | [What would validate] | [What would kill] | [Method] | [When] |

### 4. Wire Into M2 Frameworks

Connect to other M2 work:
- **Assumption Mapping:** Add critical economic assumptions to high-importance quadrant
- **Leap of Faith:** Add as growth hypothesis assumptions
- **Pre-mortem:** Flag as financial failure modes

> "These critical assumptions should be added to:
> - Assumption Mapping: [List IDs]
> - Pre-mortem: [List as failure modes]"

### 5. Create Master Assumptions Table

Consolidate ALL assumptions from Steps 2-4:

| ID | Assumption | Base | Pessimistic | Optimistic | Source | Confidence | Critical? |
|----|------------|------|-------------|------------|--------|------------|-----------|
| REV-1 | [Description] | [X] | [X] | [X] | [source] | [H/M/L] | [Yes/No] |
| CAC-1 | [Description] | [X] | [X] | [X] | [source] | [H/M/L] | [Yes/No] |
| LTV-1 | [Description] | [X] | [X] | [X] | [source] | [H/M/L] | [Yes/No] |
| BE-1 | [Description] | [X] | [X] | [X] | [source] | [H/M/L] | [Yes/No] |

### 6. Synthesize Viability Conclusion

Write a clear viability statement:

> "## Viability Assessment
>
> **Base Case:** [Viable/Marginal/Non-viable]. LTV:CAC of [X]:1, payback of [X] months, break-even at [X] customers.
>
> **Pessimistic Case:** [Viable/Marginal/Non-viable]. LTV:CAC of [X]:1. [What breaks if true].
>
> **Critical Assumption:** The single assumption that most affects viability is [X]. If wrong, [consequence].
>
> **Capital Requirement:** $[X] to reach break-even under base assumptions.
>
> **Recommendation:** [Proceed / Validate assumptions first / Revisit pricing/costs]"

### 7. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md` for M2.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 8. Update Output Document

Finalize unit-economics.md with:
- Break-even analysis
- Sensitivity analysis
- Critical assumptions with validation criteria
- Master Assumptions Table
- Viability conclusion

Update frontmatter:
- Add `step-05-synthesis` to `stepsCompleted`
- Set `status: completed`

### 9. Update project-memo.md

Add Unit Economics synthesis to project-memo.md:

**In Validation Progress section:**
```markdown
### Unit Economics
**Status:** Complete
**LTV:CAC Ratio:** [Base: X:1 | Pessimistic: Y:1]
**Payback Period:** [X] months
**Break-even:** [X] customers, [Y] months
**Capital Required:** $[X]
**Viability:** [Viable/Marginal/Non-viable]

**Critical Assumptions:**
1. [Assumption]: [Validation needed]
2. [Assumption]: [Validation needed]

**Integration:** Assumptions wired to Assumption Mapping, Pre-mortem
```

Update project-memo.md frontmatter: add `bi-m2-unit-economics` to `stepsCompleted`

### 10. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 11. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M2.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M2 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 12. Present Completion Summary

> "## Unit Economics Complete
>
> **Key Findings:**
> - LTV:CAC: [X]:1 (base) / [Y]:1 (pessimistic)
> - Payback: [X] months
> - Break-even: [X] customers requiring $[Y] capital
> - Critical assumptions: [List top 3]
>
> **Next Steps:**
> - Return to M2 workflow for remaining frameworks
> - Validate critical assumptions through [Assumption Mapping / market testing]
>
> [Return to M2 Milestone workflow]"

---

## VALIDATION CHECKLIST

Before completing, verify:
- [ ] Break-even includes founder salaries (not $0)
- [ ] Break-even customer count is realistic vs SOM
- [ ] Top 3-5 critical assumptions are explicitly identified
- [ ] Each critical assumption has validation/invalidation criteria
- [ ] Viability conclusion is honest about pessimistic scenario
- [ ] project-memo.md is updated with synthesis

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Break-even modelled, critical assumptions identified, project-memo updated

❌ **FAILURE:** $0 founder salaries, no sensitivity analysis, optimistic-only conclusion
