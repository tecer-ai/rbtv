You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context; do not consult other files except the ones in the allowlist and the binding-source you are instructed to copy from.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate code/content by the exact strings quoted in this file. NEVER use line numbers — they go stale.

# PB-T1 — Build the fixture library VERBATIM

## Objective
Create the synthetic `fixture-library` exactly as specified in `fixture-spec.md`, plus run its §H self-check. This fixture is what the engine (PB-T2) is verified against. Content is LITERAL — copy character-for-character.

## FILE ALLOWLIST
- ✚ create all files under `html/slide-library/tests/fixture-library/` per the tree below.
- ✚ create `html/slide-library/tests/shared-brand/partner-mark.png` (the extra-root sibling).
- ✗ create NOTHING else. Do NOT create `html/slide-library/tests/fixture-library/assemble.py` (the engine vendoring is a later task).

## What to create (the binding source)
The file `html/slide-library/docs/fixture-spec.md` contains, in sections A–G plus the two README/CLAUDE blocks at its end, the EXACT verbatim content of every fixture file. READ that file and create every file it specifies, character-for-character, at the path it names — BUT rooted at `html/slide-library/tests/fixture-library/` (the spec says "recommended: `html/slide-library/tests/fixture-library/`" — use exactly that root) and the sibling extra-root at `html/slide-library/tests/shared-brand/` (the spec's `../shared-brand/` resolves as a sibling of the fixture root).

Create exactly this tree (paths relative to `html/slide-library/tests/`):
```
fixture-library/
├── library.json              (fixture-spec § A — verbatim)
├── README-FOR-AGENTS.md      (fixture-spec end block "README-FOR-AGENTS.md for the fixture" — verbatim)
├── CLAUDE.md                 (fixture-spec end block "fixture-library/CLAUDE.md" — verbatim)
├── manifest.md               (fixture-spec § B — verbatim)
├── presets.md                (fixture-spec § C — verbatim)
├── as-built.md               (fixture-spec § D — verbatim)
├── base.html                 (fixture-spec § E.1 — verbatim)
├── theme.css                 (fixture-spec § E.2 — verbatim)
├── slides/
│   ├── cover-nimbus.pt.html   (fixture-spec § G.1)
│   ├── cover-nimbus.en.html   (fixture-spec § G.2)
│   ├── intro-pillars.html     (fixture-spec § G.3)
│   ├── problem-cards.html     (fixture-spec § G.4)
│   ├── how-nimbus-works.html  (fixture-spec § G.5)
│   ├── nimbus-divider.html    (fixture-spec § G.6)
│   ├── proof-metrics.html     (fixture-spec § G.7)
│   ├── pricing-options.html   (fixture-spec § G.8)
│   └── closing-nimbus.html    (fixture-spec § G.9)
└── assets/
    ├── cover-bg.jpg           (placeholder image — fixture-spec § F)
    ├── bg-dark.jpg            (placeholder image — § F)
    ├── closing-bg.jpg         (placeholder image — § F)
    └── nimbus-mark.png        (placeholder image — § F)
shared-brand/
└── partner-mark.png           (placeholder image — § F)
```

For the FIVE image files, use the EXACT stdlib-only Python from `fixture-spec § F` (the `PNG_1x1`/`JPG_1x1` base64 + `write_img`), but adjust the `base` and the shared path so the files land at `html/slide-library/tests/fixture-library/assets/...` and `html/slide-library/tests/shared-brand/partner-mark.png`. The byte sequences are verified valid — do not substitute.

CRITICAL fidelity points (from fixture-spec, do not deviate):
- The `## Slides` and `## Assets` headings are EXACT case. The 10-column header row is `| id | file | section | title | audience | lang | kind | summary | assets | provenance |`.
- The seed as-built entry uses `deviations: -` (single dash), NOT `deviations: []`.
- Both covers carry NO `<div class="slide-number">`; the other 7 fragments carry exactly one `{{N}}`.
- `base.html` OMITS the CDN font/icon links (offline fixture) but has all 5 markers: `{{LANG}}`, `{{TITLE}}`, `/* {{ACCENT_CSS}} */`, `/* {{THEME_CSS}} */`, `<!-- {{SLIDES}} -->`.
- No fragment contains `<head`, `<style`, `<script`, `<html`, or `<body`.

## Acceptance criteria (self-verifiable — run these yourself)
Run `fixture-spec § H` checks 1–11 as a one-off stdlib Python script in the OS tempdir (NOT at workspace root — addendum rule 2). All 11 MUST pass:
1. `library.json` parses as JSON, has 6 keys (`convention_version, engine_version, name, default_lang, sections, extra_asset_root`).
2. `manifest.md` `## Slides` has exactly 9 data rows, each exactly 10 `|`-cells (after dropping leading/trailing empty cell).
3. All 9 `file` values exist under `slides/`.
4. Bare assets `cover-bg.jpg, bg-dark.jpg, closing-bg.jpg, nimbus-mark.png` exist under `assets/`.
5. `shared-brand/partner-mark.png` exists.
6. `presets.md` has 2 fenced ```yaml``` blocks; `as-built.md` has 1.
7. No fragment contains `<head`/`<style`/`<script`/`<html`/`<body`.
8. Both covers have NO `slide-number` div; the other 7 each have exactly one.
9. Headings exact case: `## Slides`, `## Assets`, `## Presets`, `## As-built log`.
10. No literal `|` inside any manifest cell; required cells `id,file,section,title,lang,kind,summary` non-empty; every `kind` ∈ {ready,template}; every `lang` lowercase.
11. Round-trip the seed as-built entry + both presets under the library-YAML subset: seed `deviations` == none (the `-` scalar, not `[]`/`['']`), `engine_version` == `1.0` (quotes stripped), `slides` a 7-id list; both presets' `slides` parse to 7 ids each.

Write the self-check result (the 11 PASS/FAIL lines) to the evidence file. Delete the temp script after.

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/fixture-selfcheck-result.md`:
- The 11 self-check lines (each PASS/FAIL with the measured value).
- A `git status --porcelain html/slide-library/tests/` listing showing only the created files.

DONE means: every file in the tree exists with verbatim content, all 11 §H checks PASS, evidence written. If any check FAILS, do not declare done — write the failure into the evidence file's BLOCKED section and stop.
