---
name: html-standards
description: "Use when making or reviewing Review, Presentation, Learning, or seat-plan dashboard HTML; load the matching standards for the page."
---
# html-standards — load contract

This file is the router for the HTML standards family. It states which siblings to load and when. It never restates what they say. Applied, never executed: check the page against the loaded files; the goal and steps come from the producer.

Two production models exist. Do not flatten them.

- **Agent-authored HTML** — the agent writes the HTML itself. V1 page-types: Review, Presentation.
- **Schema + deterministic builder** — the agent writes markdown page-source to a schema; a builder renders it. The agent never writes HTML, CSS, or JS. V1 page-types: Learning, and the posh document pages (v1: the seat-plan dashboard — builder and profile live with `skills/posh.md`).

V1 page-types are exactly those four. Website, Dashboards, and UI/UX are named futures — no profile ships for them.

## Load contract

1. ALWAYS load `html-quality.md`.
2. Load `html-production.md` + `html-design-system.md` IFF the page-type uses agent-authored HTML.
3. Load `html-page-<type>.md` for the page being made or reviewed.
4. Load `html-charts.md` IFF the page contains a chart AND the type is agent-authored HTML.

Stop at this contract. Load only what it names for the page in front of you.

## Request → child

Each child is a separate subject. Reach it through this router; none is a skill of its own.

| Request | Child |
|---|---|
| Make or review any HTML page | `html-quality.md` |
| Make or review Review HTML | `html-production.md`, `html-design-system.md`, `html-page-review.md` |
| Make or review Presentation HTML | `html-production.md`, `html-design-system.md`, `html-page-presentation.md` |
| Make or review Learning HTML | `html-page-learning.md` |
| Make or review a seat-plan dashboard | `skills/posh.md` |
| Add or review a chart in agent-authored HTML | `html-charts.md` |

A page-type file never restates a cross-type rule; it points here.

## What this file does not do

It does not produce a page. It does not name typefaces, colour tokens, or quality tests. Those live in the siblings this contract loads.
