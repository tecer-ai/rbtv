---
description: Memory system — lazy-loaded knowledge capture at .claude/memory/ for cross-session continuity
---
# Memory System

Structured knowledge at `.claude/memory/`. Never read proactively — only on trigger.

## Read Triggers

| Trigger | Action |
|---------|--------|
| About to execute CLI commands for tool X | Read `tools/{X}.md` if it exists — apply known workarounds |
| Need to write a new memory entry | Read `memory.md` to find the right target file |
| Session involves environment setup or config | Read `general.md` if it exists |
| Working in a specific domain topic | Read `domain/{topic}.md` if it exists |

No trigger matched → no memory files read. Zero reads is the correct default.

## Write Triggers

| Trigger | Action |
|---------|--------|
| Learned something worth remembering | Write to the correct file immediately — never defer to session end |
| Command failed → retried differently → succeeded | Write self-correction to `tools/{tool}.md` autonomously — no user prompting |
| Created or modified any memory file | Update `memory.md` index with one-line description |
| Target file or subdirectory does not exist | Create it on demand |

## Entry Format

`date | what | why`

Self-corrections: `date | SELF-CORRECTION: failed → working | reason`

## Structure

| Path | Purpose |
|------|---------|
| `memory.md` | Index — one-line description per file |
| `general.md` | Cross-project facts, preferences, environment |
| `domain/{topic}.md` | Domain-specific knowledge |
| `tools/{tool}.md` | CLI patterns, workarounds, self-corrections |

Location: `{project-root}/.claude/memory/` (IDE) or `{rbtv-root}/.claude/memory/` (admin).

## What NOT to Capture

- Routine task completions
- Content the user explicitly dictated (that belongs in context preservation / shape)
- Temporary debugging steps with no reuse value
