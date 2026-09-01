---
description: "Read at the moment of producing or reviewing a Review page (a plan, document, or diagnosis) — the page-type profile to apply."
tags: [document]
---

# html-page-review — Review page-type

Production model: **agent-authored HTML**. The agent writes the HTML file itself.

Apply, do not restate: `html-quality.md` (content quality, including the glossary bar), `html-production.md` (static markup, external assets folder, agent note, source-sync), `html-design-system.md` (the house look). When the page has a chart, also apply `html-charts.md`.

## What it is

A plan / document / diagnosis page opened in hypresent, a comment-review tool.

## Look authority

The look is `html-design-system.md`. This profile invents no typeface, no colour, and no second token vocabulary. Flag colours are the design-system tokens, named not valued:

- caution → `--amber`
- blocker → `--rose`
- resolved → `--teal`

## Hard rules that survive on this type

1. **Static markup so hypresent comments can anchor.** `html-production.md` owns the rule; this type requires it.
2. **Flags MUST read at a glance.** A caution, blocker, or resolved item uses the matching token above as the card or tag signal — yellow/red flags are visible without reading the prose.
3. **Place the html as a sibling file of the source it reviews**, in the same folder as that source.

## Structure

A Review page is a long article. Keep the design-system left index. Do not drop it. Linear reading path as `html-design-system.md` states it.

Scale down as that file allows: short pages drop the sidebar and most cards. The three hard rules above always apply.
