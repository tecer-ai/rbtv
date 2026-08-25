---
description: "Benchmark analysis — turning a folder of raw benchmark documents into a founder-approved taxonomy, one structured profile per product with a residual channel that discards nothing, and a feature-by-competitor synthesis naming table stakes, differentiators, gaps, overcrowded areas, and emerging trends."
tags: [conception]
---

# Benchmark analysis

Benchmark analysis is the technique for the situation where research already exists: a set of
documents describing real products, and no structured view of what they collectively do. It
produces three artifacts in order — a taxonomy, one profile per product, and a comparative
synthesis. Use it when the concept work needs product-level evidence, or when the starting
point is a research pile rather than a raw idea.

> Two boundaries. Research RIGOR — how a source is found, evaluated, scored, and cited —
> belongs to `../../../web/research/references/standards.md`; this reference carries the
> business-analysis frame only. And the market frame — direct and indirect alternatives,
> non-consumption, geographic benchmarks, positioning, threats and opportunities — belongs to
> the sibling `competitive-landscape.md`. This reference owns structured product-FEATURE
> comparison, nothing wider.

## Raw documents never enter the main conversation

Every read of a raw benchmark file is delegated to a sub-agent, which returns only its
structured extraction. The reason is context: a handful of raw benchmark documents will
crowd out the analysis they are meant to feed. Route the delegation through
`../../../core/sub-agents/references/sub-agents.md`.

## The sequence

Worked in this order, always. Each step consumes the previous one's output, so a skipped or
reordered step is not a shortcut — it silently invalidates everything downstream of it. Steps 2–5
are section 1 below, steps 6–7 are section 2, and steps 8–10 are section 3.

| # | Step | What it produces | What breaks if it is skipped or taken out of order |
|---|---|---|---|
| 1 | Inventory the raw documents | A list of the benchmark files to be processed, with the count checked against the five-or-more gate | Pattern percentages computed over three products read as findings when they are noise |
| 2 | Pick the two seed benchmarks | Two representative — not complete — documents named as the seeds | A taxonomy derived from one document inherits that product's idea of what a module is |
| 3 | Extract from both seeds in parallel | One sub-agent per seed returning modules, features per module, the numbered core flow, ideal-customer indicators and unique elements | Raw documents enter the main conversation and crowd out the analysis they were meant to feed |
| 4 | Merge into a proposed taxonomy | The two returns cross-referenced into one table, presented to the founder with the open questions — what is missing, what does not fit, what to split or merge | Every later extraction is filed against a schema nobody has examined |
| 5 | Get explicit founder approval | An approved taxonomy saved with its version number, its seed benchmarks and who approved it | Profiles get built against a provisional schema and must be redone when it changes |
| 6 | Extract one benchmark at a time | Per benchmark, a structured profile marking each feature ✓ / ○ / ✗ with how that company implements it, AND a separate numbered residual of everything the taxonomy did not capture | Without the residual channel, anything that fits no category is silently discarded and is never recoverable |
| 7 | Rule on the residual before the next benchmark | The founder's decision on every residual item — into the taxonomy, kept as a company note, or stored for future expansion — with the taxonomy updated BEFORE the next extraction runs | Later benchmarks are extracted against a poorer schema than the one already known to be needed, so the profiles are not comparable |
| 8 | Build the matrix | One matrix — taxonomy rows, product columns, ✓ / ○ / ✗ cells — loaded from all profiles and never from the raw documents | Patterns get asserted from memory of reading rather than counted from the grid |
| 9 | Extract the five pattern classes | Table stakes, differentiators, gaps, overcrowded areas and emerging trends, each derived from the matrix counts | The synthesis reports impressions; the thresholds that make each class mean something are never applied |
| 10 | Provoke the founder and compress | The founder's own reactions and initial positions, written into a synthesis document under 200 lines | An unreviewed synthesis, or one too long to hold in context while the product map is built, which the source workflow counts as a failure |

Step 3's two extractions run in parallel by design. Nothing else moves — in particular step 7's
taxonomy update happens between benchmarks, never batched to the end.

## 1. Taxonomy discovery

