# Coding

## Purpose

This module is for developers working with Claude Code on real codebases. It solves two problems: committing changes without thinking about repo hygiene produces messy history; and explaining code to a non-technical stakeholder in raw technical language blocks them from making decisions. `rbtv-commit` handles the commit itself with proper hygiene and conflict handling, and `rbtv-non-technical-user` switches communication into plain language when the user does not read code.

> **Retired:** the `rbtv-coding-discipline` skill that used to live here (don't overcomplicate, don't assume silently, don't touch more than asked, define success criteria) was generalized into the always-on **reasoning** rule's *Execution Discipline* section (core module). Those guardrails apply to all artifact work — vault files, docs, plans — not only code, so a code-scoped skill was the wrong shape.

---

## Components

### `rbtv-commit`

- **What**: A guided git commit workflow that analyzes your diff, clusters changes by concern (one commit per cluster — unrelated changes never share an umbrella commit), drafts a conventional commit message per cluster, checks for remote changes before committing, handles stash/conflict scenarios, stages specific files (never `git add -A`), and checks the index for pre-staged foreign files before each commit (unstage or disclose — never commit them silently).
- **When to use**: Any time you want to commit changes. Also triggers automatically when a task finishes and you say something like "done, save this."
- **How to invoke**: Say "commit", "commita", or "salva no git". The skill also fires when you say "done, commit this" after completing a task.
- **What it produces**: One or more scoped commits in the current repo, with the commit plan confirmed by you before anything is staged. Push happens only if you ask for it.
- **Example**:
  > User: "commit my changes"
  > Agent runs `git status` and `git diff`, then:
  > "Here's what changed: [summary]. Proposed message: `fix(auth): handle expired token on refresh`. Confirm or edit?"
  > User: "looks good"
  > Agent stages specific files, commits, and reports the commit hash. Does not push unless asked.

  If remote commits exist that you don't have locally, the skill fetches first, stashes your work, pulls, and pops — surfacing conflicts for you to resolve before touching the commit step.

---

### `rbtv-non-technical-user`

- **What**: A passive rule that reshapes every chat message about code. Pairs every technical name with a plain-language translation (the user is learning the names AND needs to understand them), frames every coding decision as a behavior change instead of code mechanics, leads with the decision, bans raw log/diff/stack-trace dumps, and enforces a fixed question format with concrete options.
- **When to use**: Always active once the coding module is installed. Install this module ONLY in workspaces where the human reading chat does not read code — installing it in a technical workspace will make every response unnecessarily verbose.
- **How to invoke**: Automatic. No trigger. The rule loads passively into context and applies to every response.
- **What it produces**: Changed chat behavior — every code identifier paired with what it does, every decision framed as a system-behavior change ("rework how login is handled" not "refactor the auth module"), decision-first questions with named options, summaries instead of raw output. Code, commits, PRs, and files written to disk are not affected.
- **Example**:
  > User: "Did the import work?"
  > Agent: "Yes — the part that pulls invoices from the bank (called `importInvoices.ts` in code) loaded 47 records. Two were missing a date and got skipped. Fix the two now, or move on?"
  > Without the rule, the same response might say: "`importInvoices.ts` ran successfully, returning 47 records. 2 records failed Zod validation on the `issuedAt` field…"

---

## Commit Message Style

`rbtv-commit` follows [conventional commits](https://www.conventionalcommits.org/): first line under 72 characters, message explains the *why* (the diff already shows the what).
