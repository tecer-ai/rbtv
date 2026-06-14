# Spec — Extract-Subtle-Refs Capability

> Behavior source of truth for the extract-subtle-refs capability. The capability's usage doc and the capability registry reference this spec for the behavioral floor — they never restate it. The capability lives at `{rbtv_path}/studio/capabilities/extract-subtle-refs/` and is registered in the capability registry.

## Goal

A worker can point the capability at a reference URL and receive a **subtle-refs report** — the motion and interaction character of the site (animation timings, easings, scroll behaviors, hover states, transitions, micro-interactions) — in a structured form the art-direction beat can cite.

## Context Snapshot

- **Why it exists:** references "more subtle" than tokens: how things MOVE and respond, not what color they are. Token extraction is a DIFFERENT capability (`design-extraction`).
- **Infra:** the module's browser-automation workflow + the playwright-CLI skill (real page, scripted interactions). `file://` is blocked — live URLs or local-server targets only.
- **Output:** structured markdown report (optionally + JSON) where EVERY observation carries an anchor: page/element (selector or description) + what was observed (property, duration, easing, trigger).
- **Consumer:** the art-direction beat (mini-briefs cite observed motion patterns) and the site path's output contract.

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | Invocation with a URL | The real page is loaded; computed transitions/animations are read; scroll and hover interactions are exercised; a report file lands at the given output path |
| 2 | Report content | One row per observation: pattern name · element anchor · observed values (duration/easing/transform/trigger) · where seen |
| 3 | Multiple URLs given | One report section per URL, same row contract |
| 4 | A site has NO detectable motion | The report says so explicitly — an empty-findings report is a VALID result, not an error |

## Edge Cases & Error Behavior

- **Page unreachable** → non-zero exit + reason; no empty report pretending success.
- **Heavy SPA / late-loading animation** → a wait/settle strategy is applied; if content still cannot settle, the report names the limitation per page.
- **Bot-blocked site** → surfaced as a blocker in the report/exit; NEVER fabricated observations.

## Out of Scope

Token extraction (colors/type/spacing — `design-extraction` owns it) · screenshot capture (`screenshot-capture-spec.md`) · copying content or code from reference sites · judging whether the motion is GOOD (taste lives in the taste file + owner).

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | A real site yields a grounded report | Run the capability un-piped against a real, visibly-animated public site | Exit 0; report exists; every observation row carries an element anchor + concrete values | The report file + terminal capture |
| 2 | Observations are true, not hallucinated | Spot-verify ONE reported timing/easing against the live page (DevTools computed style or visual timing) | Reported value matches the observed value | Screenshot/devtools capture alongside the report row |
| 3 | Motionless page handled honestly | Run against a static page | Exit 0; report explicitly states no motion detected | The report file |
| 4 | Unreachable target fails loud | Run against a dead URL | Non-zero exit + reason; no report claiming success | Terminal capture |

> Every criterion obeys the **Fidelity floor** + **Evidence plausibility** rules.

**Fidelity floor for every criterion:** the real application running whole against real pages; CLI exit codes read un-piped; evidence files written during the exercise. A genuinely undriveable criterion is marked `unexercisable` with the concrete blocker, never silently skipped.

**Evidence plausibility:** metrics must be physically plausible; impossible timings are auto-reject + rerun.

## Return Expectations

Executor reports: files changed · validation commands + un-piped exit codes + skips with reasons · local commit hash if committed · concerns · blockers. Report is a hint; repo state is the truth.
