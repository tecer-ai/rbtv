---
title: 'Design Extraction: artprize-shadows.com'
docType: 'design-extraction'
mode: 'create'
targetUrl: 'https://artprize-shadows.com/'
outputFormat: 'both'
stepsCompleted: ['step-01-init.md', 'step-02-capture.md', 'step-03-extract.md', 'step-04-document.md']
date: '2026-02-14'
---

# Target

- URL: https://artprize-shadows.com/

# Status

- Step 01 complete.
- Step 02 complete.
- Step 03 complete.
- Step 04 outputs generated for review.
- DOM extraction complete (`_admin-output/design-tokens/artprize-shadows.dom-scan.json`).

# Extraction Draft (from desktop screenshot)

Source screenshot:

- `_admin-output/screenshots/artprize-shadows-desktop.png` (1440x900, full page)

## Colors (measured from screenshot pixels)

- Background warm off-white: `#ECEAE4` (dominant background)
- Background/neutral off-white: `#E8E8E0` (dominant surface)
- Neutral light gray: `#E0E0E0` (secondary surface)
- Neutral mid warm gray: `#B8B0B0` (sphere + shadow transitions)
- Neutral mid gray: `#B0B0B0` (sphere pattern + edges)
- Neutral line gray: `#8A8983` (thin rule/line detail)
- Neutral dark slate: `#505860` (darkest visible structure, sphere/shadow detail)
- Neutral dark slate (alt): `#485058` (darkest visible structure, sphere/shadow detail)
- Ink / near-black: `#282828` (darkest color family present)
- Ink (deep): `#201818` (deepest sampled dark)

## Typography (visible only)

- Hero display word "Art": very large, thin/modern sans; color reads as near-white on warm off-white background.
- Measured white-text bounding box (thresholded): ~`279px` tall for the brightest pixels cluster; exact font size/family not determinable from screenshot alone.

## Spacing (qualitative)

- Very high whitespace density; minimal UI chrome.
- Large hero composition spacing dominates; no visible spacing scale tokens can be measured reliably from this single frame.

## Layout

- Full-bleed hero composition; content visually anchored around central 3D sphere.
- Minimal top-left logo cluster; otherwise no visible navigation in the captured frame.

## Visual identity

- Minimalist, gallery-like, high-key palette; soft shadows as the primary depth cue.
- Sharp rectangular planes (0 radius) + detailed 3D metallic sphere as focal point.

# Draft Outputs

- Tokens (JSON): `_admin-output/design-tokens/artprize-shadows.tokens.json`
- Brief (MD): `_admin-output/design-brief-artprize-shadows.md`
- Raw DOM scan (JSON): `_admin-output/design-tokens/artprize-shadows.dom-scan.json`
