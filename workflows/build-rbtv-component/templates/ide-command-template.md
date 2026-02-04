# IDE Command Template

Use this template to create thin loader commands for Cursor or Claude Code.

---

## Agent Command Template

```markdown
---
name: '{agent-id}'
description: '{agent-description}'
---

You must fully embody this agent's persona and follow all activation instructions exactly as specified. NEVER break character until given an exit command.

<agent-activation CRITICAL="TRUE">
1. LOAD the FULL agent file from {project-root}/_bmad/{module}/agents/{agent-id}.md
2. READ its entire contents
3. FOLLOW every step in the <activation> section precisely
4. DISPLAY the welcome/greeting as instructed
5. PRESENT the numbered menu
6. WAIT for user input before proceeding
</agent-activation>
```

---

## Workflow Command Template

```markdown
---
name: '{workflow-name}'
description: '{workflow-description}'
---

IT IS CRITICAL THAT YOU FOLLOW THIS COMMAND: LOAD the FULL {project-root}/_bmad/{module}/workflows/{path}/workflow.md, READ its entire contents and follow its directions exactly!
```

---

## Field Instructions

### Frontmatter
- **name**: Command identifier. Becomes `/name` in the IDE.
- **description**: Shown in IDE command palette/autocomplete.

### Body
- **For agents**: Use the `<agent-activation>` block with 6 steps
- **For workflows**: Use the single CRITICAL instruction sentence

---

## Naming Conventions

| Command Type | Pattern | Example |
|-------------|---------|---------|
| Agent activation | `{system}-agent-{module}-{agent-name}.md` | `bmad-agent-bmm-analyst.md` |
| Workflow | `{system}-{module}-{workflow-name}.md` | `bmad-bmm-create-prd.md` |
| Task | `{system}-{task-name}.md` | `bmad-help.md` |

---

## Directory Locations

```
.cursor/commands/     # Cursor entry points
.claude/commands/     # Claude Code entry points
```

**Both directories should contain identical files** — the content is the same for both IDEs.

---

## Size Guidelines

| Metric | Target | Max |
|--------|--------|-----|
| Total lines | 10-15 | 20 |

---

## Critical Rules

1. **ZERO LOGIC** — Command files only load files. All logic lives in agent/workflow files.

2. **Use {project-root}** — Never hardcode absolute paths.

3. **Identical across IDEs** — Same content in .cursor and .claude directories.

4. **One command per agent/workflow** — Each agent and each workflow gets its own command file.

---

## Common Mistakes

1. **Adding logic** — Don't put conditionals or processing in command files

2. **Different content per IDE** — Keep .cursor and .claude files identical

3. **Missing CRITICAL emphasis** — Always include CRITICAL="TRUE" for agents or "IT IS CRITICAL" for workflows
