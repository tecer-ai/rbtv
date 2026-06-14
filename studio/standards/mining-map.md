# Mining Map — Pitch/Deck Craft Inventory

> **Purpose:** Single consumable inventory of reusable craft mined from earlier pitch/deck components. Each row is a standalone rule — source anchors allow spot-verification but no source re-reading is needed to apply the claim.
>
> **Sources mined:** `pitch-deck-rules.md` (living corrections) · `html-patterns.md` · `html-components.md` · `pitch/workflow.md` + steps 01–06 + step-e01 · `pitch-reference.md` · `roelof.md` · `leo.md` · `vivian.md`
>
> **Consumer key:** `ban-list` · `flaw-checklist` · `Strategist-investor` · `Strategist-client` · `Designer-persona` · `message-lock beat` · `art-direction beat` · `trio beat` · `slice beat` · `gate beat`

---

## Section 1 — Visual Consistency Rules (from `pitch-deck-rules.md`)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| V-1 | All content slides MUST use `justify-content: flex-start` (top-aligned layout); only cover and closing slides may use centered layout. Titles must appear anchored at the same vertical position when flipping through the deck. | `pitch-deck-rules.md` § "Fixed Title Position Across All Slides" + Design Constraints row 17 | ban-list · flaw-checklist · art-direction beat |
| V-2 | All team/founder cards MUST have identical visual treatment (same borders, shadows, background, padding, sizing). Narrative emphasis translates to callout TEXT within the card, never to differential card styling. | `pitch-deck-rules.md` § "Team Card Visual Parity" + Design Constraints row 19 | ban-list · flaw-checklist · Designer-persona |
| V-3 | The cover slide is a title card only: brand mark + category positioning (one short line). Product definitions, value propositions, and multi-sentence descriptions belong on subsequent slides. | `pitch-deck-rules.md` § "Cover Slide Density" | ban-list · flaw-checklist · art-direction beat |
| V-4 | Cover and closing slides MUST use identical background, typography, and layout. Closing adds contact info only. | `pitch-deck-rules.md` Design Constraints row 6 | ban-list · flaw-checklist · Designer-persona |

---

## Section 2 — Data Integrity Rules (from `pitch-deck-rules.md`)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| D-1 | Use ONLY titles present in source documents — NEVER infer CEO, COO, CTO, or any other title. If titles are ambiguous or missing, ask the user. | `pitch-deck-rules.md` § "No Fabricated Titles or Organizational Structure" | ban-list · Strategist-investor · Strategist-client |
| D-2 | Use full legal/professional names in investor decks. NEVER use nicknames or informal names. If source documents use nicknames, resolve from CVs or ask the user. | `pitch-deck-rules.md` § "Formal Names in Investor Decks" | ban-list · Strategist-investor |
| D-3 | NEVER include a named fund or investor partner quote in an outbound investor deck (relationship, fundraising, or update decks). Existing investors seeing another investor's endorsement creates social dynamics the founder must control. | `pitch-deck-rules.md` § "No Named Investor Quotes in Outbound Investor Decks" | ban-list · Strategist-investor |
| D-4 | If a stat's source category does not match the company's positioning, NEVER rename the market category to fit. Instead: flag the tension to the user and present options (keep with honest label, remove, or find alternative data). Misattributed data destroys credibility if an investor checks the source. | `pitch-deck-rules.md` § "Never Relabel Third-Party Research Data" | ban-list · Strategist-investor · message-lock beat |
| D-5 | SAM and TAM MUST include full names ("Serviceable Addressable Market," "Total Addressable Market") alongside abbreviations on first use. Every market-slide number must be self-explanatory at a glance — no unexplained figures. | `pitch-deck-rules.md` § "Self-Explanatory Market Data" | ban-list · flaw-checklist · Strategist-investor |

---

## Section 3 — Source Research Rules (from `pitch-deck-rules.md`)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| SR-1 | The narrative document is NOT sufficient source material for team slides. ALWAYS read actual CV/bio files for every founder before generating team cards. If CVs are unavailable, ask the user before generating. | `pitch-deck-rules.md` § "Read Founder CVs Before Generating Team Slides" | flaw-checklist · Strategist-investor · Strategist-client · message-lock beat |
| SR-2 | Every founder card MUST show the same number and depth of career highlights. If one founder has 3 highlights with company names, all must have 3 highlights with company names. If source material for one founder is thin, ask the user for more detail — NEVER generate a shallow card. | `pitch-deck-rules.md` § "Equal Bio Depth Across All Founder Cards" | ban-list · flaw-checklist · Designer-persona |

