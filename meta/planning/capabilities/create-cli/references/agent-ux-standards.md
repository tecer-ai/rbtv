---
description: Agent UX Standards for CLIs — create-cli capability reference
tags: [planning]
---

# Agent UX Standards for CLIs

The interaction-quality rubric for CLIs whose primary user is an AI agent. Build mode satisfies
these while scaffolding; review mode judges an existing CLI against them. Distilled from a
production redesign (a multi-agent coordination CLI, 2026-07) where every standard below traces
to a measured failure or a verified win.

**Mental model:** an agent pays for every output byte twice — once in context window, once in
attention. A CLI's job is to hand over the RIGHT information at the RIGHT moment, then name what
to do next. All fourteen standards are that one idea applied to help, errors, output, and state.

## 1. Help is layered, never a manual

- Top-level `--help` ≤ ~30 lines: commands grouped by user journey (everyday / admin / rare),
  ONE line each, footer pointing to per-command help. Never dump a manual into `-h` — an agent
  re-reads it constantly and drowns.
- Per-command `--help` is complete at the point of need: what/when (2-4 lines), argument
  meanings, ONE realistic example, and a `next:` line naming what typically follows.
- The failure smell: a huge top-level help AND empty per-command help (the inversion). Both
  directions of the inversion are defects.

## 2. Errors teach

Every refusal states, in order: what was refused, why it matters, the exact fix (a runnable
command where possible), and the escape flag if one exists. The agent must be able to recover
from the error text alone — an error that requires a doc lookup wastes a full turn.

```
refused: 'alfa' is not a known recipient — no roster row, no briefing, no group. Did you mean 'alpha'?
known: all, alpha, beta, master
send anyway: --force
```

## 3. Output ends with the next step

Success output ends with the natural next command — derived from ACTUAL state, never asserted
blindly (a hint pointing at an already-settled item teaches the wrong model and spends a turn).
This turns the CLI into a self-navigating workflow: an agent that only reads the last two lines
of each output still walks the happy path correctly.

## 4. Output is bounded; continuation is safe

- Lists, logs, and feeds cap by default (~10 items) with an explicit continuation:
  `-- 14 more waiting — run <command> again`. Always show at least one item even if oversized.
- If reading CONSUMES position (a cursor, an offset, a queue), advance it only through what was
  actually SHOWN — never past hidden items. Filtered or preview views never advance consumption
  state, and say so in their output.
- Provide digest → detail navigation: a one-line-per-item scan view plus a fetch-one-item
  command. An agent triages in the digest and spends full attention only where needed.

## 5. Context is ambient and verified

- Resolve identity/target/config instead of demanding it per call: explicit flag > environment
  variable > runtime lookup (e.g. which session/pane/directory is calling). Commands shrink and
  a whole typo class disappears.
- VERIFY claims: a passed identity that contradicts the resolved one is refused loudly, with a
  deliberate override (`--as` + `--force`). Trust nothing that can be mistyped.
- When the tool spawns its own consumers (workers, sessions), inject the context at spawn time
  (env prefix) so the consumers never type it either.

## 6. Output modes: terse default, pretty opt-in, JSON for machines

- Default output is plain, terse, agent-lean. Zero decoration.
- A human mode (`--pretty` / env var) adds color and alignment for the view commands only.
- NEVER auto-detect TTY to choose the mode — agents live in TTYs too; the default must be the
  agent mode everywhere, with humans opting in explicitly.
- `--json` wherever output is machine-consumed (see agent-cli-patterns.md for shapes).

## 7. Free text has a shell-safe path

Any argument that can carry backticks, quotes, `$(...)`, or newlines gets a `--file PATH` /
`--file -` (stdin) alternative — the shell mangles inline text before the tool ever sees it
(a real corruption class). The argument's own help teaches when to switch.

## 8. References are validated, with suggestions

Names that refer to known entities (recipients, projects, IDs) are validated against the full
known set — including declared-but-not-yet-active entities — and refused with a closest-match
suggestion (difflib-style) plus the known list. A typo'd reference silently accepted becomes a
message nobody reads or a write nobody finds.

## 9. Orientation commands exist

- `doctor`: config, auth, environment health — "can this tool work here?"
- `status`: workflow state — "who am I, where am I, what needs me, what next?"
An agent with zero context (fresh session, post-crash) must reach full orientation in ONE
command, not by re-reading docs or replaying history.

## 10. Noise discipline

- Never log or report a failure for something never attempted (a skipped delivery to an absent
  recipient is not a failure — measured live: 46 fake failure lines burying 1 real one).
- Expected absences are named quietly in a summary; only genuine failures get their own lines.
- Per-item success spam collapses to one summary line: `ticks: 7 delivered, 1 failed (name:
  reason), 2 skipped (departed)`.

## 11. Concurrency honesty

- Lock every read-modify-write on shared state (flock on a lockfile); tolerate lock-acquire
  failure gracefully (read-only sandboxes) rather than crashing.
- Auxiliary persistence (cursors, bookkeeping) is NON-FATAL: its failure degrades with a
  one-line recovery hint; it never takes down the primary operation.
- Parallelize independent slow I/O (network calls, per-recipient delivery) with deterministic
  (sorted) output ordering.

## 12. Grammar is uniform

- Positional #1 means ONE class of thing across every command (e.g. always the target, never
  sometimes the caller) — mixed meanings are a live incident source.
- One consistent escape flag (`--force`) for every deliberate override; shared flag vocabulary;
  no opaque value names (`--addressed both` → `--addressed any|direct|broadcast`).
- Role-gated commands actually check the resolved identity (refuse + escape), not a "(admin)"
  note in the help.

## 13. The tool tests itself

A `selftest` command runs anywhere (external dependencies stubbed), and every new or altered
mechanic gets a check IN THE SAME CHANGE. Stubs' signatures and return types MUST match the real
functions — a stub returning a bare string where the real function returns a tuple shipped a
visible output bug while the suite stayed green.

## 14. One source of truth for teaching

The command inventory lives in exactly one place (the argument parser). Module docstrings,
READMEs, and companion docs POINT at `-h` instead of re-listing commands — every duplicated
inventory was found drifted in practice.

## Review smell table (symptom → standard)

| Symptom | Standard violated |
|---------|-------------------|
| `-h` scrolls for pages / subcommand help is empty | 1 |
| Error says only "invalid X" | 2 |
| Output stops dead; agent must know the workflow by heart | 3 |
| A catch-up read dumps everything; position advances past unshown items | 4 |
| Every command retakes the caller's name/ID; typos accepted | 5, 8 |
| Colors in piped output, or mode switches on TTY | 6 |
| Inline free text corrupted by the shell | 7 |
| Fresh session needs N commands + a doc to orient | 9 |
| Failure log full of expected absences | 10 |
| Duplicate IDs / crashes under parallel calls; cursor write kills the read | 11 |
| Positional #1 changes meaning between commands | 12 |
| Green tests, visibly wrong output | 13 |
| Docstring/README teach a grammar that now errors | 14 |
