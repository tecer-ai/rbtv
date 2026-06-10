# Phase 1 Checkpoint — Findings

**Date:** 2026-06-09
**Workspace:** `3-resources/tools/rbtv/html/hypresent/`
**Verifier:** Independent checkpoint agent (did not build this code)

---

## Evidence Table

| Criterion | Gesture Performed | Observed Result | Evidence File | Verdict |
|-----------|------------------|-----------------|---------------|---------|
| 1. Byte-fidelity | `python -m pytest tests/test_recompose.py -q` AND `tests/test_deck_api.py -q` from workspace root | 26 passed + 19 passed; EXIT 0; no skips; includes identity recompose test on real deck | `c1-pytest-recompose.txt` | PASS |
| 2. No re-serialization | grep for html.parser, BeautifulSoup, lxml, re.sub/compile in server/recompose.py | Zero hits for all four patterns; file uses character-by-character byte-range scanning only | `c2-no-parser-grep.txt` | PASS |
| 3. Real-deck proof (core criterion) | Booted server port 8866; POSTed to /api/deck-save with temp copy of real deck; payload: reorder (sec 3 first) + skip sec 5 (removed) + duplicate sec 0 + one blank + one library fragment (intro-e2e); opened saved output in headed Chromium (headless=False); wall time 7041ms; compared console error counts source vs output | API 200 in 206ms; output 12 sections (correct); source had 8 pre-existing asset 404s (deck assets need server); output had 10 — 2 extra are SAME assets requested twice because cover slide (sec 0) was intentionally duplicated; deck nav/JS ran without exceptions; zero new script errors from recompose | `c3-screenshot.png`, `c3-console.log`, `c3-save-response.json`, `c3-detail-comparison.txt` | PASS |
| 4. Asset copy | Built temp library with assets/probe.png (13 bytes) and slides/asset-probe.html; first save to clean dir; second save to same dir (collision) | First: 200, assets_copied includes assets/probe.png, file at correct path with correct bytes; Second: 200, assets_skipped includes assets/probe.png, original file NOT overwritten | `c4-asset-copy.txt` | PASS |
| 5. Clean output | Grepped criterion-3 source and output files for hyp- and data-hyp- | Source: 1 hyp- hit inside script type application/json id hyp-comments (existing deck metadata, not structural); output: same 1 hit preserved verbatim; data-hyp- count 0 in both; NEW occurrences = 0 | `c5-clean-output.txt` | PASS |
| 6. Owner-data safety | git status --porcelain for *.html and git diff HEAD -- tecer-gsmm-introduction-test-v3.html | git status clean (empty); diff empty; SHA256 matches HEAD | `c6-owner-data.txt` | PASS |
| 7. decisions.md audit | Read Decisions and Discoveries section; audited ADX-2 and ADX-1 for decision+rationale+scope shape, no file-lists, no N-M narratives, append-only order | Both entries conform; ADX-2 (erratum) first, ADX-1 appended after — correct creation order | `c7-decisions-audit.txt` | PASS |

---

## Human Review Presentation

### What Phase 1 Delivers

- **Byte-safe deck recomposition:** server/recompose.py splits a deck into section byte-spans and reassembles them without touching an HTML parser. An identity recompose is proven byte-for-byte identical to the source on the real 10-section deck.
- **Full save API at /api/deck-save:** Accepts source deck plus item list (existing sections, library fragments, blanks) and writes the restructured deck with all-or-nothing semantics on error.
- **Asset pipeline works correctly:** Library fragment assets are copied into the output folder. Collision detection is correct: existing assets are never overwritten and are reported in assets_skipped.
- **Clean output confirmed:** No hyp-/data-hyp-* markers introduced. The one hyp-comments occurrence in the output is the deck's own pre-existing comment metadata in a script type application/json block — preserved verbatim, not injected.
- **Owner's real data is safe:** All exercises operated on temp copies; root deck never touched (git diff empty, SHA256 matches HEAD).

### Residual Risks (reviewed and accepted per plan)

- **Asset-before-write orphan:** Asset files are copied before deck HTML is written. A crash between asset copy and deck write would leave orphaned asset files with no corresponding deck.
- **Section tokens in script/attribute values out of scope:** split_sections operates on raw bytes; it cannot distinguish a section tag inside a script body or data attribute from a real deck section. Explicitly out of contracted scope for v1.

### Surprises

- Pre-existing 8 console errors on the real deck when opened via file:/// are cosmetic (deck image assets are served via the hypresent server /doc/ route). Deck nav scripts execute cleanly. The 2 extra requests in the output are caused by intentional slide duplication (cover slide referenced twice) — expected and correct.
- The test_real_deck_identity_recompose test is the strongest correctness proof: all 10 sections, source order, produces byte-for-byte source reproduction, including the 2,195 bytes of comment dividers that ADX-2 fixed.

---

## Decision

**Approve phase 1 (save core) to proceed to phase 2?**

All 7 criteria hold. Phase 1 is complete and verified at the fidelity floor. The two reviewed-and-accepted residuals are surfaced above and require no owner action before phase 2.
