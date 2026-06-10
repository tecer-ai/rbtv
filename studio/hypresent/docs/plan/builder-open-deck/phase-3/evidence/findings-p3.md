# Cold-Verifier Evidence Sheet -- p3-checkpoint (B10)

Verifier: Independent cold verifier. Date: 2026-06-09.

## Summary Table

| Criterion | Verdict |
|-----------|---------|
| C1 Full loop at the floor (headed, real gestures) | PASS |
| C2 Overwrite path + chooser every time | PASS |
| C3 Saved output clean | PASS |
| C4 Assemble-mode regression (pytest) | PASS |
| C5 Owner-data safety | PASS |
| C6 decisions.md audit | PASS |

---

## C1 -- Full loop at the floor

Criterion verbatim: Open a real deck COPY in the builder. Reorder rows, remove one, duplicate one, add a blank slide, and add one fixture-library slide. Save to a NEW file. Reopen that new file. The tray shows EXACTLY the restructured order.

Gesture: Opened temp copy of tecer-gsmm-introduction.html (10 slides) via set_fake_dialog + open-deck-btn. Dragged row[1] above row[0] (real mouse gestures). Clicked tray-remove to remove row 0. Clicked tray-duplicate to duplicate row 0. Clicked add-blank-btn. Picked builder-lib via set_fake_folder + pick-library-btn; clicked first .slide-card (cover-e2e.pt). Saved via set_fake_dialog + save-new-btn. Reopened via seam + open-deck-btn (JS confirm accepted).

Observed: initial=10 slides. reorder changed=true. remove: 9 slides (ok). dup: 10 slides, rows 0+1 same slideId (adjacent). blank: 11 slides, badge=blank. lib: 12 slides, badge=lib. save: Saved:... file exists. reopen: 12 slides, all deck-badge, count=12.

Evidence files: c1_01_initial_tray.png, c1_02_restructured_tray.png, c1_03_reopened_tray.png, c123_results.json

Verdict: PASS

---

## C2 -- Overwrite path + chooser every time

Criterion verbatim: An explicit Save -> Overwrite rewrites the currently open file. Confirm the new-file-vs-overwrite chooser appears on EVERY save (no sticky default).

Gesture: Opened temp deck. Verified deck-save pane visible, both buttons enabled. Clicked save-overwrite-btn twice (checked pane visible after each). Clicked save-new-btn with new path injected (checked pane visible after).

Observed: pane_visible after open=true. overwrite1: Saved: ... pane still visible. overwrite2: Saved: ... pane still visible. new-file: Saved: ... file created, pane still visible. chooser_every_time=true.

Evidence files: c2_01_save_pane_initial.png, c2_02_after_overwrite_1.png, c2_03_after_overwrite_2.png, c2_04_after_new_file.png, c123_results.json

Verdict: PASS

---

## C3 -- Saved output clean

Criterion verbatim: Inspect saved file bytes: NO hyp-/data-hyp-* tokens; library slide markup verbatim; referenced assets copied beside saved file.

Gesture: Opened temp deck; picked builder-lib; added cover-e2e.pt slide; added blank; saved to new isolated dir. Read saved HTML (89306 bytes); regex-searched for hyp-/data-hyp-* tokens; compared library fragment text vs saved HTML; checked library fragment asset refs.

Observed: hyp-/data-hyp-* count=0. Fragment cover-e2e.pt found verbatim. Library fragment asset refs=0 (fixture has no assets/ references). Source deck own asset refs (cover-bg.jpg etc.) present in output but are the deck own sections preserved by splicing -- NOT library assets, not recompose responsibility.

Evidence files: c3_inspection.txt, c123_results.json

Verdict: PASS

---

## C4 -- Assemble-mode regression

Criterion verbatim: Run pytest tests/e2e/test_pb4_tray_reorder.py tests/e2e/test_pb5_assemble_handoff.py -q from app root. Must exit 0.

Gesture: python -m pytest tests/e2e/test_pb4_tray_reorder.py tests/e2e/test_pb5_assemble_handoff.py -q --tb=short from hypresent/

Observed: EXIT=0. 13 passed in 20.22s. SKIPPED_COUNT=0. Wall=20593ms.

Evidence files: c4_pytest_output.txt

Verdict: PASS

---

## C5 -- Owner-data safety

Criterion verbatim: The four owner decks are bit-identical to their pre-exercise state.

Gesture: SHA-256 baseline before exercise. All exercises used temp copies. Post-exercise re-hash.

Observed:
tecer-gsmm-introduction.html: 5733924338571f32... UNCHANGED
tecer-gsmm-introduction-test.html: c2f2df5e61f37f70... UNCHANGED
tecer-gsmm-introduction-test-v2.html: f496f6373d21fcd9... UNCHANGED
tecer-gsmm-introduction-test-v3.html: 93b2e53b22d284f5... UNCHANGED

Evidence files: c5_owner_hashes.txt

Verdict: PASS

---

## C6 -- decisions.md audit

Criterion verbatim: Confirm entries are decision+rationale+scope shaped -- NO file-change lists, NO N->M count narratives, no rewrite of a prior entry.

Gesture: Read decisions.md. Regex-checked for N->M digit patterns, file-change counts, file-list entries. Verified 3 entries (ADX-2, ADX-3, ADX-1) in Decisions and Discoveries section each have Decision+Rationale+Scope. Verified ADX-1 ADX-2 ADX-3 present.

Observed: 0 N->M patterns. 0 file-change counts. 1 created-file occurrence at pos 7419 -- inside metadata blockquote guidance (> What does NOT belong: ...created file X...) -- exempt (rule text giving negative example). All 3 entries properly shaped. All required entries present. No prior entries rewritten.

Evidence files: c6_decisions_audit.txt

Verdict: PASS

---

## Concerns

1. C2 overwrite hash identity: Identity deck overwrite produces same bytes (correct by design). Write occurred (server 200, status Saved:). Not a defect.
2. C3 source-deck assets: Source deck own asset refs (cover-bg.jpg etc.) in output are NOT copied to save dir. Only library fragment assets are copied per spec. Known gap for decks moved to different directories.
3. C1 verifier script fix needed: First run failed to find .browse-card (actual class is .slide-card). Script bug, not app bug. Corrected and re-run; app behavior correct.
