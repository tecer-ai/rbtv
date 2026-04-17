# Learnings Template

Use this template to create the `learnings.md` companion file for each plan. Learnings captures system improvement opportunities discovered during execution.

---

## Template

```markdown
# Learnings - {Plan Name}

> **Purpose:** This document captures system improvement opportunities for BMAD/RBTV discovered during plan execution. These are META-learnings about how the system could be improved, NOT project-specific learnings.

---

## What Belongs Here

| Include | Exclude |
|---------|---------|
| User corrections to agent behavior | Project-specific decisions |
| Missing rules or unclear instructions | Implementation details |
| Workflow gaps or friction points | Task-specific context |
| Tool limitations discovered | Bug fixes (those go in code) |
| Better patterns identified | Feature requests (those go elsewhere) |

---

## Learning Entries

> **APPEND-ONLY:** Add entries as learnings are discovered. Never modify or delete previous entries.

### Entry Format

\`\`\`markdown
### Learning [N]: {Brief Title}

**Source:** Task {task-id} | Date: YYYY-MM-DD

**Trigger:** {What happened that revealed this learning}
- [ ] User correction
- [ ] User suggestion
- [ ] Unexpected friction
- [ ] Tool limitation
- [ ] Pattern discovery

**Category:**
- [ ] Missing rule in BMAD/RBTV
- [ ] Unclear instruction that caused confusion
- [ ] Workflow gap or missing step
- [ ] Tool capability gap
- [ ] Better pattern than current approach

**User's Exact Words:**
> "{Quote the user if applicable}"

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | {Which BMAD/RBTV file or component} |
| Type | {Add rule \| Clarify instruction \| New template \| Tool enhancement} |
| Proposed Change | {Specific change to make} |

**Compound Readiness:**
- [ ] Self-contained (no dependencies on other learnings)
- [ ] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation
\`\`\`

<!-- Learning entries will be appended below this line -->

---

## Compound Generation

When learnings accumulate, the final plan task (`pN-compound`) processes them:

### Compound Criteria

A learning is compound-ready when:
1. All four checkboxes in Compound Readiness are checked
2. Implementation path is clear and specific
3. No conflicting learnings exist

### Compound Process

1. Review all learnings marked compound-ready
2. Group related learnings by target component
3. Generate compound documents for implementation
4. Mark processed learnings (append "Compounded: YYYY-MM-DD" line)

### Compound Output

For each group of related learnings:

\`\`\`markdown
## Compound: {Component Name} Improvements

**Source Learnings:** L1, L5, L8
**Target:** {File path}

### Changes

1. {Change 1 from L1}
2. {Change 2 from L5}
3. {Change 3 from L8}

### Implementation Notes

{How to apply these changes together}
\`\`\`
```

---

## Usage Instructions

### Creating learnings.md

1. Create during plan creation alongside shape.md
2. Fill header section with plan name
3. Leave Learning Entries section empty (template markers only)

### During Execution

1. When user provides correction/guidance → Add learning entry
2. When friction point discovered → Add learning entry
3. When better pattern identified → Add learning entry
4. **Tag compound readiness** as each criterion is met

### What NOT to Capture

| Don't Capture | Why |
|---------------|-----|
| "User wanted X feature" | That's a feature request, not a system improvement |
| "Bug in component Y" | That's a bug fix, track in code/issues |
| "Project needs Z approach" | That's project-specific, goes in shape.md |
| "Task took longer than expected" | That's task context, goes in shape.md |

### Examples

**Good learning:**
> "User corrected agent behavior: 'Don't create files unless explicitly asked.' This indicates a missing rule in BMAD about file creation restraint."

**Bad learning (project-specific):**
> "Decided to use Redis for caching in this project."

---

## Size Guidelines

| Section | Target | Max |
|---------|--------|-----|
| Per learning entry | 15-25 lines | 40 lines |
| Compound section | 20-30 lines | 50 lines |

**Note:** Most plans will have 0-5 learnings. Many entries indicate either over-capture or significant system gaps.
