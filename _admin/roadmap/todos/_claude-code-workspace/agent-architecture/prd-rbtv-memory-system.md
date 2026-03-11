---
title: 'RBTV Memory System'
description: 'Implement a structured memory system at .claude/memory/ for AI agents to capture and recall learnings across sessions — architectural decisions, bug fixes, gotchas, environment quirks.'
docType: 'prd'
priority: 'Medium'
source: 'user-spec'
reference: 'https://huryn.medium.com/claude-cowork-the-complete-guide-for-pms-e45e7cf0f52d'
date: '2026-03-09'
---

# RBTV Memory System

**Type:** Feature / Infrastructure
**Priority:** Medium
**Status:** Backlog

---

## Problem

AI coding sessions discover valuable knowledge — architectural decisions, bug fixes, gotchas, environment quirks — that would benefit future sessions. Today:

- There is no standard place or format to store such learnings
- Agents don't proactively capture insights during a session
- Each session starts with no memory of prior discoveries
- Users must repeat context or re-explain environment quirks

A lightweight, structured memory system would enable continuity and reduce friction across sessions.

---

## Canonical Prompt (Reference)

The following is the exact prompt to implement:

```
## Memory Management

Maintain a structured memory system rooted at .claude/memory/

### Structure

- memory.md – index of all memory files, updated whenever you create or modify one
- general.md – cross-project facts, preferences, environment setup
- domain/{topic}.md – domain-specific knowledge (one file per topic)
- tools/{tool}.md – tool configs, CLI patterns, workarounds

### Rules

1. When you learn something worth remembering, write it to the right file immediately
2. Keep memory.md as a current index with one-line descriptions
3. Entries: date, what, why – nothing more
4. Read memory.md at session start. Load other files only when relevant
5. If a file doesn't exist yet, create it

### Maintenance

When I say "reorganize memory":
1. Read all memory files
2. Remove duplicates and outdated entries
3. Merge entries that belong together
4. Split files that cover too many topics
5. Re-sort entries by date within each file
6. Update memory.md index
7. Show me a summary of what changed
```

---

## Proposed Solution

Maintain a structured memory system rooted at `.claude/memory/`.

### Structure

| Path | Purpose |
|------|---------|
| `memory.md` | Index of all memory files, updated whenever one is created or modified |
| `general.md` | Cross-project facts, preferences, environment setup |
| `domain/{topic}.md` | Domain-specific knowledge (one file per topic) |
| `tools/{tool}.md` | Tool configs, CLI patterns, workarounds |

### Entry Format

Every entry: **date, what, why** — nothing more. Keep entries short.

Example:
```
2026-03-09 | RBTV installer uses _config/.cursor/ as source; admin mode applies path substitution | Prevents confusion when editing rules in wrong location
```

### Rules (Agent Behavior)

1. **Write immediately:** When you learn something worth remembering, write it to the right file. Don't wait to be asked. Don't wait for session end.
2. **Index discipline:** Keep `memory.md` as a current index with one-line descriptions of each file.
3. **Read at session start:** Read `memory.md` at session start. Load other files (`general.md`, `domain/*`, `tools/*`) only when relevant.
4. **Create on demand:** If a file doesn't exist yet, create it.

### Maintenance Command

When the user says **"reorganize memory"**:

1. Read all memory files
2. Remove duplicates and outdated entries
3. Merge entries that belong together
4. Split files that cover too many topics
5. Re-sort entries by date within each file
6. Update `memory.md` index
7. Show a summary of what changed

---

## Implementation Scope

### In Scope

- Define `.claude/memory/` structure and create initial `memory.md`, `general.md`
- Add rule(s) or skill(s) that instruct agents to:
  - Read `memory.md` at session start (or via session hook / agent config if available)
  - Append to the appropriate file when discovering something worth remembering
  - Follow entry format: date, what, why
- Add "reorganize memory" as a command or agent-invokable workflow
- Document the system in RBTV rules or skills

### Out of Scope

- Automatic memory extraction (e.g., NLP over conversation) — manual/agent-triggered writes only
- Cross-workspace or cloud-backed memory — local filesystem only
- Claude Code native `memory:` agent field — use file-based system until/unless that is integrated

---

## Path Resolution

- **IDE mode (BMAD):** Memory lives at `{project-root}/.claude/memory/`
- **Admin mode (RBTV standalone):** Memory lives at `{rbtv-root}/.claude/memory/`

The installer does **not** create or populate memory — it is user/agent-generated content. Ensure `.claude/memory/` is in `.gitignore` or similarly excluded from version control if memory is considered local/sensitive.

---

## Acceptance Criteria

- [ ] `.claude/memory/` directory structure documented and created on first use
- [ ] `memory.md` index format defined and maintained
- [ ] Agent/rule instructs: read `memory.md` at session start
- [ ] Agent/rule instructs: append to correct file immediately when learning something worth remembering (date, what, why)
- [ ] `domain/` and `tools/` subdirs created on first write to those categories
- [ ] "Reorganize memory" command or workflow implements the 7-step maintenance protocol
- [ ] Entry format (date, what, why) enforced in documentation; agents follow it
- [ ] RBTV rules or skills document the memory system for agent awareness

---

## Dependencies

- RBTV runs in an environment where `.claude/` exists (Cursor, Claude Code, or equivalent)
- If `.claude/` is installer-managed, memory subdir must not be overwritten by installer

---

## Rationale

A file-based memory system is simple, transparent, and version-control friendly (if desired). It aligns with the "immediate capture" principle — write when you learn, not when you remember to. The structured layout (`general`, `domain/`, `tools/`) keeps content discoverable without requiring search. The maintenance command prevents entropy over time.
