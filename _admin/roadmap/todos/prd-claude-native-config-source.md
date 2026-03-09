---
title: 'Invert IDE Config Source: .claude/ as canonical, .cursor/ as derived'
description: 'Restructure _config/ and _admin/ to use .claude/ files as the source of truth. The installer converts .claude/ → .cursor/ (reversing current direction). Claude Code native format is richer and more complete — Cursor format is a lossy subset.'
docType: 'prd'
priority: 'Medium'
source: 'conversation/claude-code-native-rules-agents-discovery'
date: '2026-03-09'
---

# Invert IDE Config Source: .claude/ as canonical, .cursor/ as derived

**Type:** Infrastructure / Installer
**Priority:** Medium
**Status:** Backlog

---

## Problem

The installer (`_config/install-rbtv.py`) currently uses `.cursor/` as the source of truth for all IDE artifacts (commands, rules, agents, skills). Claude Code artifacts are derived by converting `.cursor/` → `.claude/` at install time.

This is backwards. Claude Code's native format is **strictly more expressive** than Cursor's:

| Feature | Claude Code native | Cursor equivalent | Information lost in .cursor/ → .claude/ |
|---------|-------------------|-------------------|------------------------------------------|
| Rules | `.md` with `paths:` (YAML array) | `.mdc` with `globs:` (comma string) | None (lossless direction) |
| Rules | No `alwaysApply` needed (auto-loads) | `alwaysApply: true/false` | Cursor-only concept, stripped on conversion |
| Agents | `permissionMode: plan` | `readonly: true` | Semantic precision (plan vs dontAsk vs default) |
| Agents | `tools:`, `maxTurns`, `hooks`, `memory`, `mcpServers` | Not supported | **Entire fields lost** — cannot round-trip |
| Agents | `permissionMode: dontAsk`, `bypassPermissions` | No equivalent | Lost entirely |
| Agents | `skills:` (preload skills into subagent) | No equivalent | Lost entirely |
| Commands | Identical `.md` format | Identical `.md` format | None |
| Skills | `.claude/skills/*/SKILL.md` — identical base format + `context: fork`, `agent:`, `hooks:`, `disable-model-invocation:`, `user-invocable:` | `.cursor/skills/*/SKILL.md` | **Claude has extra frontmatter fields** — cannot round-trip |

When authoring agents with Claude-native features (`tools`, `hooks`, `memory`, `permissionMode` variants), the `.cursor/` source cannot represent them. The current flow forces authors to write in the less capable format and lose features.

### Current flow

```
Source of truth          Installed (IDE mode)         Installed (admin mode)
─────────────────        ───────────────────          ────────────────────
_config/.cursor/    ──→  {root}/.cursor/              rbtv/.cursor/
                    └──→ {root}/.claude/  (converted)  rbtv/.claude/ (converted)
_admin/.cursor/     ──→  rbtv/.cursor/
```

### Proposed flow

```
Source of truth          Installed (IDE mode)         Installed (admin mode)
─────────────────        ───────────────────          ────────────────────
_config/.claude/
  ├─ commands/      ──→  {root}/.claude/commands/      rbtv/.claude/commands/
  ├─ rules/         ──→  {root}/.claude/rules/         rbtv/.claude/rules/
  ├─ agents/        ──→  {root}/.claude/agents/        rbtv/.claude/agents/
  └─ skills/        ──→  {root}/.claude/skills/        rbtv/.claude/skills/
                    └──→ {root}/.cursor/  (converted)  rbtv/.cursor/ (converted)
_config/.cursor/
  └─ mcp.json       ──→  {root}/.cursor/mcp.json      rbtv/.cursor/mcp.json (+ .claude/.mcp.json)
_admin/.claude/     ──→  rbtv/.claude/
                    └──→ rbtv/.cursor/  (converted)
```

---

## Proposed Changes

### 1. Restructure `_config/` source directories

Move canonical source from `_config/.cursor/` to `_config/.claude/`:

| Artifact type | Current source | New source | Notes |
|--------------|---------------|------------|-------|
| Commands | `_config/.cursor/commands/*.md` | `_config/.claude/commands/*.md` | Identical format, just move |
| Rules | `_config/.cursor/rules/*.mdc` | `_config/.claude/rules/*.md` | Convert to Claude `.md` format |
| Agents | `_config/.cursor/agents/*.md` | `_config/.claude/agents/*.md` | Migrate to Claude frontmatter |
| Skills | `_config/.cursor/skills/*/SKILL.md` | `_config/.claude/skills/*/SKILL.md` | Move — identical base format; Claude adds optional fields (`context`, `agent`, `hooks`, `disable-model-invocation`, `user-invocable`) |
| MCP config | `_config/.cursor/mcp.json` | `_config/.cursor/mcp.json` | **Stay** — both IDEs need it; format is the same |

### 2. Restructure `_admin/` source directories

| Artifact type | Current source | New source |
|--------------|---------------|------------|
| Admin rules | `_admin/.cursor/rules/*.mdc` | `_admin/.claude/rules/*.md` |

### 3. Update installer conversion functions

Replace the current `.cursor/ → .claude/` converters with `.claude/ → .cursor/` converters:

