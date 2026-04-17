# Learnings - Pitch Design Agent Split

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

```markdown
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
| Type | {Add rule | Clarify instruction | New template | Tool enhancement} |
| Proposed Change | {Specific change to make} |

**Compound Readiness:**
- [ ] Self-contained (no dependencies on other learnings)
- [ ] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation
```

<!-- Learning entries will be appended below this line -->

### Learning 1: PRD/Plan task files can reference non-existent directory structures

**Source:** Task p2-2 | Date: 2026-03-09

**Trigger:** The p2-2 task file referenced `_config/.cursor/sub-agents/` as the target directory for the cursor sub-agent loader file. This directory does not exist — the actual directory is `_config/.cursor/agents/`. The executor had to discover this by inspecting existing files.
- [x] Unexpected friction
- [ ] User correction
- [ ] User suggestion
- [ ] Tool limitation
- [ ] Pattern discovery

**Category:**
- [ ] Missing rule in BMAD/RBTV
- [x] Unclear instruction that caused confusion
- [ ] Workflow gap or missing step
- [ ] Tool capability gap
- [ ] Better pattern than current approach

**User's Exact Words:**
> N/A — discovered during execution

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | Plan creation workflow / PRD template |
| Type | Add rule |
| Proposed Change | Plans that reference filesystem paths should validate those paths exist before finalization. Add a "path validation" step to plan creation that verifies all referenced directories and file patterns are real. |

**Compound Readiness:**
- [x] Self-contained (no dependencies on other learnings)
- [x] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation

### Learning 2: BMAD agent naming convention — file vs frontmatter name field — undocumented

**Source:** Task p2-2 | Date: 2026-03-09

**Trigger:** The task file referenced `agents/designer.md` but the agent was created as `agents/vivian.md` (persona name) with `name: "designer"` in frontmatter. The RBTV convention appears to be: filename = persona name, frontmatter `name` = functional role. This is not documented anywhere, leading to mismatches in planning artifacts.
- [x] Unexpected friction
- [ ] User correction
- [ ] User suggestion
- [ ] Tool limitation
- [x] Pattern discovery

**Category:**
- [x] Missing rule in BMAD/RBTV
- [ ] Unclear instruction that caused confusion
- [ ] Workflow gap or missing step
- [ ] Tool capability gap
- [ ] Better pattern than current approach

**User's Exact Words:**
> N/A — discovered by comparing existing agents (roelof.md has name="investor", paul.md has name="mentor")

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | Agent creation documentation / BMAD component builder skill |
| Type | Add rule |
| Proposed Change | Document the agent naming convention: filename is the persona name (e.g., `vivian.md`), frontmatter `name` field is the functional role (e.g., `"designer"`). The functional name is used for command/loader naming (`bmad-rbtv-designer`). |

**Compound Readiness:**
- [x] Self-contained (no dependencies on other learnings)
- [x] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation

### Learning 3: Multi-agent workflow handoff pattern emerged and should be codified

**Source:** Tasks p3-1, p3-2, p4-1, p4-2 | Date: 2026-03-09

**Trigger:** Two distinct handoff patterns were implemented: one-way (pitch: Roelof → Vivian) and round-trip (brandbook: Paul → Vivian → Paul). Both use the same mechanism (AGENT HANDOFF blockquote in step file with exact command + menu selection). This pattern was invented during execution and should be a reusable template for future multi-agent workflows.
- [ ] User correction
- [ ] User suggestion
- [ ] Unexpected friction
- [ ] Tool limitation
- [x] Pattern discovery

**Category:**
- [ ] Missing rule in BMAD/RBTV
- [ ] Unclear instruction that caused confusion
- [ ] Workflow gap or missing step
- [ ] Tool capability gap
- [x] Better pattern than current approach

**User's Exact Words:**
> N/A — pattern emerged from implementation

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | Workflow architecture documentation / step file template |
| Type | New template |
| Proposed Change | Create an "Agent Handoff Block" template that step files can include at completion boundaries. Template should specify: (1) blockquote format with AGENT HANDOFF header, (2) exact command to invoke next agent, (3) menu item to select, (4) explicit prohibition against the current agent loading the next step. Document one-way vs round-trip patterns. |

**Compound Readiness:**
- [x] Self-contained (no dependencies on other learnings)
- [x] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation

---

## Compound Generation

When learnings accumulate, the final plan task (`p5-compound`) processes them:

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
