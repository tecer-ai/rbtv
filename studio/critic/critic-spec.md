# Spec — Studio Critic (v1.1)

> Behavior source of truth for the studio module's critic. The critic procedure references this spec for the behavioral floor — it never restates it. The critic is a best-effort improver + stopping rule, NEVER the quality gate. The HUMAN gate stays final.

## Goal

A worker mid-loop (or the owner) can hand the critic two or more deck/page variants — or one artifact plus the project's reference anchors — and get back a comparative, taxonomy-cited critique: which variant is stronger and why, plus a structural flaw list; aesthetic observations are advisory and routed to the human, never scored, never gating.

## Context Snapshot

- **Evidence scoping (sparring research):** absolute scoring is unreliable (35–38% exact-score accuracy) while pairwise comparison reaches 90–93% on clearly-different designs [S1]; open-ended critique is weak (F1 0.33–0.66) while taxonomy-guided critique detects and remediates better [S3]; taste is personal (Krippendorff α=0.25) so anchoring is per-project, never universal [S2].
- **The four pins:** comparative (rank / A-vs-B, never absolute scores) · taxonomy-driven (explicit flaw taxonomy, never "tell me what's wrong") · structural-auto / aesthetic-HUMAN split · per-project anchoring to THIS project's reference set + taste file.
- **Distinct from fresh-eyes:** fresh-eyes is a prompt-file review in a fresh session — no scoring, no taxonomy dataset, runs before every owner gate. The critic is the BUILT component with a maintained taxonomy and comparative protocol. Both exist; neither replaces the other.
- **Wiring:** loop beats MAY invoke the critic pre-gate (optional); the human gate remains final and is never blocked or auto-passed by critic output.

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | Two+ variants submitted (e.g. trio variants, two slice renderings) | A pairwise preference per comparison axis with taxonomy-cited reasons — never a numeric absolute score |
| 2 | A single artifact submitted | Taxonomy flaw pass only: structural findings (hierarchy, contrast, spacing, alignment, overflow) each citing the taxonomy item + the offending element; NO preference verdict fabricated without a pair |
| 3 | Any invocation | Aesthetic/distinctiveness observations are emitted in a separate ADVISORY section explicitly addressed to the human — never folded into structural findings, never phrased as pass/fail |
| 4 | Reference anchors available | Critique anchors to THIS project's references + taste file ("breaks taste principle X", "matches exemplar Y's chart treatment") |
| 5 | Critic output lands | Recorded alongside design-state for the run; the loop proceeds to the HUMAN gate regardless of critic content |

## Edge Cases & Error Behavior

- **No reference set / taste file available** → the critic declines per-project anchoring and SAYS SO; generic taxonomy findings only, flagged as unanchored.
- **Variants visually near-identical** → states that pairwise confidence is low (the 90–93% evidence holds for CLEARLY different designs); no forced preference.
- **Asked for a score ("rate this 1–10")** → refuses the frame; returns the comparative/taxonomy output instead.

## Out of Scope

Gating any decision · absolute quality scores · replacing fresh-eyes · replacing the owner's gate · taxonomy authoring from scratch beyond what the critic build builds/borrows · critiquing non-studio artifacts.

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | Pairwise critique on real variants | Run the critic on two REAL variants from the project's own run artifacts | Preference + taxonomy-cited reasons; zero absolute scores anywhere in the output | Critique output file |
| 2 | Structural findings are real | Pick one structural finding; measure the element it names in a headed browser | The measured geometry confirms the finding (e.g. the overflow/misalignment exists) | Measurement capture + the finding |
| 3 | Aesthetic split honored | Inspect the same output | Aesthetic remarks sit in the advisory-to-human section only; none gate or score | The output file |
| 4 | Single-artifact behavior | Run on one artifact | Flaw pass only; no invented preference | Output file |
| 5 | Optional wiring does not gate | Run a loop beat with critic wiring enabled and proceed to the human gate | The gate occurs regardless of critic content; critic output is attached for the human | Run capture |

**Fidelity floor for every criterion:** the real critic component running whole on real run artifacts; geometry claims verified by measurement in a headed browser; evidence files written during the exercise; undriveable criteria marked `unexercisable` with the blocker.

**Evidence plausibility:** metrics must be physically plausible; impossible timings are auto-reject + rerun.

## Return Expectations

Executor reports: files changed · validation commands + un-piped exit codes + skips with reasons · commit hash if committed · concerns · blockers. Report is a hint; repo state is the truth.
