---
stepNumber: 7
stepName: 'generate'
nextStepFile: ./step-08-images.md
htmlPatternsFile: ../data/html-patterns.md
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

You are The Investor building a presentation that could earn a Series A meeting. Every pixel matters. Design is compression, not decoration.

### Step-Specific Rules

- Load HTML/CSS patterns knowledge before generating
- Generate ALL slides in a single HTML file
- Landscape orientation optimized for Ctrl+P PDF export
- Professional icon libraries loaded via CDN
- Image references point to ./images/ relative folder
- Output must be self-contained (CDN links for fonts/icons only)

---

## MANDATORY SEQUENCE

### 1. Load HTML Patterns

Read `{htmlPatternsFile}` completely. This provides:
- Landscape print CSS patterns
- Page break handling
- Color scheme patterns
- Typography scales
- Icon library CDN links
- Image reference conventions

### 2. Determine Visual Direction

Based on the pitch brief and brand information (if available from M3 context-distill):
- Select color scheme (use brand colors if available, otherwise professional defaults from html-patterns)
- Select typography (Google Fonts, clean sans-serif)
- Determine dark/light slide alternation pattern

Present the visual direction to the user for confirmation:
```
Visual Direction:
- Primary color: {color} | Accent: {color}
- Font: {font family}
- Slide pattern: {e.g., "dark cover → light content → dark accent slides"}
- Icon library: Font Awesome 6 + Material Icons Outlined

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
- Add Phosphor, Lucide, or Bootstrap Icons only if specific icons are needed

**Image Handling:**
- All image references use relative paths: `src="images/{descriptive-name}.png"`
- Use descriptive filenames: `slide-02-problem-data.png`, `slide-09-competition-matrix.png`
- Include `alt` attributes describing what the image should show
- Image slots must work gracefully when images are not yet present (use background color fallback with `onerror="this.style.display='none'"`)

**Design Standards (non-negotiable):**
- One focal element per slide with clear hierarchy
- Minimum 15-20% whitespace on every slide
- Title at top stating the slide's POINT (not vague labels — "Companies lose $4.2M/year to manual processes" not "The Problem")
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

### 6. Present Menu

```
✅ Pitch deck generated: {output_folder}/pitch-deck.html
📁 Image folder ready: {output_folder}/images/

Slides: {count} | Type: Investor | Format: HTML → Landscape PDF
```

**Select an Option:**
- **[C] Continue** — proceed to generate image prompts
- **[X] Exit** — exit workflow (HTML is saved, image prompts can be generated later)

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
- Landscape PDF export works via Ctrl+P
- Icons render from CDN
- Image paths use ./images/ convention
- Professional visual design with clear hierarchy
- One idea per slide, glance test passes

❌ **FAILURE:**
- Missing slides from agreed structure
- Slide content diverges from the agreed narrative
- Portrait or broken print layout
- Inline images (not from ./images/ folder)
- Text-heavy slides (walls of text)
- Inconsistent design across slides
- Missing print CSS
