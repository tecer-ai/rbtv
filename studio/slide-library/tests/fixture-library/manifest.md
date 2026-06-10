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
