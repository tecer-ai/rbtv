---
description: "The web module — the system's components for reaching the open web: fetching a page, driving a browser, and whatever later joins them."
---

<module>

# web

The `web/` module hosts the components an agent reaches the open web through.

## Components

| Component | What it is |
|-----------|-----------|
| `browse/` | The BROWSER surfaces of this workspace, routed by one skill: `agent-browser` (drive a real page), the `chrome-devtools` MCP (instrument one — network, console, traces, Lighthouse), `playwright` (script a repeatable run). It answers *how much of a browser does this need*; each surface documents its own flags. |
| `capture/` | Read a page and KEEP it: one first-party CLI fetches a URL, extracts it through the strongest extractor present (`defuddle` → `trafilatura` → BeautifulSoup), rules on whether what came back was an article at all, and writes it where the caller points. Handles PDFs; owns the cheap title-only link preview. It answers *give me this page*. |
| `research/` | The web-research rigor standards — source evaluation/scoring, citation format, data-integrity rules, the sources-manifest convention — as a reference. It answers *what makes research trustworthy*; `browse/` answers which tool reaches the page. |

## Why this module exists (owner-ruled 2026-08-10)

`browse/` previously sat FLAT at `.rbtv/mirror/browse/` — at module depth, with no module above it —
placed there by owner ruling 2026-08-08 after the module/component/flat alternatives were shown.
That placement made the component unreachable by the one grammar that matters: a seat's prompt-card
`exposes:` reference resolves as `part` · `component/part` · `module/component/part`, anchored at
`<tree>/<module>/<component>/`, so **no reference of any length could name a component sitting at
module depth.** The component's own `component.md` predicted exactly this ("any reader that walks
`mirror/<module>/<component>/` will not find this component") and named the two remedies: the folder
moves under a module, or the reader learns both depths. The owner chose the move.

The predicted second component arrived 2026-08-18: `research/`, minted by owner ruling at console
(its `component.md` § Origin). The ≥2-component tension the earlier revision recorded against the
KG's module membership test (`sd-graph show module`) is thereby resolved in substance; the registry
still settles the formal membership (`PRIN-10`).

The third arrived 2026-08-21: `capture/`, a port of the generic half of sb-os's wiki source-capture
script (its `component.md`). It took `defuddle` with it, by the same ruling — the module's internal
line is now **read** (`capture/`) vs. **drive** (`browse/`) vs. **judge what you read**
(`research/`), and `browse/`'s ladder deliberately no longer starts at a rung it owns.

</module>
