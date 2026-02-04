---
name: 'git-workflow'
description: 'Execute git operations with Conventional Commits messages'
main_config: '{project-root}/_bmad/rbtv/config.yaml'
nextStep: ./steps-c/step-01-init.md
---

# Git Workflow

**Goal:** Execute git operations (stage, commit, squash merge) with well-crafted Conventional Commits messages.

**Your Role:** Git operations executor collaborating with the user. You gather context, generate commit messages, and execute git commands with user approval.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **User Approval Required** — Never execute git operations without explicit user confirmation.

### Step Processing Rules

1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: load the next step file.

### Critical Rules

- 🛑 NEVER execute git commands without user approval
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- ⏸️ ALWAYS halt at menus and wait for user input
- 🔒 NEVER use --force, --no-verify, or destructive options

---

## MODE OVERVIEW

| Mode | Command | Purpose |
|------|---------|---------|
| ST | Stage + Commit | Stage all changes and commit |
| CO | Commit Staged | Commit pre-staged changes only |
| OR | Organize | Group changes into multiple logical commits |
| SQ | Squash Merge | Squash merge current branch to target |

---

## SIZE OPTIONS

| Size | Limit | Content |
|------|-------|---------|
| 280 | 280 chars | Concise summary only |
| 1000 | 1000 chars | Summary + categorized sections |
| 2000 | 2000 chars | Comprehensive with full context |

---

## PUSH OPTION

- **+push** — Push to remote after commit(s)
- **no push** — Commit only (default)

---

## INITIALIZATION SEQUENCE

1. Parse command for mode, size, and push flag
2. Prompt for missing parameters
3. Load `steps-c/step-01-init.md`
4. Follow step instructions exactly
