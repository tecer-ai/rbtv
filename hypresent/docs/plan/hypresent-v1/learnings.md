# Learnings - Hypresent v1

> **Purpose:** Actionable items captured during plan execution to be solved or compounded after the plan ends. Each entry is a post-plan TODO with enough context for a fresh agent to act without reading the full plan. Includes META-learnings about RBTV/sb-os AND code/installer/rule bugs discovered while executing the plan.

---

## What Belongs Here

`learnings.md` is the catch-all for findings that surface during execution but do NOT change plan direction (those go in `shape.md`) and are NOT a single concrete piece of project work (those go in the project's tasks file). Every entry is **actionable**.

| Include | Exclude |
|---------|---------|
| User corrections to agent behavior | Project-specific decisions (→ shape.md) |
| Missing rules or unclear instructions | Implementation details |
| Workflow gaps or friction points | Task-specific context (→ shape.md) |
| Tool limitations discovered | Routine task completions |
| Better patterns identified | |
| Code/installer/rule bugs discovered during execution | |

---

## Learning Entries

> **APPEND-ONLY:** Add entries as learnings are discovered. Never modify or delete previous entries.

### Entry Format

```markdown
### Learning [N]: {Brief Title}

**Source:** Task {task-id} | Date: YYYY-MM-DD

**Trigger:** {What happened}
- [ ] User correction / suggestion / friction / tool limitation / pattern discovery

**Category:**
- [ ] Missing rule / Unclear instruction / Workflow gap / Tool capability gap / Better pattern

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | {Which RBTV file or component} |
| Type | {Add rule | Clarify instruction | New template | Tool enhancement} |
| Proposed Change | {Specific change} |

**Compound Readiness:**
- [ ] Self-contained
- [ ] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation
```

<!-- Learning entries will be appended below this line -->

---

## Compound Generation

The final task (`pN-compound` / `T21`) processes compound-ready learnings: group by target component, generate compound documents, mark processed with a `Compounded: YYYY-MM-DD` line.

> **Note:** Most plans have 0-5 learnings. This file starts empty; populate during execution.
