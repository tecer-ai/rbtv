---
description: "Use at the moment a static reference image must become a strict JSON visual spec — when rendered pixels are in hand. Forensic analysis of ONE image; NEVER from a text description of an image."
inputs: "One rendered image (path or attachment: PNG, JPG, WEBP, or any still raster the runtime can open). Optional output path from the caller. Optional name of an image generator the runtime actually has."
outcome: "The caller holds a valid JSON visual spec of the image, every field filled from visible pixels or marked empty/absent — never guessed — written where the caller pointed."
outputs: "A JSON file matching the schema below (property names unchanged). Optional single-line regeneration prompt only when the caller named a generator the runtime has."
---

# vision-to-json

Forensic analysis of ONE static reference image into a strict JSON visual spec. This is NOT live-site token extraction and NOT screenshot capture.

## Hard rules

- **Pixels are REQUIRED.** The capability analyses a rendered image. It NEVER derives a spec from a text description of an image.
- **Empty/absent, never invent.** A field the image does not support is left empty (`[]`, `"none"`, or `"absent"`), NEVER filled with a plausible guess.
- **Property names are the i/o contract.** NEVER rename, add, or drop a key in the schema below.
- **Output goes where the caller points.** Default filename when the caller names none: `vision-to-json-{image-name}.json`.
- Instruction-only. There is no CLI.

## Procedure

1. **Load the image.** Open the rendered pixels. If they cannot be read, halt and ask for a valid path or attachment. NEVER proceed on a description.
2. **Analyze forensically.** Inspect every region. NEVER summarize. NEVER omit micro-details. NEVER use vague words. Fill EVERY field from what is actually visible.
3. **Emit the JSON spec.** Produce ONLY valid JSON matching the schema below (well-formed, no trailing commas, property names exact).
4. **Write the file** to the caller-supplied path.
5. **Regeneration prompt (optional).** If the caller named an image generator the runtime actually has, ALSO emit one single-line regeneration prompt parameterized for that generator, combining the spec into generator-ready text. If no generator is named or none is available, omit this step. A run with no image generator still SUCCEEDS if the JSON spec is written.

## Output quality

1. The JSON MUST validate.
2. `detailed_visual_description` and `background.detailed_description` MUST be verbose paragraphs capturing every texture and micro-detail — NEVER one-liners.
3. An optional regeneration prompt MUST be a single self-sufficient line (the named generator could reproduce the image from that line alone).

## JSON schema

Use this EXACT schema (never change property names):

```json
{
  "metadata": {
    "original_width_px": "integer",
    "original_height_px": "integer",
    "aspect_ratio": "string like 16:9 or 3:4",
    "dominant_art_style": "string",
    "overall_mood": "string"
  },
  "color_palette": {
    "dominant_colors_hex": ["#hex", "#hex", "... top 6"],
    "accent_colors_hex": ["#hex"],
    "gradient_directions": ["string description"]
  },
  "lighting": {
    "key_light": "direction + temperature + softness",
    "fill_light": "direction + ratio to key",
    "rim_back_light": "present or absent + color",
    "ambient_light_color": "#hex or description",
    "shadow_hardness": "hard | medium | soft",
    "global_contrast": "low | medium | high | very high"
  },
  "composition": {
    "rule_of_thirds": "subject placement description",
    "leading_lines": "description or none",
    "symmetry": "perfect | approximate | none",
    "negative_space_usage": "description",
    "depth_layers": ["foreground", "midground", "background"]
  },
  "camera": {
    "focal_length_equivalent": "24mm | 50mm | 85mm | 200mm etc.",
    "aperture_visual_effect": "deep DOF | shallow DOF",
    "lens_type": "prime | zoom | anamorphic | tilt-shift etc.",
    "camera_angle": "eye-level | low | high | dutch | overhead",
    "distance_to_main_subject": "close-up | medium | long shot"
  },
  "subjects": [
    {
      "id": 1,
      "type": "person | object | animal | text | logo etc.",
      "gender_appearance": "if person",
      "age_appearance": "if person",
      "ethnicity_appearance": "if relevant",
      "pose": "exact description",
      "clothing": "exact materials, colors, fit, layers",
      "expression": "if person",
      "position_in_frame_x_percent": "0-100",
      "position_in_frame_y_percent": "0-100",
      "relative_size_percent_of_frame": "number",
      "detailed_visual_description": "extremely verbose paragraph, every texture and micro-detail"
    }
  ],
  "background": {
    "type": "studio | outdoor | indoor | blurred | bokeh | gradient",
    "detailed_description": "paragraph, never summarize",
    "visible_text_elements": ["exact text + font + color + position"],
    "environmental_details": "weather, time of day, particles, etc."
  },
  "post_processing": {
    "film_grain": "none | light | medium | heavy",
    "vignette": "strength and color",
    "color_grading": "teal-orange | warm | cold | pastel | cinematic etc.",
    "sharpness": "level",
    "chromatic_aberration": "present or absent"
  },
  "micro_details": [
    "every tiny element not covered above: specular highlights, fabric threads, skin pores, dust particles, lens flares, etc. – list as separate strings"
  ],
  "recommended_generators": ["string — names of generators whose documented strengths match the image; empty array when none is known"]
}
```
