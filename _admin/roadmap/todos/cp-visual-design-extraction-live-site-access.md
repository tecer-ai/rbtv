---
title: 'Compound: Visual Design Extraction — Live Site Navigation & Multi-Page Token Extraction'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted: ['step-01-init.md', 'step-02-self-assessment.md']
inputDocuments:
  - 'workflows/design-token-extraction/workflow.md'
  - 'workflows/design-token-extraction/steps-c/step-01-init.md'
  - 'workflows/design-token-extraction/steps-c/step-02-capture.md'
  - 'workflows/design-token-extraction/steps-c/step-03-extract.md'
  - 'workflows/design-token-extraction/steps-c/step-04-document.md'
  - 'workflows/design-token-extraction/templates/design-tokens.json'
  - 'workflows/design-token-extraction/templates/design-brief.md'
  - '.cursor/skills/bmad-rbtv-visual-design-extraction/SKILL.md'
outputPath: '_admin-output/planning-artifacts'
date: '2026-02-14'
yoloMode: false
---

# Visual Design Extraction — Live Site Navigation & Multi-Page Token Extraction

**Type:** Workflow
**Priority:** High
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

The `visual-design-extraction` workflow (`workflows/design-token-extraction/`) treats token extraction as a screenshot-only exercise. The entire workflow is described as extracting tokens "from website screenshots" — step-02 captures a single desktop screenshot, step-03 analyzes that screenshot visually, and step-04 writes the results. There is zero instruction to:

1. **Navigate the site** to understand its structure and pages before capturing.
2. **Capture multiple pages** (subpages, artwork detail views, navigation states, footer, etc.).
3. **Access the live DOM/CSS** to extract actual computed styles, @font-face declarations, CSS variables, stylesheet rules, media queries, transitions, or any programmatic token.
4. **Use Playwright for interaction** — the workflow references Playwright in step-02's frontmatter (`playwrightSkill`) but only uses it to take a single static screenshot.

The result: the executing agent produced a tokens JSON full of `null` values for typography (font family, sizes, weights) and spacing because those cannot be reliably derived from a PNG screenshot. It required three rounds of user intervention ("extract from the website, not only from the screenshot") before the agent performed a live DOM scan, and even then only after the user explicitly pushed.

### Goals

The redesigned workflow must:

1. **Navigate first, capture second** — enter the site, identify its structure (sitemap, main pages, interactive states), then decide what to capture.
2. **Capture multiple pages** — screenshot all main pages/sections at desktop viewport (and optionally tablet/mobile), not just the homepage hero.
3. **Extract from live DOM/CSS/HTML** — parse all loaded stylesheets, @font-face rules, CSS variables, computed styles from diverse elements, media queries, transitions/animations, and SVG colors. This is a mandatory step, not an optional enhancement.
4. **Combine screenshot analysis with DOM data** — screenshots inform visual identity, spatial relationships, and aesthetic assessment; DOM data provides precise token values (hex colors, font families, px/rem sizes, easing curves, breakpoints). The two sources are complementary and both mandatory.
5. **Produce comprehensive outputs** — the tokens JSON must never contain `null` for values that are extractable from the DOM. Fields genuinely not present in the site's CSS are marked as absent, not guessed.

### Constraints

- Must remain a 4-step micro-file workflow (init → capture → extract → document) to preserve RBTV workflow architecture.
- Must use Playwright browser automation for both navigation and DOM extraction (no separate tooling).
- Must work for sites that are JS-heavy, SPA, canvas-rendered, or otherwise non-trivial (the triggering site was Astro-built with video backgrounds and JS-driven state transitions).
- Must not break existing workflow contract (frontmatter schema, step processing rules, menu patterns).

---

## Self-Assessment

### Error Analysis

**Error type:** Knowledge gap + Execution failure (compound).

The workflow files themselves contain a fundamental design flaw: they describe token extraction as a visual-screenshot-only activity. The executing agent followed the workflow instructions correctly — which is the problem. The instructions are insufficient.

