---
description: "Read at the moment the improve-codebase-architecture skill renders its HTML report — the scaffold, the candidate card, the diagram patterns, the style, and the tone the report must follow."
tags: [coding]
---

# Architecture report — HTML format

One self-contained HTML file in the OS temp directory. Tailwind (layout and styling) and Mermaid (graph-shaped diagrams) both load from their CDNs; hand-built `div`s and inline SVG carry the editorial visuals (mass diagrams, cross-sections). Mix the two — Mermaid for everything looks generic.

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

Repo name, date, and a compact legend: solid box = module, dashed line = seam, red arrow = leakage, thick dark box = deep module. No introduction paragraph — straight into the candidates.

## Candidate card — one `<article>` each

The diagrams carry the weight; prose is sparse and uses the vocabulary without ceremony.

- **Title** — short, names the deepening ("Collapse the intake pipeline").
- **Badge row** — recommendation strength (`Strong` = emerald, `Worth exploring` = amber, `Speculative` = slate) + dependency category (`in-process`, `local-substitutable`, `remote but owned`, `true external`).
- **Files** — monospaced list (`font-mono text-sm`).
- **Before / After diagram** — the centrepiece, two columns side by side (patterns below).
- **Problem** — one sentence: what hurts.
- **Solution** — one sentence: what changes.
- **Wins** — bullets of at most 6 words, in vocabulary terms: "Tests hit one interface", "Pricing stops leaking across the seam", "Delete 4 shallow modules".
- **Decision-conflict callout** (only if applicable) — one line in an amber box: which recorded decision it reopens and why the friction justifies it.

If the diagram needs a paragraph to be understood, redraw the diagram.

## Diagram patterns — pick per candidate, vary them

- **Mermaid graph** (dependencies, call flow): `flowchart`/`graph` in a Tailwind card; `classDef` colours leakage edges red and the deep module dark; a sequence diagram for "before: 6 round-trips, after: 1".
- **Hand-built boxes and arrows** (when Mermaid's layout fights you): modules as bordered `div`s, arrows as absolutely positioned inline SVG; the "after" side is one thick-bordered deep module with greyed internals.
- **Cross-section** (layered shallowness): stacked horizontal bands (`h-12 border-l-4`); before = many thin layers doing nothing, after = one thick band with the consolidated responsibility.
- **Mass diagram** (interface as wide as implementation): two rectangles per module — interface surface vs implementation; shallow = both nearly the same height, deep = short interface over a tall implementation.
- **Call-graph collapse**: before = a tree of nested call boxes; after = one box with the now-internal calls faded inside.

## Style

- Editorial, not dashboard: generous whitespace, serif headings optional (`font-serif` with stone/slate).
- One accent colour (emerald or indigo) plus red for leakage and amber for warnings.
- Diagrams about 320px tall so before/after sits side by side without scrolling.
- `text-xs uppercase tracking-wider` for module labels inside diagrams.
- The only scripts are the Tailwind CDN and the Mermaid import; no app code, no interactivity beyond Mermaid's rendering.

## Top recommendation

One larger card: candidate name, one sentence on why, anchor link to its card.

## Tone

- **Use exactly:** module, interface, implementation, depth, deep, shallow, seam, adapter, leverage, locality.
- **Never substitute:** component, service, unit (for module) · API, signature (for interface) · boundary (for seam) · layer, wrapper (for module).
- Wins name the gain in those terms ("locality: bugs concentrate in one module", "leverage: one interface, N call sites"); never "easier to maintain" or "cleaner code".
- No hedging, no throat-clearing. A sentence that could be a bullet is a bullet; a bullet that could be cut is cut.
