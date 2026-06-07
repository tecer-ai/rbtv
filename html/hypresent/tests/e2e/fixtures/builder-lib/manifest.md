# builder-lib manifest

Single source of truth for all slide fragments and presentation assets.

## Slides

| id | file | section | title | audience | lang | kind | summary | assets | provenance |
|----|------|---------|-------|----------|------|------|---------|--------|------------|
| cover-e2e.pt | slides/cover-e2e.pt.html | opening | Capa E2E | prospect | pt | template | Co-branded cover with headline and date. | cover-bg.jpg, logo.png, {client-logo} | fixture (2026-06-06) |
| cover-e2e.en | slides/cover-e2e.en.html | opening | E2E Cover | prospect | en | template | Co-branded cover with headline and date (English). | cover-bg.jpg, logo.png, {client-logo} | fixture (2026-06-06) |
| intro-e2e | slides/intro-e2e.html | body | Introduction | general | en | ready | One-liner intro slide; ships verbatim with no tokens. | - | fixture (2026-06-06) |
| closing-e2e | slides/closing-e2e.html | closing | Closing | general | en | ready | Minimal closing statement; ships verbatim. | cover-bg.jpg | fixture (2026-06-06) |

## Assets

| file | description | used-by |
|------|-------------|---------|
| `cover-bg.jpg` | Dark branded background for cover slides. | Cover slides, closing |
| `logo.png` | E2E wordmark, white, transparent. | Cover slides |