- **User expectation:** Invoke the visual-design-extraction skill → get a comprehensive tokens JSON with actual CSS values (font families, sizes, weights, colors, spacing, transitions, breakpoints) extracted from the live website.
- **Actual behavior:** Agent took one screenshot of the homepage, tried to guess typography from pixel analysis (failed — all `null`), needed three user corrections to access the DOM, and still only scanned a shallow set of elements before being corrected again to do a deep extraction.
- **Impact:** Five user interventions across the session to get a result the workflow should produce autonomously. The workflow's "Extract only visible tokens (no guessing)" rule in step-03 actually reinforced the failure by forbidding the agent from doing anything beyond screenshot analysis.

### Context Source Evaluation

| File | Role | Issue |
|------|------|-------|
| `workflows/design-token-extraction/workflow.md` | Workflow entry | **Root cause.** Goal statement says "from website screenshots" — sets the entire workflow scope to screenshot-only. No mention of DOM/CSS extraction. |
| `steps-c/step-02-capture.md` | Capture step | **Major gap.** References `playwrightSkill` in frontmatter but only uses Playwright to take a single screenshot of the homepage. No instruction to navigate the site, identify pages, or capture multiple views. |
| `steps-c/step-03-extract.md` | Extract step | **Major gap.** Entire step is screenshot analysis. "Extract only visible tokens (no guessing)" rule actively prevents DOM extraction. No instruction to access CSS/DOM. No mention of stylesheets, computed styles, @font-face, or CSS variables. |
| `steps-c/step-04-document.md` | Document step | **Minor gap.** Template structure is adequate, but the tokens JSON template has no fields for @font-face, transitions, breakpoints, CSS variables, or alpha scales — all of which are common in real sites. |
| `templates/design-tokens.json` | Output template | **Gap.** Missing fields: `fontFace`, `letterSpacing`, `transitions`, `breakpoints`, `cssVariables`, `alphaScale`, `zIndex`, `opacity`. |
| `.cursor/skills/bmad-rbtv-visual-design-extraction/SKILL.md` | Skill entry | Correctly routes to workflow. No issue here — the problem is in the workflow itself. |

**Critical gap:** No file in the workflow instructs the agent to access the live website programmatically. The word "DOM" does not appear in any workflow file. "CSS" does not appear in any workflow file. "stylesheet" does not appear. "computed style" does not appear. The workflow is structurally blind to the most reliable source of design tokens.

### Improvement Options

1. **New Rule**: Add a Cursor rule `bmad-rbtv-design-extraction.mdc` enforcing that design-token workflows must always extract from live DOM/CSS in addition to screenshots.
   - **Rationale:** Prevents future workflows from falling into the screenshot-only trap. Acts as a guardrail across agents.
   - **Location:** `_config/.cursor/rules/bmad-rbtv-design-extraction.mdc`

2. **Modify Existing Rule**: Update step-03's "Extract only visible tokens (no guessing)" rule to "Extract from live DOM/CSS for precise values; use screenshots for visual assessment and spatial relationships only."
   - **Rationale:** The current rule actively prevents the correct behavior. Flipping its intent fixes the root cause in the extraction step.
   - **Location:** `workflows/design-token-extraction/steps-c/step-03-extract.md`, section "Step-Specific Rules"

3. **Update System File**: Redesign step-02 (capture) to include site navigation, page discovery, multi-page screenshot capture, AND live DOM/CSS extraction as a single integrated step. Rename from "Screenshot Capture" to "Site Exploration & Capture."
   - **Rationale:** Navigation and DOM extraction are logically part of the capture phase. Splitting them across steps would add unnecessary ceremony. The agent needs the browser open anyway — it should explore, capture, and extract CSS in one pass.
   - **Location:** `workflows/design-token-extraction/steps-c/step-02-capture.md` (full rewrite)

4. **Add Constraint**: Add to workflow.md a constraint that the tokens JSON output must never contain `null` for any field that is extractable from the site's DOM/CSS. `null` is only acceptable when the site genuinely does not define that token.
   - **Rationale:** The initial output was full of `null` values for typography that were easily extractable. A hard constraint prevents this regression.
   - **Location:** `workflows/design-token-extraction/workflow.md`, new "Output Quality Constraints" section

