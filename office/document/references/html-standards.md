---
description: "Read at the moment any agent is about to produce or review an HTML page — which sibling standards to load, and when. Applied against the page; never executed as a procedure."
tags: [document]
---

# html-standards — load contract

This file is the router for the HTML standards family. It states which siblings to load and when. It never restates what they say. Applied, never executed: check the page against the loaded files; the goal and steps come from the producer.

Two production models exist. Do not flatten them.

- **Agent-authored HTML** — the agent writes the HTML itself. V1 page-types: Review, Presentation.
- **Schema + deterministic builder** — the agent writes markdown page-source to a schema; a builder renders it. The agent never writes HTML, CSS, or JS. V1 page-types: Learning, and the posh document pages (v1: the seat-plan dashboard — builder and profile live with `capabilities/posh/posh.md`).

V1 page-types are exactly those four. Website, Dashboards, and UI/UX are named futures — no profile ships for them.

## Load contract

1. ALWAYS load `html-quality.md`.
2. Load `html-production.md` + `html-design-system.md` IFF the page-type uses agent-authored HTML.
3. Load `html-page-<type>.md` for the page being made or reviewed.
4. Load `html-charts.md` IFF the page contains a chart AND the type is agent-authored HTML.

Stop at this contract. Load only what it names for the page in front of you.

## Siblings

Each sibling is one subject. Reach it through this router. None of them is a skill of its own.

- `html-quality.md` — cross-type content quality (five normative rules, including the glossary bar). Binds both production models and every page-type.
- `html-production.md` — file mechanics (static markup, assets, agent-note, source-sync). Binds agent-authored HTML only.
- `html-design-system.md` — default look (tokens, type, index, cards, linear path, density). Binds agent-authored HTML only.
- `html-charts.md` — chart and dataviz standards for how a chart appears in HTML. Binds agent-authored HTML only; load only when the page contains a chart (rule 4).
- `html-page-review.md` — Review type-only rules (production model, look authority, type-only structure). Binds agent-authored HTML.
- `html-page-presentation.md` — Presentation type-only rules (production model, look authority, type-only structure). Binds agent-authored HTML.
- `html-page-learning.md` — Learning type-only rules (production model, look authority, type-only authoring bar). Binds the schema + deterministic builder model.

A page-type file never restates a cross-type rule; it points here.

## What this file does not do

It does not produce a page. It does not name typefaces, colour tokens, or quality tests. Those live in the siblings this contract loads.