---

## Section 4 — Print/PDF Safety Rules (from `pitch-deck-rules.md` + `html-patterns.md`)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| P-1 | NEVER use these CSS properties on elements that must render in PDF: `aspect-ratio` (ignored by print renderers — use explicit `width` + `height`), CSS transforms on positioned elements (break in Decktape — use `writing-mode: vertical-rl` for rotated text), pseudo-elements for structural content like midlines/dividers (invisible in PDF — use real DOM elements), complex `clip-path` (use simple shapes or SVG). | `pitch-deck-rules.md` § "Print-Unsafe CSS Properties" + Design Constraints row 18 | ban-list · flaw-checklist · Designer-persona · art-direction beat |
| P-2 | Diagram slides (quadrant maps, flowcharts, timelines, complex visualizations) are the highest PDF-break risk. These slides MUST be validated first during PDF QA. Prefer simple grid layouts over positioned/transformed elements. | `pitch-deck-rules.md` § "Diagram Slides Are Highest Risk" | flaw-checklist · gate beat |
| P-3 | `@media print` block is mandatory: `body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }` and `.slide { page-break-inside: avoid; }`. `@page { size: landscape; margin: 0; }`. Without these, colors and page breaks are unreliable in Decktape/Chromium export. | `html-patterns.md` § "Critical Print CSS" | ban-list · art-direction beat |

---

## Section 5 — Layout & Density Constraints (from `html-patterns.md` + `pitch-deck-rules.md`)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| L-1 | The slide container MUST use `justify-content: flex-start` globally; the `.slide-content` div inside uses `justify-content: center` so content centers in the remaining space below the title. Cover slides add a stronger optical offset via `padding-bottom: calc(60px + 14vh)`. | `html-patterns.md` § "Slide Container Pattern" | art-direction beat · Designer-persona |
| L-2 | Grid constraints: `.grid-3` — max 6 cards (2 rows); `.grid-4` — only when each cell ≤3 lines; for richer content, use `.grid-3` or `.grid-2`. Never exceed these card counts or switch grids mid-deck without a visual reason. | `html-patterns.md` § "Layout Patterns" + `pitch-deck-rules.md` Design Constraints row 3 | ban-list · flaw-checklist · art-direction beat |
| L-3 | Max 3 distinct content zones per slide. 4+ zones MUST split into separate slides. On slides with 3+ sections, add a `.zone-label` above every distinct content zone to establish reading order and prevent zones from merging visually. | `pitch-deck-rules.md` Design Constraints row 4 + `html-components.md` § "Zone Label (Multi-Section Slides)" | ban-list · flaw-checklist · art-direction beat |
| L-4 | Content-fit check before finalizing: if title + subtitle + content block exceeds ~70vh, switch to top-aligned layout with reduced padding. Slides with >3 content zones, process diagrams, or >4 bullet items MUST use `justify-content: flex-start` with `padding-top: 50px; padding-bottom: 40px;`. | `pitch-deck-rules.md` Design Constraints rows 13 and 16 | flaw-checklist · gate beat |
| L-5 | Max textured backgrounds: 3 per deck (cover, closing, and 1 accent). ALWAYS set `background-color` fallback before `background-image`. If texture competes with text readability, mute with a semi-transparent overlay. | `html-patterns.md` § "Background Image Pattern" + Design Constraints row 15 | ban-list · flaw-checklist · art-direction beat |

---

