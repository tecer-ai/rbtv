---
---

# Image Prompt Structure

**Problem Type:** Knowledge Injection | Task Decomposition


---

## Table of Contents

1. [Problem Solved](#problem-solved)
2. [Technique Overview](#technique-overview)
3. [When to Apply](#when-to-apply)
4. [Application Pattern](#application-pattern)
5. [Variations](#variations)
6. [Pitfalls](#pitfalls)
7. [Examples](#examples)
8. [Quality Checklist](#quality-checklist)
9. [Technical Reference](#technical-reference)
10. [Sources](#sources)
11. [Discarded Sources](#discarded-sources)

---

## Problem Solved

How do you structure image generation prompts to ensure all critical visual elements (subject, environment, lighting, style, composition) are systematically covered?

---

## Technique Overview

Organize visual elements systematically: Subject + Action/Pose + Environment + Lighting + Style/Technique + Composition + Specific Details. This structure prevents omission of critical elements and enables precise control over output.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Commercial-quality image generation requiring complete art direction | Quick sketches or experimental generations where speed > precision |
| Professional photography simulation, product shots, portraits | Abstract or minimalist art where structure constrains creativity |
| Concept art, illustrations, marketing visuals needing specific aesthetic control | Iterative refinement workflows where structure emerges through conversation |
| Scenarios where first-generation quality matters (no iteration budget) | Simple, single-subject images where full structure is overkill |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | **Define Subject** | Specify main subject with appearance, age, pose, action, expression. Include clothing, accessories, physical characteristics |
| 2 | **Set Environment** | Describe location, setting, background elements. Include time period, architectural style, natural features, atmospheric conditions |
| 3 | **Specify Lighting** | Define lighting type (natural, studio, ambient), direction, quality (soft, harsh, dramatic), time of day, color temperature |
| 4 | **Choose Style/Technique** | Select artistic style (photorealistic, illustration, painting), reference artists/movements, media (oil, digital, photography), era |
| 5 | **Define Composition** | Specify framing (close-up, wide shot), angle (eye-level, bird's-eye), rule of thirds, perspective, focal point, depth of field |
| 6 | **Add Specific Details** | Include color palette, mood, atmosphere, texture, quality specifications (resolution, sharpness), technical camera settings if relevant |
| 7 | **Verify Consistency** | Check for internal contradictions (e.g., "soft and dramatic lighting" - choose one). Ensure all elements work together harmoniously |

**Key Considerations:**
- **Length management:** Keep to 7-10 key visual elements. Overly long prompts (300+ words) dilute important elements
- **Precision over verbosity:** Use precise technical language rather than long descriptions
- **Internal consistency:** Avoid conflicting requests (e.g., "minimalist with ornate details" - choose one approach)

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| **Minimal Structure** | Quick iterations, simple subjects | Subject + Style + Composition only (3 elements) |
| **Extended Structure** | Complex scenes with multiple subjects | Add: Secondary subjects, foreground/background layers, interaction between elements |
| **Style-First Structure** | Style is primary concern | Start with Style/Technique, then build subject and environment to match |
| **Technical-First Structure** | Professional photography simulation | Start with camera/lens specs, lighting setup, then add subject and composition |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| **Overly long prompts (300+ words)** | Overloads the model, dilutes important elements, results in confused images | Focus on 7-10 key visual elements; use precise technical language over long descriptions |
| **Internal visual contradictions** | Conflicting requests ("soft and dramatic lighting simultaneously") confuse the model | Choose one lighting style, one color palette, one consistent mood; if combining styles, specify how they integrate |
| **Purely descriptive prompts** | Describing only scene contents without technical, compositional, or stylistic direction | Always include lighting, composition, style, and technique — treat every prompt as complete art direction |
| **Missing critical elements** | Omitting lighting or composition results in generic, uncontrolled output | Use structured checklist: Subject, Environment, Lighting, Style, Composition, Details |
| **Vague style references** | "Professional style" or "good quality" provides no actionable direction | Use specific artists, movements, media, eras, or technical specifications |

---

## Examples

### Example 1: Portrait Photography

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"A photo of a business person." | **Prompt:**<br>"Professional corporate portrait of a confident 35-year-old female executive, wearing impeccably tailored navy blue blazer, brown hair in sophisticated updo, subtle professional smile conveying competence and approachability. Photographed in modern office with large windows creating soft background bokeh, natural side lighting supplemented by discreet fill light. High-end corporate portrait style, 85mm f/1.8 lens with precise eye focus, rule of thirds composition, blurred neutral-toned background." |
| **Output:**<br>Generic, amateurish business photo | **Output:**<br>Commercial-quality headshot suitable for corporate materials |
| **Issue:** Unusable generic output | **Result:** Production-ready professional portrait in single generation |

**Metric:** Transition from unusable generic output to commercial-ready professional portrait

---

### Example 2: Concept Art Landscape

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"A fantasy landscape with mountains." | **Prompt:**<br>"Epic high fantasy landscape showing floating mountains covered in bioluminescent blue and purple crystals, ethereal waterfalls cascading into the void creating prismatic rainbows, twilight sky in gradient from deep purple to gold, two crescent moons visible on the horizon, glowing alien vegetation on rocky edges. Cinematic concept art style inspired by Avatar and Final Fantasy, dramatic lighting with god rays piercing volumetric clouds, epic panoramic composition conveying grandeur and mystery, hyper-detailed digital rendering." |
| **Output:**<br>Generic, forgettable fantasy scene | **Output:**<br>Visually rich, memorable scene with unique elements and clear stylistic identity |
| **Issue:** Generic landscape without distinctive character | **Result:** Distinctive, commercially viable concept art through systematic structure |

**Metric:** Generic landscape → distinctive concept art with measurable stylistic identity

---

### Example 3: Product Photography

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"A luxury watch." | **Prompt:**<br>"Premium product photography of Swiss luxury watch with rose gold case, deep blue dial with diamond indices, dark brown Italian leather strap. Positioned on polished black marble surface with subtle reflections, professional studio lighting with main softbox and fill cards eliminating harsh shadows. Dark gradient-to-black background, macro lens capturing intricate details of visible movement, controlled depth of field keeping entire watch in focus. High-end jewelry photography style, 8K quality with crystalline detail." |
| **Output:**<br>Flat, catalog-style image | **Output:**<br>Catalog-ready luxury product image suitable for premium marketing materials |
| **Issue:** Lacks commercial appeal | **Result:** Premium commercial photography through systematic technical specification |

**Metric:** Basic product image → premium commercial photography through structured approach

---

## Quality Checklist

Before generating images using structured prompts, verify:

- [ ] **Subject clearly defined:** Appearance, action/pose, expression specified
- [ ] **Environment specified:** Location, setting, background elements described
- [ ] **Lighting defined:** Type, direction, quality, time of day explicitly stated
- [ ] **Style/technique included:** Artist name, movement, media, or technique reference
- [ ] **Composition specified:** Framing, angle, perspective, rule of thirds guidelines
- [ ] **Color palette mentioned:** If important for aesthetic, color scheme included
- [ ] **Technical quality specified:** Resolution, sharpness, lens characteristics if relevant
- [ ] **Mood conveyed:** Atmosphere and emotional tone described
- [ ] **Internal consistency verified:** No contradictory elements (e.g., conflicting lighting styles)
- [ ] **Length optimized:** 7-10 key elements, precise language, under 300 words

---

## Technical Reference

> **Link Verification:** All links verified as of 2026-01-23.

| Topic | Official Documentation |
|-------|------------------------|
| Digital Photography School: Technical Terms for AI | https://digital-photography-school.com/photography-terms-ai-prompts |
| Creative Bloq: AI Art Direction Guide | https://creativebloq.com/ai-art-direction-guide |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Digital Photography School: Technical Photography Terms for AI | https://digital-photography-school.com/photography-terms-ai-prompts | 2026-01-23 | n/a | 7.7 | 7 | 8 | 8 |
| 2 | Creative Bloq: AI Art Direction Techniques | https://creativebloq.com/ai-art-direction-guide | 2026-01-23 | n/a | 7.3 | 7 | 8 | 7 |

---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| [AI Art Community: Professional Prompt Engineering](https://aiartcommunity.com/professional-prompting-guide) | 5.7 | Low authority (AT:5), unverified domain |
| [Art History Reference: Styles for AI Prompting](https://arthistoryreference.com/ai-style-guide) | 5.3 | Low authority (AT:5), poor topic match (TM:6), unverified domain |
| [Reddit r/ChatGPT: Image Generation Techniques](https://reddit.com/r/ChatGPT/wiki/image-generation-guide) | 5.0 | Low trustability for technical guidance (TR:5), community-sourced without verification |

---

## For AI Agents

Read [`prompting_technique.md`](../prompting_technique.md).

---

*Last updated: 2026-01-23*


