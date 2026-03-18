# HTML Pitch Deck Patterns

CSS and HTML patterns for building pitch decks that export perfectly to landscape PDF via Ctrl+P.

**Also read `html-components.md` in this directory** for component-specific patterns (comparison cards, scenario tables, callouts, flow connectors, zone labels).

---

## Document Foundation

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{Project Name} — {Pitch Type} Pitch</title>
<!-- Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<!-- Icon Libraries -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">
</head>
```

---

## Critical Print CSS

```css
@page {
  size: landscape;
  margin: 0;
}

@media print {
  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .slide { page-break-inside: avoid; }
  .no-print { display: none !important; }
}
```

---

## Slide Container Pattern

```css
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Inter', -apple-system, sans-serif;
  background: var(--white);
  color: var(--gray-800);
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

.slide {
  width: 100%;
  min-height: 100vh;
  padding: 60px 80px;
  padding-bottom: calc(60px + 10vh); /* optical center — content sits slightly above geometric center */
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  overflow: hidden;
  page-break-after: always;
  break-after: page;
}

.slide:last-child {
  page-break-after: avoid;
  break-after: avoid;
}
```

---

## Slide Variants

```css
.slide--dark { background: var(--navy); color: var(--white); }

.slide--gradient {
  background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 100%);
  color: var(--white);
}

.slide--accent { background: var(--primary); color: var(--white); }

.slide--cover {
  padding-bottom: calc(60px + 14vh); /* stronger optical offset for cover slides */
}

.slide--warm {
  background: var(--bg-warm, #F5EDE4);
  color: var(--navy);
}

.slide--soft {
  background: var(--bg-soft, #F7F8FA);
  color: var(--navy);
}
```

Use `.slide--warm` for team, product narrative, and closing slides to create visual breaks. Max 3–4 warm slides in a 20-slide deck.

---

## Color Scheme Pattern

Use CSS custom properties on `:root` for easy theming:

```css
:root {
  /* ⚠️ REPLACE ALL VALUES BELOW WITH BRAND TOKENS */
  --primary: #00C896;        /* brand primary */
  --primary-dark: #009E78;   /* primary darkened ~15% */
  --secondary: #3A7BD5;      /* brand secondary */
  --secondary-light: #6A9FE8;
  /* Dark backgrounds */
  --navy: #1B2B4B;
  --navy-light: #243A60;
  /* Warm/neutral backgrounds */
  --bg-warm: #F5EDE4;        /* warm cream for alternate slides */
  --bg-soft: #F7F8FA;        /* soft gray for content slides */
  /* Semantic */
  --danger: #ff6b6b;
  --warning: #ffd93d;
  /* Neutrals */
  --white: #ffffff;
  --gray-100: #f0f2f5;
  --gray-200: #e1e5eb;
  --gray-400: #8c95a6;
  --gray-600: #5a6577;
  --gray-800: #2d3748;
}
```

---

## Typography Scale

```css
.slide-title {
  font-size: clamp(28px, 3.5vw, 42px);
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin-bottom: 12px;
}

.slide-subtitle {
  font-size: clamp(16px, 1.8vw, 22px);
  font-weight: 400;
  opacity: 0.7;
  margin-bottom: 40px;
}

.stat-number {
  font-size: clamp(36px, 5vw, 64px);
  font-weight: 900;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  max-width: 160px;
  margin: 0 auto;
  text-align: center;
  line-height: 1.3;
}

.card-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.body-text { font-size: 16px; font-weight: 400; line-height: 1.6; }
```

---

## Slide Number

```css
.slide-number {
  position: absolute;
  bottom: 30px;
  right: 40px;
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-400);
  letter-spacing: 0.05em;
}
```

---

## Layout Patterns

```css
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }

.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  /* CONSTRAINT: Max 6 cards (2 rows). Beyond 6, split to a new slide. */
}

.grid-4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  /* CONSTRAINT: Only when each cell ≤3 lines. For richer content, use .grid-3 or .grid-2. */
}
```

---

## Image Reference Pattern

```html
<div class="image-slot" style="background: var(--gray-100); border-radius: 12px; padding: 40px; text-align: center;">
  <img src="images/slide-02-problem.png" alt="Problem visualization"
       style="max-width: 100%; max-height: 400px; border-radius: 8px;"
       onerror="this.style.display='none'">
</div>
```

Name images descriptively: `slide-{number}-{topic}.png`

---

## Icon Libraries

### Font Awesome 6 (Primary)

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<!-- Usage: <i class="fas fa-chart-line"></i> -->
```

Best for: Business, finance, technology, general purpose icons.

### Material Icons Outlined

```html
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">
<!-- Usage: <span class="material-icons-outlined">trending_up</span> -->
```

Best for: Clean, minimal UI-style icons.

### Alternatives (add as needed)

- **Phosphor Icons**: `https://unpkg.com/@phosphor-icons/web` — Flexible weights, modern feel
- **Lucide Icons**: `https://unpkg.com/lucide@latest` — Fork of Feather Icons, clean
- **Bootstrap Icons**: `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css`

Use Font Awesome as primary. Add Material Icons Outlined for variety. Feature card icons must be at least 24px in `var(--primary)` — smaller or muted icons should be removed.

