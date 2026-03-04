---
stepNumber: 7
stepName: 'generate'
nextStepFile: ./step-08-images.md
htmlPatternsFile: ../../_shared/pitch-data/html-patterns.md
htmlComponentsFile: ../../_shared/pitch-data/html-components.md
---

# Step 07: Generate HTML Pitch Deck

**Progress: Step 7 of 9** — Next: Image Prompts

---

## STEP GOAL

Generate a complete, professional HTML pitch deck optimized for landscape PDF export via Ctrl+P, based on the validated narrative and agreed structure.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Buyer building a presentation that could win a six-figure contract. Every pixel matters. Client pitches must feel trustworthy and professional — no flashy gimmicks, just clarity and confidence.

### Step-Specific Rules

- Load HTML/CSS patterns knowledge before generating
- Generate ALL slides in a single HTML file
- Landscape orientation optimized for Ctrl+P PDF export
- Professional icon libraries loaded via CDN
- Image references point to ./images/ relative folder
- Output must be self-contained (CDN links for fonts/icons only)
- Client decks should feel MORE conservative than investor decks — trust over excitement

---

## MANDATORY SEQUENCE

### 1. Load HTML Patterns

Read `{htmlPatternsFile}` completely — this provides layout foundations, colors, typography, grids, print CSS, icon libraries, and design constraints.

Read `{htmlComponentsFile}` completely — this provides component patterns (stat blocks, comparison cards, scenario tables, callout boxes, flow connectors, zone labels).

### 2. Determine Visual Direction

Based on the pitch brief and brand information (if available from M3 context-distill):
- Select color scheme (use brand colors if available, otherwise professional defaults)
- Select typography (Google Fonts, clean sans-serif)
- Determine dark/light slide alternation pattern
- Client decks benefit from a more conservative palette — blues, grays, whites convey trust

Present the visual direction to the user for confirmation:
```
Visual Direction:
- Primary color: {color} | Accent: {color}
- Font: {font family}
- Slide pattern: {e.g., "light cover → light content → subtle accent slides"}
- Icon library: Font Awesome 6 + Material Icons Outlined
- Tone: Professional/conservative (trust-first)

Does this look right, or would you like to adjust?
```

Wait for response.

### 3. Generate HTML Document

Create the complete HTML file following these requirements:

**Document Structure:**
- Single HTML file with all CSS embedded in `<style>`
- No external CSS files (except CDN links for fonts/icons)
- Each slide is a `<section class="slide">` element
- Slides use `page-break-after: always` and `break-after: page`

**Print / PDF Optimization:**
- `@page { size: landscape; margin: 0; }`
- `@media print` block hiding non-essential elements
- `-webkit-print-color-adjust: exact; print-color-adjust: exact;`
- `min-height: 100vh` for each slide
- Ctrl+P must produce perfect landscape pages with no content clipping

**Icon Libraries (load via CDN):**
- Font Awesome 6: `<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">`
- Material Icons Outlined: `<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">`

**Image Handling:**
- All image references use relative paths: `src="images/{descriptive-name}.png"`
- Use descriptive filenames: `slide-02-client-problem.png`, `slide-07-proof-points.png`
- Include `alt` attributes describing what the image should show
- Image slots must work gracefully when images are not yet present

**Design Standards (non-negotiable):**
- One focal element per slide with clear hierarchy
- Minimum 15-20% whitespace on every slide
- Title at top stating the slide's POINT (not vague labels — "Manual processes cost your team 12 hours/week" not "The Problem")
- Consistent color application throughout
- Minimum 4.5:1 contrast ratio for all text
- No paragraphs of text — bullets, numbers, visuals only
- Slide numbers on each slide (except title/cover)

### 4. Save HTML File

Save to: `{output_folder}/pitch-deck.html`

Ensure the images directory exists: `{output_folder}/images/`

### 5. Verify Output

Self-check the generated HTML:

| Check | Criteria |
|-------|----------|
| Slide count | Matches agreed structure |
| Page breaks | Every slide has `page-break-after: always` (except last) |
| Icons | CDN links present and icon elements render |
| Images | All src paths use `images/` prefix with descriptive names |
| Colors | Consistent palette, `:root` variables used |
| Typography | Single font family, clear hierarchy |
| Whitespace | No cramped slides |
| Contrast | Text readable on all backgrounds |
| Narrative | Slide titles match the agreed narrative points |
| Tone | Professional/conservative — appropriate for B2B |

### 6. Present Menu

```
✅ Pitch deck generated: {output_folder}/pitch-deck.html
📁 Image folder ready: {output_folder}/images/

Slides: {count} | Type: Client | Target: {target_client} | Format: HTML → Landscape PDF
```

**Select an Option:**
- **[C] Continue** — proceed to generate image prompts
- **[X] Exit** — exit workflow (HTML is saved)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load `{nextStepFile}`

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Complete HTML file with all slides
- Slide content matches the agreed narrative
- Professional, trust-first visual design
- Landscape PDF export works via Ctrl+P
- One idea per slide, glance test passes

❌ **FAILURE:**
- Slide content diverges from the agreed narrative
- Flashy/startup-y design inappropriate for B2B
- Text-heavy slides
- Missing print CSS
