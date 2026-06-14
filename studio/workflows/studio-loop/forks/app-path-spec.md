# Spec — Studio App Path

> Behavior source of truth for the studio loop's app fork. The app fork and the UX companion-docs contract reference this spec for the behavioral floor — they never restate it.

## Goal

The owner can drive the studio app path from product goals to a wired-ready UI package: goals beat → user-flow beat → UX beat → UI beat producing plain HTML screens PLUS UX companion docs that a coding agent can wire into a real app without asking the designer anything.

## Context Snapshot

- **Fork point:** apps fork at discovery (goal → user-flow, interactive-driven) and converge with the other artifacts at art-direction → layout → visual.
- **The split that survives every tool's failure mode:** design UI + UX companion docs; hand WIRING to a coding agent. The UI beat NEVER writes application code — plain HTML/CSS (+ minimal demo-state JS where a state must be SHOWN), with states designed, not implemented.
- **UX companion-docs contract:** per-screen — screen goal · flow position (from/to) · states (empty, loading, error, success) · interactions (what each control does) · acceptance notes. The coding agent reads ONLY these + the HTML.
- **Quality bar:** intuitive flow toward the user's goal; edge states and responsive breakpoints designed explicitly (the gap every UI generator leaves).

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | Owner starts the app path with product goals | Goals beat: what the user must achieve/be enabled to do — testable phrasing |
| 2 | User-flow beat runs | Flow map: screens, transitions, decision points — each goal reachable |
| 3 | UX beat runs | Per-screen UX docs per the companion contract (states + interactions explicit) |
| 4 | UI beat runs under the chosen direction | Plain HTML screens for every flow screen incl. edge states; responsive breakpoints designed; zero app-code wiring |
| 5 | Coding-agent handoff | The package (HTML + companion docs) answers wiring questions without the designer in the loop |

## Edge Cases & Error Behavior

A screen with undesigned states (empty/error) is INCOMPLETE — the beat flags it rather than shipping happy-path-only; flows with unreachable goals halt at the user-flow beat.

## Out of Scope

Code wiring, backend, data models (coding agents) · site marketing pages (`site-path-spec.md`) · accessibility certification (designed-for, not certified here) · native-platform UI.

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | Flow covers the goals | Run goals + user-flow beats on a real product brief | Every goal reachable through the flow map | Flow artifacts |
| 2 | Screens render with designed states | Open UI screens in a headed browser, walk the flow incl. one edge state | Measured geometry sane; edge states visibly designed | Headed screenshots |
| 3 | Handoff is self-sufficient | A coding agent (fresh context) reads ONLY the package and answers 3 wiring questions | Correct answers without designer input | Q&A capture |

**Fidelity floor for every criterion:** real application whole, real brief, visible browser + real input, measured geometry for layout claims; evidence files written during the exercise; undriveable criteria marked `unexercisable` with the blocker.

**Evidence plausibility:** metrics must be physically plausible; impossible timings are auto-reject + rerun.

## Return Expectations

Executor reports: files changed · validation commands + un-piped exit codes + skips with reasons · commit hash if committed · concerns · blockers. Report is a hint; repo state is the truth.
