# Fixture Library Spec — `fixture-library` (executor-ready)

**Purpose:** a small synthetic, RBTV-generic slide library that exercises EVERY feature of the RBTV slide-library convention v1 (`convention-spec.md`). Workstream 2 builds and verifies the engine against THIS fixture before touching any real library.

**Executor instruction (read first):** create every file below VERBATIM at the stated path. Content is literal — copy character-for-character, including HTML comments, token casing, and the trailing newline. Do NOT improvise content, rename ids, reorder columns, or "improve" copy. The content is intentionally generic ("Nimbus", a fake product) and carries ZERO real client/brand data. Where a file is binary (an image asset), create a placeholder per § F.

**Root:** the fixture library is the folder `fixture-library/`. Its location is set by the engine workstream (recommended: `html/slide-library/tests/fixture-library/`). All paths below are relative to that root.

---

## Feature coverage matrix (what this fixture proves)

| Convention feature | Exercised by |
|--------------------|--------------|
| ≥3 sections, declared + ordered | `library.json` `sections`: 6 sections (opening, intro, diagnosis, product, proof, closing) |
| Both languages | `pt` and `en` slides present |
| A bilingual pair (same concept, two langs) | `cover-nimbus.pt` + `cover-nimbus.en` |
| `ready` kind | `intro-pillars`, `how-nimbus-works`, `nimbus-divider`, `closing-nimbus` |
| `template` kind | `cover-nimbus.pt`, `cover-nimbus.en`, `problem-cards`, `proof-metrics`, `pricing-options` |
| Asset from library root (bare filename) | `cover-bg.jpg`, `bg-dark.jpg`, `closing-bg.jpg`, `nimbus-mark.png` |
| Asset from the extra root (`@root/...`) | `proof-metrics` references `@root/partner-mark.png` |
| `extra_asset_root` declared | `library.json` `extra_asset_root: "../shared-brand"` |
| Slide with NO assets (`-`) | `intro-pillars`, `problem-cards`, `pricing-options` |
| Multi-asset slide | `closing-nimbus` (3 assets) |
| Token-dense template | `problem-cards` (10 tokens) and `proof-metrics` (10 tokens) |
| Token authoring comments (fill-spec) | every token in every template slide is comment-annotated |
| Numbered slides (`{{N}}`) | all body slides carry `<div class="slide-number">{{N}}</div>` |
| Unnumbered slides | both covers carry NO slide-number div |
| Client-lockup tokens | `cover-nimbus.pt`/`.en` use `{{CLIENT_LOGO_SRC}}` + `{{CLIENT_NAME}}` |
| `{client-logo}` asset-cell sentinel | `cover-nimbus.pt`/`.en` list `{client-logo}` in their assets cell |
| ≥2 presets | `nimbus-intro-en`, `nimbus-intro-pt` |
| Preset spanning multiple lines | `nimbus-intro-en` `slides:` list wraps |
| As-built log (seeded with 1 historical entry) | `as-built.md` |
| Variant classes | `slide--cover`, `slide--dark`, `slide--closing`, `slide--soft`, plain `slide` |
| Self-description (DT4 interface) | `README-FOR-AGENTS.md` |
| Thin `CLAUDE.md` pointer | `CLAUDE.md` |

The fixture has **9 fragments across 6 sections, 2 languages, 4 ready + 5 template** (the 9th fragment, `nimbus-divider`, is a plain-`slide` ready divider exercising the no-header variant, and is the 4th `ready` fragment). Two assets live in the library; one lives in the extra root.

---

## File tree to create

```
fixture-library/
├── library.json
├── README-FOR-AGENTS.md
├── CLAUDE.md
├── manifest.md
├── presets.md
├── as-built.md
├── base.html
├── theme.css
├── slides/
│   ├── cover-nimbus.pt.html
│   ├── cover-nimbus.en.html
│   ├── intro-pillars.html
│   ├── problem-cards.html
│   ├── how-nimbus-works.html
│   ├── nimbus-divider.html
│   ├── proof-metrics.html
│   ├── pricing-options.html
│   └── closing-nimbus.html
└── assets/
    ├── cover-bg.jpg          (placeholder image — § F)
    ├── bg-dark.jpg           (placeholder image — § F)
    ├── closing-bg.jpg        (placeholder image — § F)
    └── nimbus-mark.png       (placeholder image — § F)

../shared-brand/              (sibling of fixture-library/, for the extra-root test)
└── partner-mark.png          (placeholder image — § F)
```

> NOTE the engine workstream MUST also have the `assemble.py` engine copy in the fixture root once the engine is built (per convention § 1.1). The fixture-creation executor does NOT create `assemble.py` — that is the engine workstream's vendoring step. Everything else below is created verbatim now.

---

## A. `library.json`

Create `fixture-library/library.json` with exactly:

```json
{
  "convention_version": "1.0",
  "engine_version": "1.0",
  "name": "fixture-library",
  "default_lang": "en",
  "sections": [
    "opening",
    "intro",
    "diagnosis",
    "product",
    "proof",
    "closing"
  ],
  "extra_asset_root": "../shared-brand"
}
```

---

## B. `manifest.md`

Create `fixture-library/manifest.md` with exactly:

