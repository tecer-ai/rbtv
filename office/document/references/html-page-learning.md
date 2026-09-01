---
description: "Read at the moment a Learning page is being produced or reviewed — the schema + deterministic builder profile, the agent-facing authoring bar, and what the builder owns."
tags: [document]
---

# html-page-learning — Learning page-type profile

Applied against a Learning page. Never executed as a procedure.

## Production model

Learning uses the **schema + deterministic builder** model. The agent authors markdown page-source to a schema. A deterministic builder — the live sb-tutor stylesheet, script, and renderer — turns that source into the page. The agent never writes HTML, CSS, or JavaScript. The builder owns layout, sizing, table styling, diagram fit, and interactivity.

This is the opposite of Review and Presentation, which use agent-authored HTML. Production model is a first-class axis. Flattening the two models is a defect.

## What this profile binds

This profile DOES bind `html-quality.md` — the cross-type content-quality layer, including the glossary bar. The glossary bar: every technical term, acronym, or piece of jargon gets a plain one-sentence definition; a definition that itself uses jargon is a defect; undefined jargon is a fail. Here the builder surfaces each definition on hover or focus through CSS; that surfacing is the one Learning-only part of the bar.

This profile does NOT bind `html-production.md` and does NOT bind `html-design-system.md`. There is no agent writing HTML here for either file's rules to apply to; binding them would flatten the two production models.

`html-production.md` is the agent-authored-HTML file mechanics: static markup, external assets folder, agent note, source-sync. `html-design-system.md` is the agent-authored-HTML look: tokens, typefaces, left index, cards. Neither has an agent writing HTML on a Learning page.

Charts on a Learning page are schema chart blocks the builder renders. The agent does NOT apply `html-charts.md` as HTML rules.

## Cost of Learning's interactivity

A Learning page is NOT hypresent-comment-anchorable. hypresent is the comment-review tool Review and Presentation pages open in. It can only anchor a comment to a node that already exists in the saved markup. Learning's builder adds content at load time, so comments cannot anchor.

## Agent-facing authoring bar

The agent owns content quality. The builder owns look, layout, and interactivity. A page that misses this bar is a defect, not a draft. This section carries the bar in this profile's words. The live copy, until the tutor is wired to load this library, is `3-resources/tools/sb-os/wiki/workflows/sb-tutor/library-protocol.md` — open that file when applying or checking the authoring bar; it is the tutor's agent-facing rules for a Learning page.

Pitch depth to the session's technicality level (`lay` / `applied` / `technical` / `expert`). Technicality sets depth. Clarity and the glossary hold at every level.

1. Deep and wiki-grounded, never a stub. Build each section from real substance — definitions, distinctions, decision criteria, tradeoffs, quantified facts — so the page reconstructs the idea. A thin 1–2-section page is a fail.
2. Visual-heavy. Every concept MUST earn a visual. Lead each section with a diagram, chart, table, or callout, not a wall of prose. Per topic MUST include an interactive graph, a chart for anything quantitative, a table for any comparison, callouts for mental models and cautions, at least one deeper aside, and when they fit: trace, flow, tabs, anncode, and one quiz.
3. Interactive-light. Every graph node and every graph edge MUST carry a desc — its click-to-explain text. A graph without descs is half-built.
4. YAML-safe blocks. Inside graph, chart, and quiz YAML, quote any value containing a colon, a hash, or quote marks. Single-quote it; double any inner apostrophe. One unquoted colon breaks the block.
5. Author markdown only. NEVER write HTML, CSS, or JS. Scale section count to the topic.
6. Macro visible, micro collapsed. A section's main substance MUST stay visible. NEVER hide a section's core inside a single deeper. Use deeper ONLY for optional micro-detail behind a point. If expanding one collapsed block reveals the section's actual content, promote it to visible body.
7. Glossary. Every technical term, acronym, or piece of jargon MUST get a plain one-sentence definition, including terms that appear only inside a graph or deeper explanation. A definition that itself uses jargon is a defect. Undefined jargon is a fail.
8. Scannable prose. Bullets and tables over walls of text, including inside deeper. When a passage enumerates items, options, a sequence, or tradeoffs, it MUST be a list or table. A wall of prose that hides a list is a defect.

## Page-source schema — pointer only

NEVER duplicate the schema. Open `3-resources/tools/sb-os/wiki/scripts/learning-library/page-source-schema.md` at the moment of authoring or checking page-source shape. It is the authoring shape: frontmatter, sections, graph, chart, trace, flow, tabs, anncode, quiz, deeper, and citations.

## Builder interactivity — pointer only

NEVER copy the builder script. Open `3-resources/tools/sb-os/wiki/scripts/learning-library/assets/app.js` at the moment of asking what the builder adds at load. It is the builder's interactivity: glossary hover, citation provenance, click-to-explain graph panels, quiz, tabs, modal, TOC.

## The three sb-os pointers

The three paths above are the sb-tutor's live sources in the sb-os repo — a documented cross-repo relationship, not an instance path. A reader without that repo is looking at the tutor's authoring bar, page-source schema, and builder script as they live there.

## Builder-owned — the agent NEVER implements these

Lumen type and palette; collapsible sections; knowledge-map index; glossary tooltips; citation provenance popups; click-to-explain graph panels; quiz; tabs; shared modal; copy, expand, and zoom; table of contents built at load.

Name them so no agent tries to implement them.
