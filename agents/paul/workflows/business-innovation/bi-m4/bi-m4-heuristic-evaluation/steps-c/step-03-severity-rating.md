---
name: 'step-03-severity-rating'
description: 'Rate severity of each violation (0-4 scale), prioritize issues'
nextStepFile: './step-04-recommendations.md'
outputFile: '{bmad_output}/{project-name}/business-innovation/m4-prototypation/heuristic-evaluation.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 3: Severity Rating

**Progress: Step 3 of 5** — Next: Recommendations

---

## STEP GOAL

Assign severity ratings (0-4 scale) to each violation identified in Step 2, prioritize issues by severity, and create a severity summary.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor helping the founder prioritize usability fixes. Be realistic about severity. Not everything is catastrophic. Focus on user impact.

### Step-Specific Rules
- Use the 0-4 severity scale consistently (reference framework knowledge)
- Consider frequency, impact, and persistence when rating
- Severity 3-4 issues MUST be flagged for immediate attention
- If founder disagrees with severity, discuss but document their final decision

---

## EXECUTION PROTOCOLS

1. Load violations from output document
2. For each violation, assess severity using 0-4 scale
3. Update violations with severity ratings
4. Generate severity summary (count by severity level)
5. Flag critical issues (severity 3-4)

---

## CONTEXT BOUNDARIES

**Available context:**
- Violations documented in Step 2
- Severity scale from framework knowledge (0-4)
- User flows and conversion goals from M4 outputs

**Out of scope:**
- Recommendations (that's step-04)
- Implementation effort (focus on user impact, not dev cost)

---

## MANDATORY SEQUENCE

### 1. Review Severity Scale

Present the severity scale to the founder:

---

**Severity Rating Scale (0-4):**

| Rating | Severity | Description | Action Required |
|--------|----------|-------------|-----------------|
| 0 | Not a problem | Not a usability issue | None |
| 1 | Cosmetic | Doesn't need fixing unless extra time | Fix if easy |
| 2 | Minor | Low priority, fix if time allows | Schedule for future |
| 3 | Major | Important to fix, causes confusion or errors | Fix before launch |
| 4 | Catastrophic | Imperative to fix, blocks critical tasks | Fix immediately |

**Severity Factors:**
- **Frequency:** How often does this problem occur?
- **Impact:** When it occurs, how difficult is it for users to overcome?
- **Persistence:** Is it a one-time problem or does it keep bothering users?

---

### 2. Rate Each Violation

For EACH violation documented in Step 2, work with the founder to assign a severity rating.

**Rating Process:**

For each violation, ask:
1. **Frequency:** "How often will users encounter this issue?" (every time, occasionally, rarely)
2. **Impact:** "When they encounter it, how much does it hinder them?" (blocks task, causes confusion, minor annoyance)
3. **Persistence:** "Is this a one-time issue or recurring?" (every session, one-time learning curve)

Based on answers, suggest a severity rating and get founder's confirmation.

**Example Dialogue:**

> **Mentor:** "Let's rate this violation: 'No loading indicator when submitting form.'"
> 
> **Frequency:** Every user, every form submission.
> **Impact:** Users don't know if their action worked. They might click multiple times, causing duplicate submissions.
> **Persistence:** Happens every time they submit.
> 
> **Suggested Severity: 3 (Major)** — This causes confusion and errors. Should be fixed before launch.
> 
> Do you agree, or would you rate it differently?

### 3. Update Violations with Severity Ratings

For each violation in the output document, add the severity rating:

```markdown
### Heuristic {N}: {Name}

**Violations:**

1. **Location:** {Screen/element}
   **Issue:** {What's wrong}
   **Example:** {Specific instance}
   **Severity: {0-4} — {Severity Name}**
   **Rationale:** {Brief explanation of severity factors}
```

### 4. Generate Severity Summary

Count violations by severity level and create a summary table:

```markdown
## Severity Summary

| Severity | Count | Violations |
|----------|-------|------------|
| 4 - Catastrophic | {count} | {list violation IDs or brief descriptions} |
| 3 - Major | {count} | {list violation IDs or brief descriptions} |
| 2 - Minor | {count} | {list violation IDs or brief descriptions} |
| 1 - Cosmetic | {count} | {list violation IDs or brief descriptions} |
| 0 - Not a problem | {count} | {list violation IDs or brief descriptions} |

**Total Violations:** {total count}

### Critical Issues (Severity 3-4)

{List all severity 3-4 violations with brief description}

**Action Required:** These {count} critical issues MUST be addressed before launch.
```

### 5. Flag Critical Issues

If any severity 3-4 violations exist, present a warning:

---

**🚨 CRITICAL USABILITY ISSUES IDENTIFIED 🚨**

You have {count} severity 3-4 violations that MUST be fixed before launch:

{List each critical violation with location and issue}

**Next Step:** In Step 4, we'll generate specific recommendations to fix these issues.

---

### 6. Update Output Document

Append the Severity Summary to the output document.

Update frontmatter: add `step-03-severity-rating.md` to `stepsCompleted`

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to recommendations

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Confirm all violations have severity ratings
2. Confirm severity summary is complete
3. Confirm frontmatter is updated
4. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 
- All violations have severity ratings (0-4)
- Severity ratings are justified with rationale
- Severity summary table is complete
- Critical issues (severity 3-4) are flagged
- Founder understands priority order

❌ **FAILURE:** 
- Assigning severity without founder input
- All violations rated the same severity
- No critical issues flagged (unlikely for most designs)
- Loading next step before [C] is selected