```markdown
# fixture-library manifest

Single source of truth for all slide fragments and presentation assets.

## Slides

| id | file | section | title | audience | lang | kind | summary | assets | provenance |
|----|------|---------|-------|----------|------|------|---------|--------|------------|
| cover-nimbus.pt | slides/cover-nimbus.pt.html | opening | Capa Nimbus | prospect | pt | template | Co-branded cover (Nimbus x counterparty) with headline, subtitle and date over a dark background. | cover-bg.jpg, nimbus-mark.png, {client-logo} | fixture (2026-06-06) |
| cover-nimbus.en | slides/cover-nimbus.en.html | opening | Nimbus cover | prospect | en | template | Co-branded cover (Nimbus x counterparty) with headline, subtitle and date over a dark background (English). | cover-bg.jpg, nimbus-mark.png, {client-logo} | fixture (2026-06-06) |
| intro-pillars | slides/intro-pillars.html | intro | Three pillars | general | en | ready | Nimbus one-liner plus three product pillars; ships verbatim with no tokens. | - | fixture (2026-06-06) |
| problem-cards | slides/problem-cards.html | diagnosis | Problem cards | prospect | en | template | Three problem cards the audience faces plus a synthesis aside; token-dense. | - | fixture (2026-06-06) |
| how-nimbus-works | slides/how-nimbus-works.html | product | How Nimbus works | general | en | ready | Dark slide naming the Nimbus layer in three capabilities plus a callout; ships verbatim. | bg-dark.jpg | fixture (2026-06-06) |
| nimbus-divider | slides/nimbus-divider.html | product | Section divider | general | en | ready | Minimal plain-slide divider with a single statement and no header; ships verbatim. | - | fixture (2026-06-06) |
| proof-metrics | slides/proof-metrics.html | proof | Proof metrics | general | en | template | Three metric cards plus a partner mark and a sources line; metrics filled per deck. | @root/partner-mark.png | fixture (2026-06-06) |
| pricing-options | slides/pricing-options.html | product | Pricing options | prospect | en | template | Three pricing options plus a two-ways-to-buy column; filled per deck. | - | fixture (2026-06-06) |
| closing-nimbus | slides/closing-nimbus.html | closing | Closing | general | en | ready | Lean closing statement plus a contact row and wordmark; multi-asset, ships verbatim. | closing-bg.jpg, nimbus-mark.png, bg-dark.jpg | fixture (2026-06-06) |

## Assets

| file | description | used-by |
|------|-------------|---------|
| `cover-bg.jpg` | Dark branded background for cover slides (theme.css `.slide--cover`). | Cover slides |
| `bg-dark.jpg` | Dark accent background for dark-variant slides (theme.css `.slide--dark`). | Dark slides |
| `closing-bg.jpg` | Dark branded background for closing slides (theme.css `.slide--closing`). | Closing slide |
| `nimbus-mark.png` | Nimbus wordmark, white, transparent. | Cover and closing slides |
```

> The `@root/partner-mark.png` entry resolves from `extra_asset_root` (`../shared-brand`) and intentionally has NO `## Assets` row (the assets table inventories library-root assets only). This exercises extra-root resolution.

---

## C. `presets.md`

Create `fixture-library/presets.md` with exactly:

````markdown
# fixture-library presets

## Presets

<!-- One entry per named composition: a prose intro paragraph followed by a fenced YAML block. -->

### nimbus-intro-en

First-touch Nimbus introduction for a prospect (English). Opens on the co-branded cover, frames the three pillars, names the problems, shows how Nimbus works, proves it with metrics, and closes. Use this when the audience is meeting Nimbus for the first time; swap `pricing-options` in only when commercials are on the table.

```yaml
preset: nimbus-intro-en
lang: en
title: Nimbus Introduction
audience: prospect
slides: [cover-nimbus.en, intro-pillars, problem-cards, how-nimbus-works, nimbus-divider,
         proof-metrics, closing-nimbus]
```

### nimbus-intro-pt

Brazilian-Portuguese first-touch introduction. Same spine as nimbus-intro-en with the Portuguese cover.

```yaml
preset: nimbus-intro-pt
lang: pt
slides: [cover-nimbus.pt, intro-pillars, problem-cards, how-nimbus-works, nimbus-divider, proof-metrics, closing-nimbus]
```
````

> The `nimbus-intro-en` `slides:` list intentionally wraps across two physical lines to exercise the multi-line list parser. The `nimbus-intro-pt` list is single-line and mixes a `pt` cover with `en` body slides — valid (audience/lang are advisory; the document `lang` is `pt`).

---

## D. `as-built.md`

Create `fixture-library/as-built.md` with exactly:

````markdown
# fixture-library as-built log

## As-built log

<!-- One entry per assembled deck, appended by the engine on every assembly. -->

---

### 2026-06-06-seed-demo

```yaml
date: 2026-06-06
timestamp: 2026-06-06T09:00:00
output: ../decks/seed-demo/nimbus-seed-demo.html
preset: nimbus-intro-en
slides: [cover-nimbus.en, intro-pillars, problem-cards, how-nimbus-works, nimbus-divider, proof-metrics, closing-nimbus]
lang: en
title: Nimbus Introduction
accent: -
client_logo: -
engine_version: "1.0"
deviations: -
intent: Seed historical entry for fixture validation — a clean preset assembly, no deviations.
upstream: n/a
```
````

