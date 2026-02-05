---
name: 'step-04-recommendations'
description: 'Generate prioritized improvement recommendations with rationale'
nextStepFile: './step-05-synthesis.md'
outputFile: '{project-root}/_bmad-output/{project-name}/founder/m4-prototypation/heuristic-evaluation.md'
---

# Step 4: Recommendations

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

Generate specific, actionable recommendations to fix each violation, prioritized by severity and effort, with implementation guidance.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor helping the founder create an actionable fix list. Be specific. Provide examples. Prioritize ruthlessly.

### Step-Specific Rules
- Every severity 3-4 violation MUST have a recommendation
- Recommendations must be specific and actionable (not "improve UX")
- Include effort estimates (hours or days, not "low/medium/high")
- Identify quick wins (high severity, low effort)
- If founder lacks design skills, suggest no-code solutions or simple fixes

---

## EXECUTION PROTOCOLS

1. Load violations and severity ratings from output document
2. For each violation (prioritizing severity 3-4), generate recommendations
3. Estimate effort for each recommendation
4. Identify quick wins (high impact, low effort)
5. Create prioritized recommendations list

---

## CONTEXT BOUNDARIES

**Available context:**
- Violations with severity ratings from Step 3
- Nielsen's heuristics and best practices from framework knowledge
- Founder's technical capabilities and resources

**Out of scope:**
- Implementation details (focus on what to fix, not how to code it)
- Design aesthetics (focus on usability, not visual design)

---

## MANDATORY SEQUENCE

### 1. Review Violations by Priority

Load the Severity Summary from Step 3. Focus on severity 3-4 violations first, then 2, then 1.

### 2. Generate Recommendations for Each Violation

For EACH violation (starting with severity 3-4), work with the founder to create a recommendation.

**Recommendation Template:**

```markdown
**Violation:** {Brief description}
**Heuristic:** {Which heuristic was violated}
**Severity:** {0-4}

**Recommendation:**
{Specific, actionable fix}

**Example/Guidance:**
{Show what good looks like, reference patterns, provide examples}

**Effort Estimate:** {hours or days}
**Priority:** {Critical / High / Medium / Low}
```

**Example Recommendation:**

```markdown
**Violation:** No loading indicator when submitting form
**Heuristic:** Visibility of System Status
**Severity:** 3 (Major)

**Recommendation:**
Add a loading spinner and disable the submit button immediately after click. Display "Submitting..." text below the button.

**Example/Guidance:**
- Use a simple CSS spinner (no need for complex animations)
- Change button text from "Submit" to "Submitting..." while loading
- Disable button to prevent double-clicks
- On success, show "Submitted successfully!" with checkmark icon
- On error, re-enable button and show error message

**Effort Estimate:** 2-4 hours
**Priority:** Critical (Severity 3, blocks user confidence)
```

### 3. Identify Quick Wins

Quick wins are high-severity violations with low-effort fixes. These should be tackled first.

**Quick Win Criteria:**
- Severity 3-4 (high impact)
- Effort < 1 day (low effort)
- No dependencies on other fixes

Create a "Quick Wins" section:

```markdown
## Quick Wins (High Impact, Low Effort)

These fixes provide the most value for the least effort. Tackle these first:

1. **{Violation}** — {Brief recommendation} — Effort: {hours}
2. **{Violation}** — {Brief recommendation} — Effort: {hours}
3. {Additional quick wins}
```

### 4. Create Prioritized Recommendations List

Organize all recommendations by priority:

```markdown
## Prioritized Recommendations

### Critical (Fix Immediately)

Severity 4 violations that block critical tasks:

1. **{Violation}**
   - **Recommendation:** {Fix}
   - **Effort:** {estimate}
   - **Impact:** {what improves}

{Additional critical recommendations}

---

### High Priority (Fix Before Launch)

Severity 3 violations that cause confusion or errors:

1. **{Violation}**
   - **Recommendation:** {Fix}
   - **Effort:** {estimate}
   - **Impact:** {what improves}

{Additional high priority recommendations}

---

### Medium Priority (Fix If Time Allows)

Severity 2 violations that are annoying but not blocking:

1. **{Violation}**
   - **Recommendation:** {Fix}
   - **Effort:** {estimate}
   - **Impact:** {what improves}

{Additional medium priority recommendations}

---

### Low Priority (Nice to Have)

Severity 1 cosmetic issues:

1. **{Violation}**
   - **Recommendation:** {Fix}
   - **Effort:** {estimate}
   - **Impact:** {what improves}

{Additional low priority recommendations}
```

### 5. Estimate Total Effort

Calculate total effort for each priority tier:

```markdown
## Effort Summary

| Priority | Count | Total Effort |
|----------|-------|--------------|
| Critical | {count} | {hours/days} |
| High | {count} | {hours/days} |
| Medium | {count} | {hours/days} |
| Low | {count} | {hours/days} |

**Total Effort (All Fixes):** {hours/days}
**Critical + High Priority Effort:** {hours/days}

**Recommendation:** Focus on Critical and High priority fixes before launch. Medium and Low can be addressed post-launch based on user feedback.
```

### 6. Provide Implementation Guidance

Add a section with general guidance:

```markdown
## Implementation Guidance

**Approach:**
1. Start with Quick Wins (high impact, low effort)
2. Fix all Critical issues (severity 4)
3. Fix all High Priority issues (severity 3)
4. Re-evaluate Medium/Low priority after user testing

**Resources:**
- Nielsen Norman Group articles: https://www.nngroup.com/articles/
- Web Content Accessibility Guidelines (WCAG): https://www.w3.org/WAI/WCAG21/quickref/
- UI patterns library: https://ui-patterns.com/

**Next Steps:**
- Implement fixes in design/prototype
- Re-run heuristic evaluation after major changes
- Conduct user testing to validate fixes
```

### 7. Update Output Document

Append all recommendations sections to the output document.

Update frontmatter: add `step-04-recommendations.md` to `stepsCompleted`

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — discuss any recommendation in detail
- **[P] Party Mode** — get multi-agent perspectives on prioritization
- **[C] Continue** — proceed to synthesis

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Confirm all violations have recommendations
2. Confirm prioritization is complete
3. Confirm effort estimates are documented
4. Confirm frontmatter is updated
5. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 
- All severity 3-4 violations have specific recommendations
- Recommendations are actionable with examples
- Effort estimates are realistic
- Quick wins identified
- Prioritized list is clear and complete
- Total effort calculated

❌ **FAILURE:** 
- Vague recommendations ("improve UX")
- No effort estimates
- All recommendations same priority
- Generating recommendations without founder input
- Loading next step before [C] is selected
