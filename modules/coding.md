# Coding

## Purpose

This module is for workspaces where the human reading chat does not read code. It solves one problem: explaining code to a non-technical stakeholder in raw technical language blocks them from making decisions. `rbtv-non-technical-user` switches communication into plain language when the user does not read code.

> **Moved:** `rbtv-commit` (guided git commits) moved to the **core** module — committing with hygiene is a foundation concern, not a developer-only one. See [modules/core.md](./core.md).
>
> **Retired:** the `rbtv-coding-discipline` skill that used to live here (don't overcomplicate, don't assume silently, don't touch more than asked, define success criteria) was generalized into the always-on **reasoning** rule's *Execution Discipline* section (core module). Those guardrails apply to all artifact work — vault files, docs, plans — not only code, so a code-scoped skill was the wrong shape.

---

## Components

### `rbtv-non-technical-user`

- **What**: A passive rule that reshapes every chat message about code. Pairs every technical name with a plain-language translation (the user is learning the names AND needs to understand them), frames every coding decision as a behavior change instead of code mechanics, leads with the decision, bans raw log/diff/stack-trace dumps, and enforces a fixed question format with concrete options.
- **When to use**: Always active once the coding module is installed. Install this module ONLY in workspaces where the human reading chat does not read code — installing it in a technical workspace will make every response unnecessarily verbose.
- **How to invoke**: Automatic. No trigger. The rule loads passively into context and applies to every response.
- **What it produces**: Changed chat behavior — every code identifier paired with what it does, every decision framed as a system-behavior change ("rework how login is handled" not "refactor the auth module"), decision-first questions with named options, summaries instead of raw output. Code, commits, PRs, and files written to disk are not affected.
- **Example**:
  > User: "Did the import work?"
  > Agent: "Yes — the part that pulls invoices from the bank (called `importInvoices.ts` in code) loaded 47 records. Two were missing a date and got skipped. Fix the two now, or move on?"
  > Without the rule, the same response might say: "`importInvoices.ts` ran successfully, returning 47 records. 2 records failed Zod validation on the `issuedAt` field…"
