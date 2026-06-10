# FIX DIRECTION — p1-1 (resumed session) — ADX-2

Your p1-1 work passed the return gate but the review surfaced a SPEC DEFECT that is now corrected. You must apply ONE bounded fix. You remain a NON-REASONING executor: the corrected contract below is fully pre-resolved — implement it exactly; HALT with `DOUBT_ESCALATED` on any ambiguity.

## What changed since your commit cff2be0

- Both your files were amended IN PLACE by the reviewer (uncommitted): `server/recompose.py` (+4 lines — `RecomposeError` for missing `index`/`html` keys) and `tests/test_recompose.py` (+45 lines — 4 new tests). KEEP these amendments; build on the CURRENT disk state. Suite currently: 24 passed.
- The spec at `docs/plan/builder-open-deck/specs/deck-save-spec.md` now carries an **ADX-2 erratum** (bottom of the file) correcting the `recompose` contract. READ IT FIRST — it is the authoritative behavior.

## The fix (per the ADX-2 erratum — summary; the erratum is authoritative)

`recompose` must PRESERVE inter-slide separators: output = `prefix + item₀ + sep(item₀) + item₁ + sep(item₁) + … + itemₙ₋₁ + suffix` (separators BETWEEN items, none after the last). `sep(item)`:
- `existing` item with source index `i < n-1` → the source's own separator `html[end_of_section_i : start_of_section_i+1]` (its trailing separator travels with it);
- `existing` item that was the source's LAST section, or any `fragment`/`blank` item → the deck DEFAULT separator = the most common source separator string (tie → first occurrence in document order); `"\n"` when the deck has fewer than 2 sections.
- Consequence: identity recompose (all sections, source order) returns the source EXACTLY, byte-for-byte.
- `split_sections` is UNCHANGED. Zero-section behavior is UNCHANGED.

## Acceptance (all four required)

1. NEW test: identity recompose of the real deck (`shutil.copy` of `tecer-gsmm-introduction-test-v3.html` to `tmp_path`, items = all sections in source order) returns the source string EXACTLY — full equality assertion.
2. All existing tests pass — update ONLY tests whose expectations encode the old separator-dropping join; do NOT weaken any other assertion.
3. `python -m pytest tests/test_recompose.py -q` → EXIT 0, no skips.
4. Self-check: no `html.parser`/`BeautifulSoup`/`lxml` imports — byte-range splicing only.

## Binding obligations (unchanged from your original dispatch)

- Allowlist: ONLY `server/recompose.py` and `tests/test_recompose.py`. No stray files. Root decks READ-ONLY.
- Commit local-only on `master`: stage EXACTLY the 2 allowlist files (never `git add -A`), subject starts `[p1-1] fix:`. NEVER push/amend/force-reset.
- Return the five named fields: `status` · `landed` (files + commit hash) · `validation` (command + EXIT + WALL_MS + SKIPPED_COUNT) · `concerns` · `open_questions`.