5. **Alternative Approach**: Restructure the workflow as a 5-step process: (1) Init, (2) **Site Discovery** (navigate, map pages, identify interactive states), (3) **Multi-Page Capture** (screenshot all discovered pages at standard viewports), (4) **DOM/CSS Extraction + Visual Analysis** (combined: parse stylesheets AND analyze screenshots), (5) Document. This separates discovery from capture from analysis more cleanly.
   - **Rationale:** The current 4-step workflow tries to do too little in capture and too much in extract. A 5-step workflow gives each concern its own step without overloading any single step. Discovery as a separate step ensures the agent understands the site before capturing.
   - **Location:** Full workflow restructure: `workflow.md` + all `steps-c/*.md` files

---

## Proposed Solution

**Selected approach:** Combination of options 3, 4, and 5 — restructure the workflow as a 5-step process with integrated DOM extraction and output quality constraints.

### New Workflow Steps

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | URL confirmation, output format, create output document (unchanged) |
| 02 | Site Discovery | Navigate site with Playwright. Map pages/sections/interactive states. Produce a site structure summary for user confirmation. |
| 03 | Multi-Page Capture & DOM Extraction | For each discovered page: set viewport, capture full-page screenshot, AND run DOM/CSS extraction (stylesheets, computed styles, @font-face, CSS vars, media queries). Save screenshots + raw scan JSON. |
| 04 | Token Synthesis | Combine screenshot visual analysis with DOM data. Produce consolidated tokens across all pages. Present to user for review. |
| 05 | Document | Generate brief and/or tokens JSON from synthesized data. Save to output folder. (Largely unchanged from current step-04.) |

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify/create | `workflows/design-token-extraction/workflow.md` (update goal, step count, mode table), `steps-c/step-02-capture.md` → rename to `step-02-discover.md` (new), `steps-c/step-03-extract.md` → rename to `step-03-capture-extract.md` (new), `steps-c/step-04-document.md` → rename to `step-04-synthesize.md` (new), create `steps-c/step-05-document.md` (adapted from current step-04), `templates/design-tokens.json` (add missing fields) |
| Scope of change | Full workflow redesign — all step files rewritten, workflow.md updated, template extended |
| Related files | `.cursor/skills/bmad-rbtv-visual-design-extraction/SKILL.md` (no change needed — routes to workflow.md), `_mobile/skills/visual-design-extraction/SKILL.md` (does not exist — browser-dependent skill excluded from Nanobot) |

### Step-02 (Site Discovery) Key Requirements

- Navigate to target URL with Playwright
- Identify all reachable pages: scan `<a>` hrefs, navigation menus, sitemap if available
- Detect interactive states: buttons that reveal content, JS-driven navigation, modals
- Click through main sections and record what content each reveals
- Present site structure summary to user: "I found N pages/sections: [list]. Which should I capture?"
- User confirms or adjusts page list
- Output: ordered list of URLs/states to capture in step-03

### Step-03 (Capture & DOM Extraction) Key Requirements

- For each confirmed page/state:
  - Navigate to it
  - Set viewport (desktop 1440x900 default; user can request additional)
  - Capture full-page PNG screenshot
  - Run comprehensive DOM/CSS extraction:
    - All `document.styleSheets` → rules, selectors, property values
    - All `@font-face` declarations (family, src, weight, style, display)
    - All `@media` queries (conditions, breakpoints)
    - CSS custom properties (`:root` and inline `--var` on elements)
    - Computed styles from 50+ diverse elements (headings, paragraphs, buttons, links, navigation, cards, labels, SVGs)
    - Unique values inventory: colors, font families, font sizes, font weights, line heights, letter spacings, border radii, shadows, transitions, z-indices, opacity values, spacing (margins, paddings, gaps)
  - Save screenshot to `{output_folder}/screenshots/{slug}-{page-name}.png`
  - Save raw scan to `{output_folder}/design-tokens/{slug}-{page-name}.scan.json`
- Output: set of screenshots + scan JSONs ready for synthesis

