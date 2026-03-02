---
stepNumber: 5
stepName: 'images'
nextStepFile: ./step-06-synthesis.md
---

# Step 05: Generate Image Prompts

**Progress: Step 5 of 6** — Next: Synthesis

---

## STEP GOAL

Generate Google Nano Banana image prompts for each slide that needs imagery, with filenames exactly matching the HTML references.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are a Pitch Deck Architect specifying images that reinforce your narrative. Every image earns its place — no decorative fluff.

### Step-Specific Rules

- Each prompt must produce images suitable for a professional pitch deck
- Filenames must exactly match the HTML `src` attributes
- Prompts should specify style, composition, and what NOT to include
- Images should complement the slide content, not repeat it

---

## MANDATORY SEQUENCE

### 1. Audit HTML for Image Slots

Read the generated `{output_folder}/pitch-deck.html` and identify every `<img>` element:
- Extract `src` attribute (filename)
- Extract `alt` attribute (description)
- Note the slide context (what the image supports)
- Note the slide's background color (dark or light) — image must work on it

### 2. Generate Prompts

For each image, create a prompt optimized for Google Nano Banana:

**Prompt structure per image:**
```
### Slide {n}: {slide_title}
**File:** `images/{filename}`
**Slide background:** {dark/light}

**Prompt:** "{detailed prompt text}"

**Style:** {professional, clean, minimal — suitable for {dark/light} slide background, no text in image, no watermark}
**Dimensions:** Landscape 16:9
```

**Prompt best practices:**
- Specify visual style explicitly (flat illustration, isometric, photographic, abstract geometric)
- Include color guidance matching the deck's palette (e.g., "using teal (#00d4aa) and navy (#0a1628) tones")
- State "no text", "no watermark", "no borders" when needed
- Specify "professional", "clean", "minimal" for pitch deck context
- Mention composition (centered, left-aligned, full-bleed)
- Use "on transparent background" or "on solid {color} background" when the image sits on a specific slide color
- Avoid overly complex scenes — images should be glanceable like the slides themselves

### 3. Save Image Prompts

Save to: `{output_folder}/pitch-image-prompts.md`

```markdown
# Pitch Deck Image Prompts

## {project_name} — {pitch_type}

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
- Prompts specify professional style suitable for pitch deck
- Style notes match the deck's visual direction and slide backgrounds

❌ **FAILURE:**
- Mismatched filenames between HTML and prompts
- Generic or vague prompts ("a nice picture of technology")
- Missing any image from the HTML
- Prompts that would produce text-heavy or cluttered images