| Function | Current direction | New direction |
|----------|------------------|---------------|
| `_convert_mdc_frontmatter_to_claude` | .mdc → .md | **Delete** |
| `_convert_agent_frontmatter_to_claude` | Cursor → Claude | **Delete** |
| `_convert_claude_rule_to_mdc` | *(new)* | .md → .mdc: `paths:` → `globs:`, add `alwaysApply:` |
| `_convert_claude_agent_to_cursor` | *(new)* | Claude → Cursor: `permissionMode: plan` → `readonly: true`, strip unsupported fields |
| `ide_replicate_rules_to_claude` → `ide_replicate_rules_to_cursor` | Rename + reverse | `.claude/rules/` → `.cursor/rules/` |
| `ide_replicate_agents_to_claude` → `ide_replicate_agents_to_cursor` | Rename + reverse | `.claude/agents/` → `.cursor/agents/` |
| `ide_replicate_commands_to_claude` → `ide_replicate_commands_to_cursor` | Rename + reverse | `.claude/commands/` → `.cursor/commands/` |
| `ide_replicate_skills_to_claude` → `ide_replicate_skills_to_cursor` | Rename + reverse | `.claude/skills/` → `.cursor/skills/` (direct copy — strip Claude-only frontmatter fields) |

### 4. Update IDE mode flow

Current:
1. Copy `_config/.cursor/` → `{root}/.cursor/`
2. Replicate commands → `.claude/commands/`
3. Replicate rules → `.claude/rules/` (convert)
4. Replicate agents → `.claude/agents/` (convert)

New:
1. Copy `_config/.claude/` → `{root}/.claude/`
2. Replicate commands → `.cursor/commands/`
3. Replicate rules → `.cursor/rules/` (convert `.md` → `.mdc`)
4. Replicate agents → `.cursor/agents/` (convert, drop unsupported fields)
5. Replicate skills → `.cursor/skills/` (copy, strip Claude-only frontmatter fields)
6. MCP merge: both `.cursor/mcp.json` and `.claude/.mcp.json` (unchanged)

### 5. Update admin mode flow

Same inversion applies. Admin rules source moves from `_admin/.cursor/rules/*.mdc` to `_admin/.claude/rules/*.md`.

### 6. Update cleanup constants

`IDE_RBTV_SEARCH_DIRS` and `ADMIN_SEARCH_DIRS` already cover both `.cursor/` and `.claude/` directories — no change needed for cleanup.

### 7. Update `bmad-rbtv-cursor-rules.mdc`

This meta-rule documents the `.cursor/rules/` format. It should remain as-is (it's a Cursor-specific rule about Cursor rules). However, a companion `.claude/rules/bmad-rbtv-claude-rules.md` may be needed to document Claude Code rule format.

---

## Out of Scope

- **CLAUDE.md restructuring:** The recent cleanup (removing manual rule-loading instructions) is sufficient. No further CLAUDE.md changes needed.
- **Behavioral changes:** This is a pure infrastructure change. No agent, rule, or command behavior should change.
- **Claude-only skill features in v1:** Skills like `context: fork`, `agent:`, `hooks:`, `disable-model-invocation:`, `user-invocable:` are available in Claude Code but not Cursor. Initial migration moves skills to `.claude/` as-is. Leveraging Claude-only skill features is a follow-up enhancement.

---

## Acceptance Criteria

- [ ] `_config/.claude/commands/` contains all command files (moved from `_config/.cursor/commands/`)
- [ ] `_config/.claude/rules/` contains all rule files in `.md` format with Claude-native frontmatter
- [ ] `_config/.claude/agents/` contains all agent files with Claude-native frontmatter (including any `tools`, `permissionMode`, etc.)
- [ ] `_config/.claude/skills/` contains all skill directories (moved from `_config/.cursor/skills/`)
- [ ] `_config/.cursor/` retains only `mcp.json`
- [ ] `_admin/.claude/rules/` contains admin rules in `.md` format
- [ ] `_admin/.cursor/` is empty or removed
- [ ] Installer converts `.claude/` → `.cursor/` (new direction)
- [ ] Installer replicates skills from `.claude/skills/` → `.cursor/skills/` (stripping Claude-only fields)
- [ ] Installer copies MCP from `_config/.cursor/` directly
- [ ] IDE mode produces identical installed output (`.cursor/` and `.claude/` at project root both populated correctly)
- [ ] Admin mode produces identical installed output at rbtv root
- [ ] `admin-rbtv-bmad-mirror.mdc` updated to reflect new source-of-truth direction
- [ ] No behavioral changes to any rules, agents, or commands

---

## Migration Steps

1. Convert existing `_config/.cursor/rules/*.mdc` → `_config/.claude/rules/*.md` (use the existing `_convert_mdc_frontmatter_to_claude` function as a one-time migration tool)
2. Move `_config/.cursor/agents/*.md` → `_config/.claude/agents/*.md`, updating frontmatter to Claude-native format
3. Move `_config/.cursor/commands/*.md` → `_config/.claude/commands/*.md`
4. Move `_config/.cursor/skills/*/` → `_config/.claude/skills/*/` (identical format)
5. Move `_admin/.cursor/rules/*.mdc` → `_admin/.claude/rules/*.md`
6. Rewrite installer conversion functions (reverse direction)
7. Update all documentation (`admin-rbtv-bmad-mirror.mdc`, `CLAUDE.md`, installer docstring)
8. Test both IDE and admin modes produce correct output
9. Delete emptied `_config/.cursor/{commands,rules,agents,skills}/` directories
10. Delete `_admin/.cursor/` directory

---

## Rationale

The `.claude/` format is a strict superset of `.cursor/`. Converting superset → subset is safe (drop unsupported fields). Converting subset → superset loses information. Authoring in the richer format and deriving the simpler one is the correct direction. This also positions RBTV to leverage Claude Code agent features (`tools`, `hooks`, `memory`, `permissionMode` variants) as they become relevant.
