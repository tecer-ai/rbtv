# Phase 2 — Independent Checkpoint Verifier Findings

**Verifier:** claude:sonnet (independent — did not build this code)  
**Date:** 2026-06-09  
**Task:** phase-2 checkpoint (ingest) for builder-open-deck  
**Fidelity floor:** real app, real deck copy (`tecer-gsmm-introduction-test-v3.html`), headed Playwright (headless=False), dialog injection via `/api/_test/set-dialog`, evidence files captured during exercise.

---

## Evidence Table

| Criterion | Gesture performed | Observed result | Evidence file | Verdict |
|-----------|-------------------|-----------------|---------------|---------|
| C1 — Open → full tray | Boot server (PORT 8899, HYP_TEST_DIALOG=1). Copy real deck to temp. Inject via `/api/_test/set-dialog`. Navigate to `/app/builder.html`. Click `#open-deck-btn`. Wait for `.tray-row` (12s timeout). Count rows. | 10 `.tray-row` elements in tray. Deck chip shows `"deck.html"`. Wall: 1284 ms. | `c1-tray-full.png` | **held** |
| C2 — Thumbnails themed | Same open flow. After tray populated, wait 500ms for async srcdoc. Read `srcdoc` attr of iframe in each of 10 rows. | All 10 rows: `has_section=True`, `has_slide_css=True`. srcdoc lengths 54-59 KB (head CSS + section markup). Visual screenshot shows dark-navy styled slides with deck theme. | `c2-thumbnails-themed.png`, `c2-srcdoc-details.json` | **held** |
| C3 — Rejection path | Write sectionless HTML to temp. Inject as dialog result. Click `#open-deck-btn`. Wait for `.shell-status.error` (8s). | Status has `.error` class (red). Text: `"Deck open failed: no <section> slides found — not a conforming deck"`. Tray = 0 rows. | `c3-rejection.png` | **held** |
| C4 — Cancel path | Set dialog to return `null`. Navigate. Click `#open-deck-btn`. Wait 1500ms. | Status empty before and after. Rows = 0 before and after. No error class. Wall: 1596 ms. | `c4-cancel.png` | **held** |
| C5 — Assemble-mode regression | `python -m pytest tests/e2e/test_pb2_library_load.py tests/e2e/test_pb3_previews.py -q --tb=short` | Exit 0. `9 passed in 14.98s`. 0 skips. | `c5-regression-pytest.txt` | **held** |
| C6 — decisions.md audit | Read decisions.md. Extract ADX-* entries. Check each for Decision/Rationale/Scope fields and absence of file-lists or N->M narratives. | 3 entries: ADX-1, ADX-2, ADX-3. All have all 3 required fields. No violations. Append-only preserved. | `c6-decisions-audit.txt` | **held** |

---

## Human Review Presentation

### What phase 2 delivers

Phase 2 (ingest) enables opening an existing HTML presentation deck in the builder so its slides populate the assembly tray as an ordered set of styled thumbnails. The owner clicks "Open deck…", picks a conforming deck, and sees one tray row per slide with the deck's own CSS styling visible in each thumbnail.

**Verified deliverables:**

1. **Deck load API** (`server/deck_api.py`, `server/server.py`): `/api/deck-load` and `/api/dialog-open-path` wired and functional. Returns head HTML (scripts stripped) and ordered section spans.
2. **Client-side ingest** (`app/js/builder/deck-load.js`): picks dialog result, posts to `/api/deck-load`, returns structured result.
3. **Builder main wiring** (`app/js/builder/builder-main.js`): `loadDeckIntoTray` sets per-row srcdoc provider via `tray.setSrcdocProvider` BEFORE calling `tray.setFromPreset` — correct ordering.
4. **Per-row srcdoc provider** (`app/js/builder/tray.js`): `setSrcdocProvider` added; `render()` uses it before falling back to `getSlideSrcdoc`. ADX-3 stopgap (manual srcdoc injection after setFromPreset) confirmed absent.
5. **`buildDeckSrcdoc`** (`app/js/builder/previews.js`): composes full `<!DOCTYPE html><html><head>${head}</head><body>${section.html}</body></html>` including deck CSS.
6. **Deck chip**: `#deck-chip` / `#deck-chip-name` shows filename on open.
7. **Error and cancel paths**: both verified at fidelity floor.

### Residual risks

1. **Thumbnail re-render after remove** (low): `test_thumbnails_survive_rerender` (ADX-3 guard) exists in `test_pb8_deck_open.py` but was not in the C5 regression contract. The provider is called on every `render()` call in `tray.js`, so it should survive; but not independently exercised here.
2. **Section order** (very low): order confirmed as 10 rows matching 10 sections, but exact DOM-order mapping not byte-verified. `split_sections` + positional indexing makes mis-ordering implausible.
3. **Asset 404s in thumbnails** (expected): deck assets (images) return 404 through the server. Thumbnails render correctly with CSS/text content — missing images show broken icons, which is the decorative-thumbnail spec behaviour.

### Surprises

None. The C3 status message reads "Deck open **failed**: no `<section>`..." because the client catch block in `handlePickDeck` prefixes "Deck open failed: " to the API error. The test in `test_pb8_deck_open.py::test_non_conforming_rejected` correctly uses `assertIn("section", status_text.lower())` which passes.

---

## Decision

**Auto-pass phase 2 (ingest)? YES.**

All 6 criteria exercised at the fidelity floor with real data on the real running application. All 6 verdicts: `held`. Regression suite: 9 passed, 0 skipped, exit 0.
