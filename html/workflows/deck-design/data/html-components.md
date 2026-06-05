# HTML Pitch Deck Components

Reusable HTML/CSS component patterns for pitch deck slides. Use alongside `html-patterns.md` which provides the foundational layout, colors, and typography.

---

## Stat Block

```html
<div class="stat-block">
  <div class="stat-number" style="color: var(--primary)">47%</div>
  <div class="stat-label">Reduction in cost</div>
</div>
```

---

## Feature Card

```html
<div class="card">
  <i class="fas fa-brain" style="font-size: 28px; color: var(--primary);"></i>
  <div class="card-title">Feature Name</div>
  <div class="body-text">Brief description of value.</div>
</div>
```

---

## Comparison Card — Winner Emphasis

In competitive comparison grids, the product card must visually dominate competitors.

```css
.card--winner {
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.10);
  border-top: 3px solid var(--primary);
  transform: translateY(-4px);
  position: relative;
  z-index: 1;
}

.card--loser { opacity: 0.75; }
```

```html
<div class="grid-3">
  <div class="card card--loser"><!-- Competitor A --></div>
  <div class="card card--loser"><!-- Competitor B --></div>
  <div class="card card--winner"><!-- Our Product --></div>
</div>
```

---

## Scenario Table

Color-coded columns for pessimistic/base/optimistic financial tables. Red = floor, blue = base, green = ceiling.

```css
.scenario-table { border-collapse: collapse; width: 100%; }

.scenario-table th {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 8px 16px;
  border-bottom: 2px solid var(--gray-200);
}

.scenario-table td {
  font-size: 15px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--gray-100);
}

.scenario-table .pessimistic { color: var(--danger); opacity: 0.85; }
.scenario-table .base { color: var(--secondary); font-weight: 700; }
.scenario-table .optimistic { color: var(--primary-dark); }
```

---

## Callout Boxes

Use `.callout--risk` for failure modes and kill criteria. Use `.callout--gate` for decision gates. NEVER style risk/gate statements as footnotes.

```css
.callout--risk {
  border-left: 3px solid var(--danger);
  background: rgba(255, 107, 107, 0.06);
  border-radius: 0 8px 8px 0;
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 500;
}

.callout--gate {
  border-left: 3px solid var(--warning);
  background: rgba(255, 217, 61, 0.08);
  border-radius: 0 8px 8px 0;
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 500;
}

.callout-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 4px;
}

.callout--risk .callout-label { color: var(--danger); }
.callout--gate .callout-label { color: var(--warning); }
```

---

## Flow Diagram Connector

Use Unicode arrows styled with brand color — they render reliably in PDF export. NEVER use 1px gray connectors (they disappear in PDF).

```css
.flow-arrow {
  display: flex;
  align-items: center;
  padding: 0 12px;
  flex-shrink: 0;
}

.flow-arrow::after {
  content: '→';
  font-size: 22px;
  font-weight: 300;
  color: var(--secondary);
}

.flow-arrow--vertical::after { content: '↓'; }
```

```html
<div style="display: flex; align-items: center;">
  <div class="flow-node">Input</div>
  <div class="flow-arrow"></div>
  <div class="flow-node">Process</div>
  <div class="flow-arrow"></div>
  <div class="flow-node">Output</div>
</div>
```

---

## Zone Label (Multi-Section Slides)

Add a `.zone-label` above every distinct content zone on slides with 3+ sections. Establishes reading order and prevents zones from merging visually.

```css
.zone-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--gray-400);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--gray-200);
}
```

```html
<div class="zone-label">Technology Readiness</div>
<!-- content -->
<div class="zone-label" style="margin-top: 24px;">90-Day Validation Plan</div>
<!-- content -->
```

---

## Before/After Comparison

In before/after columns, the "after" (positive) column must have higher visual weight.

```css
.comparison-before {
  color: var(--gray-600);
  font-weight: 400;
}

.comparison-after {
  color: var(--primary-dark);
  font-weight: 600;
}
```

---

## Decision Framework Box

Decision framework boxes (kill criteria, go/no-go gates) must use neutral borders — red borders signal danger rather than rigor.

```css
.decision-framework {
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  padding: 20px 24px;
}

.decision-framework .kill-item {
  color: var(--danger);
  font-weight: 500;
}
```
