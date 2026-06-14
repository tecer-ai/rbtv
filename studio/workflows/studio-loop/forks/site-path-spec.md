# Spec — Studio Site Path

> Behavior source of truth for the studio loop's site fork. The site fork references this spec for the behavioral floor — it never restates it.

## Goal

The owner can drive the studio site path from a brief to a multi-page HTML site: structure beat (linear-led information architecture) → per-page content specs → the shared designer beats (direction, page-template pick, slice generation, fresh-eyes, human gate) → pages that meet the site quality bar (images + motion that read professional, never AI-generated).

## Context Snapshot

- **Fork point:** pitch and site share the message-driven discovery; the genuine fork is the STRUCTURE phase — linear-led, multi-page for sites (vs slide-led for decks; vs interactive-driven for apps). After structure, the designer beats are the deck loop's, parameterized for pages.
- **Quality bar:** sites leverage images and animations to look professional; target-audience reaction "WOW I need IT".
- **Inputs:** same reference-set convention; subtle-refs reports (the extract-subtle-refs capability) feed motion language; image-gen (the image-gen capability) feeds imagery.
- **Output contract:** responsive multi-page HTML; motion within the direction mini-brief's character; images sourced via image-gen or owner-supplied assets — never fabricated stock-lookalikes passed as real photos of real things.

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | Owner starts the site path with a brief | Structure beat produces a sitemap + per-page narrative (one communication goal per page), no design |
| 2 | Designer beats run per page | Direction mini-briefs → owner pick → page-template pick → page generation, riding the deck loop's mechanics (fresh contexts, design-state, surgical patches) |
| 3 | Owner reviews in a headed browser at desktop AND mobile viewports | Pages render responsively; accept/bounce per page with notes |

## Edge Cases & Error Behavior

Missing imagery assets halt to the owner (no fabricated "real" photos); motion degraded gracefully when reduced-motion is requested.

## Out of Scope

App UI/UX (`app-path-spec.md`) · production code wiring (coding agents own it) · CMS/deployment concerns · SEO copywriting beyond the structure beat's narrative.

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | Structure beat yields a navigable sitemap + per-page points | Run the site path on a real brief | Sitemap + per-page narrative readable by the owner | Structure files |
| 2 | A generated page holds at the bar in a headed browser | Open generated pages headed, desktop + mobile viewport | Measured geometry sane at both viewports; motion matches the direction brief | Headed screenshots both viewports |
| 3 | Owner gate works per page | Bounce one page with a note | Surgical patch; other pages untouched | Hashes + screenshots |

**Fidelity floor for every criterion:** real application whole, real brief, visible browser + real input, measured geometry for layout claims; evidence files written during the exercise; undriveable criteria marked `unexercisable` with the blocker.

**Evidence plausibility:** metrics must be physically plausible; impossible timings are auto-reject + rerun.

## Return Expectations

Executor reports: files changed · validation commands + un-piped exit codes + skips with reasons · commit hash if committed · concerns · blockers. Report is a hint; repo state is the truth.