### Step-04 (Token Synthesis) Key Requirements

- Load all screenshots into context (visual analysis)
- Load all scan JSONs (DOM data)
- Merge unique values across all pages into consolidated token categories
- For each token: prefer DOM-extracted value; use screenshot-sampled value only when DOM reports transparent/absent (document which source)
- Present consolidated tokens to user for review
- Output quality constraint: `null` only when genuinely absent from site CSS/DOM

### Template Extension (design-tokens.json)

Add fields: `fontFace[]`, `letterSpacing{}`, `transition{}` (durations, easings, animation), `breakpoints{}`, `cssVariables{}`, `alphaScale{}` (white/black/brand alpha variants), `zIndex{}`, `opacity{}`.

---

## Rationale

The current workflow was designed for a simpler use case (static marketing pages where screenshot analysis is sufficient). Modern websites use custom fonts served via @font-face, CSS variables for theming, complex transition systems, responsive breakpoints, and JS-driven state changes. Screenshot-only analysis cannot extract any of these. The redesigned workflow treats the live DOM as the primary token source and screenshots as the complementary visual reference — matching how a human designer would actually reverse-engineer a site's design system.

---

## Acceptance Criteria

- [ ] Workflow navigates and maps site structure before any capture
- [ ] Multiple pages/sections are captured, not just the homepage
- [ ] DOM/CSS extraction is mandatory in every execution (not optional or user-prompted)
- [ ] @font-face declarations are extracted with family, src, weight, style
- [ ] CSS variables are extracted from :root and inline styles
- [ ] Media queries / breakpoints are extracted
- [ ] Transitions and animations (durations, easings, keyframes) are extracted
- [ ] Tokens JSON never contains `null` for values present in the site's CSS
- [ ] Each token documents its source: "dom" or "screenshot-sampled"
- [ ] design-tokens.json template includes all new fields
- [ ] Workflow remains compatible with RBTV micro-file architecture (sequential steps, frontmatter tracking, menu halts)

---

## Related Files

| File | Relationship |
|------|--------------|
| `workflows/design-token-extraction/workflow.md` | Workflow entry — must be updated |
| `workflows/design-token-extraction/steps-c/step-01-init.md` | Step 1 — minor update (step count 4→5) |
| `workflows/design-token-extraction/steps-c/step-02-capture.md` | Step 2 — full rewrite as site discovery |
| `workflows/design-token-extraction/steps-c/step-03-extract.md` | Step 3 — full rewrite as capture + DOM extraction |
| `workflows/design-token-extraction/steps-c/step-04-document.md` | Step 4 — becomes synthesis step; current logic moves to step 5 |
| `workflows/design-token-extraction/templates/design-tokens.json` | Template — extend with new fields |
| `workflows/design-token-extraction/templates/design-brief.md` | Template — no structural change needed |
| `.cursor/skills/bmad-rbtv-visual-design-extraction/SKILL.md` | Skill entry — no change (routes to workflow.md) |
| `.cursor/rules/admin-rbtv-component-patterns.mdc` | Component patterns — step file size limits may need review (DOM extraction instructions are verbose) |

---

## References

- Triggering conversation: p6-4 design token extraction from `https://artprize-shadows.com/` — required 5 user interventions to achieve DOM-based extraction
- Deep scan output that demonstrates what the workflow should produce autonomously: `_admin-output/design-tokens/artprize-shadows.deep-scan.json`
- RBTV component patterns: `.cursor/rules/admin-rbtv-component-patterns.mdc` (step file size: 80-200 lines recommended, 250 max)

---

## Discussion Notes

User requirements captured during compound creation:

1. **Navigate first:** "first enter website and understand its structure and main pages"
2. **Multi-page capture:** "navigate and take screenshot of main pages"
3. **Richer extraction:** "extract design tokens based on main pages (there is more information available then only the home, both in prints and in CSS/DOM/HTML)"
4. **Integrated output:** "create the other md files in the process"
5. **Playwright mandatory:** "the visual-design-extraction workflow must navigate the site and take print screen of different pages with playwright"
