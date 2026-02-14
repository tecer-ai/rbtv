---
title: 'Design Extraction: artprize-shadows.com'
docType: 'design-brief'
targetUrl: 'https://artprize-shadows.com/'
date: '2026-02-14'
---

# Design Extraction: artprize-shadows.com

## Color Strategy

The palette operates on two distinct layers: a **dark immersive layer** (video/3D backgrounds) and a **light rendered layer** (the warm off-white scene visible in the hero).

On the dark layer, three deep hues anchor the brand: navy (`#011B50`), indigo (`#14093A`), and purple (`#412762`). These appear as text colors on light surfaces, background tints, and overlay bases. White (`#FFFFFF`) is the dominant accent — used for hero typography, SVG icons, glow effects, and navigation on dark backgrounds. A rich alpha scale (8 white alphas from 0.08 to 0.7, plus 3 black alphas and a 50% indigo) provides layered depth without introducing new hues.

On the light layer (the rendered 3D scene), warm off-whites (`#ECEAE4`, `#E8E8E0`) dominate. These are not set via CSS (the DOM reports transparent backgrounds over video), so they exist only in the rendered visual output.

## Typography Direction

Three typefaces serve distinct roles:

- **Neue Haas Grotesk Display Pro** (weight 450 "book") — the display face. Used for hero wordmark at `7rem` (112px) with dramatic letter-spacing (`15.16px`), and for artwork titles at `1.5625rem` (25px) and subtitles at `1.375rem` (22px). Clean, geometric, authoritative.

- **Interstate** (weights 300 light, 400 regular) — the UI face. Used for CTA labels, scroll prompts, and small text at `0.875rem` (14px) and `0.75rem` (12px). Functional and unobtrusive.

- **Times New Roman** — the body default. Appears on unstyled containers and inherited text at `16px`. Likely a deliberate fallback rather than a primary design choice.

The type scale spans from `0.75rem` to `7rem` — a 9.3x ratio between caption and hero, reflecting a layout where typography is either monumental or minimal.

Line heights are tight across the board: `0.9` (hero), `1.1` (display), `1.2` (titles), `1.84` (body/reading). Letter-spacing is pronounced on display text (`~13–15px`) and normal everywhere else.

## Spacing Philosophy

Spacing is composition-driven rather than systematic. There is no base-unit grid; instead, values appear to be hand-tuned per component:

- Paddings range from `16px` to `60px`, with a responsive horizontal inset of `max(150px, 10vw)` on content containers.
- Gaps range from `6px` (tight icon clusters) to `80px` (section-level separation), with `7vh` used for viewport-relative breathing room.
- Margins are sparse: `80px` top on the hero title, `6px` bottom on artwork titles, `25–30px` bottom on section elements.

The overall effect is spacious and gallery-like — large empty areas are the dominant visual element.

## Layout Patterns

This is a **single-screen experience**: the page height equals the viewport height (900px). Content is not revealed by scrolling but by JavaScript-driven state transitions (clicking "Start exploring", selecting artworks).

Layout is entirely absolute-positioned overlays — no CSS grid or column system. Containers span the full viewport (`1440px` or `1446px` with a `-3px` offset bleed). Navigation, artwork titles, and UI elements float in fixed positions over the video/3D background.

Breakpoints exist at `48em` (tablet) and `64em` (desktop), with interaction-type queries for touch vs. pointer devices. A landscape blocker appears below `48em` in landscape orientation — the experience is portrait-first on mobile.

## Visual Identity

The site is a premium art exhibition microsite (Richard Mille Art Prize at Louvre Abu Dhabi). The visual identity is:

- **Minimal and restrained** — mostly empty space with a few precise typographic and interactive elements.
- **Motion-heavy** — 42 transition tokens with carefully crafted cubic-bezier easings (`0.32, 0.94, 0.6, 1` for smooth deceleration; `0.66, 0, 0.34, 1` for symmetrical ease).
- **Glow-based depth** — shadows are white glows over dark backgrounds (`0px 0px 2px white`, `0px 0px 8px white`), not traditional elevation shadows.
- **Rounded CTAs** — border-radii range from `25px` to `76px` plus `50%` circles, creating pill-shaped buttons and circular indicators.
- **Opacity as interaction language** — elements transition between `0` (hidden), `0.5` (muted/inactive), and `1` (active) to communicate state.

---

## Token Summary

| Category | Key Values |
|----------|------------|
| Primary Color | `#011B50` (navy) |
| Secondary Color | `#412762` (purple) |
| Tertiary Color | `#14093A` (indigo) |
| Background (rendered) | `#ECEAE4` (warm off-white) |
| Display Font | Neue Haas Grotesk Display Pro, 450 |
| UI Font | Interstate, 300–400 |
| Hero Size | 7rem (112px) |
| CTA Radius | 50px (pill) |
| Primary Easing | cubic-bezier(0.32, 0.94, 0.6, 1) |
| Breakpoints | 48em / 64em |
| @font-face | 3 (WOFF2, swap) |
| Total Unique Colors | 17 |
| Total Font Sizes | 11 |
