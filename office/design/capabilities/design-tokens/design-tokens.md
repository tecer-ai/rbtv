---
id: design-tokens
description: Extract design tokens (colour, typography, spacing, layout, visual identity, transitions, CSS variables) from a live site into a tokens JSON and/or a design brief.
inputs: live URL(s); optional page list / capture scope; output path (`--out` or the invoking seat's seed); optional format (brief | tokens | both, default both)
outcome: the caller holds a tokens JSON and/or a design brief whose every token was read from the live site, each token sourced as `dom` or `screenshot-sampled`, with `null` only for genuine absence
outputs: tokens JSON matching `design-tokens.json` beside this file; optional design brief matching `design-brief.md` beside this file; per-page screenshots and scan JSONs as working artifacts under the caller-supplied output path
---

# design-tokens

Extract design tokens from a live site into a tokens JSON and/or a design brief. Instruction-only — this capability has no CLI. Drive the site through the environment's browser surface (the `web/browse` capability). NEVER duplicate that surface here. NEVER invent a capture executable.

## Standing rules

1. **DOM over screenshot.** Values read from the DOM or computed CSS ALWAYS win over values sampled from a screenshot.
2. **Every token records its source** as `"dom"` or `"screenshot-sampled"`.
3. **`null` is used ONLY when the site genuinely lacks the token** — NEVER as a stand-in for "did not look".
4. **Output paths come from the caller** — an `--out` argument or the invoking seat's seed. NEVER invent a destination. NEVER consult a retired path-resolution helper.

Interactive confirmation of URL and capture scope happens at most ONCE. Research seats invoke this capability non-interactively: if URL or output path is missing, stop and report the gap — NEVER prompt.

## Token categories

| Category | What to capture |
|---|---|
| Colors | Primary, secondary, neutral, accent, background |
| Typography | `@font-face`, families, sizes, weights, line heights, letter spacing |
| Spacing | Base unit, scale, section gaps, padding, margins, gaps |
| Layout | Grid, columns, max-widths, breakpoints, media queries |
| Visual identity | Brand tone, aesthetic, border radius, shadows, density |
| Transitions | Durations, easings, animation keyframes |
| CSS variables | `:root` custom properties and inline variable declarations |

The files `design-tokens.json` and `design-brief.md` beside this file are the i/o contract. Property names and nesting MUST match the tokens schema. Empty strings in that schema are unfilled slots, not absence. A produced file fills every slot the site defines.

When writing a produced tokens JSON, keep every harvest property name. Fill each scalar with the extracted value. Record source on every token: replace a filled scalar with `{"value": "<extracted>", "source": "dom"}` or `{"value": "<extracted>", "source": "screenshot-sampled"}`; on objects the schema already uses (a `fontFace` entry, a nested group), add `"source"` on that object. Metadata stays in schema form.

---

## Init — target URL and capture scope

Resolve, in this order:

1. Target URL(s) from the invocation. If several URLs, the first is the origin; the rest are extra pages to include.
2. Output path from `--out` or the invoking seat's seed. Stop if neither is present.
3. Format: `brief`, `tokens`, or `both`. Default `both` when the caller is silent.
4. Capture scope: a caller-supplied page list, or homepage only, or all same-domain main pages (the default when the caller is silent).

When invoked interactively and URL or scope is missing, ask ONCE for URL, format, and scope, then NEVER halt again. When the invocation already names them, proceed with no questions.

Write a working note at the output path recording `targetUrl`, `outputFormat`, `captureScope`, and the date. Then continue.

## Resume a partial extraction run

Before starting discovery, inspect the caller-supplied output path. If a partial extraction run is present — a page list, screenshots, scan JSONs, synthesized notes, or unfinished outputs — resume from the first incomplete stage. NEVER redo a completed stage. NEVER rewrite artifacts a completed stage already wrote. NEVER invent missing tokens to finish a thin capture; recapture that page instead.

Detect the resume point from artifacts, not from a menu:

| Present | Missing | Resume at |
|---|---|---|
| working note only | page list | page discovery |
| page list | screenshots or scans | capture and extract |
| screenshots + scans | synthesized tokens | synthesis |
| synthesized tokens | final brief and/or JSON | document |
| final outputs matching the requested format | — | stop; already done |

## Page discovery — which pages to sample

Navigate the target URL with the environment's browser surface. Wait for network idle. Dismiss cookie banners or blocking modals that hide content. Take one orientation screenshot (not the full-page capture).

Discover structure — NEVER guess it:

| Source | How |
|---|---|
| Navigation | `nav a`, `header a`, `[role="navigation"]` |
| Footer | `footer a` |
| Internal hrefs | same-domain `<a href>` |
| Sitemap | `/sitemap.xml` when reachable |

Keep same-domain URLs only. Deduplicate (trailing slashes, anchors). Drop `mailto:`, `tel:`, `javascript:`, and `#`.

Detect interactive states that reveal distinct visuals: dropdowns, mega-menus, tabs, accordions, modal overlays, client-side routes. Record each as a capture target.

| Scenario | Action |
|---|---|
| SPA with client-side routing | Click nav links, wait for content change, record each route as a page |
| Single-page site | One page, multiple sections; scroll and record section anchors |
| Authentication wall | Report it. Skip protected pages unless the caller already supplied a session |
| Site blocks automation | Report it. Fall back to caller-supplied screenshots; mark those tokens `screenshot-sampled` |

If the caller already named a page list, use it. If scope is homepage-only, capture the origin only. If this sitting is interactive, the single init confirmation already covered scope — do not re-ask. Write the confirmed page list to the output path, then continue.

## Capture and extract — screenshots and computed-style dumps

Both sources are mandatory for every confirmed page: a full-page screenshot AND a DOM/CSS extraction. Screenshots give visual context; the DOM is the primary source of precise values. NEVER skip DOM extraction. NEVER guess a value.

For each page:

1. Navigate. Wait for network idle. Viewport 1440×900 unless the caller named another. Dismiss blocking banners. Scroll to bottom and back to top to trigger lazy content.
2. Capture a full-page PNG of the entire scrollable area. Save under `{out}/screenshots/`.
3. Run one in-page scan that returns structured JSON covering every category below. Save under `{out}/scans/` as `{page}.scan.json`.
4. Additional viewports (tablet 768×1024, mobile 375×812) ONLY when the caller named them in scope.

Scan categories:

| Category | Extract |
|---|---|
| Stylesheets | Accessible `document.styleSheets` — selectors + property/value pairs |
| `@font-face` | Family, src, weight, style, display |
| `@media` | Condition strings and min-/max-width breakpoints |
| `@keyframes` | Names and definitions |
| CSS variables | All `--*` from `:root` and other elements |
| Computed styles | Sample 50+ diverse elements (sampling table below) |
| Unique colors | Deduplicated hex-normalized text, background, border, fill, stroke |
| Unique typography | Families, sizes, weights, line heights, letter spacings |
| Unique spacing | Margins, paddings, gaps |
| Transitions | property, duration, timing-function, delay |

Computed-style fields per sampled element: `fontFamily`, `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing`, `color`, `backgroundColor`, `padding`, `margin`, `gap`, `borderRadius`, `borderWidth`, `borderColor`, `boxShadow`, `textShadow`, `opacity`, `zIndex`, `transition`.

Element sampling — query at minimum:

| Selector | Purpose |
|---|---|
| `h1, h2, h3, h4, h5, h6` | Heading hierarchy |
| `p` (first 5) | Body text |
| `a` (first 10, diverse contexts) | Links |
| `button, [role="button"], input[type="submit"]` | Interactive |
| `nav a, nav button` | Navigation |
| `[class*="card"], [class*="feature"], [class*="hero"]` | Components |
| `svg` | Fill/stroke |
| `input, select, textarea` | Forms |
| `header, footer, main, section` | Structure |
| `img` (first 5) | Image treatment |
| `[class*="btn"], [class*="badge"], [class*="tag"]` | UI chrome |

Skip elements that return only browser defaults.

Stylesheet parsing:

1. Iterate `document.styleSheets`. Catch cross-origin access errors — log the sheet as inaccessible, do NOT fail the page.
2. Extract style-rule declarations from accessible sheets.
3. Collect `@font-face`, `@media`, `@keyframes` separately.
4. Normalize colors to hex (`#RRGGBB` or `#RRGGBBAA`).
5. Deduplicate after collection.

Report pages processed, paths written, and any partial extraction (blocked sheets). Then continue — do not halt.

## Synthesis — raw values into a coherent token set

Load every scan JSON and every screenshot. Merge unique values across pages into one coherent token set. Precision from the DOM; spatial relationships, density, and brand tone from the screenshots.

| Category | Merge |
|---|---|
| Colors | Union of hex values. Group by usage: text, background, border, accent, SVG fill/stroke |
| `@font-face` | Union of family + src + weight + style |
| Font families | Union of `@font-face` + computed; match computed names to `@font-face` |
| Font sizes / weights / line heights / letter spacings | Unique values; sizes ordered by frequency |
| Spacing | Unique margin/padding/gap. Identify base unit and scale |
| Border radii / shadows | Unique values; radii ordered by size |
| Transitions / animations | Unique declarations and `@keyframes` |
| Breakpoints | `@media` values, ascending |
| CSS variables | `:root` and element-scoped |
| Z-index / opacity | Unique values with element context; opacity only when not `1` |

Source attribution: `"dom"` from stylesheets or computed styles; `"screenshot-sampled"` from visual analysis. DOM-extracted values ALWAYS take precedence over screenshot-sampled values when both exist for the same token.

Identify patterns, not only raw values: palette groupings and contrast pairs; type-scale ratio; spacing base and multiplier; radius philosophy (sharp / soft / rounded / pill); shadow elevation; density (compact / comfortable / spacious); brand tone from screenshots.

| Scenario | Resolution |
|---|---|
| Same role, different values per page | Keep all variants, note the page |
| Slight hex drift (< 5% in any channel) | Group as one token; note variants |
| Contradictory values (body 16px vs 14px) | Keep both; flag in the working note |

NEVER write `null` for a token present in any scan. NEVER fill a gap by inventing a typical scale.

## Document — write the tokens JSON and the design brief

Generate the format(s) chosen at init. Save under the caller-supplied output path:

- Brief: `design-brief-{slug}.md` matching `design-brief.md` beside this file
- Tokens: `design-tokens-{slug}.json` matching `design-tokens.json` beside this file

Design brief (prose, informed by screenshots): Color Strategy, Typography Direction, Spacing Philosophy, Layout Patterns, Visual Identity, plus the Token Summary table. Fill every section from what was extracted. NEVER pad with generic design advice.

Tokens JSON: populate every field from the synthesized set. Use DOM-extracted values for concrete fields. Record source `"dom"` or `"screenshot-sampled"` on every token. NEVER leave a schema slot as an empty string when data was extracted. Mark genuinely absent tokens `null`.

Write a completion note: pages analyzed, screenshot count, scan count, and per-category token counts. Stop.

## What this never does

- It NEVER decides where output lives.
- It NEVER duplicates `web/browse`.
- It NEVER fabricates a palette, type scale, or spacing scale the site does not use.
- It NEVER treats a blocked cross-origin stylesheet as an empty site.
- It NEVER prompts after the single URL/scope confirmation.
