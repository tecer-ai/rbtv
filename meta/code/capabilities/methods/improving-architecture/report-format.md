# Architecture report format

The result: the HTML of the report that [Improving architecture](../improving-architecture.md) renders in its step 5, one self-contained file. That step owns the file's name and folder and what is done with the file.

Inputs: the repository's name, the date, and the candidates, each with its files, problem, solution, wins, recommendation strength, dependency class and any decision conflict; the candidate recommended first and the reason. When one of these is absent, return to the method's step that produces it; do not fill a card with invented content.

Tailwind (layout and styling) and Mermaid (graph-shaped diagrams) both load from their CDNs. Hand-built `div`s and inline SVG carry the editorial visuals: the mass diagrams and the cross-sections. Use both kinds; a report drawn only in Mermaid looks generic.

## Scaffold

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Architecture review for {{repo name}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({ startOnLoad: true, theme: "neutral", securityLevel: "loose" });
    </script>
    <style>
      .seam { stroke-dasharray: 4 4; }   /* dashed seam lines */
      .leak { stroke: #dc2626; }          /* leakage arrows */
      .deep { background: linear-gradient(135deg, #0f172a, #1e293b); }  /* the deep module */
    </style>
  </head>
  <body class="bg-stone-50 text-slate-900 font-sans">
    <main class="max-w-5xl mx-auto px-6 py-12 space-y-12">
      <header>...</header>
      <section id="candidates" class="space-y-10">...</section>
      <section id="top-recommendation">...</section>
    </main>
  </body>
</html>
```

## Header

The repository's name, the date and a compact legend: solid box = module, dashed line = seam, red arrow = leakage, thick dark box = deep module. Write no introduction paragraph; the candidates follow the header directly.

## Candidate card

Write one `<article>` per candidate. The diagrams carry the content; the prose is sparse.

- **Title**: short, names the deepening ("Collapse the intake pipeline").
- **Badge row**: the recommendation strength (`Strong` in emerald, `Worth exploring` in amber, `Speculative` in slate) and the dependency class (`in-process`, `local-substitutable`, `remote but owned`, `true external`).
- **Files**: a monospaced list (`font-mono text-sm`).
- **Before / After diagram**: the centrepiece, two columns side by side, drawn in one of the patterns below.
- **Problem**: one sentence on what hurts.
- **Solution**: one sentence on what changes.
- **Wins**: bullets of at most six words, in the vocabulary's terms: "Tests hit one interface", "Pricing stops leaking across the seam", "Delete 4 shallow modules".
- **Decision-conflict callout**, only when the candidate reopens a recorded decision: one line in an amber box naming the decision and why the friction justifies reopening it.

When a diagram needs a paragraph to be understood, redraw the diagram.

## Diagram patterns

Pick one pattern per candidate and vary the patterns across the report.

- **Mermaid graph**, for dependencies and call flow: `flowchart` or `graph` in a Tailwind card; `classDef` colours leakage edges red and the deep module dark; a sequence diagram for "before: 6 round-trips, after: 1".
- **Hand-built boxes and arrows**, when Mermaid's layout does not give the picture: modules as bordered `div`s, arrows as absolutely positioned inline SVG; the "after" side is one thick-bordered deep module with greyed internals.
- **Cross-section**, for stacked shallow modules: stacked horizontal bands (`h-12 border-l-4`); before is many thin bands that do nothing, after is one thick band with the consolidated responsibility.
- **Mass diagram**, for an interface as wide as its implementation: two rectangles per module, the interface surface and the implementation; a shallow module has both nearly the same height, a deep module has a short interface over a tall implementation.
- **Call-graph collapse**: before is a tree of nested call boxes; after is one box with the now-internal calls faded inside.

## Style

- Editorial, not a dashboard: generous whitespace; serif headings are optional (`font-serif` with stone or slate).
- One accent colour (emerald or indigo), plus red for leakage and amber for warnings.
- Diagrams about 320px tall, so before and after sit side by side without scrolling.
- `text-xs uppercase tracking-wider` for module labels inside diagrams.
- The only scripts are the Tailwind CDN and the Mermaid import: no application code and no interactivity beyond Mermaid's rendering.

## Top recommendation

One larger card: the candidate's name, one sentence on why, and an anchor link to its card.

## Tone

- Use the words of [the method's vocabulary](../improving-architecture.md#the-vocabulary) exactly, and none of the substitutes it excludes.
- A win names the gain in those words ("locality: bugs concentrate in one module", "leverage: one interface, N call sites"), never "easier to maintain" or "cleaner code".
- Do not hedge and do not write introductory sentences. A sentence that could be a bullet is a bullet; a bullet that could be cut is cut.
