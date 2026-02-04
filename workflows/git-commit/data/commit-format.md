# Conventional Commits Reference

Quick reference for commit message format.

---

## Structure

```
<type>[scope][!]: <title>

<body>

[footer]
```

---

## Types

| Type | Purpose | Example |
|------|---------|---------|
| feat | New feature | `feat(auth): add password reset flow` |
| fix | Bug fix | `fix(api): handle null response` |
| docs | Documentation | `docs(readme): update install steps` |
| style | Formatting only | `style: format with prettier` |
| refactor | Code restructuring | `refactor(db): extract query builder` |
| test | Test changes | `test(auth): add login unit tests` |
| other | Maintenance | `other: update dependencies` |

---

## Title Rules

| Rule | Requirement |
|------|-------------|
| Length | Target ~50 chars, max 80 |
| Casing | Lowercase only |
| Punctuation | No period at end |
| Mood | Imperative ("add" not "added") |

---

## Scope Detection

Auto-detect from primary file paths:

- Changes in `agents/` → scope `agents`
- Changes in `commands/` → scope `commands`
- Changes in `api/` → scope `api`
- Multiple areas → omit scope or use broader term

---

## Breaking Changes

Add `!` after scope when:

- Removed or renamed public functions/methods
- Changed function signatures
- Removed or renamed files that may be imported
- Changed configuration formats

Example: `feat(api)!: change response format`

---

## Body Guidelines

| Size | Content |
|------|---------|
| 280 | Summary only (1-2 sentences) |
| 1000 | Summary + 2-3 categorized sections |
| 2000 | Full structure with impact statement |

**Categorized sections example:**

```
Key changes:

Authentication:
- Added JWT refresh token support
- Implemented session expiry handling

API:
- New /auth/refresh endpoint
- Updated response format for tokens
```

---

## Reference Example

```
feat(agents): add navigation capabilities

Implements navigation rule for agents to access system map
and follow structured navigation patterns.

Key changes:

Navigation:
- Added navigation.mdc rule
- Updated judge with navigation awareness

Documentation:
- Documented patterns in agent map

This maintains backward compatibility with existing patterns.
```
