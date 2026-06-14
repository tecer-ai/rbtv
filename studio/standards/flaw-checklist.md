---
type: standard
module: studio
created: 2026-06-09
status: active
---

# Studio Flaw Checklist — Fresh-Eyes Pass

The structural craft checklist a fresh-context reviewer runs against a full deck before the owner sees it. Each item is a flaw a reviewer with zero conversation history can spot from the rendered deck alone — no scoring, no taxonomy, no aesthetic judgment. The output is a punch-list of concrete flaws, each tied to a slide.

This is a **module-internal standard** — not a `.claude/` rule and NOT the v1.1 critic (no scoring, no gating).

## Binding

This checklist drives the fresh-eyes pass. Read `{rbtv_path}/studio/deck-loop-spec.md`:

- **Fresh-eyes pass (Behavior Specification row 6)** — a fresh-context review against the chosen direction mini-brief AND this checklist, producing a punch-list; patches apply to flagged slides only.

The reviewer checks the rendered deck (headed browser, real geometry) against every item below. Each item carries: the **flaw** and **how to spot it**. Items cite the mining-map row (`./mining-map.md`) they derive from.

---

## The Checklist

| # | Axis | Flaw | How to spot it | Mining-map row |
|---|------|------|----------------|----------------|
| 1 | **Hierarchy / message-per-slide** | A slide carries more than one idea, or its title labels the topic instead of stating the takeaway | Read each slide for one second: can a stranger say the single point? A title like "Market" (a label) instead of "$4.2B SAM, bottom-up" (the point) fails. Two competing focal elements = two ideas = split or rethink | PR-4, ML-4, SL-1 |
| 2 | **Contrast / legibility** | Low contrast or undersized type; key content not at the top of the slide | Scan at full-screen for any text that strains to read; check body ≥15px, diagram nodes ≥14px, table cells ≥13px, nothing below 13px; any two-line stat label is a flag | PR-4, T-1 |
| 3 | **Alignment / title anchoring** | Title position drifts slide-to-slide; content slides mix centered and top-aligned layouts | Flip through the deck watching only the title: it must stay anchored at one vertical position. A title that jumps between slides means a content slide is wrongly centered (only cover/closing may center) | V-1 |
| 4 | **Spacing rhythm** | Excessive gap between the slide header and the primary content block; sparse, unconvincing rhythm | Measure the header-to-content gap — over 40px reads as "sparse and unconvincing." Check whitespace is intentional (≈15–20% minimum), not accidental dead space | AD-4, L-4 |
| 5 | **Overflow / density** | Content overruns the slide; more than 3 content zones; grid card-count exceeded | Look for any content block pushed past ~70vh or clipped at the slide edge; count content zones (>3 must split); count grid cards (`.grid-3` >6 cards is overflow). Zones without a `.zone-label` that merge visually are a flag | L-2, L-3, L-4 |
| 6 | **Type-pairing consistency** | Fonts, icon libraries, or type scales vary across slides without reason | Compare type treatment slide-to-slide: 1–2 fonts max held consistently; one icon library at brand weight (never mixed on a semantic set); the fluid type scale used uniformly, not arbitrary sizes per slide | T-3 |
| 7 | **Color system integrity** | Stat colors mixed within a semantic group; `var(--danger)` on non-negative values; colored borders used randomly | Check every stat grid uses one accent per semantic group and uniform currency/time basis; confirm red appears only on genuinely negative values; confirm colored borders follow a consistent intentional logic, not diagonal/random use | C-2, C-4 |
| 8 | **Component-weight asymmetry** | Comparison grids, before/after columns, or risk/gate callouts rendered at equal/under weight | Competitive grids must show the product card dominant (not equal-weight); "after" columns must outweigh "before"; risk and decision-gate statements must be first-class callouts, never footnotes | CP-1, CP-3, CP-5 |
| 9 | **Chart communication** | A chart labels axes instead of the takeaway; undersized or unreadable scatter plots; connectors that vanish | Read each chart's title: it must state the takeaway ("Revenue up 340% YoY"), not the axis name. Scatter plots ≥500×380px with scale values and ≥13px labels; flow connectors ≥2px brand color (1px gray disappears) | PR-4, AD-3, CP-4 |
| 10 | **Cover & closing treatment** | An overloaded cover; cover and closing that do not match | The cover is a title card only — brand mark + one category line; any product definition or multi-sentence text on it is a flaw. Cover and closing must share identical background, typography, and layout (closing adds contact only) | V-3, V-4 |
| 11 | **Team-card parity** | Founder/team cards with differential styling or uneven bio depth | All team cards must share identical treatment (borders, shadow, padding, sizing); every card must show equal number and depth of career highlights. One accented card, or one shallow card beside a rich one, is a flaw | V-2, SR-2 |
| 12 | **PDF-break risk** | Diagram slides (quadrant maps, flowcharts, timelines) at high risk of breaking in PDF export | Diagram slides are the highest PDF-break risk — flag them for validation FIRST; look for print-unsafe construction (positioned/transformed elements, pseudo-element dividers) that renders in-browser but breaks in the shipped PDF | P-1, P-2, G-4 |
| 13 | **Source-citation placement** | Source citations rendered inline / mid-text instead of as footnotes at the slide bottom | Scan each slide that cites a source: the citation must sit as a footnote at the slide bottom, visually subordinate — a `(Source: …)` or marker beside the claim in the body is a flaw. Distinct from risk/decision statements (item 8), which stay first-class callouts, never footnotes | ban-list F-5 |
| 14 | **Logo fidelity** | A client logo recolored — white/black knockout, inverted, tinted, or hue-shifted to fit a slide | Check every slide carrying a client logo: the mark must show its ORIGINAL brand colors. A logo turned solid white/black, inverted, or tinted is a flaw — on dark backgrounds it must sit on a light backing panel or use a client-supplied reversed logo, never be recolored | ban-list E-6 |

---

> **Reviewer note:** the checklist catches STRUCTURAL flaws. Aesthetic and distinctiveness judgment is the owner's at the human gate (deck-loop-spec Behavior Specification row 7) — never substituted by this pass. A flaw not on this list, but genuinely structural, is still reported; surface it in the punch-list with a one-line spotting cue.
