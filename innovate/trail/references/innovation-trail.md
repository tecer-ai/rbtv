---
description: "The innovation trail — the M1 Conception → M2 Validation → M3 Brand sequence, the recommended framework order per milestone, which framework owns which concept, and the one-memo state protocol that makes a run resumable."
tags: [trail]
---

# The innovation trail

Three milestones take an idea to a brand. Each milestone is a set of frameworks worked ONE at a time,
conversationally, with the founder supplying the domain knowledge. The frameworks themselves live in
the sibling components; this file carries only the order, the ownership map, and the state.

## The milestones

| Milestone | Goal | Recommended framework order | References live in |
|---|---|---|---|
| **M1 Conception** | Structure a raw idea into a comprehensive business concept | Working Backwards → Jobs-to-be-Done → Competitive Landscape → Problem-Solution Fit → Lean Canvas → Five Whys. Optional, when the market is crowded enough to warrant it: Benchmark Analysis and Product Landscape (folded in from the old product-discovery workflow) — run them after Competitive Landscape. | `3-resources/tools/rbtv/innovate/conception/references/` |
| **M2 Validation** | Validate technical and financial feasibility | Leap of Faith → Assumption Mapping → TAM/SAM/SOM → Unit Economics → Technology Readiness Level → Pre-mortem. Optional, when a build follows: V1 Scoping (folded in from the old product-discovery workflow) — run it last, its output feeds product planning. | `3-resources/tools/rbtv/innovate/validation/references/` |
| **M3 Brand** | Produce a comprehensive brand book | Brand Archetypes → Brand Prism → Golden Circle → Brand Positioning → Tone of Voice → Messaging Architecture → Brandbook | `3-resources/tools/rbtv/innovate/brand/references/` |

The order is RECOMMENDED, never enforced. It is the order in which each framework's inputs become
available, so running it forward costs the least backtracking — but the founder may run any subset,
in any order, or a single framework standalone with no trail at all. Brandbook is the exception worth
saying out loud: it consolidates the six M3 frameworks before it, so running it first produces
nothing.

## Concept ownership

Within a milestone every concept has exactly ONE owning framework — the first in the sequence that
defines it. A later framework may extend, challenge, or refine that concept, and must reference the
owner's definition rather than restate it. This is what keeps a run's outputs consistent instead of
six documents each redefining "the customer". In an output file, referenced prior definitions go
under a `## Prior Context` heading — cited from the owning framework's output, never restated.

### M1 Conception

| Concept | Owning framework | Later frameworks reference + add |
|---------|-----------------|----------------------------------|
| Customer definition / target customer | Working Backwards | Problem-Solution Fit refines segment boundaries; Lean Canvas maps segments to channels |
| Problem statement / customer problem | Working Backwards | Problem-Solution Fit adds triggers and emotional dimensions; Lean Canvas distills to a top-3 list; Five Whys traces root causes |
| Value proposition | Working Backwards | Lean Canvas distills to a single unique-value-proposition statement |
| Customer jobs / hiring-firing criteria | Jobs-to-be-Done | Problem-Solution Fit references jobs when mapping solution fit |
| Competitive positioning / market alternatives | Competitive Landscape | Lean Canvas references it for unfair advantage |
| Solution description / fit validation | Problem-Solution Fit | Lean Canvas references it for the solution box |
| Customer segments / business model structure | Lean Canvas | — (terminal framework for the business model) |
| Root cause structure | Five Whys | — (terminal framework for causal analysis) |

### M2 Validation

| Concept | Owning framework | Later frameworks reference + add |
|---------|-----------------|----------------------------------|
| Assumption inventory / classification | Leap of Faith | Assumption Mapping scores and prioritizes; Pre-mortem references it for failure-mode alignment |
| Assumption scoring / test cards | Assumption Mapping | — |
| Market sizing (TAM/SAM/SOM) | TAM/SAM/SOM | Unit Economics references the serviceable available market for revenue projections |
| Unit economics (customer acquisition cost, lifetime value, payback) | Unit Economics | — |
| Technical feasibility / component readiness | Technology Readiness Level | — |
| Failure modes / risk mitigation | Pre-mortem | — |

### M3 Brand

| Concept | Owning framework | Later frameworks reference + add |
|---------|-----------------|----------------------------------|
| Emotional territory / archetype selection | Brand Archetypes | Brand Prism references it for the personality facet; Tone of Voice references it for emotional register |
| Brand identity facets (physique, personality, culture, reflection, self-image, relationship) | Brand Prism | Brandbook consolidates all facets |
| Purpose (Why / How / What) | Golden Circle | Brand Positioning references the Why for positioning rationale; Messaging Architecture references it for the brand promise |
| Positioning statement / perceptual map | Brand Positioning | Messaging Architecture references it for message differentiation |
| Voice dimensions / communication style | Tone of Voice | Messaging Architecture references it for message tone; Brandbook consolidates |
| Brand promise / key messages / proof points | Messaging Architecture | Brandbook consolidates |
| Consolidated brand identity | Brandbook | — (terminal framework — synthesizes all M3 outputs) |

## State protocol

One file per project, `innovation-memo.md`, and nothing else is tracked. No per-step state, no
frontmatter on the framework outputs, no status tags.

**Where it lives.** ASK THE USER at the start of every run — including a resume. Never assume, never
carry a location over from a previous session. Suggest `1-projects/{project}/` as the default and
accept whatever they name.

**The memo is frontmatter only:**

```yaml
---
project: acme-marketplace
milestone: M2 Validation
framework: Unit Economics
completed: [working-backwards, jobs-to-be-done, competitive-landscape, lean-canvas]
updated: 2026-08-21
---
```

- `project` — the project's name.
- `milestone` — where the run is: `M1 Conception`, `M2 Validation`, or `M3 Brand`.
- `framework` — the framework currently in progress, or `none`.
- `completed` — the framework REFERENCE NAMES already finished, in completion order (the kebab-case
  file names, so the list resolves straight to files).
- `updated` — the date of the last write.

**Framework outputs** are ordinary markdown files in the same folder, named after the framework
reference (`working-backwards.md`, `lean-canvas.md`, `brandbook.md`). No frontmatter is required on
them.

**Resume** = read the memo, state the position back to the user in one line (milestone, last
completed framework, what is next in the recommended order), confirm it is still what they want, and
continue. A resume never re-derives state from the output files; the memo is the only source.

## Run protocol

1. Adopt the persona from `../prompts/innovation-mentor.md`.
2. Ask where the project folder lives. New run: create the folder if needed and write
   `innovation-memo.md` with `completed: []`. Resume: read the memo and confirm the position.
3. Work ONE framework at a time. Read that framework's reference from the sibling component before
   running it — never run a framework from memory.
4. When the framework's output is agreed with the user, write the output file, update the memo
   (`framework`, `completed`, `updated`, and `milestone` when the milestone advances), and offer the
   next framework in the recommended order.
5. Never start a second framework before the current one's output is written and the memo updated.
6. Once three or more frameworks of a milestone are complete, offer a consistency review: read the
   completed outputs together and surface drift or contradictions between them (a fresh context is
   best for this). Non-blocking — the founder may decline and move on.

## Sources

Migrated 2026-08-21 from `3-resources/tools/rbtv/innovation/workflows/business-innovation/` —
`workflow.md` (milestone routing), `data/founder-process.md` (milestone summary, framework order,
content-ownership mapping), `templates/project-memo.md` (the old, larger state file this protocol
replaces), and the per-milestone `bi-m1/`, `bi-m2/`, `bi-m3/` `workflow.md` routing orders.
