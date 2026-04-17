# Thin Loader Templates

Thin loaders are entry points that load and delegate to an RBTV agent, workflow, or task. There are two types: **skills** (user-invoked and AI auto-detected) and **cursor sub-agents** (AI-delegated with fresh context).

When creating a new AI-available tool, create both a skill and a cursor sub-agent.

---

## 1. Skill Templates

Skills live in `.cursor/skills/{system}-{module}-{name}/SKILL.md`. They are auto-detected by AI agents in the current context.

The `name` field MUST match the parent folder name exactly (e.g., folder `doc` → `name: doc`).

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
1. LOAD the FULL agent file from {rbtv_path}/personas/{agent-id}.md
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

Load and follow: `{rbtv_path}/{type}/{path}`
```

### Thin Loader Design Decisions

RBTV skills are thin loaders by default — `SKILL.md` only loads and delegates to an agent, workflow, or task. All logic lives in the BMAD architecture (`personas/`, `workflows/`, `tasks/`).

A skill MUST go beyond thin loader when any of these apply:

| Condition | What to add to the skill folder |
|---|---|
| Skill needs custom tool definitions (MCP tools, API integrations) | Tool config files in skill directory |
| Skill needs co-located data not part of BMAD architecture (schemas, prompt templates specific to this skill only) | Data files in skill directory |
| Skill is standalone — does not wrap an existing BMAD agent/task/workflow | Full logic in `SKILL.md` or co-located files |

If none apply, use the thin loader pattern. The `description` and `When to use` fields are what the AI reads for auto-trigger matching — these MUST be rich enough for accurate detection regardless of whether the skill is thin or fat.

---

## 2. Cursor Sub-agent Templates

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
1. LOAD the FULL agent file from {rbtv_path}/personas/{agent-id}.md
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

**IMMEDIATELY** load and execute: `{rbtv_path}/{type}/{path}`

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
| Skill | `.cursor/skills/{system}-{module}-{name}/` | `SKILL.md` (name field = folder name) |
| Cursor sub-agent | `.cursor/agents/` | `{system}-{module}-{name}.md` |

For RBTV: `{system}` = `bmad`, `{module}` = `rbtv`.

---

## Size Guidelines

| Type | Target | Max |
|------|--------|-----|
| Skill (thin loader) | 20-30 lines | 35 |
| Cursor sub-agent | 20-30 lines | 40 |

---

## Critical Rules

1. **ZERO LOGIC in thin loaders** — Thin loaders only load files. All logic lives in agent/workflow/task files.
2. **Use {project-root}** — Never hardcode absolute paths. Never use `@{project-root}`.
3. **Agent activation standard** — When loading an RBTV agent, ALWAYS use the 4-step `<agent-activation>` block. Never use the single-line "IT IS CRITICAL" pattern for agents.
4. **Cursor sub-agent inputs** — Cursor sub-agents run with zero context. ALWAYS specify required inputs and return values.
5. **Skills are the only entry point** — RBTV does not use commands. Skills serve both human invocation and AI auto-detection. The installer deploys skills to `.claude/skills/` and `.cursor/skills/`.
6. **Register AI-available tools** — If creating skill + cursor sub-agent, add entry to `tools-manifest.csv`.
7. **Name matches folder** — The `name` field in SKILL.md MUST match the parent folder name exactly.
8. **No README.md in skill folders** — Skill folders MUST NOT contain a `README.md` file.
9. **No XML angle brackets in frontmatter** — YAML frontmatter MUST NOT contain XML angle brackets (`< >`) (security restriction).
