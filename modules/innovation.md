# Innovation

## Purpose

This module covers the early-stage journey from raw idea to defined product — structuring a business concept, stress-testing its assumptions, building a brand, and scoping a V1. It's built for founders and PMs who are pre-product or exploring a new initiative and need a rigorous, framework-driven thinking partner rather than a yes-and brainstorming assistant. Reach for this module when you have an idea worth stress-testing, competitor research worth synthesizing, or a brand worth defining from scratch — not when you already have a product and need execution help.

---

## Components

### `/rbtv-innovator`

- **What**: Activates Paul, a YC-mentor persona — a former founder with two exits who has evaluated 500+ startups. Paul is direct to the point of bluntness, obsessed with customer evidence, and has no patience for hand-wavy market sizing or unvalidated assumptions. He guides you through a 3-milestone lifecycle:
  - **M1 Conception** — six frameworks: Lean Canvas, Jobs to Be Done, Five Whys, Competitive Landscape, Problem-Solution Fit, Working Backwards
  - **M2 Validation** — six frameworks: Assumption Mapping, Leap of Faith Assumptions, Pre-Mortem, TAM/SAM/SOM, Technology Readiness Level, Unit Economics
  - **M3 Brand** — seven frameworks: Brand Archetypes, Brand Positioning, Brand Prism, Golden Circle, Messaging Architecture, Tone of Voice, Brandbook (synthesized output)

- **When to use**: You have a business idea and want to pressure-test it end-to-end — from first principles (what problem, for whom, how) through feasibility (can it work, does it scale) through brand (who are you, how do you speak). Also useful for resuming an in-progress project from whichever milestone you left off.

- **How to invoke**: `/rbtv-innovator`  
  Paul greets you and presents a menu. Type `N` (or "new project") to start from scratch, or `C` (or "continue") to resume an existing project — bring your `project-memo.md` into context for the second option.

- **What it produces**: Per-framework output documents saved incrementally, a `project-memo.md` tracking your milestone and progress, and — at M3 — a unified brandbook document. All outputs go under `{project-name}/business-innovation/`.

- **Example**:
  - User: `/rbtv-innovator` → Paul presents the menu → User types `N`
  - Paul walks you through Lean Canvas first, challenging every box with "What did the customer actually say?" before moving to JTBD.

---

### `/rbtv-product-discoverer`

- **What**: A product strategist workflow — no persona, just structured process — that transforms raw competitor and benchmark research into defined product artifacts. It uses sub-agents to process individual benchmark files so the main conversation never gets bloated with raw research. The output is designed to feed directly into a product brief.

- **When to use**: You've done market and competitor research (saved as files) but haven't yet structured it into a product definition. You know what exists in the market but haven't decided what *you* are building, for whom, or what V1 looks like. Use this before writing a product brief or spec — not after.

- **How to invoke**: `/rbtv-product-discoverer`  
  The workflow initializes and walks you step by step. Bring your benchmark/research files into the working directory before starting — the workflow will point sub-agents at them.

- **What it produces**: A structured set of artifacts across five steps:
  1. `taxonomy.md` — categorized framework of what exists in the market
  2. `profiles/{company}.md` — per-competitor structured profiles
  3. `benchmark-synthesis.md` — comparative synthesis across competitors
  4. `product-landscape.md` — product map of the space
  5. `v1-scope.md` — defined V1 scope, ready for handoff to a product brief workflow

- **Example**:
  - User: `/rbtv-product-discoverer` (with 8 competitor research files in context)
  - Workflow initializes taxonomy from 2 seed benchmarks via sub-agents, then loops through the remaining competitors one by one, updating the taxonomy as new patterns emerge.

---

## How they fit together

These two commands serve adjacent but distinct phases. `/rbtv-innovator` (M1–M3) is for idea-to-brand: you start with a concept and finish with a validated business and a brandbook. `/rbtv-product-discoverer` is for research-to-product-definition: you start with competitor knowledge and finish with a scoped V1 ready for a product brief.

The natural sequence is **innovator M1–M2 first**, then **product-discoverer** once you have validated your concept and want to structure your competitive research into a product definition, then back to **innovator M3** for brand. They can also run independently if you're entering mid-stream — for example, running product-discoverer alone if the ideation is done and you just need to synthesize research.