> This one seeded entry lets a reproduction test (DT5) read a known composition and re-assemble it. Its `slides` list equals the `nimbus-intro-en` preset exactly (no deviations) so reproduction parity is the cleanest possible case.
>
> **`deviations: -`** (NOT `[]`) per convention-spec § 4.1: an empty deviation set is the single `-` scalar meaning "none"; `[]` would parse as a one-element flow list containing the empty string under the library-YAML subset.
> **`title: Nimbus Introduction`** is the RESOLVED title (from the `nimbus-intro-en` preset's `title:` — they MUST agree); `accent`/`client_logo` are `-` because this clean assembly passed neither flag (convention-spec § 4.2).
> **The `output` path is a HISTORICAL SENTINEL** (convention-spec § 4.2 / RV-5): it records where the deck went; the file need NOT exist on disk. The DT5 reproduction test re-assembles fresh and runs the § 4.4 property checks — it does NOT diff against any committed expected-output (there is none).

---

## E. `base.html` and `theme.css`

### E.1 `base.html`

Create `fixture-library/base.html` with exactly:

```html
<!DOCTYPE html>
<html lang="{{LANG}}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
<style>
/* {{ACCENT_CSS}} */
/* {{THEME_CSS}} */
</style>
</head>
<body>
<!-- {{SLIDES}} -->
</body>
</html>
```

> The fixture `base.html` deliberately OMITS the CDN font/icon links so the fixture renders fully offline (no network needed for tests). The 5 markers are exactly present. Engine validation of all 5 markers is exercised. Per RV-16: only the 5 markers are CONTRACTUAL — the CDN `<link>` block (present in the convention-spec reference `base.html`, absent here) is optional chrome, not a marker; the engine validates only the 5 markers, never the CDN lines.

### E.2 `theme.css`

Create `fixture-library/theme.css` with exactly the following. It is a small but complete design system: it defines every class the fixture fragments use, the `@page` print frame, the variant backgrounds (which exercise CSS-driven asset resolution for cover/dark/closing), and the `--client-accent` hook.

```css
/* fixture-library theme.css — synthetic design system for engine tests */
:root {
  --bg: #0E1116;
  --bg-soft: #F7F8FA;
  --fg: #11151B;
  --fg-invert: #FFFFFF;
  --muted: #5B6470;
  --brand: #3A7BD5;
  --client-accent: #3A7BD5;
}

@page { size: 1280px 720px; margin: 0; }

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: "Segoe UI", system-ui, sans-serif;
  color: var(--fg);
  background: #222;
}

.slide {
  position: relative;
  width: 1280px;
  height: 720px;
  padding: 72px 96px;
  background: #FFFFFF;
  color: var(--fg);
  overflow: hidden;
  page-break-after: always;
}

.slide--soft { background: var(--bg-soft); }

.slide--dark {
  background: var(--bg) url('assets/bg-dark.jpg') center/cover no-repeat;
  color: var(--fg-invert);
}

.slide--cover {
  background: var(--bg) url('assets/cover-bg.jpg') center/cover no-repeat;
  color: var(--fg-invert);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.slide--closing {
  background: var(--bg) url('assets/closing-bg.jpg') center/cover no-repeat;
  color: var(--fg-invert);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.dark-bg-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.35);
  z-index: 0;
}
.slide--dark > *:not(.dark-bg-overlay) { position: relative; z-index: 1; }

.slide-header { margin-bottom: 32px; }
.kicker { font-size: 16px; letter-spacing: 2px; text-transform: uppercase; color: var(--client-accent); }
.slide-title { font-size: 40px; font-weight: 800; margin-top: 8px; }
.slide-subtitle { font-size: 20px; color: var(--muted); margin-top: 12px; }
.slide--dark .slide-subtitle { color: rgba(255,255,255,0.8); }

.slide-body { font-size: 18px; }

.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 24px; }
.card { padding: 24px; border: 1px solid rgba(0,0,0,0.1); border-radius: 12px; background: rgba(255,255,255,0.6); }
.slide--dark .card { border-color: rgba(255,255,255,0.2); background: rgba(255,255,255,0.06); }
.card-icon { font-size: 28px; color: var(--client-accent); }
.card-title { font-size: 20px; font-weight: 700; margin: 12px 0 8px; }
.card-body { font-size: 16px; color: var(--muted); }
.slide--dark .card-body { color: rgba(255,255,255,0.75); }

.aside-note { margin-top: 28px; font-size: 16px; color: var(--muted); }
.dark-callout { margin-top: 28px; font-size: 18px; color: rgba(255,255,255,0.9); }

.cover-logos { display: flex; align-items: center; gap: 20px; margin-bottom: 28px; }
.cover-mark { height: 48px; }
.cover-logos-sep { font-size: 28px; opacity: 0.6; }
.cover-client { height: 48px; }
.cover-title { font-size: 56px; font-weight: 900; }
.cover-subtitle { font-size: 22px; opacity: 0.8; margin-top: 16px; }
.cover-date { font-size: 18px; opacity: 0.6; margin-top: 24px; }

.divider-statement { font-size: 44px; font-weight: 800; color: var(--fg-invert); }

.sources-line { margin-top: 24px; font-size: 14px; color: var(--muted); }
.partner-mark { height: 32px; margin-top: 24px; opacity: 0.85; }

.closing-statement { font-size: 52px; font-weight: 900; }
.closing-contacts { margin-top: 32px; font-size: 18px; opacity: 0.85; }
.closing-wordmark { height: 40px; margin-top: 32px; }

.slide-number {
  position: absolute;
  bottom: 28px;
  right: 32px;
  font-size: 14px;
  color: var(--muted);
}
.slide--dark .slide-number, .slide--cover .slide-number, .slide--closing .slide-number { color: rgba(255,255,255,0.6); }
```

---

## F. Asset placeholders

The engine tests need the asset FILES to exist (the engine validates existence and copies them). Exact image content does not matter — create small valid placeholder images.

Create each of these as a placeholder image file (any valid JPG/PNG; a 16x16 solid-color image is sufficient):

| Path | Format |
|------|--------|
| `fixture-library/assets/cover-bg.jpg` | JPG |
| `fixture-library/assets/bg-dark.jpg` | JPG |
| `fixture-library/assets/closing-bg.jpg` | JPG |
| `fixture-library/assets/nimbus-mark.png` | PNG |
| `../shared-brand/partner-mark.png` (sibling of `fixture-library/`) | PNG |

**Executor method (Python, stdlib only — no Pillow):** write these exact byte sequences to create minimal valid files. A 1x1 PNG and a 1x1 JPG:

```python
import base64, os

PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
# Minimal valid JPEG (1x1, white).
JPG_1x1 = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
    "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAAB"
    "AAAAAAAAAAAAAAAAAAAAAP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AfwD/2Q=="
)

def write_img(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)

base = "fixture-library"
write_img(os.path.join(base, "assets", "cover-bg.jpg"), JPG_1x1)
write_img(os.path.join(base, "assets", "bg-dark.jpg"), JPG_1x1)
write_img(os.path.join(base, "assets", "closing-bg.jpg"), JPG_1x1)
write_img(os.path.join(base, "assets", "nimbus-mark.png"), PNG_1x1)
write_img(os.path.join("shared-brand", "partner-mark.png"), PNG_1x1)
```

> The byte sequences above are verified valid (the PNG is a 1x1 RGBA image; the JPG is a 160-byte 1x1 baseline JPEG). The engine only checks existence and copies the bytes — it never decodes them — so any valid placeholder image works if you prefer to substitute.

---

## G. The 9 fragment files (`slides/`)

Create each file VERBATIM. Tokens, HTML comments, variant classes, and the presence/absence of the slide-number div are all load-bearing — copy exactly.

### G.1 `slides/cover-nimbus.pt.html`  (template, opening, pt, unnumbered, client-lockup)

```html
<!-- provenance: fixture (2026-06-06) — co-branded prospect cover (Nimbus x {client}) -->
<section class="slide slide--cover">
  <div class="cover-logos">
    <img src="assets/nimbus-mark.png" alt="Nimbus" class="cover-mark" onerror="this.style.display='none'">
    <span class="cover-logos-sep">x</span>
    <!-- CLIENT_LOGO_SRC: path to the counterparty's logo (drop the file into the deck's assets/ and reference it, e.g. "assets/{client}-logo.png"). -->
    <!-- CLIENT_NAME: the counterparty's display name, used as alt text and the text fallback. -->
    <img src="{{CLIENT_LOGO_SRC}}" alt="{{CLIENT_NAME}}" class="cover-client" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
    <span class="cover-client-fallback" style="display:none">{{CLIENT_NAME}}</span>
  </div>
  <!-- COVER_TITLE: deck headline, 3-6 words — the core promise for this occasion. -->
  <div class="cover-title">{{COVER_TITLE}}</div>
  <!-- COVER_SUBTITLE: one sentence positioning the promise for THIS counterparty. -->
  <div class="cover-subtitle">{{COVER_SUBTITLE}}</div>
  <!-- COVER_DATE: month and year of the presentation (e.g., "Junho de 2026"). -->
  <div class="cover-date">{{COVER_DATE}}</div>
</section>
```

### G.2 `slides/cover-nimbus.en.html`  (template, opening, en, unnumbered, client-lockup)

```html
<!-- provenance: fixture (2026-06-06) — co-branded prospect cover (Nimbus x {client}) (English) -->
<section class="slide slide--cover">
  <div class="cover-logos">
    <img src="assets/nimbus-mark.png" alt="Nimbus" class="cover-mark" onerror="this.style.display='none'">
    <span class="cover-logos-sep">x</span>
    <!-- CLIENT_LOGO_SRC: path to the counterparty's logo (drop the file into the deck's assets/ and reference it, e.g. "assets/{client}-logo.png"). -->
    <!-- CLIENT_NAME: the counterparty's display name, used as alt text and the text fallback. -->
    <img src="{{CLIENT_LOGO_SRC}}" alt="{{CLIENT_NAME}}" class="cover-client" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
    <span class="cover-client-fallback" style="display:none">{{CLIENT_NAME}}</span>
  </div>
  <!-- COVER_TITLE: deck headline, 3-6 words — the core promise for this occasion. -->
  <div class="cover-title">{{COVER_TITLE}}</div>
  <!-- COVER_SUBTITLE: one sentence positioning the promise for THIS counterparty. -->
  <div class="cover-subtitle">{{COVER_SUBTITLE}}</div>
  <!-- COVER_DATE: month and year of the presentation (e.g., "June 2026"). -->
  <div class="cover-date">{{COVER_DATE}}</div>
</section>
```

### G.3 `slides/intro-pillars.html`  (ready, intro, en, numbered, no assets)

```html
<!-- provenance: fixture (2026-06-06) — ready intro slide, no tokens -->
<section class="slide slide--soft">
  <div class="slide-header">
    <div class="kicker">What Nimbus is</div>
    <div class="slide-title">One layer that learns the operation and compounds on it</div>
    <div class="slide-subtitle">Nimbus runs over the sources you already have, absorbs the repetitive work, and hands the operation back ready for decisions.</div>
  </div>
  <div class="slide-body">
    <div class="grid-3">
      <div class="card">
        <div class="card-title">Continuous</div>
        <div class="card-body">Work that took weeks runs in hours. The monthly cycle stops being the bottleneck.</div>
      </div>
      <div class="card">
        <div class="card-title">Online visibility</div>
        <div class="card-body">Position, runway, and scenarios on demand — not after close. The answer arrives when the question is asked.</div>
      </div>
      <div class="card">
        <div class="card-title">Knowledge in the system</div>
        <div class="card-body">Every rule and exception lives in the layer. The operation stops depending on who sits in the chair.</div>
      </div>
    </div>
    <div class="aside-note">The layer is one. What changes per customer is the configuration around the real operation.</div>
  </div>
  <div class="slide-number">{{N}}</div>
</section>
```

### G.4 `slides/problem-cards.html`  (template, diagnosis, en, numbered, no assets, token-dense)

```html
<!-- provenance: fixture (2026-06-06) — token-dense template; fill every {{TOKEN}} in the output -->
<section class="slide slide--soft">
  <div class="slide-header">
    <!-- PROBLEM_KICKER: short framing of the audience's situation (e.g., "A group in formation"). -->
    <div class="kicker">{{PROBLEM_KICKER}}</div>
    <!-- PROBLEM_TITLE: headline naming the structural difficulty they face, 6-10 words. -->
    <div class="slide-title">{{PROBLEM_TITLE}}</div>
    <!-- PROBLEM_SUBTITLE: 1-2 sentences grounding the difficulty in their reality. -->
    <div class="slide-subtitle">{{PROBLEM_SUBTITLE}}</div>
  </div>
  <div class="slide-body">
    <div class="grid-3">
      <!-- 3 cards. Each: a headline (4-8 words) + a 2-3 sentence description citing the audience's OWN situation. -->
      <div class="card">
        <div class="card-title">{{PROBLEM_1_TITLE}}</div>
        <div class="card-body">{{PROBLEM_1_DESC}}</div>
      </div>
      <div class="card">
        <div class="card-title">{{PROBLEM_2_TITLE}}</div>
        <div class="card-body">{{PROBLEM_2_DESC}}</div>
      </div>
      <div class="card">
        <div class="card-title">{{PROBLEM_3_TITLE}}</div>
        <div class="card-body">{{PROBLEM_3_DESC}}</div>
      </div>
    </div>
    <!-- PROBLEM_ASIDE: one-sentence synthesis of what their operation needs. -->
    <div class="aside-note">{{PROBLEM_ASIDE}}</div>
  </div>
  <div class="slide-number">{{N}}</div>
</section>
```

### G.5 `slides/how-nimbus-works.html`  (ready, product, en, numbered, dark, library asset)

```html
<!-- provenance: fixture (2026-06-06) — ready dark slide; background bg-dark.jpg is listed in the manifest assets cell -->
<section class="slide slide--dark">
  <div class="dark-bg-overlay"></div>
  <div class="slide-header">
    <div class="kicker">How Nimbus works</div>
    <div class="slide-title">An intelligence layer that learns the operation and composes on it</div>
    <div class="slide-subtitle">Not another system to operate. A layer that runs over existing sources, absorbs the repetitive work, and returns the operation ready for decisions.</div>
  </div>
  <div class="slide-body">
    <div class="grid-3">
      <div class="card">
        <div class="card-title">Speed</div>
        <div class="card-body">Reconciliation and close that took weeks run in hours.</div>
      </div>
      <div class="card">
        <div class="card-title">Online view</div>
        <div class="card-body">Position and scenarios on demand, not post-close.</div>
      </div>
      <div class="card">
        <div class="card-title">Knowledge retained</div>
        <div class="card-body">Every rule and exception is recorded in the layer.</div>
      </div>
    </div>
    <div class="dark-callout">The layer is one. What changes per customer is the configuration around their real operation.</div>
  </div>
  <div class="slide-number">{{N}}</div>
</section>
```

### G.6 `slides/nimbus-divider.html`  (ready, product, en, numbered, plain slide, no header, no assets)

```html
<!-- provenance: fixture (2026-06-06) — minimal plain-slide divider, no header, exercises the bare variant -->
<section class="slide slide--dark">
  <div class="dark-bg-overlay"></div>
  <div class="slide-body">
    <div class="divider-statement">From operation to decision.</div>
  </div>
  <div class="slide-number">{{N}}</div>
</section>
```

### G.7 `slides/proof-metrics.html`  (template, proof, en, numbered, extra-root asset, token-dense)

```html
<!-- provenance: fixture (2026-06-06) — template; references @root/partner-mark.png from the extra asset root -->
<section class="slide">
  <div class="slide-header">
    <!-- PROOF_KICKER: short framing for the proof slide. -->
    <div class="kicker">{{PROOF_KICKER}}</div>
    <!-- PROOF_TITLE: headline for the proof, 5-9 words. -->
    <div class="slide-title">{{PROOF_TITLE}}</div>
  </div>
  <div class="slide-body">
    <div class="grid-3">
      <!-- 3 metric cards. Each: a metric value/label + a one-line explanation. -->
      <div class="card">
        <div class="card-title">{{METRIC_1_VALUE}}</div>
        <div class="card-body">{{METRIC_1_DESC}}</div>
      </div>
      <div class="card">
        <div class="card-title">{{METRIC_2_VALUE}}</div>
        <div class="card-body">{{METRIC_2_DESC}}</div>
      </div>
      <div class="card">
        <div class="card-title">{{METRIC_3_VALUE}}</div>
        <div class="card-body">{{METRIC_3_DESC}}</div>
      </div>
    </div>
    <img src="assets/partner-mark.png" alt="Partner" class="partner-mark" onerror="this.style.display='none'">
    <!-- SOURCES_LINE: numbered sources backing the metrics above. -->
    <div class="sources-line">{{SOURCES_LINE}}</div>
  </div>
  <div class="slide-number">{{N}}</div>
</section>
```

> NOTE the fragment `<img src="assets/partner-mark.png">` references the asset by its leaf name under the output's `assets/` — the engine copies `@root/partner-mark.png` INTO the deck's sibling `assets/` as `partner-mark.png`, so the relative reference resolves in the output. This is the same pattern tecer uses for cross-root assets.

### G.8 `slides/pricing-options.html`  (template, product, en, numbered, no assets)

```html
<!-- provenance: fixture (2026-06-06) — template pricing slide, no assets -->
<section class="slide slide--soft">
  <div class="slide-header">
    <!-- PRICING_TITLE: headline for the pricing slide, 4-8 words. -->
    <div class="slide-title">{{PRICING_TITLE}}</div>
    <!-- PRICING_SUBTITLE: one sentence on how pricing scales. -->
    <div class="slide-subtitle">{{PRICING_SUBTITLE}}</div>
  </div>
  <div class="slide-body">
    <div class="grid-3">
      <div class="card">
        <!-- TIER_1_NAME / TIER_1_PRICE / TIER_1_DESC: name, price, and one-line scope of the first option. -->
        <div class="card-title">{{TIER_1_NAME}} — {{TIER_1_PRICE}}</div>
        <div class="card-body">{{TIER_1_DESC}}</div>
      </div>
      <div class="card">
        <div class="card-title">{{TIER_2_NAME}} — {{TIER_2_PRICE}}</div>
        <div class="card-body">{{TIER_2_DESC}}</div>
      </div>
      <div class="card">
        <div class="card-title">{{TIER_3_NAME}} — {{TIER_3_PRICE}}</div>
        <div class="card-body">{{TIER_3_DESC}}</div>
      </div>
    </div>
    <!-- PRICING_ASIDE: one sentence on the two ways to buy. -->
    <div class="aside-note">{{PRICING_ASIDE}}</div>
  </div>
  <div class="slide-number">{{N}}</div>
</section>
```

### G.9 `slides/closing-nimbus.html`  (ready, closing, en, numbered, multi-asset)

```html
<!-- provenance: fixture (2026-06-06) — ready closing slide; multi-asset (closing-bg.jpg + nimbus-mark.png + bg-dark.jpg) -->
<section class="slide slide--closing">
  <div class="closing-statement">Let's talk.</div>
  <div class="closing-contacts">team@nimbus.example &nbsp;|&nbsp; www.nimbus.example</div>
  <img src="assets/nimbus-mark.png" alt="Nimbus" class="closing-wordmark" onerror="this.style.display='none'">
  <div class="slide-number">{{N}}</div>
</section>
```

> `closing-nimbus` lists THREE assets in its manifest cell (`closing-bg.jpg, nimbus-mark.png, bg-dark.jpg`) — `closing-bg.jpg` (CSS background via `.slide--closing`), `nimbus-mark.png` (the `<img>`), and `bg-dark.jpg` (listed to exercise the multi-asset copy path even though this fragment does not visually use it). This makes it the multi-asset edge case: the engine MUST copy all three.

---

## H. Post-creation self-check (executor runs, no engine needed)

After creating every file, verify (stdlib Python or shell):

1. `library.json` parses as JSON and has all 6 required keys.
2. `manifest.md` `## Slides` has exactly 9 data rows, each with exactly 10 `|`-cells.
3. Every `file` value in the manifest exists under `slides/` (9 files).
4. Every bare asset filename in any `assets` cell exists under `assets/` (`cover-bg.jpg`, `bg-dark.jpg`, `closing-bg.jpg`, `nimbus-mark.png`).
5. `../shared-brand/partner-mark.png` exists.
6. `presets.md` contains 2 fenced `yaml` blocks; `as-built.md` contains 1.
7. No fragment in `slides/` contains the strings `<head`, `<style`, `<script`, `<html`, or `<body` (the full convention-spec § 6.3 / § 8 check-12 purity set).
8. Both covers (`cover-nimbus.pt.html`, `cover-nimbus.en.html`) contain NO `slide-number` div; all 7 other fragments contain exactly one.
9. Section headings are EXACT case (per RV-4): `manifest.md` has `## Slides` and `## Assets` (not `## slides`); `presets.md` has `## Presets`; `as-built.md` has `## As-built log`.
10. The manifest data rows carry NO literal `|` inside any cell (per RV-2), and every required cell (`id,file,section,title,lang,kind,summary`) is non-empty (per RV-14); every `kind` is exactly `ready` or `template` and every `lang` is lowercase (per RV-4).
11. **Round-trip (per RV-1):** parsing the seed as-built entry and both presets under the library-YAML subset (convention-spec § 4.1) yields: seed `deviations` == none (the `-` scalar, NOT `[]`/`['']`), `engine_version` == `1.0` (quotes stripped), `slides` a 7-id list; both presets' `slides` parse to 7 ids each (the wrapped `nimbus-intro-en` list and the single-line `nimbus-intro-pt` list). This confirms what the engine writes it can read back.

These checks confirm the fixture is structurally valid BEFORE the engine exists. The engine workstream then runs the engine against this fixture as its first verification gate.

---

## I. Negative-case matrix (per fixture-negative-cases direction)

The fixture on disk STAYS a single VALID library. This matrix is the negative-test contract: each row is a PROGRAMMATIC mutation workstream 2's test task applies to an in-memory / temp copy of the valid fixture, plus the EXACT expected error class/message pattern. **No broken libraries are shipped on disk** — the tests mutate, assert the failure, and discard. One row per validation rule in convention-spec § 8 (rule numbers cross-referenced). Each ERROR-verdict rule MUST `die()` (exit 1) with a message matching the pattern; WARNING-verdict rules MUST proceed AND emit the warning.

| § 8 rule | Mutation applied to the valid fixture | Expected verdict | Error/message pattern (regex-ish) |
|----------|----------------------------------------|------------------|-----------------------------------|
| 1 | Delete `theme.css` (a REQUIRED artifact) | ERROR | `theme.css not found` |
| 2a | Lowercase the `## Slides` heading to `## slides` | ERROR | `(?i)slides .*heading|section heading` (case-sensitive heading rejected) |
| 2b | Rename column header `id`→`Id` | ERROR | `header.*mismatch` |
| 4 | Delete one cell from a slide row (9 cells) | ERROR | `(9 columns|cells).*expected 10|line \d+` |
| 5 | Insert a literal `\|` into `cover-nimbus.en`'s `summary` | ERROR | `pipe.*cover-nimbus\.en|line \d+` (cites row id or line) |
| 6 | Blank the `title` cell of `intro-pillars` | ERROR | `empty.*required.*intro-pillars|title` |
| 7 | Set `cover-nimbus.pt` `kind` to `Template` | ERROR | `kind.*Template.*not in .*ready.*template` |
| 8 | Set `intro-pillars` `lang` to `EN` | ERROR | `lang.*EN` (uppercase rejected) |
| 9 | Set `proof-metrics` `section` to `proofs` (not in `library.json`) | ERROR | `section.*proofs.*not declared` |
| 10 | Duplicate the `intro-pillars` id onto a second row | ERROR | `duplicate.*id.*intro-pillars` |
| 11 | Delete `slides/proof-metrics.html` (manifest row stays) | ERROR | `fragment.*missing.*proof-metrics|not found` |
| 12 | Add a `<style>` block inside `intro-pillars.html` | ERROR | `(?i)fragment.*<style|purity` |
| 13 | Delete `assets/nimbus-mark.png` (referenced by covers) | ERROR | `asset.*nimbus-mark\.png.*not found` |
| 14 | Add a `@root/x.png` asset entry, set `library.json` `extra_asset_root: null` | ERROR | `@root.*extra_asset_root|no extra_asset_root` |
| 15 | Assemble a preset including a `{client-logo}`-bearing cover with NO `--client-logo` | ERROR | `\{client-logo\}.*--client-logo` |
| 16 | Put a comma inside an asset filename (`nim,bus-mark.png`) | ERROR | `asset.*comma|not found` (mis-split → unresolved) |
| 17 | Remove the `nimbus-mark.png` row from `## Assets` (file still on disk) | WARNING (proceeds) | warns `(?i)assets.*row.*nimbus-mark` ; assembly still succeeds |
| 18 | Delete the `<!-- {{SLIDES}} -->` marker from `base.html` | ERROR | `base\.html.*missing.*marker.*SLIDES` |
| 19 | (covered by rule 1) Delete `theme.css` | ERROR | `theme.css not found` |
| 20 | Set `library.json` `convention_version: "2.0"` (unsupported MAJOR) | ERROR | `convention.*2\.0.*unsupported|major` |
| 21 | Set `convention_version: "1.9"` (MINOR ahead) | WARNING (proceeds) | warns `(?i)minor` ; assembly succeeds |
| 22 | Set `library.json` `engine_version: "9.9"` (≠ engine stamp) | WARNING (proceeds) | warns `(?i)engine.*version.*drift|stamp` ; assembly succeeds |
| 23 | (round-trip) Hand-write an as-built entry with `deviations: [modified: x]` (`:` in flow elem) | ERROR | round-trip / parse failure on the `:`-in-flow-element |
| 24 | `--check` the un-filled seed reproduction (templates unfilled) | reports (exit 1) | lists `{{TOKEN}}`s ; exit 1 |

Rule 3 (positional separator skip) is a parse step, not a die()-able rule — it is covered by self-check § H step 2 (exactly 9 data rows parsed). The version-mismatch (rules 20-22), `@root`-without-root (14), and `{client-logo}`-without-flag (15) cases close the F-4 "no negative fixtures" gap the review identified.

---

## README-FOR-AGENTS.md and CLAUDE.md for the fixture

### `fixture-library/CLAUDE.md`

Create with exactly:

```markdown
# CLAUDE.md — fixture-library

Read `README-FOR-AGENTS.md` in this folder before assembling any deck. It is the
self-contained agent guide for this slide library.
```

### `fixture-library/README-FOR-AGENTS.md`

Create from the convention spec § 5.1 template, with the fixture's specifics filled in. Use exactly:

````markdown
# Assembling Decks From This Slide Library — Agent Guide

You are pointed at a **slide library**: a folder from which you assemble a presentation
deck. Everything you need is in this folder. This guide is self-contained — read it
fully, then assemble.

## 1. What this library is

This is a synthetic fixture library for the fictional product "Nimbus". Its slides carry
generic, brand-neutral copy and exist to exercise the assembly engine. There is NO real
client data here — slides are reusable inputs only.

This library follows the RBTV slide-library convention. Its machine-readable contract:
- `library.json` — convention version, configuration, and the ordered list of sections.
- `manifest.md` — every slide with its metadata (the source of truth).
- `presets.md` — named, ready-to-use compositions.
- `as-built.md` — the log of past assemblies (the engine appends here automatically).

## 2. How to read the manifest

Open `manifest.md`. The `## Slides` table has one row per slide with these columns:
`id | file | section | title | audience | lang | kind | summary | assets | provenance`.

- **id** is the contract — you select slides by id.
- **section** groups slides by narrative role (sections are ordered in `library.json`).
- **lang** is the slide's language — filter to the deck's language.
- **kind** is `ready` (ships verbatim) or `template` (you MUST fill `{{TOKEN}}` slots).
- **summary** distinguishes a slide from its siblings — read it to choose between similar slides.
- **audience** is an advisory hint, NOT a hard filter.

## 3. How to choose a composition

You were given a deck **intent**: audience, occasion, language. Choose one of:
- **A preset** — open `presets.md`. Each preset has a prose intro saying WHEN to use it.
  If one matches your intent, use its `slides` list and `lang`.
- **A custom order** — otherwise build an ordered list of ids yourself from the manifest:
  filter by `lang`, pick one opening / closing, and select body slides whose `section`
  and `summary` fit the occasion.

For bilingual concepts pick the right `.{lang}` id (`cover-nimbus.pt` vs `cover-nimbus.en`).
Name fully-qualified ids — `--lang` sets the document language only; it never rewrites or
auto-selects a `.{lang}` id. Unsuffixed ids (e.g. `intro-pillars`) are language-neutral.

## 4. How to assemble (the exact tool invocation)

Run the engine that ships in this folder. From the library directory:

```bash
# From a preset:
python assemble.py --preset nimbus-intro-en --out ../decks/demo/nimbus-demo.html [--lang en] [--title "Title"] [--accent "#3A7BD5"] [--client-logo path/to/logo.png]

# From an explicit id order:
python assemble.py --slides cover-nimbus.en,intro-pillars,problem-cards,closing-nimbus --out ../decks/demo/nimbus-demo.html [--lang en]
```

The engine: resolves the order, concatenates `base.html` + the chosen fragments, inlines
`theme.css`, renumbers slide numbers, injects language/title/accent, copies each fragment's
assets into a sibling `assets/` folder beside the output, prints the list of unfilled
`{{TOKEN}}`s, and appends an entry to `as-built.md` automatically (recording the resolved
`slides`, `lang`, `title`, `accent`, and `client_logo` so the deck is reproducible).

**Write the deck OUTSIDE this library** — never `--out` into this folder. The default output
scheme is `../decks/{slug}/{deck}.html` relative to this library (here `../decks/demo/nimbus-demo.html`).

**Confirm the log:** after assembly, open `as-built.md` and verify your new entry was appended
(the last `### {date}-{slug}` block). If missing, the assembly did not complete — do not ship.

## 5. The creative pass — filling tokens

After assembly, the engine lists every unfilled `{{TOKEN}}`. Fill them in the OUTPUT file
(never edit the fragments):
- Tokens are `{{SCREAMING_SNAKE_CASE}}`. Each one in a template slide is preceded by an
  HTML comment stating what to author — follow that comment.
- `ready` slides have no tokens — leave them verbatim.
- For a per-deck client logo/name, fill `{{CLIENT_LOGO_SRC}}` (drop the logo file into the
  output's `assets/`) and `{{CLIENT_NAME}}`.
- `{{N}}` slide numbers are already filled by the engine — do not touch them.

Verify when done:
```bash
python assemble.py --check ../decks/demo/nimbus-demo.html   # MUST report zero unfilled tokens
```

## 6. Human / agent judgment — NOT automated

These remain your responsibility; the engine does not enforce them:
- **Freshness:** this fixture carries no time-sensitive facts — nothing to verify.
- **Leakage rule:** slides carry ZERO client data. Read exemplar decks (the `provenance`
  column) to learn a template's SHAPE — never copy their content into a fragment or another
  deck. Client copy enters ONLY this deck's output. Every fragment here has a synthetic
  `provenance` (`fixture (...)`) with no real exemplar deck on disk — author tokens from the
  template's authoring comments and your intent.
- **Upstream proposals:** if you improve a `ready` slide during a build, propose it back:
  update `slides/{id}.html` + its manifest row + regenerate the catalog, and note it in your
  as-built entry's `upstream` field. Client-specific copy is never upstreamed.
````
