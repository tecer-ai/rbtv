# Cold Verifier Findings --- p4-checkpoint (B12)

**Verifier:** independent cold run (no access to builder tests, claims, or sheet)
**Date:** 2026-06-10
**Sessions:** exercised across two verifier sessions --- session 1 (criteria 1-7, evidence
c1-* through c7-*, driver cv_driver.py) and session 2 (criterion-1 completion at content level,
evidence c1-fix-*, after the conductor return-gate found C1 under-evidenced). Criterion-1
findings below are session 2; all other sections are session 1.
**Driver scripts:** evidence/cv_driver.py (session 1), evidence/c1_fix_driver.py (session 2)
**App root:** studio/hypresent/

---

## Pre-exercise owner-deck hashes (READ-ONLY proof)

| Deck | SHA-256 |
|------|---------|
| tecer-gsmm-introduction.html | 5733924338571f3246b49c38e1ac6af7c210ef372fb1948c383d0026583332ae |
| tecer-gsmm-introduction-test.html | c2f2df5e61f37f70b8ac10ab74a5d91bae8cf51f95a4d4dea731611c62e6ecb0 |
| tecer-gsmm-introduction-test-v2.html | f496f6373d21fcd981cf00139a6954284280f5c049a9f7d0c48c05dd5db519db |
| tecer-gsmm-introduction-test-v3.html | 93b2e53b22d284f5d7b7781da3d05d5ed6a3289625467160c45ee4d2e2a9ad4a |

Post-exercise hashes: identical to pre-exercise for all four, in BOTH sessions. See
c2-owner-deck-hash-post.json (session 1) and c1-fix-owner-hashes.json (session 2).

---

## Criterion 1 --- Round trip at the floor (HEADED, real gestures)

**Criterion verbatim:** The full cycle --- open deck in builder, reorder slides, switch to editor,
edit text, open in builder --- completes successfully at the fidelity floor: headed Chromium, real
mouse/keyboard gestures, real server, real deck copy.

**Gesture performed (session 2 --- c1_fix_driver.py):**

1. Copied tecer-gsmm-introduction.html (owner deck) to a fresh OS temp dir as deck.html.
2. Opened deck.html in the headed builder via dialog seam + #open-deck-btn. Tray populated
   (10 rows). Captured per-row slide identity (li_text labels + srcdoc snippets) to
   c1-fix-order-before.json. Screenshot: c1-fix-01-loaded.png.
3. Real drag: mouse.down on row-0 body, moved to below row-1, mouse.up. Tray re-read:
   position 0 now shows Slide 2 content (Uma plataforma inteligente), position 1 shows Slide 1
   content (cover/logo slide). Swap assertion in c1-fix-order.json (reorder_happened: true).
   Screenshot: c1-fix-02-reordered.png.
4. Injected crossing-1.html path via seam. Clicked #switch-to-editor-btn. Navigated to
   editor URL. OIB button enabled (runtime ready). crossing-1.html written to disk.
5. Edit: dblclick at (0.5, 0.2) of iframe frame area. Selection confirmed (has-selection).
   Typed [CV-B12]. Marker present in iframe DOM immediately after typing (JS eval).
   Screenshot: c1-fix-03-edited.png.
6. Injected crossing-2.html path via seam. Clicked #open-in-builder-btn. Navigated to
   builder URL. Tray populated (10 rows). crossing-2.html written to disk.
7. Captured final tray per-row identity. Read full srcdoc for all 10 rows scanning for
   [CV-B12]. Found marker in row 0 (context: A Tecer reune [CV-B12]fontes).
   DOM dump in c1-fix-thumbnail-dom.txt. Screenshots: c1-fix-04-final-tray.png,
   c1-fix-05-thumbnail-zoom.png.
8. Disk verification: crossing-2.html bytes contain [CV-B12] (true); crossing-1 hash differs
   from original deck hash (true - reorder serialized). Owner deck hashes unchanged.

**Key assertions resolved:**

| Assertion | Method | Result |
|-----------|--------|--------|
| Reorder happened in tray | li_text slide-label swap: pos 0 -> Slide 2 (Uma plataforma), pos 1 -> Slide 1 (cover) | True |
| Reorder serialized into crossing-1 | Disk: crossing-1 section-0 text = Uma plataforma inteligente (originally section 1) | True |
| Order preserved in crossing-2 | Disk: crossing-2 section-0 text = Uma plataforma inteligente | True |
| Marker in final tray DOM | srcdoc scan row 0: contains [CV-B12] in context snippet | True |
| Marker in crossing-2 on disk | bytes scan: [CV-B12] in crossing-2.html | True |
| Marker in section matching reordered slide | crossing-2 section 0 (reordered-to-front slide) contains marker | True |
| Owner decks unchanged | SHA-256 pre = post for all 4 decks | True |

