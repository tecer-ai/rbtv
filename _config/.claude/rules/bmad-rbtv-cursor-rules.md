---
description: Format and structure standards for creating Cursor rules in .cursor/rules/
---
# Cursor Rules Format

Rules provide persistent instructions included at the start of model context.

## File Requirements

| Requirement | Value |
|-------------|-------|
| Location | `.cursor/rules/` (subdirectories allowed) |
| Extension | `.mdc` |
| Naming | kebab-case (e.g., `typescript-style.mdc`) |
| Max length | 500 lines |

## Required Structure

```markdown
---
description: "Short description of rule purpose"
globs: "optional/path/pattern/**/*"
alwaysApply: false
---
# Rule Title

Instructions with markdown formatting.
```

## Frontmatter Fields

| Field | Required | Purpose |
|-------|----------|---------|
| `description` | Yes | Agent uses this to determine relevance |
| `globs` | No | File patterns that trigger the rule |
| `alwaysApply` | No | `true` = every conversation, `false` = agent decides |

## Rule Types

| Type | Configuration | Behavior |
|------|---------------|----------|
| Always Apply | `alwaysApply: true` | Applied to every chat session |
| Glob-Based | `globs: "**/*.html"` | Applied when editing matching files |
| Agent-Decides | `alwaysApply: false`, no globs | Agent determines relevance from description |
| Manual | No description, no globs | Only applied when @-mentioned |

## Content Guidelines

1. **Be specific** - Provide clear, actionable instructions
2. **Include examples** - Show good and bad patterns
3. **Reference files** - Use `[file.tsx](mdc:path/to/file.tsx)` format
4. **Stay focused** - One concern per rule

## Example

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
// ✅ Good
const userName = "alice";
function getUserById(id: string) {}

// ❌ Bad
const user_name = "alice";
function get_user_by_id(id: string) {}
```
```

## What NOT to Include in Rules

- Entire style guides (use linters)
- Common tool documentation (agent knows npm, git, pytest)
- Edge cases that rarely apply
- Content already in your codebase

## Validation Checklist

- [ ] File in `.cursor/rules/` directory
- [ ] Filename uses kebab-case with `.mdc` extension
- [ ] Frontmatter includes `description`
- [ ] Content under 500 lines
- [ ] Examples show good AND bad patterns