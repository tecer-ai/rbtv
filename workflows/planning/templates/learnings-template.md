# Learnings Template

Use this template to create the `learnings.md` companion file for each plan. Learnings captures **actionable items** discovered during plan execution that must be solved or compounded **after** the plan ends — system improvement opportunities, code/installer bugs uncovered, missing rules, workflow gaps, better patterns.

---

## Template

```markdown
# Learnings - {Plan Name}

> **Purpose:** Actionable items captured during plan execution to be solved or compounded after the plan ends. Each entry is a post-plan TODO with enough context for a fresh agent to act on it without reading the full plan. Includes META-learnings about how BMAD/RBTV/sb-os could be improved AND code/installer/rule bugs discovered while executing the plan — both classes of finding are actionable post-plan items.

---

## What Belongs Here

`learnings.md` is the catch-all for findings that surface during plan execution but do NOT change plan direction (those go in `shape.md`) and are NOT a single concrete piece of project work (those go in the project's tasks file). The defining trait: every entry is **actionable** — solvable now or compoundable into a later system change. If there is no action, it is not a learning.

| Include | Exclude |
|---------|---------|
| User corrections to agent behavior | Project-specific decisions |
| Missing rules or unclear instructions | Implementation details |
| Workflow gaps or friction points | Task-specific context |
| Tool limitations discovered | Feature requests (those go elsewhere) |
| Better patterns identified | Routine task completions ("created file X", "ran test Y") |
| Code/installer/rule bugs discovered during plan execution — even if fixed in-plan, log here so the fix is auditable and the discovery pattern is preserved as precedent | |
| Meta-observations about the planning/orchestration system itself | |

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
| "User wanted X feature" | Feature request — open an issue or task in the relevant system, not here |
| "Bug in some unrelated component" | If the bug is unrelated to anything you encountered during plan execution, it belongs in that system's issue tracker — not here. Bugs DISCOVERED during plan execution DO belong here (see Include) |
| "Project needs Z approach" | Project-specific decision, goes in `shape.md` |
| "Task took longer than expected" | Task context, goes in `shape.md` |

### Examples

**Good learning (system improvement):**
> "User corrected agent behavior: 'Don't create files unless explicitly asked.' This indicates a missing rule in BMAD about file creation restraint."

**Good learning (code bug discovered during execution):**
> "`upgrade.py` copies rule files via `shutil.copyfile` without substituting `{sb_os_path}` placeholders. Affects every rule containing the placeholder. Fix: route rule installs through a `substitute_rule_placeholders` helper. Logged here so the discovery and fix path are preserved as precedent for future installer work."

**Bad learning (project-specific):**
> "Decided to use Redis for caching in this project."

**Bad learning (no action):**
> "Phase 3 was harder than expected." → no actionable system change → discard, or move to `shape.md` if it changes plan direction.

---

## Size Guidelines

| Section | Target | Max |
|---------|--------|-----|
| Per learning entry | 15-25 lines | 40 lines |
| Compound section | 20-30 lines | 50 lines |

**Note:** Most plans will have 0-5 learnings. Many entries indicate either over-capture or significant system gaps.