## Section 6 — Typography & Icon Standards (from `html-patterns.md` + `pitch-deck-rules.md`)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| T-1 | Minimum font sizes: body 15px, diagram nodes 14px, table cells 13px. No content element below 13px. Stat labels MUST fit on a single line at rendered width — shorten copy rather than accepting two-line labels. | `pitch-deck-rules.md` Design Constraints rows 1 and 2 | ban-list · flaw-checklist · art-direction beat |
| T-2 | Typography scale is fluid: `.slide-title` uses `clamp(28px, 3.5vw, 42px)` at weight 800; `.stat-number` uses `clamp(36px, 5vw, 64px)` at weight 900; `.slide-subtitle` uses `clamp(16px, 1.8vw, 22px)` at weight 400, opacity 0.7. Use these exact scales — do not substitute arbitrary sizes. | `html-patterns.md` § "Typography Scale" | art-direction beat · Designer-persona |
| T-3 | Feature card icons: minimum 24px in `var(--primary)`. Smaller or muted icons should be removed entirely — they add visual noise without function. | `pitch-deck-rules.md` Design Constraints row 9 | ban-list · flaw-checklist · art-direction beat |
| T-4 | Primary icon library: Font Awesome 6.5.1. Secondary: Material Icons Outlined for variety. Add Phosphor/Lucide/Bootstrap Icons as needed. NEVER mix libraries on the same semantic set. | `html-patterns.md` § "Icon Libraries" | art-direction beat · Designer-persona |

---

