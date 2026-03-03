# HTML Pitch Deck Patterns

CSS and HTML patterns for building pitch decks that export perfectly to landscape PDF via Ctrl+P.

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
```

---

## Color Scheme Pattern

Use CSS custom properties on `:root` for easy theming:

```css
:root {
  /* Primary palette — adapt to brand */
  --navy: #0a1628;
  --navy-light: #132240;
  --primary: #00d4aa;
  --primary-dark: #00b894;
  --secondary: #4a9eff;
  --secondary-light: #74b9ff;
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
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
```

### Stat Block

```html
<div class="stat-block">
  <div class="stat-number" style="color: var(--primary)">47%</div>
  <div class="stat-label">Reduction in operational cost</div>
</div>
```

### Feature Card

```html
<div class="card">
  <i class="fas fa-brain" style="font-size: 28px; color: var(--primary);"></i>
  <div class="card-title">Feature Name</div>
  <div class="body-text">Brief description of value.</div>
</div>
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

- **Phosphor Icons**: `https://unpkg.com/@phosphor-icons/web` — Flexible weights (thin to bold), modern feel
- **Lucide Icons**: `https://unpkg.com/lucide@latest` — Fork of Feather Icons, clean and consistent
- **Bootstrap Icons**: `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css` — Comprehensive

**Recommendation:** Use Font Awesome as primary. Add Material Icons Outlined for variety. Only add a third library if specific icons are needed.

---

## Full Slide Example

```html
<section class="slide slide--dark">
  <div class="slide-title">The Problem</div>
  <div class="slide-subtitle">Companies waste millions on processes that should be automated</div>
  <div class="grid-3" style="margin-top: 40px;">
    <div class="stat-block">
      <div class="stat-number" style="color: var(--danger);">68%</div>
      <div class="stat-label">Time lost to manual processes</div>
    </div>
    <div class="stat-block">
      <div class="stat-number" style="color: var(--warning);">3.2x</div>
      <div class="stat-label">Cost vs automated alternative</div>
    </div>
    <div class="stat-block">
      <div class="stat-number" style="color: var(--primary);">$4.2M</div>
      <div class="stat-label">Average annual waste per company</div>
    </div>
  </div>
  <div class="slide-number">02</div>
</section>
```