**Clarification --- final tray labels:** The builder re-labels tray rows ordinally (Slide 1,
Slide 2, ...) based on current position after each reload. When crossing-2 is opened as a new
file the tray renumbers from 1. The li_text in c1-fix-order.json therefore shows Slide 1 at
position 0 in the final tray --- this is the NEW ordinal label for what was originally Slide 2.
Disk-level section-text comparison (conductor-computed deterministic section-order check in
c1-fix-conductor-order-check.txt) confirms the content at position 0 is Uma plataforma
inteligente, not the cover slide --- the reorder IS preserved.

**Observed result:** Both crossings wrote distinct new files. Reorder serialized and preserved
end-to-end (disk-verified via the conductor-computed deterministic section-text comparison of
deck/crossing-1/crossing-2 in c1-fix-conductor-order-check.txt). Marker [CV-B12] present in
editor iframe DOM at edit time, in final tray srcdoc (row 0), and in crossing-2.html bytes on
disk. Thumbnail screenshot c1-fix-05-thumbnail-zoom.png captures the row-0 element; marker is
NOT pixel-legible at thumbnail scale (inherent to thumbnails) but DOM and disk proof are
unambiguous.

**Evidence files (session 2):**
c1-fix-order-before.json, c1-fix-order.json (per-row tray identity + swap/marker assertions),
c1-fix-conductor-order-check.txt (conductor-computed deterministic section-order proof),
c1-fix-thumbnail-dom.txt, c1-fix-owner-hashes.json,
c1-fix-01-loaded.png through c1-fix-05-thumbnail-zoom.png,
c1-fix-run-log.txt, c1_fix_driver.py

**Verdict: PASS** --- Full round trip completed at the fidelity floor. Reorder serialized and
preserved end-to-end (disk-verified). Marker [CV-B12] present in DOM and on disk in the final
tray slide. Owner decks unchanged throughout.

---

## Criterion 2 --- New-file guarantee

**Criterion verbatim:** Each crossing wrote a DISTINCT new file; no crossing overwrote its
source. Compare directory file lists + source-file hashes before/after each crossing; include
the owner-deck before/after hashes. Capture the listings and hash comparisons.

**Gesture performed:**
- Opened deck copy in builder (isolated server instance).
- STE crossing: injected c2-crossing-1.html path, clicked #switch-to-editor-btn.
- OIB crossing: waited for runtime ready, injected c2-crossing-2.html path, clicked #open-in-builder-btn.
- After each crossing: hashed source deck; confirmed written file at distinct path.

**Observed result (from c2-hash-comparison.json):**
- crossing1_wrote_new_distinct_file: true
- crossing2_wrote_new_distinct_file: true
- source_deck_unchanged_after_c1: true
- source_deck_unchanged_after_c2: true
- owner_decks_unchanged: true (all 4)
- Paths: source tmpji9y32qp/deck.html, crossing1 tmpb7jgkxn4/c2-crossing-1.html,
  crossing2 tmpk46nyqo7/c2-crossing-2.html --- all distinct.

**Evidence files:** c2-hash-comparison.json, c2-owner-deck-hash-post.json,
c2-builder-after-second-crossing.png

**Verdict: PASS** --- Each crossing wrote a distinct new file; source and all owner decks unchanged.

---

## Criterion 3 --- Cancel semantics

**Criterion verbatim:** Cancelling either dialog leaves the current view fully intact --- no
navigation, no file written, no error surfaced. Exercise BOTH crossings cancel paths.

**Gesture performed:**
- STE cancel: opened deck in builder, injected null, clicked #switch-to-editor-btn, waited 2.5s.
- OIB cancel: opened doc in editor via seam, waited for OIB enable, injected null,
  clicked #open-in-builder-btn, waited 2.5s.

**Observed result:**
- STE cancel: URL remained builder.html after 2.5s. No navigation, no error.
- OIB cancel: URL remained editor (/app/) after 2.5s. No navigation, no error.

**Evidence files:** c3-01-builder-deck-loaded.png, c3-02-builder-after-cancel.png,
c3-03-editor-doc-loaded.png, c3-04-editor-after-cancel.png

**Verdict: PASS** --- Both cancel paths leave current view intact; no navigation or error.

---

## Criterion 4 --- Disabled states

**Criterion verbatim:** Switch to editor is disabled when the builder tray is empty;
Open in builder is disabled when the editor has no document open. Observe both headed,
capture screenshots of both disabled states (and show the control enabling once content exists).

**Gesture performed:**
- Fresh builder.html load; checked #switch-to-editor-btn disabled.
- Fresh index.html load (no doc); checked #open-in-builder-btn disabled.
- Opened deck in builder; verified STE enabled after tray populated.
- Opened doc in editor; waited for OIB to enable (runtime ready).

