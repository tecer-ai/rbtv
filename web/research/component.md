---
description: "The research component — the workspace's web-research rigor standards: source evaluation and scoring, citation format, data-integrity rules, and the sources-manifest convention. It owns HOW research is conducted and reported; which tool reads a page is the sibling browse component's question."
---

# research

The web-research procedure — source scoring (AT/TR/TM, the TS ≥ 6 bar), citation and legend format,
data-integrity and quantification rules, domain grouping, and the optional user-curated
sources-manifest convention.

## Parts

One reference carries the whole procedure, reached by an explicit prose read — no exposure manifest
exists yet because no part is exposed on its own (a row appears only on a real exposure decision,
per the reference kind's default).

| Part | What it is |
|---|---|
| `references/standards.md` (reference) | The research-rigor procedure and standards, carried over from the rbtv repo's `core/workflows/web-search/` Research Mode + `web-research-standards.md`, now deprecated there in favor of this component. |

## Boundary with `capture/` and `browse/`

`capture/` answers *give me this page* (fetch, extract, judge, save — defuddle / trafilatura /
BeautifulSoup). `browse/` answers *how much of a browser does this need* (agent-browser / playwright
/ the DevTools MCP). This component answers *what makes the resulting research trustworthy* —
evaluation, citation, integrity. A research run uses all three: capture to read sources, browse when
a page will not be read without a browser, this reference to score and report them.

## Origin (owner-ruled 2026-08-18)

Minted at console by owner ruling during the forge routing of the web-research move: forge never
mints a component, and the owner chose a console scaffold over a full planning run for a
one-reference component. This is also the second occupant `../module.md` predicted for the `web/`
module.
