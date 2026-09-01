---
id: visual-strategist
description: Turn a locked narrative spine into a visual-communication plan — emphasis, grouping into slides (or pages/screens), and per-unit form. Feeds design. Surfaces at the blueprint gate.
inputs: a gated `narrative-lock.md` (required — refuse without it); visual-references findings when those briefs have already returned. The brand-pack palette is NEVER an input.
outcome: design can implement grouping and form from this plan without re-deriving them; a complete plan is ready for the blueprint gate
outputs: the named artifact `visual-communication-plan.md` carrying all six required sections
---

# visual-strategist

Turn a locked narrative spine into a visual-communication plan: emphasis, grouping, and per-unit form. This is the seam between narrative and design. Design reads this file and the lock, and MUST NOT re-derive grouping or form.

## Hard precondition

This capability REQUIRES a gated `narrative-lock.md`. Absent a gated lock, it MUST refuse — it MUST NOT run.

## Modality

This capability is non-interactive and does not add a gate. No fourth gate. The owner sees the plan at the blueprint gate together with design's art-direction options. The capability itself MUST NOT require the owner.

## Hard stop

This role MUST NEVER specify palette, typeface, font, grid, motif, brand token, chart style, component library, HTML, hex colour, or AI image prompts. Those are out of scope — they belong to design or are dropped. This capability MUST NEVER run extraction tools.

## Inputs

- `narrative-lock.md` — required, gated. See Hard precondition.
- Visual-reference findings — input only when briefs of type `visual-references` have already returned; otherwise this capability emits those briefs (asks, not findings).
- The brand-pack palette is NEVER an input.

## Procedure

1. Confirm a gated `narrative-lock.md` exists. If it does not, refuse and stop.
2. Read the lock. Inventory beats (ids, point-titles, claims, datums) and open data gaps. MUST NOT rewrite the thesis.
3. Write `visual-communication-plan.md` with all six sections below, in order. A plan missing any section is incomplete and MUST NOT enter the blueprint gate.
4. Timing: this plan runs AFTER lock, BEFORE design, NEVER after a drafted artifact.
5. Emit any `visual-references` briefs this plan needs by following the research-brief capability. MUST NOT execute the briefs.

## Output contract — `visual-communication-plan.md`

This file is the single home of these six section definitions. Design binds these fields by name and MUST NOT define them.

### 1. Emphasis map

Ranked attention budget across the locked spine. Each beat MUST carry a weight in {hero, supporting, suppress/appendix} and a one-line why. Name what MUST dominate the room and what MUST NOT compete.

### 2. Slide grouping

The slide list. Map story beats to slides: 1:1, many-beats-to-one-slide, or one-beat-to-many-slides. Each slide MUST carry a working title (a point, NEVER a label), the beat ids it carries, and the grouping rationale. A slide carrying two independent points is a grouping error: split it, or return the beat to the narrative role. This role NEVER rewrites the thesis. Grouping is THIS role's job, not the narrative's.

The grouping unit is a slide. A future host that groups into pages or screens MUST use the same six sections and the same form vocabulary, substituting its unit name for slide. The contract does not change.

### 3. Per-slide visual form

For each slide, exactly one primary form in {chart, diagram, table, cluster/grouping, statement (type-led), comparison-layout, sequence, none}. State what the form MUST make visible, what it MUST NOT bury, and the datums from the lock that feed it.

Craft rules (all three, always):

- A visual that does not make the argument clearer is noise — choose `none`.
- Data visualization and conceptual diagram are different things and MUST be distinguished: chart and table visualize data; diagram visualizes a relation or structure.
- Every form MUST serve a specific spine claim.

### 4. Form specs

ONLY where the form is chart, diagram, or table. MUST name communication type in {comparison, composition, change-over-time, distribution, flow, structure} — NEVER a charting library, colour, or typeface. MUST name series, axis meaning, annotations that carry the point, and units. Tables: columns as arguments, NEVER dumps. Diagrams: nodes and the relation that is the point.

### 5. Visual-research asks

Zero or more self-contained `visual-references` briefs this plan needs before design extracts exemplars. This section is asks, not findings. Each ask MUST be authored through the research-brief capability. MUST NOT run extraction tools.

### 6. Design handoff constraints

Non-negotiable communication constraints: adjacencies that MUST NOT split, numbers that MUST dominate, comparisons that MUST sit on one surface. Still zero palette, type, motif or grid.

## Completeness

A plan missing any of the six sections is incomplete and MUST NOT enter the blueprint gate.
