# Cursor Rules - Platform Interface Knowledge

**Platform:** Cursor IDE
**Feature:** Rules (.mdc files)
**Purpose:** Guide AI agents through Cursor rules creation, structure, and configuration

---

## 1. Interface Overview

### What Are Rules

Rules are YAML-frontmatter markdown files (`.mdc`) that provide persistent instructions to AI agents. They live in `.cursor/rules/` and are loaded into model context based on their configuration type.

### File Requirements

| Requirement | Value |
|-------------|-------|
| Location | `.cursor/rules/` (subdirectories allowed) |
| Extension | `.mdc` |
| Naming | kebab-case (e.g., `typescript-style.mdc`) |
| Max length | 500 lines |

---

## 2. Structure

### Required Format

```markdown
---
description: "Short description of rule purpose"
globs: "optional/path/pattern/**/*"
alwaysApply: false
---
# Rule Title

Instructions with markdown formatting.
```

### Frontmatter Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `description` | Yes | string | Agent uses this to determine relevance |
| `globs` | No | string | Comma-separated file patterns that trigger the rule |
| `alwaysApply` | No | boolean | `true` = every conversation, `false` = agent decides |

---

## 3. Rule Types

| Type | Configuration | Behavior |
|------|---------------|----------|
| Always Apply | `alwaysApply: true` | Applied to every chat session |
| Glob-Based | `globs: "**/*.html"` | Applied when editing matching files |
| Agent-Decides | `alwaysApply: false`, no globs | Agent determines relevance from description |
| Manual | No description, no globs | Only applied when @-mentioned |

---

## 4. Content Guidelines

1. **Be specific** — Provide clear, actionable instructions
2. **Include examples** — Show good and bad patterns
3. **Reference files** — Use `[file.tsx](mdc:path/to/file.tsx)` format
4. **Stay focused** — One concern per rule

### What NOT to Include

- Entire style guides (use linters)
- Common tool documentation (agent knows npm, git, pytest)
- Edge cases that rarely apply
- Content already in your codebase

---

## 5. Example

```markdown
---
description: "TypeScript naming conventions for this project"
globs: "**/*.ts"
alwaysApply: false
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

## 6. Validation Checklist

- [ ] File in `.cursor/rules/` directory
- [ ] Filename uses kebab-case with `.mdc` extension
- [ ] Frontmatter includes `description`
- [ ] Content under 500 lines
- [ ] Examples show good AND bad patterns

---

## 7. Relationship to Claude Rules

Cursor rules (`.mdc` with `globs` string) and Claude rules (`.md` with `paths` array) serve the same purpose but differ in format. When both platforms are supported, `.claude/rules/` is the canonical source and Cursor rules are derived via format conversion:

| Claude Format | Cursor Format |
|---------------|---------------|
| `.md` extension | `.mdc` extension |
| `paths:` YAML array | `globs:` comma-separated string |
| No `paths` = always applied | `alwaysApply: true` |
| Has `paths` = path-triggered | `alwaysApply: false` + `globs` |

---

*Last updated: 2026-03-12*
