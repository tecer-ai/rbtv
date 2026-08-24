---
description: "Brandbook — the terminal brand framework: consolidates the other six into one canonical reference and adds the visual identity specification (logo, color, typography, imagery, iconography)."
tags: [brand]
---

# Brandbook

The brandbook is the single authoritative document that lets any team member, partner, or external
collaborator represent the brand consistently. It is the only framework in this component that
**discovers nothing new** — it compiles, extends and operationalizes the outputs of the six others,
and adds the one thing they defined only conceptually: the visual identity specification.

Run it last. Every other reference in this component should have produced an output first.

## The sequence

Worked in this order, always. Each step consumes the previous one's output, so a skipped or
reordered step is not a shortcut — it silently invalidates everything downstream of it. Steps 3–8
are section 2 below, the only section that creates rather than compiles.

| # | Step | What it produces | What breaks if it is skipped or taken out of order |
|---|---|---|---|
| 1 | Check the six inputs exist | A confirmation that each of the other six brand frameworks has produced an output, with the missing ones named | The brandbook has nothing to consolidate and invents brand decisions the frameworks were supposed to make |
| 2 | Compile section 1 — brand identity | Mission, vision, brand persona, target audience, values and brand story, each REFERENCING its source framework rather than restating it | Restated content forks from its source, and two documents then disagree about what the brand believes |
| 3 | Agree the visual method with the founder | An explicit agreement on how the visual work will be produced — a design skill, an image-generation tool, or prompts the founder runs themselves | Asset production stalls halfway, or assets arrive in a form the founder cannot use or edit |
| 4 | Specify the color palette | 1–3 primary, 2–4 secondary and accent colors, each with HEX, RGB and CMYK values, plus usage guidelines and the contrast check | Specified after the logo, the palette is forced to accommodate a logo that was drawn against nothing |
| 5 | Specify typography | Primary and secondary typefaces, weights, the H1–H3 / body / caption hierarchy, line heights, and the accessibility notes | Same as above — type is a constraint on the logo, not a decoration applied after it |
| 6 | Design the logo | Primary, secondary and monochromatic variations with clear-space rules and do's and don'ts, iterated until the founder EXPLICITLY approves | An unapproved logo propagates into every other asset and every reference below before anyone rules on it |
| 7 | Specify imagery and iconography | Photographic style and icon style, each traced to the physique facet, the archetype's visual direction and the category expectations, with do's and don'ts | The brand looks coherent in the logo and incoherent everywhere the logo is not |
| 8 | Run the accessibility check | Contrast verified at 4.5:1 for body text and 3:1 for large text across the specified combinations | The palette ships unusable for part of the audience, and the fix later invalidates every asset built on it |
| 9 | Compile section 3 — messaging and tone | Brand voice, tone guidelines, value proposition and key messaging referenced from their frameworks, plus a tagline crafted here from the brand promise and approved by the founder | The tagline gets written before the promise it is meant to distil, and becomes a slogan with nothing under it |
| 10 | Run the consistency check | Contradictions between the compiled sections found and resolved, with the resolutions recorded | The brandbook publishes the disagreements between six frameworks as though they were one position |
| 11 | Build the quick reference sheet | A genuine one-page sheet: logo thumbnails, palette HEX codes, typefaces, a 2–3 sentence voice summary, the tagline, and the core do's and don'ts | A quick reference that runs past one page is not used, which leaves the whole brandbook unused in practice |

Steps 4 and 5 may be worked in either order — both must precede step 6. Nothing else moves.

## Structure

### Section 1 — Brand identity (compiled)

| Element | Compiled from |
|---|---|
| Mission statement | `golden-circle.md` — the Why |
| Vision statement | `golden-circle.md` — the What, as an aspirational future |
| Brand persona | `brand-archetypes.md` (primary archetype, IS/IS-NOT traits) + `brand-prism.md` (personality facet) |
| Target audience | The venture's customer jobs and segment work |
| Brand values | `brand-prism.md` (culture facet) + `golden-circle.md` (How) |
| Brand story | The venture's customer narrative + the Why/How/What arc |

