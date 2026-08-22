---
description: CLI UX Review Mode — create-cli capability reference
tags: [planning]
---

# CLI UX Review Mode

Critically review and redesign an EXISTING CLI as a UX designer for AI-agent interfaces. This is
the playbook that redesigned a production multi-agent coordination CLI end-to-end (2026-07):
hands-on audit → evidence-backed findings → owner debate → settled spec → staged implementation
→ independent verification. Judge everything against [agent-ux-standards.md](agent-ux-standards.md).

**Posture:** critical, evidence-first. Your value is proportional to the defects you find and
prove, not the compliments you pay. Never propose a change you cannot tie to a measured number,
an observed incident, or a named standard.

## Phase 0 — Intake (before touching anything)

Ask 2-4 multiple-choice questions, each with consequences per option and ONE recommendation:

1. **Breaking freedom** — may command names/flags/output change (docs updated in the same
   change), additive-only, or new-surface-with-aliases?
2. **Audience** — agents only, agents-first, or two output modes (agent default + human flag)?
3. **Ambition** — top 2-3 wins, or everything that survives the debate?

Then locate the binding constraints BEFORE planning: required test gates (a selftest that must
stay green), doc-sync rules (design docs updated in the same change), generated/installed copies
(NEVER edit a copy an installer regenerates — find the source), and frozen surfaces (state-file
formats other tools parse).

## Phase 1 — Hands-on exploration

- Run `-h` at every level yourself; read the FULL source; read every doc that teaches the tool
  (protocol docs, templates, prompts that embed its command lines).
- **Map the consumers:** grep the workspace for callers; find every parser of its output or
  state files; find every doc/template embedding its grammar. This map is the blast radius of
  any breaking change — without it the redesign ships breakage.
- **Measure real usage at scale:** find production state/logs and compute the numbers (item
  counts, sizes, over-threshold counts). "305 messages averaging 1,243 chars" argues; "output
  feels long" doesn't. Mine incident/observation logs for already-known defects — absorb any
  queued fix backlog into the redesign instead of colliding with it.
- Exercise the tool against real data READ-ONLY (peek/dry-run modes, scratch copies). Never
  mutate live state; check for live consumers (running sessions) before assuming safety.
- Baseline the test suite (run it yourself, record the count).

## Phase 2 — Findings

Two lists in a working doc: **what it does well** (keep; generalize its best patterns) and
**defects, each with evidence** (a number, an incident reference, or file:line) ranked by user
impact. Use the standards' smell table as the sweep. Then group defects into 4-7 debate topics.

**Working doc discipline:** one doc holds status, rulings, spec, and execution state — updated
the SAME turn anything changes. A fresh agent must be able to resume from the doc alone.

## Phase 3 — Debate, one topic at a time

- One topic per round, plain words, zero jargon, every ID/acronym expanded.
- Options a/b/c with honest consequences for each and one recommendation with its reason.
  Before/after command mockups beat prose descriptions.
- Record each ruling in the working doc immediately. Defects you discover WHILE specifying
  (they happen — filtered reads that silently consume position) get folded in and flagged.

## Phase 4 — Settled spec

Written so implementers need nothing else: final command surface table (grammar + gate per
command), resolution/edge rules (identity precedence, cursor rules, validation sets, limits),
frozen surfaces + out-of-scope list, doc-sweep list (every file that teaches the old grammar),
and the verification plan.

## Phase 5 — Staged implementation

- **Sequential agents on shared files, never parallel:** behavior/mechanics first, then
  presentation/help/docs. The presentation agent MUST NOT alter behavioral semantics — it
  reports suspected behavior bugs, never fixes them.
- Each brief: self-contained, workspace-absolute paths, the spec section it executes, hard
  constraints (tests green in the same change, frozen grammars, no commits, footgun warnings),
  and a required report file listing changes, deviations WITH reasons, and test output tails.
- Verify every return yourself before proceeding: rerun the tests, diffstat the claimed files,
  confirm the report exists. Relay each agent's deviations forward to the next brief.

## Phase 6 — Verification, fix round, presentation

1. Rerun ALL test suites yourself (never trust a reported pass).
2. **Live drill:** a scripted end-to-end run in a scratch environment (scratch state + real
   runtime, e.g. a throwaway tmux session) exercising every new behavior AND every refusal
   path, with machine-checked PASS/FAIL lines. The drill catches what stubbed tests cannot
   (a real one caught a phantom-failure class the suite missed).
3. **Stale-grammar sweep:** grep every teaching doc for old flags/forms — expect zero hits.
4. **Consumer-contract check:** run the mapped external parsers against new-code output.
5. One fix agent for the numbered backlog (drill failures + agent-reported items), precisely
   scoped; then re-verify to 100% (drill fully green) before presenting.
6. Present leading with the outcome and the numbers (checks passed, drill score, files, +/-),
   the rulings implemented, deviations approved, what was deliberately NOT done (commits,
   deferred items), and where every artifact lives. Commit only on the owner's explicit ask.

## Never

- Never edit an installed/generated copy — find the source, then reinstall/regenerate.
- Never rewrite closed/historical artifacts that cite the old grammar — history stays.
- Never let presentation work change behavior, or a fix agent exceed its numbered scope.
- Never present with a known-red check, a skipped drill, or an unverified agent claim.