## Section 7 — Color Discipline (from `html-patterns.md` + `pitch-deck-rules.md`)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| C-1 | Use CSS custom properties on `:root` for ALL color values. Every value in the `:root` block MUST be replaced with real brand tokens — the placeholder values in the pattern are for reference only. Dark-background logos MUST use `filter: brightness(0) invert(1)`. | `html-patterns.md` § "Color Scheme Pattern" + § "Logo Pattern" | ban-list · art-direction beat · Designer-persona |
| C-2 | Stat color discipline: single accent color for all stats in the same semantic group. Reserve `var(--danger)` (#ff6b6b) ONLY for genuinely negative values. All stats in a grid must use the same currency and time basis. | `html-patterns.md` § "Full Slide Example" + `pitch-deck-rules.md` Design Constraints rows 5 and 8 | ban-list · flaw-checklist · art-direction beat |
| C-3 | Use `.slide--warm` for team, product narrative, and closing slides to create visual breaks. Max 3–4 warm slides in a 20-slide deck. Variant palette: `--bg-warm: #F5EDE4` (warm cream), `--bg-soft: #F7F8FA` (soft gray for content slides). | `html-patterns.md` § "Slide Variants" | art-direction beat · Designer-persona |
| C-4 | Color-coded borders as a visual system must have consistent, intentional logic across the deck. Diagonal or random use of colored borders destroys the system signal. Decision framework boxes (kill criteria, go/no-go gates) use NEUTRAL borders — red borders signal danger rather than rigor. | `pitch-deck-rules.md` Design Constraints row 12 + `html-components.md` § "Decision Framework Box" | ban-list · flaw-checklist · art-direction beat |

---

## Section 8 — Component Patterns (from `html-components.md`)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| CP-1 | Competitive comparison grids: the product card dominates visually with `.card--winner` (elevation via `transform: translateY(-4px)`, stronger shadow, brand accent `border-top`). Competitors get `.card--loser` (opacity 0.75). This asymmetry is mandatory — equal-weight comparison grids signal lack of confidence. | `html-components.md` § "Comparison Card — Winner Emphasis" | ban-list · flaw-checklist · Designer-persona · art-direction beat |
| CP-2 | Scenario tables (financial, pessimistic/base/optimistic): red = floor (`var(--danger)`), blue = base (`var(--secondary)`, font-weight 700), green = ceiling (`var(--primary-dark)`). Color coding is standard — deviating from it requires explanation in Structure Notes. | `html-components.md` § "Scenario Table" | art-direction beat · Designer-persona |
| CP-3 | Callout boxes for risk and decision gates: use `.callout--risk` (danger-bordered) for failure modes and kill criteria. Use `.callout--gate` (warning-bordered) for decision gates. NEVER style risk/gate statements as footnotes — they are first-class content. | `html-components.md` § "Callout Boxes" | ban-list · flaw-checklist · art-direction beat |
| CP-4 | Flow diagram connectors: use Unicode arrows (→, ↓) styled with brand color. NEVER use 1px gray connectors — they disappear in PDF. Minimum connector weight: 2px brand color. | `html-components.md` § "Flow Diagram Connector" + `pitch-deck-rules.md` Design Constraints row 11 | ban-list · flaw-checklist · art-direction beat |
| CP-5 | Before/after columns: the "after" (positive) column MUST have higher visual weight — `color: var(--primary-dark)`, `font-weight: 600`. The "before" is de-emphasized: `color: var(--gray-600)`, `font-weight: 400`. Never render both columns at equal weight. | `html-components.md` § "Before/After Comparison" | ban-list · flaw-checklist · art-direction beat |

---

## Section 9 — Pitch Reference Standards (from `pitch-reference.md`)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| PR-1 | Investor deck: 12–15 slides max plus appendix. If any section needs expansion, add slides within the set (keep any set n ≤ 3). Never exceed 15 main slides — everything else is appendix. | `pitch-reference.md` § "Investor Pitch — Consensus Structure" | Strategist-investor · message-lock beat |
| PR-2 | Client deck: 10–12 slides. Proof slides must be positioned early — buyers need conviction fast. If ROI and proof slides are buried after slide 6, restructure before locking. | `pitch-reference.md` § "Client Pitch — Recommended Structure" | Strategist-client · message-lock beat · slice beat |
| PR-3 | Investors screen decks in 10–60 seconds via five questions: trust the team? early proof? venture-scale? thesis match? understand quickly? Average review time: 2:40–4:10. Only ~22% receive a complete read-through. Drop-off zone: pages 5–9. Implication: front-load the strongest slides; the deck must work standalone without narration. | `pitch-reference.md` § "What Investors Screen For" | Strategist-investor · message-lock beat |
| PR-4 | Three non-negotiable slide qualities (Kevin Hale / YC): Legible (high contrast, large type, key text at top). Simple (each slide expresses ONE idea). Obvious (understood at a glance — if a stranger can't immediately say your idea, the slide fails). | `pitch-reference.md` § "Three Non-Negotiable Slide Qualities" | ban-list · flaw-checklist · Strategist-investor · Strategist-client |
| PR-5 | Design standards from synthesized sources: 1–2 fonts max; 24pt+ body minimum; one focal element per slide with a descriptive title stating the POINT (not a label); 15–20% minimum whitespace; 5–7 lines per slide / 5–7 words per line; label graphs with the takeaway ("Revenue up 340% YoY"), not axis names. | `pitch-reference.md` § "Design Standards" | ban-list · flaw-checklist · art-direction beat · Designer-persona |
| PR-6 | Common mistakes to avoid (ban-list anchors): starting with solution instead of problem; vague market sizing ("$50B market" without bottom-up methodology); no traction whatsoever; unclear ask (missing amount + use of funds + 12-month milestones); screenshots (almost always illegible — use clean illustrations); paragraphs of text; default templates; complex diagrams ("little mazes for ideas"). | `pitch-reference.md` § "Common Mistakes" | ban-list · Strategist-investor · Strategist-client |
| PR-7 | Seed vs. Series A framing: Seed narrative = vision + problem insight + team; Series A narrative = execution + repeatable growth. Seed traction = pilots/early revenue/LOIs; Series A traction = MRR/CAC/LTV/churn/velocity. NEVER apply Series A evidence standards to a seed deck or vice versa. | `pitch-reference.md` § "Seed vs. Series A" | Strategist-investor · message-lock beat |

---

## Section 10 — Strategist: Investor Mode (from `roelof.md` + pitch steps 03–04)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| SI-1 | The Strategist in investor mode sits ACROSS the table, not beside it. Every question is the question VCs ask in partner meetings WHEN THE FOUNDER LEAVES THE ROOM. Zero sycophancy. When a narrative is weak, say "I wouldn't take this to my partners — here's why." When it's strong, say "This works. Move on." | `roelof.md` `<communication_style>` | Strategist-investor |
| SI-2 | Five investor principles to enforce at every challenge: (1) "I don't invest in slides — I invest in founders who understand their business cold." (2) "The best pitch decks answer questions before I ask them." (3) "If you can't explain your defensibility in one sentence, you don't have any." (4) "Show me the smallest possible market where you win — then show me how it expands." (5) "Every number in your deck is a promise. Don't put numbers you can't defend." | `roelof.md` `<principles>` | Strategist-investor · message-lock beat |
| SI-3 | For every investor slide, challenge it with the hard question a VC would ask, then assess whether the current narrative answers it. If not, state what is missing or weak AND propose a concrete alternative. NEVER rubber-stamp. NEVER present a challenge without a concrete alternative or better angle. | `pitch/steps-c/step-03-narrative.md` § "Mandatory Execution Rules / Role Reinforcement (investor)" | Strategist-investor · message-lock beat |
| SI-4 | Narrative assessment format at the end of the investor narrative draft: Story arc strength (Strong/Needs work/Weak + why) → Slides I'd fund on → Slides that need work (with specific problems) → Missing from the story → Kill question (the single hardest question; does the deck answer it?). | `pitch/steps-c/step-03-narrative.md` § "Narrative Assessment (investor)" | Strategist-investor · message-lock beat · gate beat |
| SI-5 | Counter-thesis research is mandatory: generate a genuinely adversarial research prompt structured as a VC analyst finding reasons NOT to invest. Research: key business model risks, market headwinds, competitive threats (larger players, well-funded competitors), regulatory risks, technology risks, historical failures in this space and why they failed. | `pitch/steps-c/step-05-research-prompt.md` § "Generate Counter-Thesis Research Prompt" | Strategist-investor |
| SI-6 | Standard investor slide arc (13 slides, adapt based on content strength): Title/Company Purpose → Problem (data-backed) → Problem (human/emotional) → Solution → Why Now (timing/tailwinds) → Traction/Validation → Market Size (bottom-up) → Competition/Positioning → Business Model/Unit Economics → Go-to-Market → Team → The Ask (amount, use of funds, milestones) → Vision (optional — only if genuinely compelling). | `pitch/steps-c/step-03-narrative.md` § "Standard investor slide arc" | Strategist-investor · message-lock beat |

---

## Section 11 — Strategist: Client Mode (from `leo.md` + pitch steps 03–04)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| SC-1 | The Strategist in client mode thinks in BUSINESS OUTCOMES, not features. Every slide is evaluated against "Would this survive a procurement committee review?" The kill question for every slide: "Would I sign a contract based on this?" | `leo.md` `<communication_style>` + `<rules>` | Strategist-client · message-lock beat |
| SC-2 | Five client principles to enforce at every challenge: (1) "I don't buy products — I buy solutions to problems I can quantify." (2) "Every vendor says they're different. Show me the proof, not the claim." (3) "If you can't show ROI in the first 5 slides, I'm checking email by slide 6." (4) "The best client pitches answer my objections before I raise them." (5) "I need to defend this purchase to my CFO and my board. Make it easy for me." | `leo.md` `<principles>` | Strategist-client · message-lock beat |
| SC-3 | No kitchen details: NEVER expose internal implementation details in a client pitch — technology stack, AI model choices, infrastructure decisions, internal tooling, or engineering architecture. Describe capabilities and outcomes, never the machinery behind them. | `pitch/steps-c/step-03-narrative.md` § "No kitchen details" | ban-list · Strategist-client |
| SC-4 | Positive scope by default: frame scope by describing what the solution IS and what it delivers. NEVER default to negative scope statements ("we will NOT do X") — they invite "why not?" and plant doubt. If negative scope exists in the context, capture it internally and ask the user whether to state it explicitly. | `pitch/steps-c/step-03-narrative.md` § "Positive scope by default" | Strategist-client · message-lock beat |
| SC-5 | Frame EVERYTHING from the CLIENT'S perspective, never the vendor's. "You'll gain X" not "We're the best at X." Feature dumps instead of outcome-focused messaging = failure condition. The artifact language must match the client's language, not the vendor's internal language. | `pitch/steps-c/step-03-narrative.md` § "Step-Specific Rules (client)" + § "Failure conditions (client)" | ban-list · Strategist-client · message-lock beat |
| SC-6 | Standard client slide arc (11 slides): Title/Who You Are (one line — client doesn't care about origin story) → Their Problem (data-backed, in their language) → Current Reality (how they solve it today, what it costs them) → Your Solution (what changes for THEM, not a feature list) → How It Works (process, workflow, integration — tangible) → Before/After (concrete transformation with metrics) → Proof Points (case studies, testimonials, pilot results) → Why Us vs. Alternatives (honest competitive positioning) → Pricing & ROI (plans, payback period, TCO) → Implementation & Timeline (what it takes to switch) → Next Steps (clear CTA). | `pitch/steps-c/step-03-narrative.md` § "Standard client slide arc" | Strategist-client · message-lock beat |
| SC-7 | Common buyer objections to research and pre-empt: real total cost of ownership (hidden costs, integration, training); who else in this industry uses this (references, case studies); what happens if this doesn't work (SLAs, exit clauses); how this compares to specific competitors; implementation risk (timeline, resources, disruption). | `pitch/steps-c/step-04-data-layer.md` § "Common buyer objections to research" | Strategist-client · message-lock beat |

---

## Section 12 — Message Lock Beat (narrative-first discipline)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| ML-1 | Narrative First is the foundational ordering rule: the pitch STORY is agreed before ANY HTML is generated. Story drives design, not the other way around. This is non-negotiable — generating HTML before narrative lock is a failure condition. | `pitch/workflow.md` § "Core Principles: Narrative First" | message-lock beat · gate beat |
| ML-2 | The handoff contract between narrative and design is two artifacts: `pitch-narrative.md` (slide-by-slide story with data annotations) + `pitch-structure.md` (frontmatter + per-slide spec table with layout, focal element, data/proof, density). The deck-design workflow reads them from disk — zero conversation context required. | `pitch/workflow.md` § "Handoff Contract" + `pitch/steps-c/step-06-structure.md` § "6b. Write the Structure Artifact" | message-lock beat · gate beat |
| ML-3 | Narrative and structure artifacts are a LINKED UNIT. When the story or slide set changes, update BOTH in the same operation. NEVER let the structure artifact go stale against the narrative. A revised narrative with an existing deck = HTML drift — ALWAYS flag it and route to the design mode for sync. | `roelof.md` `<rules>` (fourth rule) + `leo.md` `<rules>` (fourth rule) + `pitch/steps-e/step-e01-narrative.md` § "Mandatory Execution Rules / Step-Specific Rules" | message-lock beat · Strategist-investor · Strategist-client |
| ML-4 | Slide titles are the POINT, not a label. "Slide 7: Traction" fails. "Slide 7: $120K MRR, 40% MoM" passes. Every title must state the takeaway — what the investor/buyer should think after reading it. | `pitch/steps-c/step-03-narrative.md` § "each slide gets: a title (the POINT, not a label)" | message-lock beat · ban-list · flaw-checklist |
| ML-5 | Data discussion is conceptual before research: identify WHAT data would validate each slide and WHERE it might exist — do NOT present specific numbers unless they already exist in the pitch brief. Discuss data types and sources, not specific values. The goal is a data wishlist the research prompt pursues. | `pitch/steps-c/step-04-data-layer.md` § "Step-Specific Rules" | message-lock beat · Strategist-investor · Strategist-client |
| ML-6 | Research prompts must be BROADER than specific data points (room for the AI to find adjacent/proxy data). Never send a shopping list of exact numbers — the researching AI doesn't know the pitch narrative. Embed web-research-standards in the prompt so the AI follows them. | `pitch/steps-c/step-05-research-prompt.md` § "Step-Specific Rules" | message-lock beat |
| ML-7 | Context gathering reads entity directory ROOT-LEVEL `.md` files only (non-recursive). Do NOT descend into subdirectories. Do NOT ask the user questions already answered in the documents. If CVs/bio files exist, read them before drafting team slides. | `pitch/steps-c/step-02-context-gather.md` § "Step-Specific Rules" + § "Mandatory Sequence: 1. Identify the Entity Directory" | message-lock beat · Strategist-investor · Strategist-client |

---

## Section 13 — Designer Persona (from `vivian.md` + pitch steps)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| DP-1 | Start EVERY design conversation with imagery — describe the mood, the scene, the feeling before discussing tactics or specifications. The opening is cinematic, not a feature list. | `vivian.md` `<rules>` (second rule) | Designer-persona |
| DP-2 | Always offer THREE visual directions. Be transparent about which one you believe in and why. NEVER hide the preferred direction. | `vivian.md` `<rules>` (third rule) + `<principles>` ("Treat every stakeholder as a co-director — offer three directions") | trio beat · Designer-persona |
| DP-3 | Push past the safe choice. When a decision feels obvious, name it and propose the more daring alternative alongside it. Safe is boring — the final work matters more than being agreeable. | `vivian.md` `<rules>` (fourth rule) + `<principles>` ("Safe is boring. Push past the obvious") | trio beat · Designer-persona |
| DP-4 | Design takes strategy and structure documents as INPUT — never redo narrative or strategic work. Design within those constraints. However, when user-directed HTML changes alter content that exists in the narrative, the narrative MUST be updated to match. | `vivian.md` `<rules>` (fifth rule) | Designer-persona · gate beat |
| DP-5 | Pitch artifacts (HTML deck, narrative, structure, companion docs) are a linked unit. When editing ANY pitch artifact, ALL related documents MUST be updated in the same operation. Content-only changes in HTML MUST be reflected in the narrative — and in the structure artifact when the slide set changes. | `vivian.md` `<rules>` (sixth rule) | Designer-persona · gate beat |
| DP-6 | Build tension, then drop the jaw — design is storytelling with a plot twist. The visual arc of the deck has its own emotional rhythm: tension builds through problem slides, breaks on solution, and peaks at the strongest proof moment. | `vivian.md` `<principles>` ("Build tension, then drop the jaw") | Designer-persona · art-direction beat |

---

## Section 14 — Art-Direction Beat (image/visual craft from `html-patterns.md`)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| AD-1 | Image reference pattern: use named slots (`slide-{number}-{topic}.png`) with fallback `onerror="this.style.display='none'"`. Slot containers use a branded background (`var(--gray-100)`) so the deck never renders a broken image state. | `html-patterns.md` § "Image Reference Pattern" | art-direction beat · Designer-persona |
| AD-2 | Multi-logo compositions: logos with more visual mass (icon + text) must be sized 10–20% SMALLER in height than simpler wordmarks to achieve visual balance. Separator: `×` character, font-weight 300, opacity 0.5–0.6. ALWAYS test multi-logo compositions at actual slide size — aspect ratio differences cause surprises. | `html-patterns.md` § "Multi-Logo Composition" | art-direction beat · Designer-persona |
| AD-3 | Scatter plot sizing: minimum 500px wide × 380px tall. Axes must include scale values. Labels minimum 13px with background overlay to ensure readability over data points. | `pitch-deck-rules.md` Design Constraints row 7 | flaw-checklist · art-direction beat |
| AD-4 | Gap between slide header and primary content block MUST NOT exceed 40px. The visual tightness between title and content is a legibility and skim-speed signal — excessive gap reads as "sparse and unconvincing." | `pitch-deck-rules.md` Design Constraints row 10 | flaw-checklist · art-direction beat |
| AD-5 | Asset manifests (`manifest.md`) MUST document whether each logo/asset is dark-on-transparent or light-on-transparent, and include the CSS filter instruction for dark-background usage. This prevents silent logo inversion errors across slide variants. | `html-patterns.md` § "Asset Manifest Color Handling" | art-direction beat · Designer-persona |

---

## Section 15 — Slice Beat (per-slide structural craft)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| SL-1 | Each slide expresses ONE idea. Every focal element gets a descriptive title stating the point. 15–20% minimum whitespace. 5–7 lines per slide, 5–7 words per line. These are hard constraints — enforce at generation time, not QA time. | `pitch-reference.md` § "Design Standards" + § "Three Non-Negotiable Slide Qualities" | slice beat · ban-list |
| SL-2 | Layout typing by slide purpose (investor): Hero slides (title, vision) — large text, minimal elements. Data slides (traction, market, unit economics) — numbers as focal point. Comparison slides (competition, before/after) — side-by-side or matrix. Story slides (problem, solution) — icon + text or image + text. Action slides (the ask) — clear CTA with supporting detail. | `pitch/steps-c/step-06-structure.md` § "Identify Slide Patterns (investor)" | slice beat · Strategist-investor |
| SL-3 | Layout typing by slide purpose (client): Hero slides — clean, confident, minimal. Problem slides — empathy-driven, data-supported. Solution slides — process diagrams, before/after. Proof slides — numbers as focal point, trust signals. Comparison slides — honest, side-by-side. Action slides (pricing, next steps) — clear CTA, remove friction. | `pitch/steps-c/step-06-structure.md` § "Identify Slide Patterns (client)" | slice beat · Strategist-client |
| SL-4 | The pitch-structure.md spec table drives generation: each row carries slide title, layout type, focal element, data/proof points, content density (sparse/medium/dense), and visual type (image/icon/chart/text-only). Structure Notes carry slide pattern groupings, dark/light alternation preferences, and brand color hints. | `pitch/steps-c/step-06-structure.md` § "6b. Write the Structure Artifact" | slice beat · message-lock beat |

---

## Section 16 — Gate Beat (quality and handoff gates)

| # | Claim | Source | Consumer |
|---|-------|--------|----------|
| G-1 | Narrative lock gate: do not proceed to HTML generation until both Strategist and user agree the narrative arc is solid. The definition of "solid" for investor mode: "strong enough to defend in a partner meeting." For client mode: "would survive a procurement committee review." | `pitch/steps-c/step-03-narrative.md` § "Iterate with User" | gate beat · Strategist-investor · Strategist-client |
| G-2 | HTML handoff gate: the design agent loads `pitch-narrative.md` and `pitch-structure.md` from disk — zero conversation context. If either artifact is missing, the handoff CANNOT proceed. Never begin HTML generation with an incomplete or unconfirmed structure artifact. | `pitch/steps-c/step-06-structure.md` § "Critical Step Completion Note" | gate beat · Designer-persona |
| G-3 | Deck-edit / narrative-drift gate: small in-deck fixes (a number, a typo, a color) do NOT belong in narrative revision mode — route to the design agent's deck-edit mode directly. When narrative changes leave an existing deck out of sync, ALWAYS flag it and instruct the user to invoke the design agent to sync. Never leave drift unflagged. | `pitch/steps-e/step-e01-narrative.md` § "Step-Specific Rules" + § "Critical Step Completion Note (Done)" | gate beat · Strategist-investor · Strategist-client · Designer-persona |
| G-4 | PDF QA gate: diagram slides (quadrant maps, flowcharts, timelines) must be validated FIRST in the PDF QA loop. Run Decktape export and verify: no broken layout, no missing connectors, no invisible pseudo-elements, no color loss. This check is not optional even if HTML renders correctly in browser. | `pitch-deck-rules.md` § "Diagram Slides Are Highest Risk" | gate beat · flaw-checklist |
| G-5 | Research impact gate: after the research agent returns findings, review them BEFORE continuing to structure. The data may require narrative changes — market sizes, competitive dynamics, growth rates might not support the "why now" or positioning. Better to discover contradictions before HTML than after. | `pitch/steps-c/step-04-data-layer.md` § "Warn About Research Impact" + `pitch/steps-c/step-05-research-prompt.md` § "Remind User About Narrative Impact" | gate beat · Strategist-investor · Strategist-client |

---

## Claim Count by Consumer

| Consumer | Claims |
|----------|--------|
| ban-list | V-1, V-2, V-3, V-4, D-1, D-2, D-3, D-4, D-5, SR-1, SR-2, P-1, P-3, L-2, L-3, C-1, C-2, C-4, CP-1, CP-3, CP-4, CP-5, PR-4, PR-6, SC-3, SC-5, ML-1 (via gate), ML-4, SL-1 |
| flaw-checklist | V-1, V-2, V-3, V-4, D-5, SR-1, SR-2, P-1, P-2, L-2, L-3, L-4, T-1, T-3, C-2, C-4, CP-1, CP-3, CP-4, CP-5, PR-4, AD-3, AD-4, G-4 |
| Strategist-investor | D-1, D-2, D-3, D-4, D-5, SR-1, PR-1, PR-3, PR-6, PR-7, SI-1, SI-2, SI-3, SI-4, SI-5, SI-6, ML-3, ML-5, ML-7, G-1, G-3 |
| Strategist-client | D-1, SR-1, PR-2, PR-6, SC-1, SC-2, SC-3, SC-4, SC-5, SC-6, SC-7, ML-3, ML-5, ML-7, G-1, G-3 |
| Designer-persona | V-2, V-4, SR-2, P-1, T-2, T-4, C-1, C-3, CP-1, CP-2, PR-5, DP-1, DP-2, DP-3, DP-4, DP-5, DP-6, AD-1, AD-2, AD-5, G-2, G-3 |
| message-lock beat | D-4, SR-1, PR-1, PR-2, PR-3, PR-7, SI-2, SI-4, SI-6, SC-1, SC-2, SC-4, SC-5, SC-6, SC-7, ML-1–ML-7, SL-4 |
| art-direction beat | V-1, V-3, P-1, P-3, L-1, L-2, L-3, L-5, T-1, T-3, T-4, C-1, C-2, C-3, C-4, CP-1, CP-3, CP-4, CP-5, PR-5, AD-1–AD-5, DP-6 |
| trio beat | DP-2, DP-3 |
| slice beat | L-1, PR-5, SL-1–SL-4 |
| gate beat | L-4, P-2, ML-1, ML-2, ML-3, DP-4, DP-5, G-1–G-5 |

**Total claim rows: 86**