---

## Logo Pattern

### Single Logo (Cover/Closing)

```css
.cover-wordmark {
  height: clamp(40px, 6vh, 80px);
  filter: brightness(0) invert(1); /* renders white on dark backgrounds */
}
```

- Cover/closing logo height: 5–8% of viewport height (`clamp(40px, 6vh, 80px)`)
- Dark backgrounds: ALWAYS apply `filter: brightness(0) invert(1)` to non-white logos
- Light backgrounds: use logo as-is (no filter)
- `onerror="this.style.display='none'"` on all logo `<img>` tags

### Multi-Logo Composition

```css
.cover-logos {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: clamp(20px, 3vw, 40px);
}
```

- Logos with more visual mass (icon + text) must be sized 10–20% smaller in height than simpler wordmarks to achieve visual balance
- Separator between logos: `×` character, font-weight 300, opacity 0.5–0.6
- ALWAYS test multi-logo compositions at the actual slide size — aspect ratio differences cause surprises

### Asset Manifest Color Handling

When creating or reading asset manifests (`manifest.md`), document whether each logo/asset is dark-on-transparent or light-on-transparent. Include the CSS filter instruction for dark background usage.

---

## Background Image Pattern

```css
.slide--textured {
  background-color: var(--fallback-color);
  background-image: url('images/texture.png');
  background-size: cover;
  background-position: center;
}
```

| Constraint | Rule |
|---|---|
| Max textured slides | Max 3 textured backgrounds per deck (cover, closing, and 1 accent). Remaining slides use flat colors. |
| Fallback color | ALWAYS set `background-color` as fallback before `background-image` |
| Subtlety test | If the texture competes with text readability, mute it with a semi-transparent overlay: `background-image: linear-gradient(rgba(R,G,B,0.7), rgba(R,G,B,0.7)), url(...)` |
| Print rendering | Background images require `print-color-adjust: exact` — already set globally but verify |

---

## Full Slide Example

```html
<section class="slide slide--dark">
  <div class="slide-title">The Problem</div>
  <div class="slide-subtitle">Companies waste millions on processes that should be automated</div>
  <div class="grid-3" style="margin-top: 40px;">
    <div class="stat-block">
      <div class="stat-number" style="color: var(--primary);">68%</div>
      <div class="stat-label">Time lost to manual work</div>
    </div>
    <div class="stat-block">
      <div class="stat-number" style="color: var(--primary);">3.2x</div>
      <div class="stat-label">Cost vs automated alt</div>
    </div>
    <div class="stat-block">
      <div class="stat-number" style="color: var(--primary);">$4.2M</div>
      <div class="stat-label">Average annual waste</div>
    </div>
  </div>
  <div class="slide-number">02</div>
</section>
```

Use a single accent color for all stats in the same semantic group. Reserve `var(--danger)` for genuinely negative stats only.

---

## Design Constraints

These constraints MUST be enforced at generation time.

| # | Constraint | Rule |
|---|---|---|
| 1 | **Min font sizes** | Body: 15px. Diagram nodes: 14px. Table cells: 13px. No content element below 13px. |
| 2 | **Stat labels** | Must fit on a single line at rendered width. Shorten copy — never accept two-line stat labels. |
| 3 | **Max cards per grid** | Max 4 cards in a column < 50% slide width. Max 6 cards total in any `.grid-3`/`.grid-4`. |
| 4 | **Max zones per slide** | Max 3 distinct content zones per slide. 4+ zones must split into separate slides. |
| 5 | **Currency consistency** | All cards in the same grid must use the same currency and time basis. |
| 6 | **Cover/closing mirror** | Cover and closing slides must use identical background, typography, and layout. Closing adds contact info only. |
| 7 | **Scatter plot sizing** | Min 500px wide × 380px tall. Axes must include scale values. Labels min 13px with background overlay. |
| 8 | **Stat color discipline** | Single accent color for all stats in the same group. `var(--danger)` only for genuinely negative values. |
| 9 | **Icon minimums** | Feature card icons: min 24px in `var(--primary)`. Smaller icons should be removed entirely. |
| 10 | **Header-content gap** | Gap between slide header and primary content block must not exceed 40px. |
| 11 | **Flow connectors** | Diagram connectors: min 2px, brand color. 1px gray connectors disappear in PDF. |
| 12 | **Color-coded borders** | When using colored left borders as a visual system, color logic must be consistent and intentional. |
| 13 | **Content overflow** | Slides with >3 content zones, process diagrams, or >4 bullet items must use `justify-content: flex-start` with `padding-top: 50px; padding-bottom: 40px;` instead of centered layout. Centered layout is only safe for sparse slides. |
| 14 | **Logo sizing** | Cover logo height: `clamp(40px, 6vh, 80px)`. Multi-logo: size by visual mass, not pixel height. Dark bg logos must use `filter: brightness(0) invert(1)`. |
| 15 | **Background texture limit** | Max 3 textured slides per deck. Never apply the same texture to more than 2 slides. |
| 16 | **Content-fit validation** | Before finalizing, estimate each slide's total content height. If title + subtitle + content block exceeds ~70vh, switch to top-aligned layout with reduced padding. |
