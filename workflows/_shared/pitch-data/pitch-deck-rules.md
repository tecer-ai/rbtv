# Pitch Deck Design Rules

Living document of design and content rules for HTML pitch deck generation. Vivian MUST follow every rule in this file. Rules are cumulative — new entries are appended, never removed unless explicitly superseded.

**Last updated:** 2026-04-02

---

## Visual Consistency Rules

### 1. Fixed Title Position Across All Slides

All content slides (non-cover, non-closing) MUST place the `.slide-title` at the same position. Titles MUST NOT float or shift between slides. When flipping through the deck, every title must appear anchored to the same spot.

**Implementation:** Content slides MUST use `justify-content: flex-start` (top-aligned layout). Cover and closing slides may use centered layout. See html-patterns.md for the CSS.

### 2. Team Card Visual Parity

All team/founder cards MUST have identical visual treatment — same borders, shadows, background, padding, and sizing. NEVER apply a highlight class, accent border, or shadow to one card that others lack. Narrative emphasis translates to callout text within the card, not to card styling.

### 3. Cover Slide Density

The cover slide is a title card. It contains: brand mark + category positioning (one short line). Product definitions, value propositions, and multi-sentence descriptions belong on subsequent slides. NEVER put more than one line of descriptive text on the cover.

---

## Data Integrity Rules

### 4. No Fabricated Titles or Organizational Structure

Use ONLY titles present in source documents. If a source says "Co-founder," the deck says "Co-founder." NEVER infer CEO, COO, CTO, or any other title. If titles are ambiguous or missing, ask the user.

### 5. Formal Names in Investor Decks

Use full legal/professional names in investor decks. NEVER use nicknames, diminutives, or informal names. If source documents use nicknames, resolve the full name from CVs, founder profiles, or ask the user.

### 6. No Named Investor Quotes in Outbound Investor Decks

NEVER include a named fund or investor partner quote in an outbound investor deck (relationship, fundraising, or update decks). Existing investors seeing another investor's endorsement creates social dynamics the founder must control — not the deck.

### 7. Never Relabel Third-Party Research Data

If a stat's source category does not match the company's positioning, NEVER rename the market category to fit. Instead: flag the tension to the user and present options — keep with honest label, remove, or find alternative data. Misattributed data destroys credibility if an investor checks the source.

### 8. Self-Explanatory Market Data

SAM and TAM MUST include full names ("Serviceable Addressable Market," "Total Addressable Market") alongside abbreviations on first use. Every number on a market slide MUST be self-explanatory at a glance — no unexplained figures. Investment signals and expansion paths require one-line context.

---

## Source Research Rules

### 9. Read Founder CVs Before Generating Team Slides

The narrative document is NOT sufficient source material for team slides. ALWAYS read actual CV/bio files for every founder before generating team cards. If CVs are unavailable, ask the user before generating. All founders MUST have comparable depth — same number of career highlights with company names and specifics. Flag depth gaps rather than generating uneven content.

### 10. Equal Bio Depth Across All Founder Cards

Every founder card MUST show the same number and depth of career highlights. If one founder has 3 highlights with company names, all founders must have 3 highlights with company names. If source material for one founder is thin, ask the user for more detail rather than generating a shallow card.

---

## Print/PDF CSS Rules

### 11. Print-Unsafe CSS Properties

NEVER use these CSS properties on elements that must render in PDF:

| Property | Problem | Alternative |
|----------|---------|-------------|
| `aspect-ratio` | Ignored by print renderers | Use explicit `width` + `height` |
| CSS transforms on positioned elements | Break in Decktape/Chromium print | Use `writing-mode: vertical-rl` for rotated text |
| Pseudo-elements for structural content | Invisible in PDF (midlines, dividers) | Use real DOM elements (`<div>`, `<hr>`) |
| Complex `clip-path` | Inconsistent print rendering | Use simple shapes or SVG |

### 12. Diagram Slides Are Highest Risk

Quadrant maps, flowcharts, timelines, and complex visualizations are the most likely to break in PDF. These slides MUST be validated first during the step-10 QA loop. Prefer simple grid layouts over positioned/transformed elements.