Pick TWO seed benchmarks — chosen for being representative, not for being complete. One
sub-agent per seed, run in parallel, each asked to read its file and extract: **product
modules** (distinct functional areas, the logical groupings of features); **features per
module**; the **core flow** (the primary user journey, numbered); **ideal-customer
indicators** (company size, industry, user role); and **unique elements** (anything
distinctive that fits no standard category). The sub-agent is told to be exhaustive, to list
anything it cannot classify and note the ambiguity, to preserve specificity ("AI-powered
receipt matching" beats "automation"), and NOT to evaluate, rank, or compare.

Cross-reference the two returns, merge the common modules and features into one proposed
taxonomy, and present it to the founder as a table. Ask what is missing, what does not fit
the domain, and what should be split or merged. Iterate until the founder **explicitly**
approves — a taxonomy is never finalized without that. Save it with its version number, its
seed benchmarks, and who approved it.

## 2. Per-benchmark extraction, with a residual channel

One sub-agent per remaining benchmark, given the raw file and the full current taxonomy,
returning TWO clearly separated outputs.

**Output 1 — the structured profile.** An overview (company, ideal customer profile, main
problem solved, value proposition, main user flow), then one section per taxonomy module with
a feature table marking each feature ✓ (clearly present and described), ○ (partial, inferred,
or mentioned without detail), or ✗ (clearly absent), each with a short description of how
this company implements it. Where a feature exists but works differently from what the
taxonomy implies, the difference is described rather than flattened.

**Output 2 — the residual.** Everything product-relevant in the document that NO taxonomy
module or feature captured: capabilities that fit no category, product approaches not
represented, integration patterns and partnerships, business-model elements that affect
product design, pricing and packaging structures, anything else. Numbered, described
concretely, each with a suggested category. **Nothing is ever silently discarded** — if it
does not fit the taxonomy, it MUST appear in the residual.

The founder reviews each profile AND its residual, and rules on every residual item: add it
to the taxonomy (which is then updated **before** the next benchmark is processed, so later
extractions use the richer schema), keep it as a company-specific note on that profile, or
store it in a residual file for possible future expansion.

## 3. Comparative synthesis

Load all profiles and build one matrix: rows are taxonomy modules and features, columns are
the products, cells are ✓ / ○ / ✗. Then extract five pattern classes from it.

| Class | Definition |
|---|---|
| Table stakes | Present in 80% or more — the minimum expectation |
| Differentiators | Present in fewer than 30% — candidate competitive advantages |
| Gaps | Absent from ALL of them — candidate open space |
| Overcrowded | Where everyone competes hard — difficult to differentiate on |
| Emerging | Appearing only in newer or smaller products — possible trends |

Then provoke the founder against the matrix: which patterns are surprising; which gaps are
real opportunities versus things nobody wants; where to compete on execution (table stakes)
versus on differentiation; and whether anything in the residual file now looks more important
in light of the full picture.

## What a good output contains

- A taxonomy carrying its version, its seed benchmarks, and an explicit founder approval.
- One profile per processed benchmark, each with its overview, its per-module feature table,
  and its company-specific notes; plus a residual file in which every unclassified item is
  preserved under its company heading.
- A synthesis document holding the matrix, all five pattern classes, and the founder's own
  reactions and initial positions — **under 200 lines**. The source workflow states the
  reason plainly: if the synthesis is too long to sit in context while the product map is
  built, it has failed. Compress; do not expand.
- Enough processed benchmarks for the pattern percentages to mean anything — the source
  workflow gates its synthesis at five or more.

## Builds on / feeds

Builds on `competitive-landscape.md`, which owns the market alternatives and the positioning
this feature comparison sits inside. Feeds `product-landscape.md`, which is built from the
synthesis and never from the raw benchmarks, and supplies Lean Canvas with evidence for its
Solution and Unfair Advantage blocks.

## Sources

Distilled from `3-resources/tools/rbtv/innovation/workflows/product-discovery/` — steps
`step-01-init.md`, `step-02-benchmark-loop.md`, `step-03-comparative-synthesis.md`,
`data/sub-agent-prompts.md`, and the `templates/taxonomy-template.md` and
`templates/profile-template.md` output shapes. Folded into conception by owner ruling
(2026-08-21) rather than migrated as a fourth milestone.
