# Coding

## Purpose

This module is for workspaces where the human reading chat does not read code. It solves three problems:

1. **Communication** — explaining code to a non-technical stakeholder in raw technical language blocks them from making decisions. `rbtv-non-technical-user` switches communication into plain language.
2. **Trust in "done"** — agents declare done on self-graded, presence-shaped proof (tests green, element renders) that a non-technical owner cannot audit, so broken features surface under the owner's hand at point of real use. `rbtv-done-gate` makes done purchasable only with user-fidelity evidence.
3. **Re-discovered test seams** — agents hit a surface they cannot drive (a native OS dialog, an isolated-run config that leaks to real data, a fused output where you can't tell which arm fired) at done-time, then re-invent the same workaround on the next project. `rbtv-build-for-agent-testability` moves that discovery to build-time and transmits the known seam patterns so the feature is built drivable from the start.

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

### `rbtv-done-gate`

- **What**: A passive rule that gates every done-claim on coding tasks. At task intake the agent drafts outcome criteria in plain language ("when done, the owner can {gesture} and {visible result} happens") and confirms them in one pass — the owner never writes formalism. Before declaring done, the agent exercises each criterion the way the owner will use the feature (real application running whole, owner's actual data when it exists, visible browser + real gestures for UI) and fills a per-criterion evidence sheet — gesture performed, observed result, capture file, verdict. No sheet → done is undeclarable; a failed row → back to build; unexercisable rows must be surfaced in the done message. `held-surprising` rows — where a criterion holds technically but via a non-obvious mechanism the owner must judge — are also surfaced in the done message; the owner decides acceptance.
- **When to use**: Always active once the coding module is installed. Fires on every coding task except an explicit exempt list (typos, formatting, comments, zero-behavior cleanups, runtime-invisible config). Non-code work is out of scope.
- **How to invoke**: Automatic. No trigger. Loads passively and fires at task intake (Contract) and at every done-claim (Exercise + Exhibit).
- **What it produces**: An owner-auditable evidence sheet on disk per task, capture files created during the exercise, and done messages that cite the sheet and surface every `failed`, `unexercisable`, and `held-surprising` row. For orchestrated development dispatches, an independent cold verifier re-exercises the contract from day one.
- **Example**:
  > Agent at intake: "Done means: you drag the right edge of a slide element and it visibly resizes, on your real deck. Confirm?"
  > …builds, then drives the deck in a visible browser, performs the drag, captures before/after screenshots…
  > Agent: "Done — 1/1 criteria held. Evidence: `docs/done-gate-evidence/hypresent/2026-06-06-resize.md` (width 312→468px, screenshots attached)."

### `rbtv-build-for-agent-testability`

- **What**: A passive rule that is the build-time twin of `rbtv-done-gate`. At the done gate's Contract moment it runs a per-criterion **drivability check** before any code is written: for each owner-observable outcome, is its surface something the agent can drive and observe with a real gesture? If not, the agent must build a **test seam** for that surface as part of the feature — a guarded path that supplies or exposes only the unreachable part while the human-facing gesture stays real. It ships three evidenced seam patterns (native OS dialogs/widgets, isolated-run config isolation, fused/composed output) drawn from real escapes, and explicitly excludes broader agent-operability doctrine (parity audits, CRUD completeness, capability discovery) that has no evidence yet.
- **When to use**: Always active once the coding module is installed. Same default-ON coding-task scope as `rbtv-done-gate`; shares its exempt list and its evidence sheet.
- **How to invoke**: Automatic. No trigger. Loads passively and fires at Contract time, one drivability row per criterion on the done-gate evidence sheet.
- **What it produces**: A drivability row per criterion at Contract time (`criterion | surface | verdict | seam built`), and test seams built into the feature so each owner-observable outcome is exercisable at the done gate's fidelity floor instead of re-discovered at done-time.
- **Example**:
  > Agent at intake: "Done means: you click Open…, pick a deck, and it loads. That click hits the native file picker, which I can't drive — so I'll build a test seam (env-gated path injection) while the Open… click stays a real gesture. Confirm the outcome?"
  > …builds the feature AND the seam together, so the done-gate exercise can drive the real flow without faking the click.
