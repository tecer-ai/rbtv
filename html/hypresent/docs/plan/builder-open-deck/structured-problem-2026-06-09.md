---
type: structured-problem
status: complete
stepsCompleted: [step-01-init, step-02-discover, step-03-structure, step-04-deliver]
created: 2026-06-09
completed: 2026-06-09
problemType: solution
---

# Problem Structuring: Open Existing Deck in the Builder (v1)

## Initial Statement

Today, opening an existing presentation in hypresent gives only *content* editing (the editor). The user wants that same deck to **also open in the builder**, where it can be restructured — reorder slides, remove them, add **blank** placeholders, and **pull in existing slides from a library** to improve it — then save the restructured deck.

**v1 explicitly excludes:** saving slides *back* into the library, and the marker/hash provenance / round-trip system. Both deferred to a later cycle.

**Decision already taken:** the home is the **builder** (not the editor), because library augmentation is core and the editor has no concept of a library.

## Context Assessment

| Dimension | Assessment |
|-----------|------------|
| Clarity | Emerging → Clear (goal + v1 scope sharp; architecture open) |
| Scope | Single feature, multiple intertwined sub-problems; the blank-slide button is an approved sibling that shares this home |
| Type | Solution-architecture |
| Key Stakeholders | Henrique (sole owner/user of hypresent); downstream planning + execution agents; future cold agents that drive the builder |

## Deep Context

### Key Discoveries

1. **Home = builder, pages stay separate.** The builder gains the ability to open an existing deck; the editor keeps content editing. The two remain distinct pages (no merge).
2. **Bridge = save-and-switch with a Save-As window.** Switching builder↔editor opens a Save-As dialog (writes a NEW file, never overwrites), then opens that file in the target view. No shared live state, no unified page. (User stepped back from "live flip" once its cost — merging the two pages — was visible.)
3. **Existing slides = raw opaque sections.** On re-open, the deck's current slides are treated as anonymous `<section>`s the user can reorder, remove, or duplicate. The builder does NOT identify them → the saved deck stays clean (no provenance markers).
4. **Adding slides = blanks + any-library raw insert.** New slides come from blank placeholders or from ANY library, inserted as-is. A library fragment carries no inline style, so a cross-theme add may render largely unstyled; the user restyles later. No theme reconciliation in v1.
5. **Heterogeneous tray.** The compose tray holds a mix — existing-deck sections + new library fragments + blanks — all reorderable together.
6. **Restructure-save bypasses the assembler.** Rebuilding via `assemble.py` would regenerate the deck from library fragments and wipe the deck's filled-in content. So restructure-save instead manipulates the deck's OWN sections (reorder / remove / splice in new fragments + blanks) and serializes — closer to the editor's live-DOM + strip-only save than to library assembly. **This is the technical heart of v1.**
7. **Save options.** Explicit save asks new-file vs overwrite each time; a view-switch always uses Save-As (new file).

### Constraints Identified

- **ADX-2** (builder never duplicates engine assembly): honored — restructuring an existing deck is section manipulation on a finished file, a NEW path distinct from `assemble.py`, not a re-implementation of it.
- **Clean standalone output** (strip-only serializer, no markers): reaffirmed by the "raw sections" choice.
- **Two-page architecture (D20)** preserved — no page merge.
- **Per-deck inlined theme**; library fragments carry no inline styling (the source of the restyle-later cost).
- Windows-only native dialogs; same-origin server.

### Success Criteria (v1 "done")

- Open an existing deck in the builder and see its slides as a reorderable tray with thumbnails.
- Reorder, remove, and duplicate existing slides; add blank placeholders; add slides from a library.
- Save the restructured deck (choose new-file or overwrite).
- Switch to the editor (via Save-As) to edit content, and back.

### Explicitly Out of v1

- Saving slides back into a library (round-trip).
- The marker/hash provenance system.
- Theme reconciliation / auto-merge when adding cross-library slides.
- Live shared-state flipping / merging the builder and editor into one page.

## Refined Problem Statement

Henrique (the hypresent owner) needs to restructure an existing presentation from within the builder — reorder, remove, and duplicate its slides, and add new slides (blank or from a library) — and save the result, in order to evolve decks *after* assembly without rebuilding them from scratch. Constrained by: (a) the library assembler cannot rebuild an already-filled deck without wiping its content, so a new save path is required; (b) the saved deck stays clean (no provenance markers); (c) the deck's own theme/scripts are preserved; (d) the builder and editor remain separate pages, bridged by save-and-switch (a Save-As window on each crossing).

## Problem Tree

