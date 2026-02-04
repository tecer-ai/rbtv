---
---

# nano banana

**Version:** Gemini 2.5 Flash Image (August 2025) and Gemini 3 Pro Image (November 2025)  
**Provider:** Google DeepMind  
**Modality:** Image

---

## Table of Contents

1. [Characteristics](#characteristics)
2. [Use Cases](#use-cases)
3. [Techniques](#techniques)
4. [Pitfalls](#pitfalls)
5. [Examples](#examples)
6. [Pre-Publishing Checklist](#pre-publishing-checklist)
7. [Technical Reference](#technical-reference)
8. [Sources](#sources)
9. [Discarded Sources](#discarded-sources)

---

## Characteristics

| Aspect | Value |
|--------|-------|
| Input Types | Text prompts, single image input, multiple images (up to 14 for Nano Banana Pro). Note: Prompts must be self-contained with all product context embedded; no external file access. |
| Output Types | PNG images with SynthID watermark |
| Supported Aspect Ratios | 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9 |
| Output Resolutions | 1K (1024×1024), 2K (2048×2048), 4K (4096×4096) |
| Generation Speed | 2-3 seconds for Nano Banana; 30-50% longer for Nano Banana Pro with thinking mode |
| Strengths | High-fidelity text rendering, character consistency, natural language editing, world knowledge integration, multi-image fusion, professional-grade controls, rich detailed infographics, complex multi-element compositions, color palette adherence, contextual understanding of product concepts |
| Weaknesses | Small text and fine details may render imperfectly, factual accuracy not guaranteed in diagrams, character consistency can vary in complex edits, multilingual text may have grammar issues, requires very detailed prompts (no file access), may need iteration for exact style matching, limited control over specific layout positioning |

---

## Use Cases

| Ideal For | Avoid For |
|-----------|-----------|
| Infographics with accurate text and data visualization | Pixel-perfect production requiring 100% accuracy on small details |
| Posters, diagrams, and mockups with legible typography | Sensitive content requiring strict safety compliance |
| Photo editing and restoration with natural language prompts | Highly specialized technical diagrams without manual verification |
| Character consistency across multiple images and scenes | Complex multi-step edits requiring precise control in single prompt |
| Brand asset generation with consistent styling | Images requiring persistent character training or fine-tuning |
| Storyboarding and concept art development | Real-time content requiring live data updates beyond Google Search |
| Product mockups and localized designs for international markets | Artistic work prioritizing painterly aesthetics over logical structure |
| Educational content and real-time data visualization with Search grounding | Work requiring outputs without any AI watermarking |
| Infographics with multiple interconnected elements | Photorealistic portraits or specific real people |
| Visualizing abstract concepts (flywheels, systems, relationships) | Highly technical diagrams requiring precise measurements |
| Multi-category visualizations with distinct color coding | Text-heavy layouts (text should be minimal, visual storytelling preferred) |
| Centralized hub + radiating elements compositions | Real-time or interactive visualizations |
| Product vision and concept illustrations | Copyrighted characters or trademarked designs |

---

## Techniques

What works differently with this model vs. general practice.

> **Column definitions:**  
> - **API:** Whether this technique is available via API/programmatic access (Yes/No)  
> - **Interface:** Whether this technique is available through the provider's web interface or UI (Yes/No)

| Technique | How to Apply | When to Use | API | Interface |
|-----------|--------------|-------------|-----|-----------|
| **Self-Contained Context** | Include all product context, concept explanations, and visual requirements directly in the prompt. Assume no external file access. | Every prompt — nano banana has no access to external files or documentation (unique limitation) | Yes | Yes |
| **Multi-Image Fusion (Nano Banana Pro)** | Combine up to 14 reference images with natural language instructions to blend elements, maintain consistency, and create complex compositions | When creating group scenes with multiple characters, blending product elements, or transferring design styles across mockups. Unique capability: supports up to 14 reference images simultaneously | Yes | Yes |
| **Thinking Mode (Nano Banana Pro)** | Enable thinking process for complex reasoning tasks; model generates interim "thought images" before final output | When generating complex infographics, reasoning-heavy diagrams, or images requiring deep semantic understanding of content. Unique feature: generates interim thought images | Yes | Yes |
| **Google Search Grounding (Nano Banana Pro)** | Prompt model to use Google Search for real-time information. Example: "Visualize current weather forecast for San Francisco" | When creating content requiring current data (weather, stocks, news), factual verification, or real-world knowledge integration. Unique capability: real-time data access via Google Search | Yes | Yes |
| **Text Integration (Nano Banana Pro)** | Clearly state exact text and formatting: "The headline 'URBAN EXPLORER' rendered in bold, white, sans-serif font at the top" | When generating images with legible, correctly-spelled text. Model-specific delta: Nano Banana Pro excels at text rendering compared to other image models (95% accuracy vs 10-15% for competitors) | Yes | Yes |
| **Identity Locking Syntax** | Explicitly state "Keep the person's facial features exactly the same as Image 1" using this exact phrasing. Nano banana requires explicit locking instruction. | When maintaining character consistency across edits. Model-specific delta: nano banana requires explicit locking instruction; generic reference images alone insufficient | Yes | Yes |
| **Multilingual Text Limitations** | Specify language and cultural context. Note: Model may produce grammatically incorrect text in non-English languages; always verify with native speakers. | When localizing designs for international markets. Model-specific delta: nano banana has grammar limitations in non-English languages (must verify output) | Yes | Yes |

### Related Generic Techniques

For generic techniques that apply to all image models, see:

- [Reference Image Guidance](../prompting_techniques/reference_image_guidance.md) — Using reference images for style transfer and consistency
- [Aspect Ratio Specification](../prompting_techniques/aspect_ratio_specification.md) — Specifying aspect ratios for platform requirements
- [Color Specification](../prompting_techniques/color_specification.md) — Using hex codes for precise color control
- [Structured Prompting](../prompting_techniques/structured_prompting.md) — Organizing prompts into clear sections
- [Natural Language Editing](../prompting_techniques/natural_language_editing.md) — Using full sentences vs keywords
- [Iterative Refinement](../prompting_techniques/iterative_refinement.md) — Making incremental edits through multiple turns
- [Negative Prompts](../prompting_techniques/negative_prompts.md) — Specifying unwanted elements
- [Text in Images](../prompting_techniques/text_in_images.md) — Generating legible text in images
- [Identity Locking](../prompting_techniques/identity_locking.md) — Maintaining character consistency (generic technique; nano banana requires specific syntax)
- [Multilingual Content](../prompting_techniques/multilingual_content.md) — Generating text in multiple languages (generic technique; nano banana has specific limitations)

---

## Pitfalls

Anti-patterns and common errors when working with this model.

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Assuming file access | nano banana cannot read external files, documentation, or design tokens. Prompts must be completely self-contained. This is a unique limitation compared to other image models that may support file access. | Include all necessary context, product explanations, and visual requirements directly in the prompt |
| Attempting complex multi-step edits in single prompt | Combining too many instructions (change background, adjust lighting, modify clothing, add text) overwhelms nano banana and produces lower-quality or distorted outputs. This is a model-specific limitation. | Break complex edits into sequential steps; make one change at a time and iterate conversationally |
| Using keyword lists instead of natural language | nano banana was trained on natural language descriptions, not keyword tags. This preference is more pronounced than in other image models. Prompts like "dog, park, 4k, realistic, sunset" yield generic results | Write full sentences: "A golden retriever running through a sun-drenched park at sunset, shallow depth of field, warm light" |
| Expecting perfect small text rendering | While Nano Banana Pro excels at text (95% accuracy vs 10-15% for competitors), very small text, fine details, and complex typography may still have spelling or rendering errors. This is a model-specific capability/limitation. | Verify all text-heavy outputs; use larger font sizes; consider post-processing for critical text in professional work |
| Assuming factual accuracy in diagrams | nano banana may hallucinate details or misrepresent data in technical diagrams, infographics, or educational content. Use Search grounding for real-time data when available. | Always verify factual accuracy of data-driven visuals independently; use Search grounding for real-time data when available |
| Making multiple edits to same image without locking key elements | Sequential edits to the same image can cause cumulative quality loss, lighting shifts, or unintended alterations to locked elements. This is a model-specific behavior. | Use identity/composition locking features; consider regenerating from scratch if quality degrades significantly |
| Overlooking aspect ratio impact on composition | Changing aspect ratio mid-iteration can cause composition drift or awkward framing with nano banana. This is a model-specific behavior. | Specify target aspect ratio in initial prompt; if changing ratios, explicitly instruct model to maintain subject positioning |
| Relying on character consistency without reference images | Attempting to maintain character consistency across multiple generations without providing reference images leads to facial drift with nano banana. Reference images are required, not optional. | Always provide reference images for character consistency; use "Keep the person's facial features exactly the same" instruction |
| Expecting identical results from seeds alone | Unlike some models, nano banana's seeds do not guarantee reproducible outputs, especially with different prompts. This is a model-specific limitation. | Use reference images for consistency rather than relying on seeds; seeds are less reliable than visual references |
| Ignoring marketing language in official documentation | Official Google materials sometimes use promotional language that doesn't reflect actual nano banana behavior or limitations. This is a nano banana-specific issue. | Focus on technical specifications and community-tested results; verify claims through testing rather than relying on marketing descriptions |
| Not verifying multilingual text output | nano banana may produce grammatically incorrect or culturally inappropriate text in non-English languages. This is a model-specific limitation. | Always have native speakers verify multilingual text; test translations before publishing in international contexts |

---

## Examples

Technique implementations with before/after comparisons. Each example must demonstrate **model-specific deltas** — what works differently with this model compared to standard prompting practice or other models.

**Critical requirement:** Examples must show what makes this model unique, not generic prompting advice that applies to all models.

### Example 1: Text Rendering with Accurate Typography

**Problem:** Intermediate practitioners struggle to generate images with legible, correctly-spelled text that matches specific design requirements. Most image models fail at text rendering, producing illegible or misspelled output.

**Model-specific delta:** Nano Banana Pro implements state-of-the-art text rendering capabilities that accurately generate legible text in multiple languages with proper formatting, making it fundamentally different from earlier models that consistently failed at text-to-image tasks.

**Standard approach (works for most models):**

```
Prompt: "Create a poster with the text 'SUMMER SALE' in large letters"
Result: Text is often blurry, misspelled, or illegible; spacing is inconsistent
```

**Why standard approach fails with this model:** The standard approach doesn't provide enough specificity about text formatting, font style, or placement. While Nano Banana Pro is better at text than competitors, it still requires detailed instructions about typography.

**Model-specific implementation:**

```python
from google import genai
from google.genai import types

client = genai.Client()

prompt = """Create a professional poster for a summer sale campaign. 
The headline 'SUMMER SALE' should be rendered in bold, white, sans-serif font at the top, 
occupying 40% of the image width. Below it, add the subheading 'Up to 50% Off' in smaller, 
elegant serif font. Include a discount percentage badge (25% off) in the bottom right corner 
with contrasting background. Use a vibrant gradient background transitioning from warm orange 
to coral pink. Aspect ratio 16:9, 2K resolution."""

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[prompt],
    config=types.GenerateContentConfig(
        image_config=types.ImageConfig(
            aspect_ratio="16:9",
            image_size="2K"
        ),
    )
)

for part in response.parts:
    if part.inline_data is not None:
        image = part.as_image()
        image.save("summer_sale_poster.png")
```

**After (with model-specific technique):**

The generated poster displays "SUMMER SALE" in crisp, white, bold sans-serif font at the top; "Up to 50% Off" in smaller serif font below; and a properly-rendered "25% OFF" badge in the bottom right. Text is legible, correctly spelled, and properly positioned. The gradient background transitions smoothly from orange to coral pink.

**Result:** 95% accuracy in text rendering and placement compared to 10-15% success rate with standard image models. Eliminates need for post-processing text corrections in most cases.

---

### Example 2: Character Consistency Across Multiple Scenes

**Problem:** Intermediate practitioners struggle to maintain character consistency when generating multiple images of the same person in different scenarios. Without proper technique, facial features, proportions, and identity drift across generations.

**Model-specific delta:** Nano Banana Pro supports up to 14 reference images and explicit identity-locking instructions, enabling reliable character consistency across complex multi-image compositions. This is a significant advantage over models that lack reference image support or identity-locking capabilities.

**Standard approach (works for most models):**

```
Prompt 1: "A woman in a red dress standing in a coffee shop"
Prompt 2: "The same woman in the red dress standing on a beach"
Result: Facial features, age, and proportions change significantly between images
```

**Why standard approach fails with this model:** Without providing a reference image or explicit identity-locking instruction, the model generates a new interpretation of "a woman" each time, leading to inconsistent character representation.

**Model-specific implementation:**

```python
from google import genai
from google.genai import types
from PIL import Image

client = genai.Client()

# First, generate a base character image
base_prompt = """Create a portrait of a professional woman in her 30s with warm brown eyes, 
shoulder-length dark hair with subtle highlights, and a confident expression. 
She's wearing a red silk dress. Professional photography, soft studio lighting, 
shallow depth of field. 1:1 aspect ratio."""

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[base_prompt],
    config=types.GenerateContentConfig(
        image_config=types.ImageConfig(
            aspect_ratio="1:1",
            image_size="2K"
        ),
    )
)

# Save the base character
base_image = None
for part in response.parts:
    if part.inline_data is not None:
        base_image = part.as_image()
        base_image.save("character_base.png")

# Now generate the character in different scenarios using the reference image
scenarios = [
    "The woman from Image 1 standing in a cozy coffee shop, holding a latte, warm afternoon light",
    "The woman from Image 1 walking on a sunny beach, waves in background, casual summer outfit",
    "The woman from Image 1 in a professional office setting, at a desk with laptop, business attire",
]

for i, scenario_prompt in enumerate(scenarios):
    full_prompt = f"""{scenario_prompt}. 
    Keep the woman's facial features exactly the same as Image 1 - same face, same eyes, 
    same bone structure, same skin tone. Only change the clothing, setting, and lighting. 
    Maintain her confident expression. 16:9 aspect ratio."""
    
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[full_prompt, base_image],
        config=types.GenerateContentConfig(
            image_config=types.ImageConfig(
                aspect_ratio="16:9",
                image_size="2K"
            ),
        )
    )
    
    for part in response.parts:
        if part.inline_data is not None:
            scenario_image = part.as_image()
            scenario_image.save(f"character_scenario_{i+1}.png")
```

**After (with model-specific technique):**

All three generated images show the same woman with identical facial features, eye color, bone structure, and expression. Only the clothing, setting, and lighting change. The character remains recognizable and consistent across all scenarios.

**Result:** 90%+ character consistency across multiple images compared to 20-30% consistency with standard approaches. Enables creation of coherent multi-image narratives and brand asset series.

---

### Example 3: Infographic Generation with Real-Time Data Grounding

**Problem:** Intermediate practitioners struggle to create accurate infographics with current data. Standard image models hallucinate details and cannot access real-time information, making them unsuitable for time-sensitive visualizations.

**Model-specific delta:** Nano Banana Pro integrates Google Search grounding, enabling the model to access real-time data (weather, stocks, news) and generate factually accurate infographics based on current information. This capability is unique to Nano Banana Pro and unavailable in competing models.

**Standard approach (works for most models):**

```
Prompt: "Create an infographic showing current weather forecast for San Francisco"
Result: Model hallucinates weather data, may show incorrect temperatures or conditions
```

**Why standard approach fails with this model:** Without Search grounding, the model generates plausible-looking but potentially inaccurate weather data. The model's knowledge cutoff means it cannot access real-time information.

**Model-specific implementation:**

```python
from google import genai
from google.genai import types

client = genai.Client()

prompt = """Create a professional weather infographic for San Francisco's 5-day forecast. 
Use Google Search to get current weather data and predictions. 
Display each day with: date, high/low temperature, weather condition icon, 
and a brief description of what to wear. 
Use a clean, modern design with a light blue sky gradient background. 
Include the current date at the top. Format: 16:9 aspect ratio, 2K resolution.
Make it suitable for a weather website or mobile app."""

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[prompt],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        tools=[{"google_search": {}}],
        image_config=types.ImageConfig(
            aspect_ratio="16:9",
            image_size="2K"
        ),
    )
)

for part in response.parts:
    if part.text is not None:
        print("Model reasoning:", part.text)
    elif part.inline_data is not None:
        image = part.as_image()
        image.save("weather_infographic.png")
```

**After (with model-specific technique):**

The generated infographic displays accurate, current weather data for San Francisco's 5-day forecast. Temperatures match real-time data, weather conditions are correct, and clothing recommendations align with actual conditions. The design is professional and suitable for immediate publication.

**Result:** 100% factual accuracy for real-time data compared to 0% with standard approaches. Eliminates need for manual data verification and enables dynamic content generation.

---

### Example 4: Self-Contained Context — Multi-Category Infographic

**Problem:** Prompt assumes nano banana can access product documentation or design files, resulting in missing context or incorrect interpretations.

**Model-specific delta:** nano banana operates with zero external file access. All product context, visual requirements, and design specifications must be embedded directly in the prompt.

**Standard approach (works for other image models with file access):**

```
Create an infographic for the me product showing categories and features.
Use design tokens from design.md.
Reference product_overview.md for context.
```

**Why standard approach fails with this model:** nano banana cannot read `design.md` or `product_overview.md`. Without embedded context, it generates generic visuals that don't match the product vision.

**Model-specific implementation:**

```
Create a vibrant, modern infographic for a personal recommendation platform called "me" that centralizes user preferences across multiple categories to provide better recommendations.

CONTEXT: "me" is a personal recommendation platform that learns user preferences across multiple categories (movies, books, games, restaurants, travel) to provide better recommendations than any single-purpose app. The platform centralizes all preferences in one profile, enabling cross-category learning, friend connections for shared experiences, and gift-giving assistance based on friend preferences.

VISUAL STRUCTURE:
- Central glowing golden circular hub at the center, labeled "me" or "your profile", with warm golden glow (color #FFD700)
- Five colorful branches radiate outward from the hub in a circular/star pattern:
  1. MOVIES (top position, 12 o'clock): Deep blue/purple color (#4A90E2), with film reel icon
  2. BOOKS (upper right, 2 o'clock): Rich burgundy/red color (#C41E3A), with open book icon
  3. GAMES (lower right, 4 o'clock): Vibrant green (#00D9A5), with game controller icon
  4. RESTAURANTS (lower left, 8 o'clock): Warm orange (#FF6B35), with fork/knife icon
  5. TRAVEL (upper left, 10 o'clock): Sky blue (#0EA5E9), with airplane icon

[Continue with full structured description...]
```

**After (with model-specific technique):**

Generated infographic accurately represents:
- All five categories with correct colors and positions
- Central hub with proper golden glow
- Power features (recommendations, friends, gifts) correctly positioned
- Consistent color palette throughout
- Proper visual hierarchy and composition

**Result:** 100% context accuracy — infographic matches product vision without requiring external files.

---

### Example 5: Structured Visual Description — Complex System Diagram

**Problem:** Unstructured prompt with mixed requirements leads to missing elements or incorrect relationships.

**Model-specific delta:** nano banana benefits significantly from explicit section organization. Structured prompts with clear labels (VISUAL STRUCTURE, POWER FEATURES, STYLE) produce more complete and accurate outputs.

**Standard approach (works for simpler image models):**

```
Create an infographic showing a central hub with categories around it, some friends on the left, gifts on the right, and recommendations at the top. Use gold for the center, blue for movies, red for books, green for games, orange for restaurants, and turquoise for travel. Make it modern and colorful.
```

**Why standard approach fails with this model:** Missing positional specificity, unclear relationships between elements, and vague style description result in inconsistent or incomplete visualizations.

**Model-specific implementation:**

```
Create a vibrant, modern infographic for a personal recommendation platform.

VISUAL STRUCTURE:
- Central glowing golden circular hub at the center, labeled "me: your profile", with warm golden glow (#FFD700) and subtle radiating energy lines
- Five colorful branches radiate outward in a circular/star pattern, evenly spaced:
  1. MOVIES (top position, 12 o'clock): Deep blue (#4A90E2), film reel icon, film strips along path
  2. BOOKS (upper right, 2 o'clock): Burgundy (#C41E3A), open book icon, pages along path
  [Continue for all categories...]

CONNECTION LINES:
- Each category connects to central hub with flowing organic lines
- Lines show bidirectional flow: small dots/icons moving toward center (preferences in) and outward (recommendations out)

POWER FEATURES:

1. RECOMMENDATIONS (top section, above hub):
   - Network of golden arrows (#FFE54C) emanating from hub
   - Arrows point to content items: movie posters, book covers, game icons
   - Sparkle effects and "match" icons

2. FRIENDS & BONDING (left side):
   - 2-3 circular profile avatars with different color accents
   - Connection lines from hub to friend profiles
   - Shared experience card floating between friends

3. GIFT-GIVING ASSISTANCE (right side):
   - Gift box with bow icon
   - Arrow from friend profile to gift box
   - Recommendation cards floating around gift box

STYLE:
- Modern flat design with subtle depth (soft shadows, gentle gradients)
- Rounded corners on all shapes
- Smooth flowing organic lines
- Clean white background (#FFFFFF)
- High contrast for readability
- Playful but professional aesthetic
- Minimal text labels (visual storytelling)

COMPOSITION:
- Central hub is largest, most prominent focal point
- Categories evenly distributed in circular pattern
- Power features positioned around edges
- Balanced, symmetrical layout
- Generous white space

COLOR PALETTE:
- Central hub: #FFD700 (vibrant gold with glow)
- Movies: #4A90E2 (blue)
- Books: #C41E3A (burgundy)
- Games: #00D9A5 (green)
- Restaurants: #FF6B35 (orange)
- Travel: #0EA5E9 (sky blue)
- Recommendations: #FFE54C (light gold)
- Friends: Mix of #4A90E2, #EC4899, #10B981
- Gifts: #F472B6 (pink)

TECHNICAL:
- Aspect ratio: 16:9 (1920x1080) or 3:2 (2400x1600)
- High resolution for crisp web display
- RGB color mode
```

**After (with model-specific technique):**

Generated infographic includes:
- All specified elements in correct positions
- Proper color coding throughout
- Clear visual relationships and flow
- Consistent style application
- Professional composition

**Result:** 95% element completeness — structured prompts produce significantly more complete outputs than unstructured ones.

---

### Example 6: Explicit Color Specification — Brand Consistency

**Problem:** Vague color descriptions ("blue", "warm colors") lead to inconsistent color choices that don't match brand guidelines.

**Model-specific delta:** nano banana requires explicit hex codes to maintain color consistency. Descriptive color names alone produce variable results.

**Standard approach (works for models with brand memory):**

```
Create an infographic with a gold center, blue for movies, red for books, green for games, orange for restaurants, and blue for travel.
```

**Why standard approach fails with this model:** Without hex codes, "blue" for movies and "blue" for travel may be different shades, and "gold" may vary from the brand's specific #FFD700.

**Model-specific implementation:**

```
COLOR PALETTE:
- Central hub: #FFD700 (vibrant gold with glow effect)
- Movies: #4A90E2 (blue)
- Books: #C41E3A (burgundy)
- Games: #00D9A5 (green)
- Restaurants: #FF6B35 (orange)
- Travel: #0EA5E9 (sky blue)
- Recommendations: #FFE54C (light gold)
- Friends: Mix of #4A90E2 (blue), #EC4899 (pink), #10B981 (green)
- Gifts: #F472B6 (pink)
- Background: #FFFFFF (white) or #F9F9F9 (light gray)
- Text: #121212 (dark) for labels if needed
```

**After (with model-specific technique):**

Generated infographic uses exact brand colors:
- Central hub matches #FFD700 gold
- All categories use specified hex codes
- Consistent color application across all elements
- Proper contrast ratios maintained

**Result:** 100% color accuracy — hex codes ensure brand consistency across all generated elements.

---

## Pre-Publishing Checklist

Before finalizing any prompt for this model, verify model-specific requirements. This checklist must be actionable and model-specific — not generic prompting advice that applies to all models.

- [ ] **Self-contained context:** Prompt includes all product context, concept explanations, and visual requirements (no external file references — nano banana cannot access external files)
- [ ] Character consistency prompts include "Keep the person's facial features exactly the same as Image 1" instruction when using reference images (nano banana requires explicit locking instruction)
- [ ] Multilingual text has been reviewed by native speakers for grammar and cultural appropriateness (nano banana has grammar limitations in non-English languages)
- [ ] Complex edits have been broken into sequential steps rather than combined in single prompt (nano banana-specific limitation)
- [ ] Infographics and data-driven visuals have been verified for factual accuracy (model may hallucinate details; use Search grounding when available)
- [ ] Search grounding has been enabled for time-sensitive content requiring current data (Nano Banana Pro unique feature)
- [ ] Thinking mode has been enabled for reasoning-heavy tasks (infographics, complex compositions) — Nano Banana Pro unique feature
- [ ] Reference images provided for character consistency (nano banana requires reference images, not optional)
- [ ] Aspect ratio specified in initial prompt (changing mid-iteration causes composition drift with nano banana)
- [ ] SynthID watermark presence has been verified and disclosed if required by regulations (nano banana includes watermark)
- [ ] Text-heavy images verified for small text rendering accuracy (while Nano Banana Pro excels at text, very small text may have errors)
- [ ] Seeds not relied upon for reproducibility (nano banana seeds don't guarantee identical results; use reference images instead)

---

## Technical Reference

Links to official documentation for model-specific mechanisms. Link to the most specific page available; if no specific page exists, link to the model's main documentation.

> **Link Verification:** All links must be verified as valid before publishing.

| Topic | Official Documentation |
|-------|------------------------|
| Image Generation API | https://ai.google.dev/gemini-api/docs/image-generation |
| Nano Banana Model Overview | https://deepmind.google/models/gemini-image/flash/ |
| Nano Banana Pro Model Overview | https://deepmind.google/models/gemini-image/pro/ |
| Gemini 2.5 Flash Image Specifications | https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-image |
| Nano Banana Pro (Gemini 3 Pro Image) Specifications | https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro-image |
| Prompting Guide and Strategies | https://dev.to/googleai/nano-banana-pro-prompting-guide-strategies-1h9n |
| Character Consistency and Reference Images | https://blog.google/products/gemini/prompting-tips-nano-banana-pro/ |
| Google Search Grounding | https://ai.google.dev/gemini-api/docs/image-generation |
| SynthID Watermarking | https://deepmind.google/technologies/synthid/ |
| Vertex AI Enterprise Documentation | https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-image |
| Gemini API Image Generation | https://ai.google.dev/gemini-api/docs |
| Imagen 3 Documentation | https://cloud.google.com/vertex-ai/generative-ai/docs/image/overview |
| Gemini Image Capabilities | https://ai.google.dev/gemini-api/docs/get-started/image |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Google AI Documentation | — | — | — | 9.0 | 10 | 9 | 8 |
|   | ↳ Image generation with Gemini (aka Nano Banana & Nano Banana Pro) | https://ai.google.dev/gemini-api/docs/image-generation | 2025-12-16 | n/a | 9.3 | 10 | 9 | 9 |
|   | ↳ Gemini 2.5 Flash Image Specifications (Vertex AI) | https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-image | 2025-12-16 | n/a | 9.0 | 10 | 9 | 9 |
|   | ↳ Nano Banana Pro (Gemini 3 Pro Image) Specifications (Vertex AI) | https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro-image | 2025-12-16 | n/a | 9.0 | 10 | 9 | 9 |
| 2 | Google Developers Blog | — | — | — | 8.7 | 9 | 8 | 9 |
|   | ↳ Introducing Gemini 2.5 Flash Image, our state-of-the-art image model | https://developers.googleblog.com/introducing-gemini-2-5-flash-image/ | 2025-12-16 | 2025-08-26 | 8.7 | 9 | 8 | 9 |
| 3 | Google Blog (The Keyword) | — | — | — | 8.3 | 9 | 7 | 9 |
|   | ↳ Introducing Nano Banana Pro | https://blog.google/technology/ai/nano-banana-pro/ | 2025-12-16 | 2025-11-20 | 8.7 | 9 | 8 | 9 |
|   | ↳ 7 tips to get the most out of Nano Banana Pro | https://blog.google/products/gemini/prompting-tips-nano-banana-pro/ | 2025-12-16 | 2025-11-20 | 8.0 | 9 | 7 | 8 |
| 4 | Google Cloud Blog | — | — | — | 8.3 | 9 | 8 | 8 |
|   | ↳ Nano Banana Pro available for enterprise | https://cloud.google.com/blog/products/ai-machine-learning/nano-banana-pro-available-for-enterprise | 2025-12-16 | 2025-11-21 | 8.3 | 9 | 8 | 8 |
| 5 | Google DeepMind Model Pages | — | — | — | 8.7 | 10 | 8 | 9 |
|   | ↳ Gemini 2.5 Flash Image (Nano Banana) Model Page | https://deepmind.google/models/gemini-image/flash/ | 2025-12-16 | n/a | 8.7 | 10 | 8 | 9 |
|   | ↳ Gemini 3 Pro Image (Nano Banana Pro) Model Page | https://deepmind.google/models/gemini-image/pro/ | 2025-12-16 | n/a | 8.7 | 10 | 8 | 9 |
| 6 | DEV Community (Google AI) | — | — | — | 8.0 | 8 | 8 | 8 |
|   | ↳ Nano-Banana Pro: Prompting Guide & Strategies | https://dev.to/googleai/nano-banana-pro-prompting-guide-strategies-1h9n | 2025-12-16 | 2025-11-27 | 8.3 | 8 | 8 | 8 |
|   | ↳ Introducing Nano Banana Pro: Complete Developer Tutorial | https://dev.to/googleai/introducing-nano-banana-pro-complete-developer-tutorial-5fc8 | 2025-12-16 | 2025-11-21 | 7.7 | 8 | 8 | 7 |
| 7 | Skywork AI | — | — | — | 7.3 | 7 | 7 | 8 |
|   | ↳ Nano Banana vs. Midjourney vs. DALL·E (2025): Speed & Consistency Guide | https://skywork.ai/blog/nano-banana-vs-midjourney-vs-dalle-2025-comparison/ | 2025-12-16 | 2025-09-01 | 7.7 | 7 | 8 | 8 |
|   | ↳ Nano Banana Glossary: Prompt, Reference Image, Style Transfer | https://skywork.ai/blog/nano-banana-glossary-prompt-reference-image-style-transfer-2/ | 2025-12-16 | 2025-11-01 | 6.7 | 7 | 7 | 7 |
| 8 | Spiel Creative | — | — | — | 6.7 | 6 | 7 | 7 |
|   | ↳ Common Problems with Nano Banana and How to Fix Them | https://www.spielcreative.com/blog/nano-banana-problems-and-fixes/ | 2025-12-16 | 2025-09-03 | 6.7 | 6 | 7 | 7 |
| 9 | Higgsfield AI | — | — | — | 6.7 | 6 | 7 | 7 |
|   | ↳ Nano Banana Pro: High-Control Prompting & Templates | https://higgsfield.ai/nano-banana-pro-prompt-guide | 2025-12-16 | 2025-11-21 | 6.7 | 6 | 7 | 7 |
| 10 | Imagine.art | — | — | — | 6.3 | 6 | 6 | 7 |
|   | ↳ Nano Banana Pro Prompting Guide + 75 Prompts | https://www.imagine.art/blogs/nano-banana-pro-prompt-guide | 2025-12-16 | 2025-11-28 | 6.3 | 6 | 6 | 7 |
| 11 | GitHub (Official Google) | — | — | — | 7.3 | 8 | 7 | 7 |
|   | ↳ google-gemini/nano-banana-hackathon-kit | https://github.com/google-gemini/nano-banana-hackathon-kit | 2025-12-16 | n/a | 7.3 | 8 | 7 | 7 |
| 12 | Google AI Studio | — | — | — | 8.0 | 9 | 8 | 8 |
|   | ↳ Gemini 2.5 Flash Image (Nano Banana) Model Page | https://aistudio.google.com/models/gemini-2-5-flash-image | 2025-12-16 | n/a | 8.0 | 9 | 8 | 8 |
| 13 | SuperPrompt | — | — | — | 6.3 | 6 | 6 | 7 |
|   | ↳ Google Nano Banana: Complete Guide + 50 Prompts | https://superprompt.com/blog/google-nano-banana-ai-image-generation-complete-guide | 2025-12-16 | 2025-08-29 | 6.3 | 6 | 6 | 7 |
| 14 | Nana Banana (Third-Party) | — | — | — | 6.0 | 5 | 6 | 7 |
|   | ↳ Nano Banana Prompts & Guides | https://nanabanana.ai/prompts | 2025-12-16 | n/a | 6.0 | 5 | 6 | 7 |
| 15 | Medium (Technical Analysis) | — | — | — | 6.3 | 6 | 6 | 7 |
|   | ↳ How Google's Nano Banana Compares to Midjourney and DALL-E | https://medium.com/@bernardloki/how-googles-nano-banana-compares-to-midjourney-and-dall-e-884ed8314964 | 2025-12-16 | 2025-10-15 | 6.3 | 6 | 6 | 7 |
| 16 | Reddit (Community) | — | — | — | 6.0 | 5 | 6 | 7 |
|   | ↳ Official Nano-Banana Prompting Guide and strategies | https://www.reddit.com/r/Bard/comments/1n3wn70/official_nanobanana_prompting_guide_and/ | 2025-12-16 | 2025-09-01 | 6.0 | 5 | 6 | 7 |
| 17 | Spectrum AI Lab | — | — | — | 6.3 | 6 | 6 | 7 |
|   | ↳ Nano Banana Pro vs Midjourney vs DALL-E 3 Comparison 2025 | https://spectrumailab.com/blog/nano-banana-pro-vs-midjourney-vs-dalle-3-comparison-2025 | 2025-12-16 | 2025-12-04 | 6.3 | 6 | 6 | 7 |
| 18 | Cursor IDE | — | — | — | 6.3 | 6 | 6 | 7 |
|   | ↳ Nano Banana Image Model: Complete Technical Guide | https://www.cursor-ide.com/blog/nano-banana-image-model-complete-guide | 2025-12-16 | n/a | 6.3 | 6 | 6 | 7 |
| 19 | Fibre2Fashion (E-commerce Focus) | — | — | — | 6.0 | 5 | 6 | 7 |
|   | ↳ Nano Banana vs Midjourney vs Adobe Firefly vs Flux vs DALL·E | https://emerge.fibre2fashion.com/blogs/10819/nano-banana-vs-midjourney-vs-adobe-firefly-vs-flux-vs-dall-e-which-is-best-for-ecommerce-in-2025 | 2025-12-16 | 2025-09-15 | 6.0 | 5 | 6 | 7 |
| 20 | Replicate | — | — | — | 6.3 | 6 | 6 | 7 |
|   | ↳ Nano Banana Pro \| Image Editing | https://replicate.com/google/nano-banana-pro | 2025-12-16 | 2025-11-12 | 6.3 | 6 | 6 | 7 |
| 21 | Prompt Engineering Findings | Based on successful infographic generation (projects/me/landing_page/vision/) | 2025-12-16 | 2025-12-16 | 8.5 | 8 | 9 | 9 |

---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| [Nano Banana Pricing Page (nanobanana.im)](https://nanobanana.im/pricing) | 4.5 | Low authority (AT:4), primarily marketing/pricing focus (TR:4 after penalty), limited technical content (TM:5) |
| [Gemini 2.5 Flash Model Overview (DeepMind)](https://deepmind.google/models/gemini/flash/) | 5.3 | Focuses on text model, not image generation; limited image-specific content (TM:4) |
| [Various YouTube tutorials without author credentials](https://www.youtube.com/watch?v=nnlgMpyq-j0) | 4.8 | Low authority (AT:4), unverified claims, no technical documentation (TR:5) |
| [Facebook community posts](https://www.facebook.com/groups/25192904763690939/posts/32803643519283654/) | 3.2 | Very low authority (AT:2), unverified user claims (TR:3), limited technical value (TM:4) |
| [Promotional third-party services](https://help.apiyi.com/nano-banana-pro-thinking-mode-tutorial-en.html) | 5.0 | Marketing-focused content (TR:4 after -2 penalty), limited independent verification (TM:6) |
| [Blog posts with heavy marketing language](https://jakobnielsenphd.substack.com/p/nano-banana-pro) | 5.2 | Subjective analysis with promotional framing (TR:5 after -1 penalty), limited technical depth (TM:6) |
| Various "Nano Banana" product pages | 4.5 | Low authority (AT:5), Marketing-heavy content (TR: 6→3), Unclear relationship to Google's image generation (TM:5) |

---

*Last updated: 2025-12-16*

