# Claude Rules - Platform Interface Knowledge

**Platform:** Claude (Claude Code CLI)
**Feature:** Rules (.md files)
**Purpose:** Guide AI agents through Claude Code rules creation, structure, and configuration

---

## 1. Interface Overview

### What Are Rules

Rules are YAML-frontmatter markdown files (`.md`) that provide persistent instructions to Claude Code agents. They live in `.claude/rules/` and are loaded into model context based on their configuration.

### File Requirements

| Requirement | Value |
|-------------|-------|
| Location | `.claude/rules/` (subdirectories allowed) |
| Extension | `.md` |
| Naming | kebab-case (e.g., `typescript-style.md`) |

---

## 2. Structure

### Required Format

```markdown
---
description: "Short description of rule purpose"
paths:
  - "src/**/*.ts"
  - "tests/**/*.test.ts"
---
# Rule Title

Instructions with markdown formatting.
```

### Frontmatter Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `description` | Yes | string | Claude uses this to determine relevance |
| `paths` | No | YAML array | File/directory patterns that trigger the rule |

### Rule Activation

| Configuration | Behavior |
|---------------|----------|
| No `paths` field | Always applied to every session |
| With `paths` array | Applied when working with files matching the patterns |

---

## 3. Content Guidelines

1. **Be specific** — Provide clear, actionable instructions
2. **Include examples** — Show good and bad patterns
3. **Stay focused** — One concern per rule

### What NOT to Include

- Entire style guides (use linters)
- Common tool documentation (agent already knows standard tools)
- Edge cases that rarely apply
- Content already in your codebase

---

## 4. Example

```markdown
---
description: "TypeScript naming conventions for this project"
paths:
  - "src/**/*.ts"
  - "lib/**/*.ts"
---
# TypeScript Naming

## Variables and Functions

Use camelCase:

```typescript
const userName = "alice";
function getUserById(id: string) {}
```
```

---

## 5. Relationship to Cursor Rules

Claude rules (`.md` with `paths` array) and Cursor rules (`.mdc` with `globs` string) serve the same purpose but differ in format. When both platforms are supported, `.claude/rules/` is the canonical source and Cursor rules are derived via format conversion:

| Claude Format | Cursor Format |
|---------------|---------------|
| `.md` extension | `.mdc` extension |
| `paths:` YAML array | `globs:` comma-separated string |
| No `paths` = always applied | `alwaysApply: true` |
| Has `paths` = path-triggered | `alwaysApply: false` + `globs` |

---

*Last updated: 2026-03-12*
