# Image-Craft Guide — the Designer's prompt/style/placement companion

> The craft layer the image-gen capability defers to the Designer ("Prompt craft (the Designer's job)" is out of the capability's scope). This guide governs WHEN to propose imagery, WHAT style to pick, HOW to write the prompt, and WHERE to place the result. Read `{rbtv_path}/studio/capabilities/image-gen/image-gen.md` for HOW to invoke the CLI and `{rbtv_path}/studio/capabilities/image-gen/image-gen-spec.md` for the behavioral floor. This guide never restates them.

Imagery is OPTIONAL and owner-gated: the Designer always PROPOSES (purpose + style) and generates only on owner-yes. A deck, site, or app with no generated imagery is a valid outcome.

---

## When to propose imagery

Propose a generated image ONLY where it strengthens the artifact's message. Reach for it on these purposes:

- Deck cover / hero — a single evocative image carrying the deck's mood behind the title card.
- Full-bleed slide / section background — an atmospheric backdrop under sparse text.
- Section divider — a transition image marking a new act in the arc.
- Conceptual / metaphor illustration — a visual for an abstract idea that resists a chart or photo.
- Product / UI mockup frame — a styled frame or device shell holding a screenshot.
- Website hero — the first full-width image a visitor meets.
- App onboarding / empty-state illustration — a friendly visual where a screen has no data yet.
- Texture / pattern — a subtle surface for an accent panel.
- Spot art — a small inline illustration beside a point.

NEVER propose imagery where it competes with the message or adds noise:

- Data-dense slides — a chart, table, or stat grid owns the focal space; an image fights it.
- Logo walls / team cards — these need real assets at parity, never generated stand-ins.
- Anywhere the image would dilute a one-idea-per-slide read or read as decoration-for-decoration's-sake.

When unsure, propose it as a question to the owner with the purpose stated — never auto-insert.

---

## Image types × purpose

| Image role | Artifact | Recommended aspect | Placement |
|------------|----------|--------------------|-----------|
| Cover / hero | deck | 16:9 | Full-bleed background behind the title card |
| Section divider | deck | 16:9 | Full-bleed background on a transition slide |
| Conceptual illustration | deck / site / app | 1:1 or 4:3 | Inline `<img>` beside or above the point |
| Product / UI mockup frame | deck / site | 16:9 or 4:3 | Inline `<img>`, centered, with a caption |
| Website hero | site | 16:9 or 21:9 | Full-bleed background on the home page |
| App onboarding / empty-state | app | 9:16 (mobile) or 1:1 | Centered inline `<img>` in the empty-state view |
| Texture / pattern | deck / site / app | matches the panel | Background on an accent panel, muted under text |
| Spot art | deck / site / app | 1:1 | Small inline `<img>`, subordinate to body text |

---

## Style families + how to pick

| Style family | Reads as |
|--------------|----------|
| Photographic-editorial | Real-world, magazine-grade photography mood |
| Cinematic | Dramatic lighting, filmic depth, widescreen feel |
| Abstract / gradient-mesh | Non-representational color fields and soft forms |
| Flat illustration | Clean vector-style shapes, minimal shading |
| Isometric / 3D | Dimensional objects at a fixed angle |
| Line art | Single-weight outlines, no fill |
| Duotone / brand-tinted | Two-tone image keyed to brand color |
| Textured | Grain, paper, or material surface treatment |

Pick the style as an art-direction decision tied to the project's reference set, taste file, and brand tokens — never a generic default. The chosen style MUST cohere with the direction mini-brief's signature motif and palette. A style picked without grounding in the reference set is the AI-slop failure: generic output that signals "generated with no brand input."

Anti-slop discipline: a generated background MUST NOT reintroduce a banned attractor. Run every proposed image through the ban-list at `{rbtv_path}/studio/standards/ban-list.md` — most directly the purple-blue-gradient default (A-1) on abstract/gradient-mesh styles. A banned attractor in a generated image is a defect, not a style choice.

---

## Prompt anatomy

Write a Gemini image prompt as an ordered composition of these elements:

1. **Subject** — what the image depicts, concretely.
2. **Style** — the chosen style family (above).
3. **Composition** — framing, focal placement, negative space.
4. **Lighting** — direction, hardness, time of day.
5. **Palette** — steer with REAL brand hex values pulled from the reference-set tokens, never invented colors.
6. **Mood** — the feeling the image must carry.
7. **Aspect** — the target ratio for the placement.
8. **Negative constraints** — what to exclude (clutter, text, specific objects).

Worked examples (generic):

- `Abstract flowing ribbons of deep teal (#0B6E6E) and warm sand (#E8D9B5), soft studio lighting, generous negative space top-left for a title, calm and premium mood, 16:9, no text, no faces.`
- `Editorial photograph of an empty modern workspace at golden hour, shallow depth of field, muted neutral palette accented with #C24E2A, optimistic and focused mood, 4:3, no logos, no on-screen text.`
- `Flat-illustration empty-state scene of a friendly open box on a plain background in brand green (#1F8A4C) and off-white, centered with breathing room, light and welcoming mood, 1:1, no text labels.`

**Text-in-image caveat:** avoid baked-in text. Generated text renders unreliably and cannot be edited, translated, or recolored later. Keep ALL real copy in HTML over the image — never inside the generated pixels.

---

## Aspect ratios per purpose

| Aspect | Use for |
|--------|---------|
| 16:9 | Deck full-bleed / cover, website hero |
| 1:1 | Spot art, conceptual illustration |
| 9:16 | Mobile / app screen imagery |
| 21:9 | Ultrawide hero |
| 4:3 | Content-area imagery, mockup frames |

The capability passes `--aspect` through to the provider, which decides final dimensions.

---

## The call recipe

Invoke the capability from the repo root:

```bash
python studio/capabilities/image-gen/generate.py --prompt "..." --out <path>.jpg [--provider gemini|fixture] [--aspect 16:9] [--env-file <path>]
```

The model is `gemini-3.1-flash-image` (v1beta). The key `GEMINI_API_KEY` resolves OS-env first, then the `--env-file` path. A missing key exits 1 naming the var and writes no file.

**Output format — the `--out` extension is honored.** Every provider, `gemini` included, writes the format implied by the `--out` extension (`png` or `jpg`): the `gemini` adapter re-encodes the API's raw bytes to the requested format, so a `.png` name yields a real PNG and a `.jpg` name a real JPEG.

**Asset-path convention:** save every generated image into the artifact's OWN `assets/` folder so the artifact's own-asset colocation keeps the image on save and reopen. Read `{rbtv_path}/studio/capabilities/image-gen/image-gen.md` for the full flag reference.

---

## Availability probe

Detect Gemini availability before proposing a live generation:

1. Check `GEMINI_API_KEY` — OS environment first, then the workspace env file (`.user/config/env/.env`).
2. Check that the `gemini` adapter is present in the capability's `adapters/` folder.

If both hold, generation is live. If either is absent, still PROPOSE the image (purpose + style) but flag it "needs the Gemini key" and offer the offline `fixture` provider as a placeholder. This is a graceful degrade — never a hard failure. The `fixture` provider is the quota-independent path: propose-and-place a placeholder now, regenerate live once the key lands.

---

## Placement + integration into HTML

| Placement | Rules |
|-----------|-------|
| Full-bleed background | Set the image as a CSS `background-image`. ALWAYS declare a `background-color` fallback FIRST so the slide reads before the image loads or if it fails. Layer a semi-transparent legibility scrim/overlay between the image and the text so copy stays readable. |
| Inline `<img>` | Use for spot art, conceptual illustrations, and mockup frames. Give it an `alt` and a max-width within its zone. |
| Cover treatment | Combine a full-bleed background with the title card; the scrim guarantees the title's contrast. |

Print-safety for decks: a deck image MUST survive print-to-PDF. Work within the mandatory `@media print` block so colors and page breaks hold in the exported PDF. Follow the ban-list print rows at `{rbtv_path}/studio/standards/ban-list.md` (the `@media print` requirement and print-unsafe-CSS attractors) rather than restating them here. Mute any competing texture under text with a semi-transparent overlay per the ban-list texture row.

---

## Real-provenance + logo discipline

Imagery comes via the image-gen capability (`{rbtv_path}/studio/capabilities/image-gen/`) OR owner-supplied assets. NEVER fabricate stock-lookalike photos passed as real photos of real things, people, or places. A slide needing an image whose asset is absent HALTS to the owner naming the missing asset — never an invented "real" photo. (The image-gen capability's FIXTURE provider is the quota-independent path — the contract may invoke the capability without assuming live image-gen quota.)

NEVER recolor a client's logo to fit a generated image or its surrounding panel — follow the ban-list logo rule (E-6) at `{rbtv_path}/studio/standards/ban-list.md`.
