---
stepNumber: 3
stepName: 'capture-extract'
nextStepFile: ./step-04-synthesize.md
playwrightSkill: 'rbtv-playwright-cli'
---

# Step 03: Multi-Page Capture & DOM Extraction

**Progress: Step 3 of 5** — Next: Token Synthesis

---

## STEP GOAL

For each page confirmed in step-02, capture a full-page screenshot AND extract all design tokens from the live DOM/CSS. Screenshots provide visual context; DOM data provides precise token values. Both sources are mandatory.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design System Analyst. You extract with precision from both visual and programmatic sources.

### Step-Specific Rules

- DOM/CSS extraction is MANDATORY for every page — never optional
- Screenshots complement DOM data; DOM is the primary source for precise token values
- Save both screenshots and raw scan JSONs per page
- Never guess values — extract from computed styles and stylesheets

---

## MANDATORY SEQUENCE

### 1. Load Confirmed Pages

Read the confirmed page list from the output document (written in step-02).

### 2. Process Each Page

For each page/state in the confirmed list, execute steps 2a through 2d:

#### 2a. Navigate and Set Viewport

1. Navigate to the page URL
2. Wait for network idle
3. Set viewport to 1440×900 (desktop default)
4. Handle cookie consent / modals if present
5. Scroll to bottom and back to top to trigger lazy-loaded content

#### 2b. Capture Full-Page Screenshot

1. Capture full-page PNG (entire scrollable area)
2. Save to: `{output_folder}/screenshots/{slug}-{page-name}.png`

#### 2c. DOM/CSS Extraction

Run JavaScript via Playwright `evaluate` to extract every category below. Execute as a single comprehensive scan that returns a structured JSON object.

| Category | What to Extract |
|----------|----------------|
| **Stylesheets** | All accessible `document.styleSheets` — iterate CSSRuleList, collect selectors + property/value pairs |
| **@font-face** | Family, src (URL), weight, style, display for every declaration |
| **@media queries** | Condition strings and breakpoint values (min-width, max-width) |
| **@keyframes** | Animation names and keyframe definitions |
| **CSS variables** | All `--*` custom properties from `:root` and other elements |
| **Computed styles** | Sample 50+ diverse elements (see Element Sampling below) — collect fontFamily, fontSize, fontWeight, lineHeight, letterSpacing, color, backgroundColor, padding, margin, gap, borderRadius, borderWidth, borderColor, boxShadow, textShadow, opacity, zIndex, transition |
| **Unique colors** | Deduplicated hex-normalized colors from all text, background, border, fill, stroke values |
| **Unique typography** | Deduplicated font families, sizes, weights, line heights, letter spacings |
| **Unique spacing** | Deduplicated margins, paddings, gaps |
| **Transitions** | Transition-property, duration, timing-function, delay from stylesheets and computed |

#### 2d. Save Raw Scan

Save the extraction output as JSON:
`{output_folder}/design-tokens/{slug}-{page-name}.scan.json`

### 3. Report Completion

Report to user:
- Number of pages processed
- Screenshots saved (with paths)
- Scan JSONs saved (with paths)
- Any pages that failed or had partial extraction (e.g., cross-origin stylesheet blocked)

### 4. Update State

Add `step-03-capture-extract.md` to `stepsCompleted` in output document frontmatter.

### 5. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to token synthesis (step-04)
- **[R] Recapture** — Re-process specific pages
- **[A] Add viewport** — Capture additional viewport sizes (tablet 768×1024, mobile 375×812)
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## ELEMENT SAMPLING STRATEGY

To capture diverse computed styles, query at minimum:

| Selector | Purpose |
|----------|---------|
| `h1, h2, h3, h4, h5, h6` | Heading typography hierarchy |
| `p` (first 5) | Body text styles |
| `a` (first 10, diverse contexts) | Link styles |
| `button, [role="button"], input[type="submit"]` | Interactive element styles |
| `nav a, nav button` | Navigation typography and spacing |
| `[class*="card"], [class*="feature"], [class*="hero"]` | Component patterns |
| `svg` (all, for fill/stroke) | SVG color extraction |
| `input, select, textarea` | Form element styles |
| `header, footer, main, section` | Structural element styles |
| `img` (first 5, for border-radius/shadow) | Image treatment patterns |
| `[class*="btn"], [class*="badge"], [class*="tag"]` | UI component patterns |

Skip elements that return only browser defaults (no meaningful styling applied).

---

## STYLESHEET PARSING RULES

1. Access `document.styleSheets` and iterate all rules
2. Catch `SecurityError` on cross-origin sheets — log as inaccessible, do not fail
3. For accessible sheets: extract all `CSSStyleRule` declarations (selector + properties)
4. Separately collect `@font-face`, `@media`, `@keyframes` at-rules
5. Normalize all color values to hex (#RRGGBB or #RRGGBBAA)
6. Deduplicate values after collection

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-03-capture-extract.md` in `stepsCompleted`
2. Load `./step-04-synthesize.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- All confirmed pages captured with full-page screenshots
- DOM/CSS extraction completed for every page
- Screenshots and scan JSONs saved to correct locations
- Cross-origin sheet limitations reported (not silently skipped)

❌ **FAILURE:**
- Skipping DOM extraction for any page
- Guessing values instead of extracting from computed styles
- Missing scan JSONs for captured pages
- Proceeding without reporting results to user
