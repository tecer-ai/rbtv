# Spec — Studio Deck Loop

> Behavior source of truth for the studio module's deck path. The studio-loop workflow, its beats, and the standards files reference this spec for the behavioral floor — they never restate it. This spec is workspace-agnostic: it names the BEHAVIOR, never a specific project's paths. Per-run inputs (the reference set, the output location) are resolved at runtime, not hardcoded here.

## Goal

The owner can take a deck brief plus this project's reference set and drive the studio deck loop end-to-end — locked message → owner-picked art direction → owner-picked template trio → full HTML deck — accepting or bouncing each slide in a headed browser, and print the accepted deck to PDF straight from the browser.

## Context Snapshot

- **The four beats:** 1. message-lock (Strategist) → 2. references + art-direction → 3. HTML generation (optional slide-library probe → trio → slices → fresh-eyes) → 4. human gate. Communication beats produce NO design; design beats never alter the locked message.
- **Reference set** (workspace-owned, provided per project at the run's `reference_set` path — contract in `{rbtv_path}/studio/standards/reference-set-contract.md`): tokens file (color/type/spacing/motion) + `exemplars/` screenshots + **taste file** (3–5 admirable-principle bullets per exemplar) + a chart exemplar. The module LOADS and ENFORCES it; it never authors or ships references.
- **Ban-list defaults:** purple-blue gradients · rounded-card-grid-of-three · default-font look · emoji icons — plus the mined corrections catalogued in `{rbtv_path}/studio/standards/ban-list.md`.
- **Design-state payload** (schema in `{rbtv_path}/studio/state/design-state-schema.md`; a module-level artifact riding the orchestration state convention, never replacing it): project meta · artifact+mode · active phase · content-spec ref · chosen art direction · per-slide HTML status · accept/bounce notes · fresh-eyes punch-lists. Any fresh agent resumes the loop from design-state + the reference set alone.
- **Strategist → Designer contract:** the content spec's exact format is defined in `{rbtv_path}/studio/architecture.md` §5. Behavioral floor: deck thesis · one point per slide · narrative arc · per-datum communication intent · owner-supplied verified numbers with sources.
- **Output contract:** HTML-native — full-screen browser deck + print-to-PDF CSS. No PPTX, ever. Rendering for review uses a local HTTP server (direct `file://` opening is blocked in the browser-automation infra).

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | Owner starts the loop with a brief + verified numbers (a prior deck may accompany as content input ONLY) | Message-lock produces a content spec: deck thesis, one point per slide, narrative arc, per-datum communication intent. Zero design decisions in it. Design-state initialized. |
| 2 | A slide's claim lacks an owner-supplied source | The slide is BLOCKED and flagged to the owner. The loop never fabricates or researches external data. |
| 3 | Art-direction beat runs on the loaded reference set | ≥2–3 genuinely distinct direction MINI-BRIEFS, each covering: type pairing · palette within tokens · grid principle · signature motif · chart style · cover treatment; each citing which taste-file principles it uses/breaks; ALL obeying the ban-list. Owner-influenced pick recorded in design-state. |
| 3·0 | Generate beat (beat 3) starts, BEFORE the trio (row 4) — the working repo is probed for a reusable slide library | Glob `**/library.json` from the repo root; KEEP a hit only if it parses with a `convention_version` and its path is NOT under `slide-library/tests/`; SELECT the one fitting the deck's context (disambiguate per `rbtv-output-resolution`). A fitting library → the loop HALTS and offers the owner **[L] assemble-from-library** (follow the library's `README-FOR-AGENTS.md` + `assemble.py` cold-agent path; the library's `theme.css` governs the deck; the trio — row 4 — is SKIPPED; uncovered content-spec slides are authored to that same `theme.css`; the library's `slides/`/`manifest.md`/`presets.md` are NEVER edited in place — the engine appends its own as-built entry) or **[B] build bespoke** (rows 4–6 unchanged). No fitting library → build bespoke (rows 4–6 unchanged). The loop NEVER requires a library; the owner gate backstops a mis-pick. |
| 4 | Template-trio beat runs under the chosen direction | 2 variants × (cover + content slide + chart slide) render in a headed browser; owner picks PAIRWISE (A-vs-B per slide type); the winning trio becomes the deck's visual contract, recorded in design-state. |
| 5 | Slice generation runs | Full deck produced slice-by-slice; each slice by a fresh-context worker resuming from design-state; every slide conforms to the trio contract; per-slide status tracked in design-state. |
| 6 | A full pass is ready, BEFORE the owner sees it | Fresh-eyes pass: a fresh-context review against the chosen direction mini-brief + the flaw checklist (`{rbtv_path}/studio/standards/flaw-checklist.md`) → punch-list → patches applied. NOT the v1.1 critic — no scoring, no gating, no taxonomy dataset. |
| 7 | Owner reviews the rendered deck (headed browser) and bounces a slide with notes | Notes land in design-state; a SURGICAL patch changes only the flagged slide — all other slides byte-identical (row 4). |
| 8 | One slide accumulates ≈3 bounces | The loop STOPS polishing and escalates to a message-level rethink (back to beat 1). The cap is a tunable parameter. |
| 9 | Any fresh agent (or worker switch, Strategist↔Designer) joins mid-loop | It resumes correctly from design-state + the reference set alone — no conversation history needed. |
| 10 | Owner accepts the deck | Print-to-PDF from the browser yields a complete PDF (page count = slide count, no clipped content). |

## Edge Cases & Error Behavior

- **Taste file absent or unannotated** → the art-direction beat HALTS to the owner; it never substitutes model taste silently.
- **Reference set empty/insufficient** → halt with a named gap (which layer is missing: tokens, exemplars, taste, chart exemplar); never proceed on training-mean defaults.
- **Owner rejects ALL direction mini-briefs** → regenerate genuinely NEW directions (no recycling of rejected briefs); after a second full rejection, escalate: the reference set may not encode the owner's taste — flag for re-curation.
- **Owner rejects both trio variants for a slide type** → new variants under the same direction; if direction itself is the problem, re-run the pick (beat 2) — recorded as a bounce against the direction, not a slide.
- **Bounce-cap trip** → behavior row 8; the escalation is recorded in design-state and the run's `decisions.md`.
- **Render server unavailable** → start the local server pattern from the browser-automation workflow; `file://` is never used.
- **No spec-compliant library fits the deck** (zero validated `library.json` hits, hits that fit no context, or only the `slide-library/tests/` fixture) → build bespoke; never force a non-fitting library (behavior row 3·0).
- **Owner picks [L] but the library covers only some content-spec slides** → the uncovered slides are authored as new fragments in the library's `theme.css` (coherence — never a fresh trio mixed in), optionally upstreamed per the slide-library convention; the trio beat (row 4) stays skipped.

## Out of Scope

Critic scoring (the v1.1 critic — `{rbtv_path}/studio/critic/`) · site/app forks own their own behavior (`{rbtv_path}/studio/workflows/studio-loop/forks/`) · PPTX export · in-loop research/grounding · brandbook/token authoring · image generation (`{rbtv_path}/studio/capabilities/image-gen/`) · improve-existing audit mode.
