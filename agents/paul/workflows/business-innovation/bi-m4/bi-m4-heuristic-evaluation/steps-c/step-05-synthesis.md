---
name: 'step-05-synthesis'
description: 'Synthesize findings, update project-memo.md, return to M4 menu'
nextStepFile: '../../workflow.md'
outputFile: '{bmad_output}/{project-name}/business-innovation/m4-prototypation/heuristic-evaluation.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Next: Return to M4 Prototypation Menu

---

## STEP GOAL

Synthesize heuristic evaluation findings, update project-memo.md with key insights, and return to the M4 milestone menu.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor helping the founder synthesize usability findings into actionable insights. Focus on patterns, critical issues, and next steps.

### Step-Specific Rules
- Identify patterns across violations (same heuristic violated repeatedly)
- Highlight critical issues (severity 3-4) for immediate action
- Update project-memo.md with synthesis (MANDATORY)
- Instruct return to M4 menu after synthesis (MANDATORY)

---

## EXECUTION PROTOCOLS

1. Load complete heuristic evaluation output
2. Identify patterns and themes
3. Synthesize key findings
4. Update project-memo.md with synthesis
5. Mark framework complete in frontmatter
6. Instruct return to M4 milestone menu

---

## CONTEXT BOUNDARIES

**Available context:**
- Complete heuristic evaluation output (violations, severity, recommendations)
- project-memo.md for project context
- M4 outputs (User Flow & IA, Design Brief, Conversion-Centered Design if completed)

**Out of scope:**
- Implementation (that happens outside this framework)
- User testing (next step after fixes are implemented)

---

## MANDATORY SEQUENCE

### 1. Load Complete Evaluation Output

Read the complete `{outputFile}` including:
- All violations by heuristic
- Severity summary
- Prioritized recommendations
- Quick wins
- Effort estimates

### 2. Identify Patterns and Themes

Analyze the violations to identify patterns:

**Pattern Analysis Questions:**

1. **Heuristic Patterns:** Which heuristic(s) are violated most frequently?
2. **Severity Patterns:** Are most violations cosmetic or critical?
3. **Location Patterns:** Are violations concentrated in specific screens/flows?
4. **Theme Patterns:** Do violations share common themes (e.g., lack of feedback, inconsistent terminology)?

Present findings to the founder:

---

**Pattern Analysis:**

**Most Violated Heuristics:**
- {Heuristic name}: {count} violations — {pattern observation}
- {Heuristic name}: {count} violations — {pattern observation}

**Severity Distribution:**
- Critical (4): {count}
- Major (3): {count}
- Minor (2): {count}
- Cosmetic (1): {count}

**Common Themes:**
- {Theme 1}: {description and examples}
- {Theme 2}: {description and examples}

**Interpretation:**
{What do these patterns tell us about the design? Are there systemic issues or isolated problems?}

---

### 3. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/agents/paul/workflows/business-innovation/data/founder-process.md` for M4.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 4. Synthesize Key Findings

Create a synthesis section in the output document:

```markdown
## Synthesis

### Executive Summary

**Evaluation Date:** {date}
**Scope:** {screens/flows evaluated}
**Total Violations:** {count}
**Critical Issues (Severity 3-4):** {count}
**Estimated Fix Effort (Critical + High):** {hours/days}

### Key Findings

1. **{Finding 1}** — {Brief description with severity context}
2. **{Finding 2}** — {Brief description with severity context}
3. **{Finding 3}** — {Brief description with severity context}

### Patterns Identified

**Most Violated Heuristics:**
- {Heuristic}: {count} violations — {why this matters}

**Common Themes:**
- {Theme}: {description and impact}

### Critical Actions Required

Before launch, you MUST address these {count} critical issues:

1. **{Violation}** — {Brief fix}
2. **{Violation}** — {Brief fix}
3. {Additional critical issues}

**Estimated Effort:** {hours/days}

### Recommended Next Steps

1. **Immediate (This Week):**
   - Fix all Quick Wins (high impact, low effort)
   - Address all Critical issues (severity 4)

2. **Before Launch:**
   - Fix all High Priority issues (severity 3)
   - Re-run heuristic evaluation on updated design

3. **Post-Launch (Based on User Feedback):**
   - Address Medium Priority issues (severity 2)
   - Consider Low Priority fixes (severity 1)

4. **Validation:**
   - Conduct user testing after implementing fixes
   - Monitor analytics for usability friction points
   - Iterate based on real user behavior

### Assumptions to Validate in M5

{List any usability assumptions that should be tested with real users in M5 Market Validation}

Example:
- "Users will understand the terminology we're using" (test in customer interviews)
- "The conversion flow is intuitive" (test with smoke test or prototype)

### Integration with Other M4 Frameworks

**User Flow & IA:**
- {How heuristic findings relate to flow design}

**Conversion-Centered Design:**
- {How usability issues impact conversion}

**Design Direction:**
- {How findings inform design refinements}
```

