---
inputs: "--html (required) HTML artifact path; --tokens (required) brand-pack token file; --profile (required) library page-type profile."
outcome: "Exit 0 when the HTML conforms to brand-pack tokens and the library profile's deterministic checks; exit 1 with a machine-readable violation list otherwise. No owner contact."
outputs: "JSON object with a `violations` array; each entry has `check_id`, `location`, `observed`, `expected`. Empty array on conformity."
exposes-cli:
  - visual-check-cli
---

# visual-check

Deterministic HTML-against-tokens-and-library checker. Any agent producing HTML loads this
capability and runs the CLI; it makes no owner contact.

Full flag reference is the tool's own `--help` — this file does not restate it.

## Entry point

```bash
python3 tool/visual-check.py --html <artifact.html> --tokens <palette.json> --profile <page-type.md>
```

## Procedure

1. Pass the three inputs as flags. Per-user brand values arrive only through `--tokens`; page-type
   floors and ceilings arrive only through `--profile`. Never substitute a remembered number.
2. Read stdout: a JSON object with a `violations` array. Exit 0 means the array is empty. Exit 1
   means at least one violation. Exit 2 means a usage or input-file error.
3. Each violation names `check_id`, `location`, `observed`, `expected`. Route the list to the
   consumer (presentation verification, `html-review`, or the producing agent). Do not grade by eye.
4. If a profile field a check needs is absent, that sub-assertion is skipped — never invent a
   default floor, ceiling, token, or typeface.

## Check catalog

Harvest row identifiers in parentheses. The CLI emits exactly these `check_id` values:

| check_id | harvest | asserts |
|---|---|---|
| palette | A-1, E-3, C-1 | Every colour in CSS/SVG is a brand-pack token or a derived tint the profile allows; no training-mean placeholder gradient in `:root` |
| fonts | A-3, T-4 | Declared families are a subset of the brand-pack pairing; no system-default stack as the only face |
| sizing | T-1, T-3, E-1, E-2 | Declared sizes meet the profile's floors (body, caption/node/cell/icon — whichever the profile names) |
| banned-css | A-4, G-1, G-2 | Named attractors in source: emoji-as-icon, `aspect-ratio` on print-critical nodes, transforms on positioned elements, pseudo-element structural dividers, missing print/`@page` block when the profile requires one |
| token-literals | role-token lint | Skin values go through `var(--token)` when the profile requires the library token contract |
| grid-ceilings | D-1, D-2, L-2, L-3 | Card counts, zone counts, and grid column counts against the profile's numeric ceilings |
| cover-closing | B-4, V-4 | Cover and closing declared styles match on background, type, and layout (the closing may add contact details) |

## What this checker does NOT assert

This checker does NOT assert hierarchy (one idea per slide, title-states-the-takeaway),
distinctiveness of the picked art direction, chart communication beyond numeric size floors,
team-card bio-depth parity, aesthetic taste, or motif fidelity. Those belong to render inspection
of screenshots, never to this script.

Scoring, taxonomy, and any gating critic are out of scope.

## Failure modes

- A missing or unreadable input file → exit 2, message on stderr, no success JSON.
- A profile that omits a named floor (node text, cell text, icon size, card/zone ceilings, allowed
  tints) → that sub-assertion is skipped, not defaulted.
- Conformity here is not a taste pass. Render inspection still runs after a clean check.
