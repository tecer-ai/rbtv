# Judge Evaluation Criteria

Reference knowledge for the judge task. Defines the five quality criteria and verdict format.

---

## Five Quality Criteria

Each must **PASS** for approval.

### Criterion 1: Completeness

**Question:** Does the work address all aspects of the task?

| PASS | FAIL |
|------|------|
| Every deliverable present | Any deliverable missing |
| All requirements fulfilled | Any requirement unaddressed |
| Scope fully covered | Work partial or incomplete |

**Feedback must specify:** Exactly what's missing or incomplete.

### Criterion 2: Accuracy

**Question:** Is the work factually and technically correct?

| PASS | FAIL |
|------|------|
| Information factually accurate | Factual errors present |
| Logic and structure correct | Logic errors or contradictions |
| References point to real files | References broken or wrong |
| Follows specifications | Misinterprets specifications |

**Feedback must specify:** What is incorrect and what the correct version should be.

### Criterion 3: Clarity

**Question:** Is the work understandable and well-structured?

| PASS | FAIL |
|------|------|
| Clear, logical structure | Confusing or unclear |
| Easy to understand | Poor structure |
| Appropriate detail level | Too vague or verbose |
| Good formatting | Formatting issues |

**Feedback must specify:** What's unclear and how to improve clarity.

### Criterion 4: Consistency

**Question:** Does the work align with provided context and existing patterns?

| PASS | FAIL |
|------|------|
| Follows architecture decisions | Contradicts architecture |
| Respects conventions | Ignores conventions |
| Matches existing style | Mismatches style |
| Adheres to cursor rules | Violated cursor rules |
| Followed documented processes | Skipped process steps |

**Feedback must specify:** What's inconsistent and what should be followed.

### Criterion 5: Quality

**Question:** Does the work meet professional standards?

| PASS | FAIL |
|------|------|
| Production-ready | Rough draft quality |
| Complete and thorough | Incomplete or partial |
| Professional presentation | Unprofessional |
| No rough edges | Obvious quality issues |

**Feedback must specify:** What quality issues exist and what standard requires.

---

## Verdict Format

```markdown
### Judge Verdict

**Status:** APPROVED | REJECTED

**Criteria:**
- Completeness: PASS | FAIL - [specific reason if FAIL]
- Accuracy: PASS | FAIL - [specific reason if FAIL]
- Clarity: PASS | FAIL - [specific reason if FAIL]
- Consistency: PASS | FAIL - [specific reason if FAIL]
- Quality: PASS | FAIL - [specific reason if FAIL]

**Feedback:**
[If REJECTED: Specific, actionable guidance on what to fix - ALL issues across ALL criteria]
[For simple fixes: Provide the exact correction (e.g., "Change 'teh' to 'the' on line 45")]
[If APPROVED: Optional brief acknowledgment]
```

---

## Feedback Standards

| BAD | GOOD |
|-----|------|
| "The documentation is unclear." | "Section 2.3 doesn't explain the setup process. Add the three key steps." |
| "This doesn't follow conventions." | "Task IDs must use `p[phase]-[number]` format. Change `task-1` to `p1-1`." |
| "There's a typo." | "Line 45: Change 'teh' to 'the'." |
| "Fix the formatting." | "Lines 12-15: Indent code blocks with 4 spaces instead of 2 tabs." |

---

## Critical Evaluation Rules

1. **Assume mistakes exist** — Never give benefit of the doubt
2. **Verify deliverables yourself** — Read actual files, don't trust summaries
3. **All feedback at once** — Never withhold known issues for later iterations
4. **Be specific and actionable** — What's wrong, where, how to fix
5. **Don't do the agent's job** — Evaluate, don't implement

---

## Edge Cases

| Case | Action |
|------|--------|
| Agent claims unable to complete | FAIL Completeness if workaround exists they missed |
| Partial success (80% good) | REJECT — quality gates are binary |
| Uncertainty in evaluation | When in doubt, FAIL |
| Disagree with requirements | Evaluate against requirements anyway, note concerns |

---

## Debugger Mode Format

Use after 5 consecutive rejections with same criterion failing:

```markdown
### Debugger Analysis (After 5 Same-Pattern Rejections)

**Repeated Failure:** [Which criterion keeps failing]

**Root Cause Analysis:**

1. **Is the task achievable as specified?**
   [Analysis]

2. **What critical context is missing?**
   [What agent needs but doesn't have]

3. **Is this a capability limitation?**
   [Whether doable with available tools]

**Recommendation:** (A) Task needs redefinition | (B) Missing context | (C) Capability limitation

**Suggested Next Steps:**
[What should happen to unblock]
```
