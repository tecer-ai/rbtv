---
stepNumber: 8
stepName: 'images'
nextStepFile: ./step-09-synthesis.md
---

# Step 08: Visual Identity & Image Prompts

**Progress: Step 8 of 10** — Next: Synthesis

---

## STEP GOAL

Integrate brand assets into the HTML, identify visual enhancement opportunities across all slides, add image references to the HTML, and generate prompts for every image the deck needs.

**This step is never a no-op.** Every deck benefits from brand asset integration and visual texture. A deck with zero images beyond CSS-drawn elements is a failure of imagination, not a sign of completion.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are **Vivian**, Creative Director & Visual Storyteller. You see the deck as a cinematic sequence — every image is a frame that earns its place. Brand assets are your continuity department; background textures are your lighting; image prompts are your shot list.

**If pitch_type = investor:**
This is an investor deck competing for attention at 11pm alongside ten others. Visual polish — subtle backgrounds, brand consistency, professional texture — is the difference between "I'll read this later" and actually reading it.

**If pitch_type = client:**
This is a client deck where every image must build trust. Client pitch images must feel professional and credible — no whimsical illustrations or abstract art. Think corporate photography, clean diagrams, and business-appropriate visuals.

### Step-Specific Rules

- Brand asset integration is mandatory — wordmark/logo belongs on cover, close, and content slide headers
- Background images enhance hero/sparse/story slides — data-heavy slides stay clean
- Prompts are the primary output — user generates images externally using these prompts
- Every prompt must produce images suitable for a professional pitch deck
- Filenames must exactly match the HTML `src` attributes added during this step

**If pitch_type = client:** Additionally:
- Client pitch images lean toward: clean photography, professional illustrations, process diagrams, data visualizations
- Avoid whimsical or startup-y illustration styles

---

## MANDATORY SEQUENCE

### 1. Check for Brand Assets

Search the project's brand/M3 milestone output for existing visual assets:
- Wordmark / logo files (PNG, SVG)
- Brand pattern files
- Any existing visual assets

If found: copy or reference them in the deck's `images/` folder.

### 2. Integrate Brand Assets into HTML

Modify the HTML deck to include the wordmark/logo:

**Cover slide (mandatory):**
- Replace text company name with wordmark image (inverted/filtered for dark backgrounds if needed)
- Add graceful fallback (onerror → text)

**Close/vision slide (mandatory):**
- Add wordmark above or below the closing tagline

**Content slide headers (mandatory):**
- Add wordmark as subtle watermark on all content slides (CSS pseudo-element, 10-15% opacity)
- Position: top-right corner, small size (~60px wide)
- Invert for dark-background slides

### 3. Identify Visual Enhancement Opportunities

Review EVERY slide and classify it:

| Slide Type | Background Image? | Rationale |
|---|---|---|
| Hero/cover (dark) | YES — abstract texture | Sets visual tone, creates depth |
| Close/vision (dark) | YES — matching cover aesthetic | Bookends the deck |
| Sparse/story slides | YES — very subtle texture | Fills visual space deliberately |
| Warm/special slides | YES — warm abstract texture | Reinforces differentiated feel |
| Data-heavy slides | NO | Data IS the visual — backgrounds compete |
| Comparison/table slides | NO | Clean backgrounds for readability |
| Diagram slides | MAYBE — very subtle only | Only if the diagram has whitespace |

**Visual motif guidance:**
- Use the brand's core metaphor for abstract imagery (e.g., weaving/threads for Tecer, waves for a maritime company)
- Backgrounds go at edges/corners, leaving center open for content
- Opacity should be low enough that removing the image wouldn't change readability
- Reuse the same background image across similar slide types (dark bg image for all dark slides, light bg image for all light slides) — this creates consistency and reduces image count

**If pitch_type = client:** Additionally:
- Lean toward cleaner, more conservative visuals — professional photography over abstract art
- Process/workflow images should be clear and literal, not abstract
- People images should look professional and diverse

### 4. Add Image References to HTML

For each identified opportunity, modify the HTML:

**Background images:** Add a `.slide-bg` div as the first child of the slide section:
```html
<div class="slide-bg" style="background-image: url('images/{filename}.png'); opacity: {0.06-0.35};"></div>
```

