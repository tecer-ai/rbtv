# Claude Skills - Platform Interface Knowledge

**Platform:** Claude (Claude Code / Claude Agent)
**Feature:** Agent Skills
**Purpose:** Guide AI agents through Claude Skills creation, structure, testing, and distribution

---

## 1. Interface Overview

### What Are Skills

Skills are YAML-frontmatter markdown files (`SKILL.md`) that extend Claude's capabilities. They live in `.claude/skills/{skill-name}/SKILL.md` and are auto-detected by Claude agents in the current workspace context.

### Folder Structure

| Component | Location | Purpose |
|-----------|----------|---------|
| Skill entry file | `.claude/skills/{name}/SKILL.md` | Main skill definition with YAML frontmatter |
| Scripts (optional) | `.claude/skills/{name}/scripts/` | Executable scripts the skill can invoke |
| References (optional) | `.claude/skills/{name}/references/` | Documentation and reference material |
| Assets (optional) | `.claude/skills/{name}/assets/` | Static files (templates, configs, data) |

---

## 2. Core Capabilities

### What Skills Can Do

| Capability | Description |
|------------|-------------|
| Auto-detection | Claude discovers skills from workspace `.claude/skills/` directory |
| Tool restriction | `allowed-tools` field limits which tools the skill can use |
| Trigger conditions | `description` field tells Claude when to activate the skill |
| Progressive disclosure | Lean SKILL.md with heavy docs in `references/` subdirectory |
| Cross-platform | Same SKILL.md format works in Claude Code CLI and IDE integrations |

### Primary Use Cases

- Automating repetitive development workflows
- Enforcing coding standards and patterns
- Providing domain-specific capabilities to Claude agents
- Creating reusable task-specific tooling

---

## 3. YAML Frontmatter Specification

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | MUST match parent folder name exactly |
| `description` | string | What the skill does AND when to use it (trigger conditions) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `license` | string | License identifier (e.g., `MIT`, `Apache-2.0`) |
| `compatibility` | string | Runtime version constraint (e.g., `claude-code >= 1.0`) |
| `metadata` | object | Contains `author` (string) and `version` (string) |
| `allowed-tools` | array | List of permitted tool names (e.g., `['Read', 'Write', 'Bash']`) |

### Example Frontmatter

```yaml
---
name: my-linter
description: Run project linting with auto-fix. Use when code needs formatting or style enforcement.
license: MIT
compatibility: 'claude-code >= 1.0'
metadata:
  author: Team Name
  version: '1.0.0'
allowed-tools: ['Read', 'Bash']
---
```

---

## 4. Writing Effective Skills

### Description Field

The `description` is the primary trigger mechanism. It MUST include:

1. **What** the skill does (first sentence)
2. **When** to use it (trigger conditions after "Use when")

| Bad Description | Good Description |
|----------------|-----------------|
| "Runs tests" | "Run project test suite with coverage reporting. Use when validating code changes, checking test coverage, or before committing." |
| "Linter" | "Apply project coding standards with auto-fix. Use when code needs formatting, style enforcement, or lint checking." |

### Body Content

| Section | Required | Purpose |
|---------|----------|---------|
| Title heading | Yes | Skill display name |
| Purpose | Yes | One-line statement of what the skill does |
| When to use | Yes | Bullet list of trigger conditions |
| Activation | Yes | Instructions for loading and executing the skill's target |

---

## 5. Naming and Structure Rules

### Folder Naming

| Rule | Example |
|------|---------|
| Kebab-case only | `my-code-formatter` |
| No spaces | `code-formatter` not `code formatter` |
| No capitals | `my-tool` not `My-Tool` |
| Name field = folder name | Folder `my-tool` → `name: my-tool` |

### Security Restrictions

| Restriction | Reason |
|-------------|--------|
| No XML angle brackets (`< >`) in YAML frontmatter | Prevents injection attacks |
| No `README.md` in skill folders | Avoids confusion with skill entry file |

---

## 6. Testing Skills

### Validation Checklist

- [ ] SKILL.md has valid YAML frontmatter (parseable, no syntax errors)
- [ ] `name` field matches parent folder name exactly
- [ ] `description` includes what AND when
- [ ] Skill activates when expected trigger conditions are met
- [ ] `allowed-tools` (if set) includes all tools the skill needs
- [ ] Body content is self-contained and actionable

---

## 7. Distribution

### Sharing Skills

Skills are portable — copy the entire skill folder to share:

```
.claude/skills/my-skill/
├── SKILL.md
├── scripts/       (optional)
├── references/    (optional)
└── assets/        (optional)
```

### Installation

Place the skill folder in the target project's `.claude/skills/` directory. Claude auto-discovers it on next session.

---

## 8. Patterns

### Thin Loader Pattern

For systems with external agents/workflows, skills act as thin loaders — minimal entry points that load and delegate:

```markdown
---
name: my-builder
description: Build components. Use when creating new system components.
---

# Builder Skill

**Purpose:** Load and execute the builder agent.

**When to use:**
- Creating new components
- User asks to build something

---

## Activation

Load and follow: `path/to/agent-or-workflow.md`
```

### Progressive Disclosure Pattern

Keep SKILL.md lean. Move heavy documentation to `references/`:

```
.claude/skills/complex-tool/
├── SKILL.md              (30 lines — lean entry point)
└── references/
    ├── api-guide.md      (detailed API documentation)
    └── examples.md       (usage examples)
```

---

## 9. Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Skill not detected | Wrong folder location | Verify path is `.claude/skills/{name}/SKILL.md` |
| Skill not triggered | Weak description | Add explicit trigger conditions with "Use when" |
| YAML parse error | Invalid frontmatter | Check for unclosed quotes, improper indentation |
| Name mismatch warning | `name` ≠ folder name | Update `name` field to match folder name exactly |
| Tools not available | `allowed-tools` too restrictive | Add missing tools to the array |
| Skill too complex | Too much content in SKILL.md | Move documentation to `references/` subdirectory |

---

*Last updated: 2026-03-11*
