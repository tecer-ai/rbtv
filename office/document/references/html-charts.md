---
description: "Read at the moment a chart is about to be drawn on an agent-authored-HTML page — the shared chart layer to apply."
tags: [document]
---

# html-charts — the shared chart layer

ONE chart layer for every page-type whose production model is agent-authored HTML. Never a chart standard inside a page-type profile. Never a fourth office component.

A future dataviz capability, if minted, would consume this layer, never replace it.

## Learning exclusion

Learning charts are authored as schema `chart` fences and rendered by the deterministic builder. The Learning agent does not apply this file as HTML rules.

## How a chart appears in HTML

- **Static SVG or static markup.** No JavaScript-appended series. hypresent would duplicate anything a script adds at load time.
- **Colours come from the design-system tokens** in `html-design-system.md`. This file holds no palette of its own.
- **One idea per chart.** A second idea is a second chart.
- **Axes and labels are self-explanatory** — readable by someone with zero project context. This is `html-quality.md`'s bar applied to a chart; apply that file, do not restate it.

A visual plan may decide whether a chart exists. This file decides how it appears in HTML. A plan does not restyle it.

## Failure

- Series that appear only after a script runs — a fail (hypresent would duplicate them).
- A colour not named in `html-design-system.md` — a fail.
- A chart that needs a caption outside itself to be understood — a fail of the self-explanatory bar.