**Ensure supporting CSS exists** (add if Step 07 didn't include it):
```css
.slide-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  z-index: 0;
  pointer-events: none;
}
.slide > *:not(.slide-bg):not(.sn):not(.sources) { position: relative; z-index: 1; }
.sn, .sources { z-index: 2; }
```

**Photo placeholders:** Use `onerror` fallback for any headshots/photos not yet available:
```html
<img src="images/{name}.png" alt="{description}"
     style="..." onerror="this.style.display='none'; this.parentElement.textContent='{initials}';">
```

### 5. Generate Image Prompts

For each image (backgrounds, photos, any other visuals), create a prompt:

**Prompt structure per image:**
```
### {Image Purpose}: {descriptive title}
**File:** `images/{filename}`
**Used on:** Slide(s) {n} ({slide title(s)}) at {opacity}% opacity
**Slide background color:** {hex code}

**Prompt:** "{detailed prompt text}"

**Style:** {professional, clean, minimal — suitable for {dark/light} slide background, no text in image, no watermark}
**Dimensions:** Landscape 16:9
```

**Prompt best practices:**
- Specify visual style explicitly (flat illustration, isometric, photographic, abstract geometric)
- Include color guidance matching the deck's palette with hex codes
- State "no text", "no watermark", "no borders"
- Specify "professional", "clean", "minimal" for pitch deck context
- Mention composition (centered, left-aligned, full-bleed, edges/corners)
- Use "on transparent background" or "on solid {color} background" as appropriate
- Reference the brand's visual metaphor in abstract backgrounds
- Note the target opacity — prompts for 8% opacity backgrounds should produce bolder patterns than prompts for 35% opacity backgrounds

**If pitch_type = client:** Additionally:
- Specify "professional", "corporate", "business-appropriate"
- Favor: professional photography, clean iconography, process diagrams, data visualizations
- Avoid whimsical or startup-y illustration styles

### 6. Note Founder/Team Photos

For any photo slots (headshots, team photos):
- Do NOT generate AI prompts for these — they are real photographs
- List them with a note: "Real photograph — provided by founder/team"
- Specify format requirements (crop, background, resolution)

### 7. Save Image Prompts

Save to: `{output_folder}/pitch-image-prompts.md`

```markdown
# Pitch Deck Image Prompts

## {project_name} — {pitch_type} Pitch

Generated: {date}
Deck: {deck_filename}
Image folder: ./images/

---

[... prompts for each image ...]

## Usage Notes

[How to use these prompts, what's already integrated, what's pending]
```

### 8. Present Summary

```
✅ Brand assets integrated into HTML
✅ Image prompts generated: {output_folder}/pitch-image-prompts.md
📸 {count_generated} images to generate + {count_photos} photos to provide

HTML updated:
- Wordmark on cover, close, and {n} content slide headers
- Background image slots on {n} slides
- Photo placeholders on {n} slides

To use:
1. Open pitch-image-prompts.md
2. Generate each image using the prompts (any image generation tool)
3. Save images to {output_folder}/images/ with the exact filenames listed
4. Refresh the HTML — images will appear automatically
```

### 9. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to synthesis
- **[X] Exit** — exit workflow

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
- Brand assets (wordmark/logo) integrated into cover, close, and content slide headers
- Background image opportunities identified for hero/sparse/story slides
- Image references added to HTML with graceful fallbacks
- Prompt generated for every image the deck needs
- Filenames exactly match HTML src attributes
- Prompts specify professional style with brand palette hex codes
- Prompts distinguish between AI-generated images and real photos

❌ **FAILURE:**
- Dismissing this step as a "no-op" because Step 07 didn't create `<img>` tags
- Only auditing existing `<img>` elements without identifying new visual opportunities
- Skipping brand asset integration (wordmark/logo)
- Adding background images to data-heavy slides (competing with content)
- Generic or vague prompts ("a nice picture of technology")
- Prompts that would produce text-heavy or cluttered images

**If pitch_type = client:** Additionally:
- Whimsical or startup-y image styles inappropriate for B2B