### 5. Update project-memo.md

**CRITICAL:** Load `{bmad_output}/{project-name}/business-innovation/project-memo.md`

Add synthesis to the M4 Prototypation section:

```markdown
#### Heuristic Evaluation

**Completed:** {date}
**Total Violations:** {count}
**Critical Issues:** {count severity 3-4}
**Estimated Fix Effort:** {hours/days}

**Key Findings:**
- {Finding 1}
- {Finding 2}
- {Finding 3}

**Critical Actions:**
- {Action 1}
- {Action 2}

**Status:** {count} critical issues identified, fixes required before launch.

**Output:** `m4-prototypation/heuristic-evaluation.md`
```

Update frontmatter in project-memo.md:
- Add `bi-m4-heuristic-evaluation/workflow.md` to `stepsCompleted`
- Update `lastUpdated` to current date

### 6. Mark Framework Complete

Update frontmatter in `{outputFile}`:
- Add `step-05-synthesis.md` to `stepsCompleted`
- Add `frameworkComplete: true`
- Add `completionDate: {current date}`

### 7. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 8. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M4.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M4 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 9. Present Completion Summary

Present this summary to the founder:

---

**🎉 Heuristic Evaluation Complete!**

**What You've Accomplished:**
- Evaluated design against all 10 Nielsen usability heuristics
- Identified {count} violations across {count} heuristics
- Rated severity of each violation (0-4 scale)
- Generated {count} prioritized recommendations
- Identified {count} quick wins (high impact, low effort)
- Flagged {count} critical issues requiring immediate attention

**Critical Next Steps:**
1. Fix all Quick Wins ({count} items, ~{hours} effort)
2. Address all Critical issues (severity 4)
3. Fix High Priority issues (severity 3) before launch
4. Re-run heuristic evaluation after implementing fixes

**Output Saved:**
- `m4-prototypation/heuristic-evaluation.md`
- `project-memo.md` updated with synthesis

**Estimated Fix Effort (Critical + High):** {hours/days}

---

### 10. Instruct Return to M4 Menu

**CRITICAL:** After presenting the summary, instruct:

> "Heuristic Evaluation framework is complete. To continue with M4 Prototypation, load `../../workflow.md` to return to the milestone menu and select your next framework."

HALT and wait for user to load the M4 workflow.

---

## CRITICAL STEP COMPLETION NOTE

After presenting the completion summary:
1. Confirm synthesis is added to output document
2. Confirm project-memo.md is updated
3. Confirm frontmatter is updated in both files
4. Instruct user to load `{nextStepFile}` (M4 workflow)
5. DO NOT auto-load the next file — user must explicitly load it

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 
- Patterns identified across violations
- Key findings synthesized (3-5 main points)
- Critical actions clearly stated
- project-memo.md updated with synthesis
- Founder understands next steps
- Return to M4 menu instructed

❌ **FAILURE:** 
- No pattern analysis
- Synthesis missing from project-memo.md
- Frontmatter not updated
- Auto-loading M4 workflow without user action
- Vague next steps
