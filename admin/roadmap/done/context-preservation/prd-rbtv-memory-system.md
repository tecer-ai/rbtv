---
title: 'RBTV Memory System'
description: 'Implement a structured memory system at .claude/memory/ for AI agents to capture and recall learnings across sessions — architectural decisions, bug fixes, gotchas, environment quirks, and agent self-corrections (failed commands/actions that were retried successfully).'
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
- Agents repeat the same execution mistakes across sessions (e.g., using bash syntax in PowerShell) because self-corrections are not persisted

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
6. Self-correction capture: when a command/action fails and a retry with a different approach succeeds, write immediately to tools/{tool}.md using format: date | SELF-CORRECTION: failed → working | reason. No user prompting required.
7. Before executing commands, read relevant tools/*.md to avoid repeating known failures

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
5. **Self-correction capture:** When a command or action fails and the agent retries with a different approach that succeeds, write the correction to memory immediately. See "Self-Correction Capture" section below.

---

### Self-Correction Capture

**What this is:** Agents sometimes attempt a command, get an error, then try a different approach that works. This trial-and-error knowledge is lost when the session ends. The same mistake repeats in future sessions.

**This differs from user-provided knowledge.** The user does not tell the agent what went wrong — the agent discovers the failure itself, self-corrects, and moves on. Without explicit capture, the correction vanishes.

#### Trigger

The agent MUST write to memory when ALL three conditions are met:

1. Agent attempted a command or action
2. It failed (non-zero exit code, parser error, unexpected output, tool rejection)
3. Agent retried with a different approach and it succeeded

#### What to Capture

| Field | Content |
|-------|---------|
| **Date** | Session date |
| **Failed approach** | The exact command or pattern that failed |
| **Working approach** | The exact command or pattern that succeeded |
| **Platform/context** | Why it failed (shell type, OS, tool version, syntax difference) |

#### Entry Format

Use the extended format for self-corrections (superset of the standard `date | what | why`):

```
date | SELF-CORRECTION: failed → working | reason
```

#### Examples

```
2026-03-15 | SELF-CORRECTION: PowerShell rejects `&&` for command chaining and `<<'EOF'` heredoc syntax → use sequential `git add` then `git commit`, use `-m` flags for multi-line messages | PowerShell is not bash — different chaining and string operators
```

```
2026-03-12 | SELF-CORRECTION: `dir /s /b file1 file2` fails in PowerShell with FileStream error → use `Get-ChildItem` or separate commands per path | PowerShell `dir` is alias for Get-ChildItem, does not support multiple bare path args like cmd.exe
```

```
2026-03-10 | SELF-CORRECTION: `git status --staged` rejected (unknown option) → use `git diff --cached --name-only` for staged files | Git version does not support --staged flag on status subcommand
```

#### Storage Location

Self-correction entries go to `tools/{tool}.md` where `{tool}` is the tool or platform that caused the failure (e.g., `tools/powershell.md`, `tools/git.md`).

#### Agent Obligation

- MUST write immediately after the successful retry — not at session end, not when asked.
- MUST NOT require user prompting. The agent recognizes the pattern (fail → retry → succeed) and writes autonomously.
- MUST read relevant `tools/*.md` files before executing commands in that tool's domain to avoid repeating known failures.

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

### Non-Committed, User-Specific Storage

Memory files MUST NOT be committed to any git repository. This is critical because:

1. **RBTV is shared.** Multiple users run RBTV. Learnings are specific to each user's environment (OS, shell, tool versions, IDE) and must not pollute the shared codebase.
2. **Self-corrections are machine-specific.** A PowerShell workaround is irrelevant to a macOS/zsh user. Committing these would create noise for other users.
3. **In BMAD IDE mode, this is already solved.** Memory lives at `{project-root}/.claude/memory/`, which is inside the BMAD workspace — outside any RBTV git tree. Each user's BMAD workspace has its own memory.
4. **In RBTV admin/standalone mode,** memory lives at `{rbtv-root}/.claude/memory/`. The `.claude/memory/` path MUST be in RBTV's `.gitignore` to prevent accidental commits.

The installer MUST NOT create or populate memory files — they are user/agent-generated content that accumulates over time per user.

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
- [ ] Self-correction capture: agent writes to `tools/{tool}.md` immediately when a command fails and a retry succeeds — without user prompting
- [ ] Self-correction entries use the extended format: `date | SELF-CORRECTION: failed → working | reason`
- [ ] Agent reads relevant `tools/*.md` before executing commands to avoid repeating known failures
- [ ] `.claude/memory/` is in RBTV's `.gitignore` (admin/standalone mode) — memory is never committed
- [ ] In BMAD IDE mode, memory path resolves outside the RBTV git tree (no gitignore needed)

---

## Dependencies

- RBTV runs in an environment where `.claude/` exists (Cursor, Claude Code, or equivalent)
- If `.claude/` is installer-managed, memory subdir must not be overwritten by installer

---

## Rationale

A file-based memory system is simple, transparent, and version-control friendly (if desired). It aligns with the "immediate capture" principle — write when you learn, not when you remember to. The structured layout (`general`, `domain/`, `tools/`) keeps content discoverable without requiring search. The maintenance command prevents entropy over time.

---

## Related: Shape Capture System

**PRD:** `_admin/roadmap/todos/compound-context-preservation-rule.md`

The Memory System and the Shape Capture system are complementary:

| Dimension | Memory System (this PRD) | Shape Capture |
|-----------|--------------------------|---------------|
| **Purpose** | Agent self-improvement — reusable knowledge across sessions | Project continuity — specific project context between agents |
| **Scope** | Cross-session, cross-project | Project-specific, session-specific |
| **Content** | Short entries: "date, what, why" + self-correction entries: "date, failed → working, reason" | Rich narrative: user inputs, decisions, reasoning, nuances |
| **Trigger** | Agent discovers knowledge OR agent self-corrects after failure (autonomous) | User provides context worth preserving (user-driven) |
| **Location** | `.claude/memory/` | Alongside workflow output: `{output-name}-shape.md` |

Both follow the "write immediately" principle. Both are file-based. They do not compete — an agent uses BOTH: reusable learnings go to memory, project context goes to shape.

**Key distinction on knowledge sources:**

| Source | Example | Capture Mechanism |
|--------|---------|-------------------|
| **User tells agent** | "This project uses PowerShell, not bash" | Context Preservation / Shape Capture |
| **Agent discovers** | Agent reads a config file and learns a convention | Memory System (standard entry) |
| **Agent fails and self-corrects** | Agent tries `&&` in PowerShell, gets error, retries with `;` | Memory System (self-correction entry) — no user input needed |
