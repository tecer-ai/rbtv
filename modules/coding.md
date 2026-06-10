# Coding

## Purpose

This module is for workspaces where the human reading chat does not read code. It solves two problems:

1. **Communication** — explaining code to a non-technical stakeholder in raw technical language blocks them from making decisions. `rbtv-non-technical-user` switches communication into plain language.
2. **Trust in "done"** — agents declare done on self-graded, presence-shaped proof (tests green, element renders) that a non-technical owner cannot audit, so broken features surface under the owner's hand at point of real use. `rbtv-done-gate` makes done purchasable only with user-fidelity evidence. It also runs a Contract-time drivability check: agents that hit a surface they cannot drive (a native OS dialog, an isolated-run config that leaks to real data, a fused output where you can't tell which arm fired) used to re-invent the same workaround at done-time on every project — the gate now moves that discovery to build-time and transmits the known seam patterns so the feature is built drivable from the start.

> **Moved:** `rbtv-commit` (guided git commits) moved to the **core** module — committing with hygiene is a foundation concern, not a developer-only one. See [modules/core.md](./core.md).
>
> **Retired:** the `rbtv-coding-discipline` skill that used to live here (don't overcomplicate, don't assume silently, don't touch more than asked, define success criteria) was generalized into the always-on **reasoning** rule's *Execution Discipline* section (core module). Those guardrails apply to all artifact work — vault files, docs, plans — not only code, so a code-scoped skill was the wrong shape.

## Scoping

Both rules load always-on once this module is installed (`rbtv-done-gate` ≈2,256 words, `rbtv-non-technical-user` 719 — ≈2,975 always-on words). The module IS the scoping boundary: a workspace that does no coding **omits the `coding` module at install** and avoids that load entirely. This is an install-time election the existing module-granular manifest already supports — not a runtime guess, so no protection is ever silent when a coding task fires. Workspaces that DO code keep both rules always-on.

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

- **What**: A passive rule that gates every done-claim on coding tasks. At task intake the agent drafts outcome criteria in plain language ("when done, the owner can {gesture} and {visible result} happens") and confirms them in one pass — the owner never writes formalism. At that same Contract moment it runs a per-criterion **drivability check** before any code is written: for each owner-observable outcome, is its surface something the agent can drive and observe with a real gesture? If not, the agent must build a **test seam** for that surface as part of the feature — a guarded path that supplies or exposes only the unreachable part while the human-facing gesture stays real (three evidenced seam patterns ship: native OS dialogs/widgets, isolated-run config isolation, fused/composed output). One surface is pre-classified at Contract: a live multi-turn interactive workflow-agent / persona session (`/sb-investor`, `/sb-tutor`, mode-routing via a fresh skill invocation) is marked `un-seamable: interactive-agent-session → owner-UAT` and exercised by the owner on a real session — never claimed `drivable`. Before declaring done, the agent exercises each criterion the way the owner will use the feature (real application running whole, owner's actual data when it exists, visible browser + real gestures for UI) and fills a per-criterion evidence sheet — gesture performed, observed result, capture file, verdict. No sheet → done is undeclarable; a failed row → back to build; unexercisable rows must be surfaced in the done message. `held-surprising` rows — where a criterion holds technically but via a non-obvious mechanism the owner must judge — are also surfaced in the done message; the owner decides acceptance.
- **When to use**: Always active once the coding module is installed. Fires on every coding task except an explicit exempt list (typos, formatting, comments, zero-behavior cleanups, runtime-invisible config). Non-code work is out of scope.
- **How to invoke**: Automatic. No trigger. Loads passively and fires at task intake (Contract — including the drivability check) and at every done-claim (Exercise + Exhibit).
- **What it produces**: A drivability row per criterion at Contract time (`criterion | surface | verdict | seam built`) plus any test seams built into the feature; an owner-auditable evidence sheet on disk per task, capture files created during the exercise, and done messages that cite the sheet and surface every `failed`, `unexercisable`, and `held-surprising` row. For orchestrated development dispatches, an independent cold verifier re-exercises the contract from day one.
- **Example**:
  > Agent at intake: "Done means: you drag the right edge of a slide element and it visibly resizes, on your real deck. Confirm?"
  > …builds, then drives the deck in a visible browser, performs the drag, captures before/after screenshots…
  > Agent: "Done — 1/1 criteria held. Evidence: `docs/done-gate-evidence/hypresent/2026-06-06-resize.md` (width 312→468px, screenshots attached)."
  > For a criterion whose surface the agent can't drive — e.g. "you click Open…, pick a deck, and it loads" hits the native file picker — the Contract-time drivability check marks it `needs-seam` and the agent builds a test seam (env-gated path injection) while the Open… click stays a real gesture, so the done-gate exercise drives the real flow without faking the click.
