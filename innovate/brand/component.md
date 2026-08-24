---
description: "The brand component — the seven brand frameworks that turn a validated business concept into a brand: archetype, identity prism, purpose, positioning, voice, messaging, and the consolidated brandbook."
---

# brand

The third milestone of the innovation trail. An agent enters here to define who a venture's brand
is, why it exists, how it sounds, what it says, and what it looks like — each through one named
framework, each producing one output document.

Boundary with the sibling `validation/` component: `validation/` asks whether the venture is worth
building (assumptions, market size, unit economics, feasibility, failure modes). This component
assumes that answer is yes and defines how the venture presents itself. Boundary with `trail/`:
the sequence these frameworks run in, the per-project state, and the mentor persona live there —
this component holds only the framework substance.

| Part | What it is |
|---|---|
| `references/brand-archetypes.md` (reference) | Jung's 12 archetypes, the 0–3 scoring dimensions, and the four expression dimensions a selection must define |
| `references/brand-prism.md` (reference) | Kapferer's six identity facets, how to define each, and the six contradiction tests |
| `references/golden-circle.md` (reference) | Sinek's Why / How / What, and the endurance, authenticity and motivation tests a Why must survive |
| `references/brand-positioning.md` (reference) | The positioning statement template, the perceptual map, and the four validation tests |
| `references/tone-of-voice.md` (reference) | The seven tone dimensions on 1–5 sliders, context adjustment rules, and the non-negotiable core |
| `references/messaging-architecture.md` (reference) | The four-level hierarchy — promise, key messages, proof points, calls to action — and the traceability requirement |
| `references/brandbook.md` (reference) | The terminal framework: consolidates the other six and adds the visual identity specification |

## Entry points

- `references/` — one file per framework, read on demand; the agent checks the founder's output
  against the reference rather than executing it as steps.
- No exposure manifest. No part is exposed on its own — the component is reached through the
  `trail/` component's mentor prompt and trail reference, which route to the framework the session
  needs. A row appears here only on a real exposure decision.

## Origin (owner-ruled 2026-08-21)

Migrated from the rbtv repo's old-standard innovation module,
`3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m3/` — the M3 Brand milestone's
seven framework folders. Each framework's knowledge document became one reference here.

Deliberately NOT carried over: the per-framework step machinery (`steps-c/`), the `[S]`/`[B]` menu
navigation, the project-memo update instructions, and the step-tracking frontmatter — pacing and
state belong to `../trail/references/innovation-trail.md`. Also dropped: the brandbook workflow's
handoff of visual guidelines to a separate external design agent. `references/brandbook.md` states
instead that the visual identity specification is produced with whatever design capability the
session has.