**Observed result:** STE disabled on empty tray: true. OIB disabled with no doc: true.
STE enables after deck load: true. OIB enables after runtime ready: true.

**Evidence files:** c4-builder-empty-disabled.png, c4-editor-no-doc-disabled.png,
c4-builder-deck-loaded-enabled.png, c4-editor-doc-open-enabled.png

**Verdict: PASS** --- Both disabled states confirmed; both enable correctly.

---

## Criterion 5 --- Editor regression

**Criterion verbatim:** Run python -m pytest tests/e2e/test_g2_save_with_comments.py
tests/e2e/test_exit_smoke.py -q from the app root. Must exit 0. Capture full pytest output.

**Gesture performed:** Ran the command from the app root with --tb=short.

**Observed result:** EXIT: 0, WALL_MS: 19045, 8 passed in 18.69s

**Evidence file:** c5-pytest-output.txt

**Verdict: PASS** --- Exit 0; 8 tests passed.

---

## Criterion 6 --- decisions.md audit

**Criterion verbatim:** Read decisions.md. Confirm entries under Decisions and Discoveries
are decision+rationale+scope shaped --- NO file-change lists, NO N->M count narratives,
no rewrite of a prior entry (append-only discipline).

**Gesture performed:** Read the file; extracted the Decisions and Discoveries section;
checked for file-change bullets and N->M narratives; counted ### entries and verified
Decision+Rationale+Scope fields per entry.

**Observed result:** 5 entries (ADX-2, ADX-3, ADX-1, D-asset-colocation,
D-bridge-runtime-ready). File-change bullets: 0. N->M narratives: 0. Decision fields: 5/5.
Rationale: 5/5. Scope: 5/5.

**Evidence file:** c6-decisions-audit.txt

**Verdict: PASS** --- No prohibited narratives; all 5 entries have Decision+Rationale+Scope.

---

## Criterion 7 --- Enable-on-ready latency

**Criterion verbatim:** The editor Open in builder button is disabled from the moment a
document open starts and enables only when the editor iframe runtime signals ready. Measure
the gap from document content becoming visible to button enabling. PASS if gap <= ~1000ms.

**Gesture performed:**
- Dialog path: navigated to editor, injected deck via seam, clicked #open-btn. Timestamped
  content visible; polled #open-in-builder-btn.disabled until enabled.
- File-param path: navigated to editor/?file=<deck_path>. Same timing.

**Observed result:**

| Open path | Content-to-button gap | Total open-to-button |
|-----------|-----------------------|----------------------|
| dialog | 155 ms | 233 ms |
| file-param | 187 ms | 265 ms |

**Evidence files:** c7-latency-log.json, c7-latency-dialog.png, c7-latency-file-param.png

**Verdict: PASS** --- 155ms and 187ms; both well under 1000ms.

---

## Summary verdict table

| Criterion | Verdict |
|-----------|---------|
| 1 --- Round trip at the floor | PASS |
| 2 --- New-file guarantee | PASS |
| 3 --- Cancel semantics | PASS |
| 4 --- Disabled states | PASS |
| 5 --- Editor regression | PASS |
| 6 --- decisions.md audit | PASS |
| 7 --- Enable-on-ready latency | PASS |

## Notes for the conductor

1. C1 order verification method (session 2): The tray li_text labels (Slide 1, Slide 2, ...)
   are ordinal display numbers that reset on every builder reload --- NOT content identifiers.
   Order preservation was verified by section-text disk comparison: crossing-1.html and
   crossing-2.html both have section-0 = Uma plataforma inteligente (originally section 1 in
   the source deck), which is the slide dragged to position 0 during the reorder. See the
   conductor-computed deterministic section-order check in c1-fix-conductor-order-check.txt.
2. C1 marker legibility note: The marker [CV-B12] is confirmed in the editor iframe DOM at edit
   time, in the final tray srcdoc (row 0, via DOM dump in c1-fix-thumbnail-dom.txt), and in
   crossing-2.html bytes on disk. The thumbnail screenshot c1-fix-05-thumbnail-zoom.png is a
   Playwright element screenshot of row 0 --- the marker is NOT pixel-legible at thumbnail
   scale (inherent to thumbnails; the edited text IS legible in the editor screenshot
   c1-fix-03-edited.png at edit time). DOM and disk evidence are authoritative. OWNER-FACING
   CAVEAT: the criterion's literal phrase "the thumbnail shows the edited text" is satisfied at
   the render-source level (the thumbnail's srcdoc carries the edit), not by pixel-legible text
   in the thumbnail itself --- see opus audit C1.
3. C7 timing is machine-specific: 155ms / 187ms on Windows 11 / SSD / localhost --- a favorable
   environment, not a cross-machine floor benchmark. (session 1)
4. No failed or unexercisable rows across all 7 criteria.