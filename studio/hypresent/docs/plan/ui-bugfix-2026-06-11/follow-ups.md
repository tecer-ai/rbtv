# Follow-ups — ui-bugfix-2026-06-11

Deferred loose ends from the 8-bug fix run. Each is cold-start sufficient (a fresh agent can execute from this text). The 8 fixes themselves are DONE + verified (see `run-log.md` exit scorecard); these are enhancements/confirmations.

---

## FU-1 — Add the two D6 regression tests (bug-7, bug-8)

**Why:** Decision D6 (`decisions.md`) committed to a new test for each path the existing suite did not cover. The fixes were verified LIVE instead (the scripts below pass), but no permanent e2e guard exists, so a future refactor could silently re-break bug-7 (data loss) or bug-8. Cold review (run-log 2026-06-11T19:52Z) flagged this as the run's one minor gap.

**Task A — bug-7 overwrite-then-blank guard.** Add a test to `tests/e2e/test_pb11_deck_save.py` (class `PB11DeckSaveTests`) named `test_overwrite_then_blank_keeps_slides`. Port the EXACT, already-passing logic from `docs/plan/ui-bugfix-2026-06-11/evidence/live_verify_bug7.py`: open the deck in the Builder (`#open-deck-btn`, wait `.tray-row`), remove `.tray-row:nth-child(2) .tray-remove`, `#add-blank-btn`, `#save-overwrite-btn` (wait `.shell-status.success`), `#add-blank-btn` again, `#save-overwrite-btn` again; then read the saved deck file, `from recompose import split_sections`, and assert (a) section count == originals−1+2 and (b) every non-removed original section's text survives. Uses the existing `DECK_FIXTURE` (`tecer-gsmm-introduction-test-v3.html`) + `builder_helpers`. Without the bug-7 fix this test fails (a real slide is replaced by a blank).

**Task B — bug-8 inline-svg editability guard.** Add a test to `tests/e2e/test_f2_select_guides.py` named `test_inline_svg_element_editable`. It needs a fixture whose registered text element contains an inline `<svg>` child. Create `tests/e2e/fixtures/inline-svg-text.html` — a minimal self-contained deck (model the markup + the registration requirements on the other `tests/e2e/fixtures/*.html` and `runtime/js/element-registry.js`'s `tag()` rules so the element gets a `data-hyp-id`) containing e.g. `<div class="lead">Pagamentos<svg viewBox="0 0 16 16" width="13" height="13"><circle cx="8" cy="8" r="6"/></svg></div>`. The test: load it, double-click the div → assert `contenteditable === "true"`; double-click the `<svg>` itself → assert it does NOT become editable. Proven-working logic to model on: `docs/plan/ui-bugfix-2026-06-11/evidence/live_verify.py` (bug-8 section, which confirmed `hyp-275` becomes editable on the real v7 board deck).

**Routing:** these are `tests/e2e/` files in the hypresent repo (`3-resources/tools/rbtv/studio/hypresent/`). Run with `$env:PYTHONPATH=<hypresent-root>; python -m pytest <file> -q`. The e2e fixtures `tecer-gsmm-introduction.html` + `…-test-v3.html` are gitignored/untracked — restore from `5-workbench/tecer-biz/prospects/gsmm/presentations/2026-06-02-introduction/tecer-gsmm-introduction.html` before running.

---

## FU-2 — Confirm bug-3 ("mark-for-agent broke the UI") with the owner

**State:** A full live repro (toggle For-agents via the label, save, reload, re-anchor, pin-click; `evidence/repro_bug3_5.py` + `repro_bug3_v2.py`) could NOT reproduce a UI break. The red border in the owner's screenshots is the NORMAL `.comment-thread-highlight` (applied when a comment's in-deck pin is clicked) — reproduced as expected. The one real defect found was the double `refreshCommentPanel()` per comment op (explicit call + `dirty-changed` handler), which is the best explanation for "the bug appears on more than just mark-for-agent." That was fixed (bug-3 = coalescing guard in `app/js/main.js refreshCommentPanel`, verified by cold review).

**Action:** Ask the owner for the EXACT reproduction (step sequence, which deck, how many comments, and what "broke" means — panel garbled? deck broke? a specific comment stuck red?) or a screen recording. If a concrete break reproduces, debug from there; the coalescing fix may already resolve the perceived glitch (a render race under many comments). If it does not reproduce for the owner either, close FU-2.