### Section 2 — Visual guidelines (created here)

| Element | What is specified |
|---|---|
| Logo | Primary, secondary and monochromatic variations; clear-space rules; do's and don'ts |
| Color palette | 1–3 primary, 2–4 secondary, accent colors; usage guidelines |
| Typography | Primary typeface (headings) and secondary (body); H1–H3, body and caption hierarchy |
| Imagery | Photographic style — subject matter, composition, lighting, color treatment; do's and don'ts |
| Iconography | Icon style — line weight, fill, corner style, detail level; usage rules |

**How the visual work gets done.** The visual identity specification is produced with whatever
design capability the session has — a design skill, an image-generation tool available to the
agent, or prompts composed for the founder to run in their own tool. Whichever it is, agree it with
the founder before starting, and iterate on each asset until the founder explicitly approves it.
No specific design tool or external designer is assumed.

Define color and typography **before** the logo — they constrain it. Every visual asset must trace
back to the physique facet (`brand-prism.md`), the archetype's visual direction
(`brand-archetypes.md`), and the category expectations named in `brand-positioning.md`. Where an
image is generated, the specification for it carries the brand context (archetype, palette,
personality, positioning category), the style direction, what to avoid, the technical
specifications, and the filename it will be saved under.

**Color specification** — record HEX (web/digital), RGB (screen), CMYK (print), and optionally the
closest Pantone match for professional printing.

**Typography specification** — required: typeface name, weight and style variants (Regular, Bold,
Italic minimum), use cases, size hierarchy per level, line height per use case, and accessibility
notes (minimum contrast ratio, legibility). Recommended: maximum line length (45–75 characters) and
a web fallback stack. Optional: letter spacing.

**Accessibility is not optional** — minimum contrast 4.5:1 for body text, 3:1 for large text.

### Section 3 — Messaging and tone (compiled)

| Element | Compiled from |
|---|---|
| Brand voice | `tone-of-voice.md` — dimensions and voice summary |
| Tone guidelines | `tone-of-voice.md` — do/don't examples, context adjustments |
| Tagline | New — crafted here from the brand promise |
| Value proposition | The venture's value proposition + `brand-positioning.md` statement |
| Key messaging | `messaging-architecture.md` — promise and key messages per audience |

### Section 4 — Quick reference sheet

One page: primary and secondary logo thumbnails (file references), palette with HEX codes, primary
and secondary typefaces, a 2–3 sentence voice summary, the tagline, and the core do's and don'ts.

## The do's and don'ts pattern

Every visual element section carries explicit do's and don'ts. For the logo, for example: DO use
the primary logo when space allows, maintain minimum clear space, use the monochromatic version on
colored backgrounds; DON'T stretch or distort proportions, change brand colors, place it on busy
backgrounds, or add shadows, glows or outlines. Apply the same pattern to color, typography,
imagery and iconography.

## What a good output contains

- All four sections above, in order.
- Every visual element with its do's and don'ts.
- Logo variations approved by the founder and saved, with clear-space and usage rules.
- A tagline the founder approved.
- The quick reference sheet as a genuine one-pager.
- Consistency check results — contradictions between compiled sections found and resolved.
- Key decisions and their rationale.
- The founder can answer three questions from this document alone: what does our brand look like,
  how does it sound, and what are the rules?

## Pitfalls

Compiling before the six inputs exist (the brandbook has nothing to consolidate) · restating an
upstream framework instead of referencing its output · specifying color or typography with no
accessibility check · shipping a logo the founder never explicitly approved · a "quick reference"
that runs past one page and so gets ignored.

## Builds on / feeds

Owns the **consolidated brand identity** and is the terminal framework of this component — it
synthesizes all six others and produces no downstream input of its own within the brand milestone.
It is the artifact any later product, prototype or campaign work reads the brand from.

Sources: `3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m3/bi-m3-brandbook/`
(`data/brandbook-framework.md`, `workflow.md`, `steps-c/step-03-visual.md`,
`steps-c/step-05-synthesis.md`). The old step 03 delegated visual guidelines to a separate design
agent; that handoff is deliberately not carried over.
