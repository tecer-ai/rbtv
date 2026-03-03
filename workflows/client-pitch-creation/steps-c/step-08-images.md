---
stepNumber: 8
stepName: 'images'
nextStepFile: ./step-09-synthesis.md
---

# Step 08: Generate Image Prompts

**Progress: Step 8 of 9** — Next: Synthesis

---

## STEP GOAL

Generate Google Nano Banana image prompts for each slide that needs imagery, with filenames exactly matching the HTML references.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Buyer specifying images that build trust and clarity. Client pitch images must feel professional and credible — no whimsical illustrations or abstract art. Think corporate photography, clean diagrams, and business-appropriate visuals.

### Step-Specific Rules

- Each prompt must produce images suitable for a professional B2B pitch
- Filenames must exactly match the HTML `src` attributes
- Prompts should specify style, composition, and what NOT to include
- Images should complement the slide content, not repeat it
- Client pitch images lean toward: clean photography, professional illustrations, process diagrams, data visualizations

---

## MANDATORY SEQUENCE

### 1. Audit HTML for Image Slots

Read the generated `{output_folder}/pitch-deck.html` and identify every `<img>` element:
- Extract `src` attribute (filename)
- Extract `alt` attribute (description)
- Note the slide context (what the image supports)
- Note the slide's background color (dark or light)

### 2. Generate Prompts

For each image, create a prompt optimized for Google Nano Banana:

**Prompt structure per image:**
```
### Slide {n}: {slide_title}
**File:** `images/{filename}`
**Slide background:** {dark/light}

**Prompt:** "{detailed prompt text}"

**Style:** {professional, corporate, clean — suitable for B2B pitch, no text in image, no watermark}
**Dimensions:** Landscape 16:9
```

**Client pitch image best practices:**
- Specify "professional", "corporate", "business-appropriate"
- Include color guidance matching the deck's palette
- State "no text", "no watermark", "no borders"
- Avoid whimsical or startup-y illustration styles
- Favor: professional photography, clean iconography, process diagrams, data visualizations
- Process/workflow images should be clear and literal, not abstract
- People images should look professional and diverse

### 3. Save Image Prompts

Save to: `{output_folder}/pitch-image-prompts.md`

```markdown
# Pitch Deck Image Prompts

## {project_name} — Client Pitch for {target_client}

Generated: {date}
Target: Google Nano Banana
Deck: pitch-deck.html
Image folder: ./images/

---

### Slide {n}: {title}
**File:** `images/{filename}`
**Prompt:** "{prompt text}"
**Style:** {style notes}
**Dimensions:** Landscape 16:9

---

[... repeat for each image ...]
```

### 4. Present Summary

```
✅ Image prompts generated: {output_folder}/pitch-image-prompts.md
📸 {count} images to generate

To use:
1. Open pitch-image-prompts.md
2. Generate each image in Google Nano Banana using the prompts
3. Save images to {output_folder}/images/ with the exact filenames listed
4. Refresh the HTML — images will appear automatically
```

### 5. Present Menu

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
- Prompt generated for every image referenced in the HTML
- Filenames exactly match HTML src attributes
- Prompts specify professional, B2B-appropriate style
- Style notes match the deck's visual direction

❌ **FAILURE:**
- Mismatched filenames
- Startup-y or whimsical image styles for a B2B deck
- Generic prompts
- Missing any image from the HTML
