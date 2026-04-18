# Task Template

Use this template to create a standalone BMAD task.

---

## Template

```xml
<task id="tasks/{task-name}.xml"
      name="{Display Name}"
      standalone="true"
      description="{What this task does}">

  <objective>
    {Clear statement of what this task accomplishes and what it produces.}
  </objective>

  <llm critical="true">
    <rule>Read the complete task before starting execution.</rule>
    <rule>Follow steps in exact order.</rule>
    <rule>{Task-specific critical rule}</rule>
  </llm>

  <flow>
    <step n="1" title="{Step Title}">
      <substep n="1a" title="{Substep Title}">
        <action>{What to do}</action>
      </substep>
      <substep n="1b" title="{Substep Title}">
        <action>{What to do}</action>
        <check if="{condition}">
          <action>{Conditional action}</action>
        </check>
      </substep>
    </step>

    <step n="2" title="{Step Title}">
      <substep n="2a" title="{Substep Title}">
        <ask>{Question to ask the user}</ask>
      </substep>
      <substep n="2b" title="{Substep Title}">
        <action>{Action based on user response}</action>
      </substep>
    </step>
  </flow>

  <halt-conditions>
    <condition>{When to stop execution}</condition>
  </halt-conditions>

  <protocols>
    <protocol name="{protocol-name}">
      <step>{Reusable procedure step 1}</step>
      <step>{Reusable procedure step 2}</step>
    </protocol>
  </protocols>

</task>
```

---

## Field Instructions

### Task Attributes
- **id**: Full path used for cross-referencing
- **name**: Display name shown to users
- **standalone**: `true` if directly invocable, `false` if only called by other components
- **description**: One-line summary

### Sections
- **objective**: What the task produces (single deliverable)
- **llm critical="true"**: Non-negotiable execution rules
- **flow**: Sequential steps with substeps
- **halt-conditions**: When to stop execution
- **protocols**: Reusable sub-procedures

### Flow Elements
- **step**: Major phase with title
- **substep**: Specific action within a step
- **action**: Instruction the AI executes
- **ask**: Question to pose to user
- **check if**: Conditional branching

---

## Task vs. Workflow

| Aspect | Task | Workflow |
|--------|------|----------|
| Structure | Single XML file | Multiple step files |
| Output | Action completion | Document with frontmatter |
| Resumability | Not resumable | Built-in via stepsCompleted |
| Use case | Single-purpose procedures | Multi-session document building |

**Use a task when:** You need a reusable procedure that completes in one go.

**Use a workflow when:** You need to build a document incrementally across multiple sessions.

---

## Size Guidelines

| Metric | Target | Max |
|--------|--------|-----|
| Total lines | 40-100 | 150 |
| Steps | 3-5 | 8 |
| Substeps per step | 2-3 | 5 |

---

## Common Mistakes

1. **Missing halt-conditions** — Always define when to stop

2. **No critical rules** — Always include at least "Read complete task" and "Follow steps in order"

3. **Using task for document building** — If you need state tracking and resumability, use a workflow instead
