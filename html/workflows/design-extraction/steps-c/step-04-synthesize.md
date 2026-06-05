---
stepNumber: 4
stepName: 'synthesize'
nextStepFile: ./step-05-document.md
---

# Step 04: Token Synthesis

**Progress: Step 4 of 5** — Next: Documentation

---

## STEP GOAL

Combine DOM extraction data with screenshot visual analysis to produce a consolidated, comprehensive set of design tokens across all captured pages.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design System Analyst. Synthesize programmatic data with visual insight — precision from the DOM, judgment from the screenshots.

### Step-Specific Rules

- DOM-extracted values are the PRIMARY source for precise tokens
- Screenshot analysis provides visual context, spatial relationships, and aesthetic assessment
- For each token: document whether source is `"dom"` or `"screenshot-sampled"`
- `null` ONLY when the site genuinely does not define that token
- Never guess — if a value cannot be extracted from DOM or identified in screenshots, mark as absent

---

## MANDATORY SEQUENCE

### 1. Load All Scan Data

Load all scan JSONs from `{output_folder}/design-tokens/{slug}-*.scan.json`.

### 2. Load All Screenshots

Load all screenshots from `{output_folder}/screenshots/{slug}-*.png` into context for visual analysis.

### 3. Merge Unique Values Across Pages

Consolidate extracted data across all pages:

| Category | Merge Strategy |
|----------|---------------|
| Colors | Union of all unique hex values. Group by usage: text, background, border, accent, SVG fill/stroke |
| @font-face | Union of all declarations (family + src + weight + style) |
| Font families | Union from @font-face + computed styles. Match computed values to @font-face declarations |
| Font sizes | All unique sizes, ordered by frequency of use |
| Font weights | All unique weights with usage context |
| Line heights | All unique values |
| Letter spacings | All unique values |
| Spacing | All unique margin/padding/gap values. Identify base unit and scale pattern |
| Border radii | All unique values, ordered by size |
| Shadows | All unique box-shadow and text-shadow declarations |
| Transitions | All unique transition declarations (property, duration, easing) |
| Animations | All @keyframes definitions |
| Breakpoints | All @media query breakpoint values, ordered ascending |
| CSS variables | All :root and element-scoped custom properties |
| Z-index | All unique values with element context |
| Opacity | All unique non-1.0 values |

### 4. Source Attribution

For each consolidated token, record its source:
- `"dom"` — extracted from stylesheets or computed styles
- `"screenshot-sampled"` — identified visually from screenshot analysis

DOM values always take precedence when both sources provide data for the same token.

### 5. Identify Design Patterns

Beyond raw values, identify structural patterns:

| Pattern | What to Identify |
|---------|-----------------|
| Color palette | Primary, secondary, neutral, accent groupings. Contrast pairs |
| Typography scale | Ratio between heading sizes. Body/display distinction |
| Spacing scale | Base unit and multiplier pattern (4px, 8px, etc.) |
| Border radius philosophy | Sharp (0-2px), soft (4-8px), rounded (12-16px+), pill |
| Shadow usage | None, subtle, pronounced. Elevation levels |
| Density | Compact, comfortable, spacious |
| Brand tone | Professional, friendly, bold, minimal — informed by screenshots |

### 6. Present Consolidated Tokens

Display the synthesized token set organized by category.

Include a summary table:

```
Token Synthesis Complete

| Category | Count | Source |
|----------|-------|--------|
| Colors | {n} | dom |
| Font families | {n} | dom (@font-face) |
| Font sizes | {n} | dom |
| Spacing values | {n} | dom |
| Breakpoints | {n} | dom |
| CSS variables | {n} | dom |
| Transitions | {n} | dom |
| Visual identity | — | screenshot-sampled |
```

Ask user: "Review the consolidated tokens. Any adjustments?"

HALT and wait for user response.

### 7. Update State

Add `step-04-synthesize.md` to `stepsCompleted` in output document frontmatter.

### 8. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to documentation (step-05)
- **[R] Refine** — Adjust specific token values or categories
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## CONFLICT RESOLUTION

When the same token has different values across pages:

| Scenario | Resolution |
|----------|-----------|
| Same element styled differently per page | Keep all variants, note which page each appears on |
| Slight variations (e.g., #333 vs #343434) | Group as a single token if difference < 5% in any channel; note variants |
| Contradictory values (e.g., body font 16px on one page, 14px on another) | Keep both, flag for user decision |

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-04-synthesize.md` in `stepsCompleted`
2. Load `./step-05-document.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- All scan JSONs and screenshots loaded and analyzed
- Tokens consolidated across all pages with deduplication
- Source attribution documented for every token
- No `null` values for tokens present in the DOM
- Design patterns identified
- User reviewed and confirmed

❌ **FAILURE:**
- Missing scan data from any page
- `null` values for tokens extractable from DOM
- No source attribution
- Skipping screenshot visual analysis
- Proceeding without user review
