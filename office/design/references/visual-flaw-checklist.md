---
description: "Load at the moment a fresh context inspects rendered screenshots of an HTML artifact for structural visual flaws the checker scripts cannot see — after visual-check has already run, before the owner taste gate."
tags: [design]
---

# visual-flaw-checklist

Structural visual flaws a fresh context can spot from **rendered screenshots**, never from source text alone. Each item is a flaw a reviewer with zero conversation history can see, plus the cue for spotting it.

This is the remainder after `visual-check` automates the machine-checkable subset (palette literals, declared fonts, size floors, banned CSS patterns, grid/zone counts, cover/closing computed-style identity). Do NOT re-litigate those here.

This file is visual craft only. Narrative quality (one idea per page as a message judgment, title-as-takeaway, data integrity, bio-substance depth) lives elsewhere. Aesthetic and distinctiveness judgment is the owner's at the human gate — NEVER substituted by this list.

The output of a pass against this list is a punch-list of concrete flaws, each tied to a page.

**Spotting method.** Inspect rendered screenshots at full-screen, never the HTML source. Flip through watching one axis at a time (title row, then weight, then color logic). A script-green artifact can still fail every row below.

---

## The remainder

| # | Axis | Flaw | How to spot it | Row |
|---|------|------|----------------|-----|
| 1 | Alignment / title anchoring | Title position drifts page-to-page; content pages mix centered and top-aligned layouts | Flip through watching only the title: it MUST stay anchored at one vertical position. A title that jumps means a content page is wrongly centered (only cover/closing MAY center) | V-1 |
| 2 | Spacing rhythm | Excessive gap between the page header and the primary content block; sparse, unconvincing rhythm | The header-to-content gap MUST NOT read as empty. Whitespace MUST look intentional (a skim-speed margin), NEVER accidental dead space | L-4 |
| 3 | Overflow / visual density | Content clipped at the page edge; zones that merge into an undifferentiated wall | Look for any block pushed past the page edge or cut off. Count distinct visual zones: unlabeled regions that blend into one mass are a flag even when the zone count is legal | L-3, L-4 |
| 4 | Type-scale consistency | Type sizes jump page-to-page without a system | Compare type treatment across pages: one scale MUST hold. A heading that is a different recipe on every page is a flag. (Declared font *families* are a script check — do not re-check families here.) | T-2 |
| 5 | Color system integrity | Stat colors mixed within a semantic group; danger token on non-negative values; colored borders used randomly | Confirm every stat grid uses one accent per semantic group and a uniform currency/time basis; red MUST appear only on genuinely negative values; colored borders MUST follow a consistent intentional logic, not diagonal or random use | C-2, C-4 |
| 6 | Component-weight asymmetry | Comparison grids, before/after columns, or risk/gate callouts rendered at equal or under weight | Competitive grids MUST show the product card dominant (not equal-weight); "after" columns MUST outweigh "before"; risk and decision-gate statements MUST be first-class callouts, NEVER footnotes | CP-1, CP-3, CP-5 |
| 7 | Chart geometry | Undersized or unreadable plots; connectors that vanish | Scatter and similar plots MUST be large enough that axes, scale values, and labels read at full-screen; flow connectors MUST hold brand color at visible weight (hairline gray disappears in print) | CP-4 |
| 8 | Cover treatment | An overloaded cover | The cover is a title card only — brand mark + one category line. Any product definition or multi-sentence text on it is a flaw. (Cover/closing identity of background/type/layout is a script check — do not re-check it here.) | V-3 |
| 9 | Team-card visual parity | Team cards with differential styling | All team cards MUST share identical treatment (borders, shadow, padding, sizing). One accented card is a flaw. (Equal bio *substance* is not a visual judgment and is not on this list.) | V-2 |
| 10 | Texture vs text | Texture competing with text; more than three textured pages; missing color fallback visible as a flash or hole | Scan textured pages for unreadable type. Texture MUST sit behind a color fallback; a competing texture MUST be muted with a semi-transparent overlay | L-5 |
| 11 | Citation placement | Source citations rendered inline / mid-text instead of as footnotes at the page bottom | Scan each page that cites a source: the citation MUST sit as a footnote at the bottom, visually subordinate. A marker beside the claim in the body is a flaw. Distinct from risk/decision statements (item 6), which stay first-class callouts, NEVER footnotes | F-5 |
| 12 | Logo fidelity | A brand or third-party mark recolored — knockout, inverted, tinted, or hue-shifted to fit a page | Check every page carrying a mark: it MUST show its ORIGINAL brand colors. A logo turned solid white/black, inverted, or tinted is a flaw. On dark backgrounds it MUST sit on a light backing panel or use a supplied reversed logo, NEVER be recolored | E-6 |
| 13 | Print-break remainder | Construction that still looks fine on screen after the CSS-pattern checker has passed, yet will fail in the shipped PDF | Look at diagram-heavy pages (maps, flowcharts, timelines) in the render: missing midlines, vanished connectors, collapsed rotated type, or clipped shapes the in-browser view hides. The named print-unsafe CSS properties themselves are a script check — this item is what those scripts cannot see | P-1 |

---

A flaw not on this list, but genuinely structural and visual, is still reported; surface it in the punch-list with a one-line spotting cue. NEVER add a narrative, data-integrity, or taste item to cover the gap.
