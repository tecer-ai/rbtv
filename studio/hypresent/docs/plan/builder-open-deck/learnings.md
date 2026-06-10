# Learnings - builder-open-deck

> **Purpose:** Actionable items captured during plan execution to be solved or compounded after the plan ends. Each entry is a post-plan TODO with enough context for a fresh agent to act on it without reading the full plan. Includes META-learnings about how RBTV/sb-os could be improved AND code/installer/rule bugs discovered while executing the plan — both classes of finding are actionable post-plan items.

---

## What Belongs Here

`learnings.md` is the catch-all for findings that surface during plan execution but do NOT change plan direction (those go in `decisions.md`) and are NOT a single concrete piece of project work (those go in the project's tasks file). The defining trait: every entry is **actionable** — solvable now or compoundable into a later system change. If there is no action, it is not a learning.

| Include | Exclude |
|---------|---------|
| User corrections to agent behavior | Project-specific decisions |
| Missing rules or unclear instructions | Implementation details |
| Workflow gaps or friction points | Task-specific context |
| Tool limitations discovered | Feature requests (those go elsewhere) |
| Better patterns identified | Routine task completions |
| Code/installer/rule bugs discovered during plan execution | |
| Meta-observations about the planning/orchestration system itself | |

---

## Learning Entries

> **APPEND-ONLY:** Add entries as learnings are discovered. Never modify or delete previous entries.

### Entry Format

```markdown
### Learning [N]: {Brief Title}

**Source:** Task {task-id} | Date: YYYY-MM-DD

**Trigger:** {What happened that revealed this learning}

**Category:** {Missing rule | Unclear instruction | Workflow gap | Tool capability gap | Better pattern}

**User's Exact Words:**
> "{Quote the user if applicable}"

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | {Which RBTV file or component} |
| Type | {Add rule | Clarify instruction | New template | Tool enhancement} |
| Proposed Change | {Specific change to make} |

**Compound Readiness:**
- [ ] Self-contained (no dependencies on other learnings)
- [ ] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation
```

<!-- Learning entries will be appended below this line -->

---

## Compound Generation

When learnings accumulate, the final plan task (`p5-compound`) processes them:

1. Review all learnings marked compound-ready
2. Group related learnings by target component
3. Generate compound documents for implementation
4. Mark processed learnings (append "Compounded: YYYY-MM-DD" line)
