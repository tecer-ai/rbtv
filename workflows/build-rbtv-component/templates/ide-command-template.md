# Thin Loader Templates

Thin loaders are entry points that load and delegate to an RBTV agent, workflow, or task. There are three types: **commands** (human-invoked), **skills** (AI auto-detected), and **cursor sub-agents** (AI-delegated with fresh context).

All skills and cursor sub-agents are also commands. When creating a new AI-available tool, create all three.

---

## 1. Command Templates

Commands live in `.cursor/commands/` and `.claude/commands/`. They are invoked by humans via `/command-name`.

### Command → Agent

```markdown
---
name: '{system}-{module}-{name}'
description: '{description}'
---

<agent-activation CRITICAL="TRUE">
1. LOAD the FULL agent file from {project-root}/_bmad/{module}/agents/{agent-id}.md
2. READ its entire contents
3. FOLLOW every step in the <activation> section precisely
4. DISPLAY the welcome/greeting as instructed
5. PRESENT the numbered menu
6. WAIT for user input before proceeding
</agent-activation>
```

### Command → Workflow or Task

```markdown
---
name: '{system}-{module}-{name}'
description: '{description}'
---

IT IS CRITICAL THAT YOU FOLLOW THIS COMMAND: LOAD the FULL {project-root}/_bmad/{module}/{type}/{path}, READ its entire contents and follow its directions exactly!
```

---

## 2. Skill Templates

Skills live in `.cursor/skills/{system}-{module}-{name}/SKILL.md`. They are auto-detected by AI agents in the current context.

The `name` field MUST match the parent folder name exactly (e.g., folder `bmad-rbtv-doc` → `name: bmad-rbtv-doc`).

### Skill → Agent

```markdown
---
name: '{system}-{module}-{name}'
description: '{description}. Use when {trigger conditions}.'
# Optional fields (per Anthropic Claude Skills spec):
# license: MIT
# compatibility: 'claude-code >= 1.0'
# metadata:
#   author: '{author}'
#   version: '{version}'
# allowed-tools: ['Read', 'Write', 'Edit', 'Bash']
---

# {Display Name} Skill

**Purpose:** {What this skill does}.

**When to use:**
- {Trigger condition 1}
- {Trigger condition 2}
- {Trigger condition 3}

---

## Activation

<agent-activation CRITICAL="TRUE">
1. LOAD the FULL agent file from {project-root}/_bmad/{module}/agents/{agent-id}.md
2. READ its entire contents
3. FOLLOW every step in the <activation> section precisely
4. After activation, process the user's request using the agent's menu handlers
</agent-activation>
```

### Skill → Workflow or Task

```markdown
---
name: '{system}-{module}-{name}'
description: '{description}. Use when {trigger conditions}.'
# Optional fields (per Anthropic Claude Skills spec):
# license: MIT
# compatibility: 'claude-code >= 1.0'
# metadata:
#   author: '{author}'
#   version: '{version}'
# allowed-tools: ['Read', 'Write', 'Edit', 'Bash']
---

# {Display Name} Skill

**Purpose:** {What this skill does}.

**When to use:**
- {Trigger condition 1}
- {Trigger condition 2}
- {Trigger condition 3}

---

## Activation

Load and follow: `{project-root}/_bmad/{module}/{type}/{path}`
```

**Optional subdirectories:** RBTV skills are thin loaders by default. However, skills MAY include optional subdirectories (`scripts/`, `references/`, `assets/`) for supplementary content when needed.

---

## 3. Cursor Sub-agent Templates

Cursor sub-agents live in `.cursor/agents/{system}-{module}-{name}.md`. They are delegated to by AI agents via the Task tool and run with **zero prior context** — all necessary inputs must be specified in the loader.

### Cursor Sub-agent → Agent

```markdown
---
name: {name}
description: {description}. Use when {task} needs isolated context.
model: inherit
readonly: false
---

You are the **{name}** cursor sub-agent — {role description} running in fresh context.

<agent-activation CRITICAL="TRUE">
1. LOAD the FULL agent file from {project-root}/_bmad/{module}/agents/{agent-id}.md
2. READ its entire contents
3. FOLLOW every step in the <activation> section precisely
4. After activation, process the user's request using the agent's menu handlers
</agent-activation>

## Required Inputs (zero-context — all must be provided by invoker)

1. **{Input 1 Name}**: {What this input is and why it's needed}
2. **{Input 2 Name}**: {What this input is and why it's needed}

## What You Return

- {Output 1}
- {Output 2}
```

### Cursor Sub-agent → Workflow or Task

```markdown
---
name: {name}
description: {description}. Use when {task} needs isolated context.
model: inherit
readonly: {true if read-only, false if writes files}
---

You are the **{name}** cursor sub-agent — {role description} running in fresh context.

**IMMEDIATELY** load and execute: `{project-root}/_bmad/{module}/{type}/{path}`

Follow the {workflow|task} exactly. {Brief scope statement}.

## Required Inputs (zero-context — all must be provided by invoker)

1. **{Input 1 Name}**: {What this input is and why it's needed}
2. **{Input 2 Name}**: {What this input is and why it's needed}

## What You Return

- {Output 1}
- {Output 2}
```

---

## Naming Conventions

| Type | Location | Pattern |
|------|----------|---------|
| Command | `.cursor/commands/` | `{system}-{module}-{name}.md` |
| Skill | `.cursor/skills/{system}-{module}-{name}/` | `SKILL.md` (name field = folder name) |
| Cursor sub-agent | `.cursor/agents/` | `{system}-{module}-{name}.md` |

For RBTV: `{system}` = `bmad`, `{module}` = `rbtv`.

---

## Size Guidelines

| Type | Target | Max |
|------|--------|-----|
| Command | 10-15 lines | 20 |
| Skill | 20-30 lines | 35 |
| Cursor sub-agent | 20-30 lines | 40 |

---

## Critical Rules

1. **ZERO LOGIC** — Thin loaders only load files. All logic lives in agent/workflow/task files.
2. **Use {project-root}** — Never hardcode absolute paths. Never use `@{project-root}`.
3. **Agent activation standard** — When loading an RBTV agent, ALWAYS use the `<agent-activation>` block. Never use the single-line "IT IS CRITICAL" pattern for agents.
4. **Cursor sub-agent inputs** — Cursor sub-agents run with zero context. ALWAYS specify required inputs and return values.
5. **Commands mirror across IDEs** — `.cursor/commands/` and `.claude/commands/` contain identical files.
6. **Register AI-available tools** — If creating skill + cursor sub-agent, add entry to `tools-manifest.csv`.
7. **Name matches folder** — The `name` field in SKILL.md MUST match the parent folder name exactly.
8. **No README.md in skill folders** — Skill folders MUST NOT contain a `README.md` file.
9. **No XML angle brackets in frontmatter** — YAML frontmatter MUST NOT contain XML angle brackets (`< >`) (security restriction).