```
How do we let an existing deck be restructured in the builder? (v1)
│
├── A. INGEST — load a deck and show its slides
│   ├── A1  Entry point: "Open deck…" in the builder + "Open in builder" from the editor
│   ├── A2  Split the deck into slides (detect its <section> boundaries)
│   └── A3  Thumbnails from each section's own HTML + the deck's theme (not the library catalog)
│
├── B. COMPOSE — manipulate a heterogeneous tray
│   ├── B1  One tray, three row kinds: existing section · library slide · blank
│   ├── B2  "Add from library" reuses the current library browse → joins the same tray
│   └── B3  Reorder / remove / duplicate (reuse the existing tray-sorter)
│
├── C. SAVE — write the restructured deck WITHOUT the assembler   ★ technical heart
│   ├── C1  Recompose from the deck's own document: reorder its sections + splice in new ones
│   ├── C2  Copy added library fragments' assets into the deck's folder
│   └── C3  New-file vs overwrite ("ask each time"; reuse Save / Save-As)
│
└── D. BRIDGE — cross to the editor without losing work
    ├── D1  Switch → Save-As window (new file, never overwrite) → open in the target view
    └── D2  Both directions reuse the existing ?file= handoff + native dialogs
```

## MECE Validation

| Level | Mutually exclusive? | Collectively exhaustive? | Issue / fix |
|-------|---------------------|--------------------------|-------------|
| Layer 2 (A·B·C·D) | ✅ distinct lifecycle phases | ⚠️ one gap | "What is a deck?" — a non-conforming HTML file may lack clean `<section>` slides. **Fix:** scope v1 to decks with clear `<section>` slides (the slide-library system's own output); arbitrary HTML is best-effort. |
| A — Ingest | ✅ | ✅ | The in-memory "deck model" is created here and consumed by B and C — a dependency, not an overlap. |
| B — Compose | ✅ | ✅ | The blank-row kind is the already-approved sibling feature; it plugs in here. |
| C — Save | ✅ | ⚠️ one gap | **Caught:** added library fragments carry their own `assets/` — the new save path must copy them (the assembler does this today; easy to miss). |
| D — Bridge | ✅ | ✅ | Mostly reuse of the existing `?file=` handoff. |

## Priority Branches

Highest-risk / highest-novelty first (where planning effort should concentrate):

1. **C — Save (the heart).** The non-assembler recompose-and-write path is the most novel and riskiest; nothing ships without it.
2. **A — Ingest.** Foundational — without loading the deck and rendering its slide thumbnails, the tray has nothing to work on.
3. **B — Compose.** Mostly reuse (existing tray, sorter, library browse + the approved blank feature); the one new wrinkle is heterogeneous row identity.
4. **D — Bridge.** Lowest risk — largely reuses the existing editor handoff plus a Save-As gate.

## Pyramid Summary

### Main Message

v1 is achievable by extending the builder along the deck's lifecycle — **Ingest → Compose → Save → Bridge** — where the only genuinely new machinery is the **Save path** that recomposes an existing deck *without* the library assembler; everything else is largely reuse of what the builder and editor already do.

### Supporting Arguments

**1. The Save path is the crux and the main risk.**
- Evidence: `assemble.py` rebuilds a deck from `base.html` + blank library fragments — running it on a filled deck would wipe the content; and the editor's serializer is a strip-only pass over its live document, not a section-recompose tool. A new path is unavoidable: reorder the deck's own sections, splice in added fragments + blanks, copy their assets, write the file.
- Data needed: client-side recompose (load the deck in a hidden iframe, reuse editor-style DOM ops + serializer) vs server-side (parse HTML, reorder sections, write); asset-copy mechanics for added fragments.

**2. Most of the rest is reuse — which de-risks the build.**
- Evidence: the builder already ships the tray, the pointer-events sorter, srcdoc previews, and library browse; the editor already detects `<section>` slides and serializes; the `/app/?file=` handoff already bridges builder→editor.
- Data needed: the heterogeneous-row identity model in the tray (existing-section vs library-id vs blank) so reorder/remove/duplicate stay stable.

**3. Two deliberate scope guards keep v1 small.**
- Evidence: MECE surfaced two collective-exhaustiveness gaps — non-conforming decks and cross-theme styling. v1 targets only well-formed decks (the slide-library system's own output) and accepts unstyled cross-theme adds (restyle-later), both confirmed by the owner.
- Data needed: confirm the section-detection heuristic is reliable on the system's own decks.

### Communication Guide

- **5 minutes:** Main Message + all 3 arguments.
- **2 minutes:** Main Message + arguments 1 and 2.
- **30 seconds:** Main Message only — "the new Save path is the crux; the rest is reuse."

## Recommended Next Steps

| # | Action | Purpose | Priority |
|---|--------|---------|----------|
| 1 | Take this structured problem into **planning** (produce the v1 implementation plan; branch order C→A→B→D) | Convert structure → executable plan | High |
| 2 | Plan/ship the approved **blank-slide** feature (it's the blank row-kind branch B reuses) | Land the sibling that plugs into Compose | High |
| 3 | **De-risk branch C first**: prototype the non-assembler recompose-and-save on one real deck | Prove the riskiest path before committing the full build | High |
| 4 | Decide **client-side vs server-side recompose** (the C1 fork) | Unblock the Save design | Medium |
