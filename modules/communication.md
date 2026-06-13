# Communication

## Purpose

Audience-adapted communication for workspaces whose chat readers are not domain experts in what the agent is doing. Elective and **independent of the coding module** — a workspace can get plain-language output without the coding done-gate, and vice versa. Two rules, layered:

- **General layer** (`rbtv-plain-language`) — make every word understandable to a non-expert: define terms, no jargon, no analogies, no bare name-drops, state what a plan phase IS.
- **Code overlay** (`rbtv-non-technical-user`) — the code-specific layer on top: translate code identifiers, frame coding decisions as behavior changes, ban raw output dumps.

Both are MECE with `chat-discipline` (core), which owns brevity + lead-with-the-decision — the communication rules never restate it.

## Scoping

Both rules load always-on once this module is installed (`rbtv-plain-language` ≈ 430 words, `rbtv-non-technical-user` ≈ 640 words after the dedup that moved its general clauses into plain-language). Install this module in workspaces where the human reading chat is not an expert in the agent's domain; a fully technical workspace can omit it and avoid the always-on load. Election is independent of the `coding` module — that was the reason for the split.

---

## Components

### `rbtv-plain-language`

- **What**: A passive rule that reshapes every explanatory chat message for a non-expert reader — defines every term on first use, bans analogies and unexpanded acronyms, forbids bare name-drops (every name paired with what it is), and requires a plan phase's meaning, not just its label.
- **When to use**: Always active once the communication module is installed.
- **How to invoke**: Automatic. No trigger. Loads passively into context.
- **What it produces**: Changed chat behavior — jargon defined inline, no "think of it like…" analogies, every codename/phase paired with what it does. Code, commits, and files on disk are unaffected (chat prose only).
- **Relation**: the general layer; `rbtv-non-technical-user` is its code-specific overlay; `chat-discipline` (core) owns brevity + decision-first.

### `rbtv-non-technical-user`

- **What**: A passive rule that adds the code-specific layer for non-technical stakeholders — pairs every code identifier with a plain-language translation, frames every coding decision as a behavior change instead of code mechanics, bans raw log/diff/stack-trace dumps, and enforces a fixed named-options question format. Defers general plain-language to `rbtv-plain-language` and lead-with-the-decision to `chat-discipline`.
- **When to use**: Always active once the communication module is installed. Install in workspaces where the human reading chat does not read code.
- **How to invoke**: Automatic. No trigger.
- **What it produces**: Every code identifier paired with what it does, every decision framed as a system-behavior change ("rework how login is handled" not "refactor the auth module"), decision-first questions with named options, summaries instead of raw output.
- **Example**:
  > User: "Did the import work?"
  > Agent: "Yes — the part that pulls invoices from the bank (called `importInvoices.ts` in code) loaded 47 records. Two were missing a date and got skipped. Fix the two now, or move on?"

> **History:** `rbtv-non-technical-user` moved here from the `coding` module (2026-06-13) so plain-language output is electable independent of coding. Its general clauses (define terms, no jargon) were lifted into the new `rbtv-plain-language` rule to keep the two MECE.
