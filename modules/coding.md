# Coding

## Purpose

This module is for developers working with Claude Code on real codebases. It solves two problems that come up constantly in AI-assisted development: LLMs tend to overcomplicate, assume silently, and touch more than they should — and committing changes without thinking about repo hygiene produces messy history. `rbtv-coding-discipline` shapes Claude's behavior during code work; `rbtv-commit` handles the commit itself with proper hygiene and conflict handling.

---

## Components

### `rbtv-coding-discipline`

- **What**: A set of behavioral guardrails that fire whenever Claude writes, reviews, or modifies code. Covers four failure modes: silent assumptions, over-engineering, orthogonal edits, and vague success criteria.
- **When to use**: Auto-triggers on any task involving code files (HTML, JS, CSS, Python, scripts). You don't invoke it — it activates when the task matches.
- **How to invoke**: Automatic. Works on any prompt that involves editing or writing code. No slash command needed.
- **What it produces**: Changed behavior, not a file. Claude will explicitly state assumptions before coding, flag when multiple interpretations exist, write minimum viable code, touch only what the task requires, and define verifiable success criteria for multi-step tasks.
- **Example**:
  > User: "Add validation to the form."
  > Agent: "Before I start — I'm assuming the form submits to `/api/register` and that validation means client-side only. Is that right? My success criteria: write a test for each invalid input, then make them pass. Here's my plan: [1] add tests → [2] implement validation → [3] verify no regressions."

---

### `rbtv-commit`

- **What**: A guided git commit workflow that analyzes your diff, drafts a conventional commit message, checks for remote changes before committing, handles stash/conflict scenarios, and stages specific files (never `git add -A`).
- **When to use**: Any time you want to commit changes. Also triggers automatically when a task finishes and you say something like "done, save this."
- **How to invoke**: Say "commit", "commita", or "salva no git". The skill also fires when you say "done, commit this" after completing a task.
- **What it produces**: A clean commit in the current repo, with the message confirmed by you before anything is staged. Push happens only if you ask for it.
- **Example**:
  > User: "commit my changes"
  > Agent runs `git status` and `git diff`, then:
  > "Here's what changed: [summary]. Proposed message: `fix(auth): handle expired token on refresh`. Confirm or edit?"
  > User: "looks good"
  > Agent stages specific files, commits, and reports the commit hash. Does not push unless asked.

  If remote commits exist that you don't have locally, the skill fetches first, stashes your work, pulls, and pops — surfacing conflicts for you to resolve before touching the commit step.

---

## Commit Message Style

Both skills align on the same convention: [conventional commits](https://www.conventionalcommits.org/), first line under 72 characters, message explains the *why* (the diff already shows the what).
