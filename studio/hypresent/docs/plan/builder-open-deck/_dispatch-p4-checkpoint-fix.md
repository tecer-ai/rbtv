# COLD VERIFIER FIX DISPATCH — p4-checkpoint (B12, C1 completion)

You are completing an interrupted COLD VERIFICATION. A prior verifier session exercised the
7 contract criteria below and produced 24 evidence files, but (a) its criterion-1 verdict was
under-evidenced (it verified the final tray by SLIDE COUNT ONLY — never the order, never the
edited text), and (b) it failed to write the required findings file. You fix exactly those two
gaps. You are still a COLD verifier: you have NO access to the builder's tests, claims, or
evidence — only this contract and the running app.

## BINDING FIX DIRECTION (the exact defects; the exact required outcomes)

**Defect 1 — criterion 1 under-evidenced.** Required outcome: re-exercise the full C1 round
trip HEADED with real gestures, and this time capture CONTENT-LEVEL proof that (i) the final
builder tray's row ORDER matches the post-reorder sequence (not the original), and (ii) the
text edited in the editor is present in the final tray's corresponding thumbnail content.
Acceptance: a JSON file recording per-row slide identity before-reorder / after-reorder /
final-tray (with an explicit order-match assertion), a DOM-level proof the final tray's row
content carries the edited marker text, and a CROPPED/ZOOMED screenshot of that thumbnail
region where the marker is visible.

**Defect 2 — findings file missing.** Required outcome: write the per-criterion findings file
(content specified below) to the exact required path. Acceptance: the file exists, one section
per criterion, your C1 section cites YOUR new captures.

---

## BINDING ADDENDUM

- **Write tool note:** the dedicated file-Write tool may be unavailable in your context — write
  ALL files via python (`pathlib.Path(...).write_text(..., encoding="utf-8")`) or shell
  redirection through Bash. The prior session wrote 24 evidence files that way.
- **Allowlist:** create files ONLY under
  `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck/phase-4/evidence/`
  plus throwaway temp deck copies under the OS temp dir. NEVER modify application source, tests,
  or owner decks. Do NOT commit.
- **Owner data READ-ONLY:** `tecer-gsmm-introduction.html`, `tecer-gsmm-introduction-test.html`,
  `tecer-gsmm-introduction-test-v2.html`, `tecer-gsmm-introduction-test-v3.html` at the app root.
  COPY to temp before exercising; SHA-256 each before and after your whole run; prove zero change.
- **Fidelity floor:** headed Chromium (`headless=False`), REAL mouse/keyboard gestures (`click`,
  `mouse.down/move/up`, `dblclick`, `keyboard.type`) — NEVER synthetic in-page `dispatchEvent`.
  Real server, real deck copy.
- **Halt policy:** genuinely undrivable → verdict `unexercisable` + concrete blocker. Never guess.
- **Return schema:** your final reply MUST be the five named fields (status / landed / validation /
  concerns / open_questions). `status` MUST be EXACTLY one of `DONE` · `DONE_WITH_NOTES` ·
  `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT` — no other word. A prose-only return or an
  invented status value is a contract violation.

## THE RUNNING ARTIFACT + SEAMS

- App root: `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent`
- Start the server yourself: `tests/e2e/conftest_helpers.py` → `start_server(port, test_dialog=True)`
  (launches `server/server.py 127.0.0.1 <port>` with `HYP_TEST_DIALOG=1`, waits for `/app/`).
- BUILDER = `/app/builder.html` · EDITOR = `/app/index.html`.
- Bridge controls: builder `#switch-to-editor-btn` ("Switch to editor"), editor `#open-in-builder-btn`
  ("Open in builder"). Each crossing runs Save-As (native dialog) then opens the NEW file in the
  target view via `?file=<abs>`.
- Dialog seam (requires `HYP_TEST_DIALOG=1`): `POST /api/_test/set-dialog` with JSON
  `{ "path": "<abs>" }` injects the next native open/save dialog result (`null` = cancel).
- Deck open in the builder: inject the path via the seam then click `#open-deck-btn`
  (or navigate with `?file=`).
- The editor's "Open in builder" button enables only when the editor iframe runtime signals
  ready — wait for it to be enabled before clicking.
- Do NOT read or run `tests/e2e/test_pb*.py` — builder evidence; you stay cold. You MAY read
  `tests/e2e/conftest_helpers.py` / `builder_helpers.py` (infrastructure) and the prior verifier's
  driver `phase-4/evidence/cv_driver.py` (a PRIOR VERIFIER's harness, not the builder's) to reuse
  server/launch mechanics.
- Known accepted limitation (`D-asset-colocation` — not a defect, do not FAIL on it): decks saved
  outside their source dir have unresolved own `assets/*` refs; judge structure and text, not
  image resolution.

## THE C1 RE-EXERCISE (do it exactly like this)

1. Copy `tecer-gsmm-introduction.html` (app root) to `<temp>/deck.html`.
2. Headed builder → inject `<temp>/deck.html` via seam → click `#open-deck-btn` → wait for the
   tray to populate. **Capture per-row identity** (for each tray row, a stable content signature:
   e.g. the first 120 chars of the row's iframe `srcdoc`, or a slide title text) →
   `c1-fix-order-before.json`. Screenshot `c1-fix-01-loaded.png`.
3. REAL drag: `mouse.down` on row 1's drag handle, move below row 2, `mouse.up`. Capture per-row
   identity again → assert rows 1 and 2 SWAPPED vs step 2 → include in `c1-fix-order.json`.
   Screenshot `c1-fix-02-reordered.png`.
4. Inject `<temp>/crossing-1.html` via seam → click `#switch-to-editor-btn` → wait for the editor
   URL. Wait for `#open-in-builder-btn` to ENABLE.
5. Edit visible text with real gestures: dblclick a text element in the editor iframe, type the
   marker ` [CV-B12]`, press Escape. Screenshot `c1-fix-03-edited.png`. (If dblclick at one spot
   doesn't open an editable text, try another visible text block — record what you did.)
6. Inject `<temp>/crossing-2.html` via seam → click `#open-in-builder-btn` → wait for the builder
   URL → wait for the tray to populate.
7. **Capture per-row identity of the FINAL tray** → `c1-fix-order-final.json`. ASSERT: final order
   matches the post-reorder sequence from step 3 (row 1 = the slide that was originally second),
   NOT the original order. Write the explicit boolean into `c1-fix-order.json`.
8. **ASSERT the marker:** find the final tray row whose `srcdoc` (or rendered content) contains
   ` [CV-B12]`; record which row, dump the matching snippet → `c1-fix-thumbnail-dom.txt`.
   Take a full screenshot `c1-fix-04-final-tray.png` AND a CROPPED/ZOOMED capture of that row's
   thumbnail where the marker text is visible → `c1-fix-05-thumbnail-zoom.png` (use Playwright
   `locator.screenshot()` on the row element, or crop with PIL — PIL is installed; if the marker
   is genuinely too small to be legible even zoomed, say so honestly and rely on the DOM dump +
   the editor screenshot; do NOT fake legibility).
9. Also verify on DISK: `crossing-2.html` bytes contain ` [CV-B12]`; `crossing-1.html` differs
   from `deck.html` by hash (the reorder serialized). Record in `c1-fix-order.json`.
10. SHA-256 the four owner decks (before step 1 and after step 9) → `c1-fix-owner-hashes.json`.

All evidence files go in the evidence dir
(`.../docs/plan/builder-open-deck/phase-4/evidence/`).

## WRITE THE FINDINGS FILE

Write `findings-p4.md` in the evidence dir via python. Its content: the prior verifier's sheet
EXACTLY as given below, with TWO changes — (1) replace the entire "## Criterion 1 …" section
with YOUR OWN evidenced version (criterion verbatim, your gestures, your observations, your
evidence file paths, your verdict); (2) keep the attribution note at the top as given (it
records the two-session split). Do not alter the other criteria's sections — they are the
prior session's authored findings over evidence that is already on disk and conductor-verified.

The content to write (between the BEGIN/END markers, markers excluded):

<<<BEGIN findings-p4.md>>>
# Cold Verifier Findings — p4-checkpoint (B12)

**Verifier:** independent cold run (no access to builder's tests, claims, or sheet)
**Date:** 2026-06-10
**Sessions:** exercised across two verifier sessions — session 1 (criteria 1–7, evidence
`c1-*`…`c7-*`, driver `cv_driver.py`) and session 2 (criterion-1 completion at content level,
evidence `c1-fix-*`, after the conductor's return-gate found C1 under-evidenced). Criterion-1
findings below are session 2's; all other sections are session 1's.
**Driver scripts:** `evidence/cv_driver.py` (session 1), `evidence/c1_fix_driver.py` (session 2)
**App root:** `studio/hypresent/`

---

## Pre-exercise owner-deck hashes (READ-ONLY proof)

| Deck | SHA-256 |
|------|---------|
| tecer-gsmm-introduction.html | `5733924338571f3246b49c38e1ac6af7c210ef372fb1948c383d0026583332ae` |
| tecer-gsmm-introduction-test.html | `c2f2df5e61f37f70b8ac10ab74a5d91bae8cf51f95a4d4dea731611c62e6ecb0` |
| tecer-gsmm-introduction-test-v2.html | `f496f6373d21fcd981cf00139a6954284280f5c049a9f7d0c48c05dd5db519db` |
| tecer-gsmm-introduction-test-v3.html | `93b2e53b22d284f5d7b7781da3d05d5ed6a3289625467160c45ee4d2e2a9ad4a` |

Post-exercise hashes: identical to pre-exercise for all four, in BOTH sessions. See
`c2-owner-deck-hash-post.json` (session 1) and `c1-fix-owner-hashes.json` (session 2).

---

## Criterion 1 — Round trip at the floor (HEADED, real gestures)

[REPLACE THIS ENTIRE SECTION WITH YOUR OWN EVIDENCED VERSION]

---

## Criterion 2 — New-file guarantee

**Criterion verbatim:** Each crossing wrote a DISTINCT new file; no crossing overwrote its
source. Compare directory file lists + source-file hashes before/after each crossing; include
the owner-deck before/after hashes. Capture the listings and hash comparisons.

**Gesture performed:**
- Opened deck copy in builder (isolated server instance).
- STE crossing: injected `c2-crossing-1.html` path, clicked `#switch-to-editor-btn`.
- OIB crossing: waited for runtime ready, injected `c2-crossing-2.html` path, clicked `#open-in-builder-btn`.
- After each crossing: hashed source deck; confirmed written file at distinct path.

**Observed result (from `c2-hash-comparison.json`):**
- `crossing1_wrote_new_distinct_file: true`
- `crossing2_wrote_new_distinct_file: true`
- `source_deck_unchanged_after_c1: true`
- `source_deck_unchanged_after_c2: true`
- `owner_decks_unchanged: true` (all 4)
- Paths: source `tmpji9y32qp/deck.html`, crossing1 `tmpb7jgkxn4/c2-crossing-1.html`, crossing2 `tmpk46nyqo7/c2-crossing-2.html` — all distinct.

**Evidence files:** `c2-hash-comparison.json`, `c2-owner-deck-hash-post.json`,
`c2-builder-after-second-crossing.png`

**Verdict:** **PASS** — Each crossing wrote a distinct new file; source and all owner decks unchanged.

---

## Criterion 3 — Cancel semantics

**Criterion verbatim:** Cancelling either dialog leaves the current view fully intact — no
navigation, no file written, no error surfaced. Exercise BOTH crossings' cancel paths.

**Gesture performed:**
- STE cancel: opened deck in builder, injected `null`, clicked `#switch-to-editor-btn`, waited 2.5s.
- OIB cancel: opened doc in editor via seam, waited for OIB enable, injected `null`, clicked `#open-in-builder-btn`, waited 2.5s.

**Observed result:**
- STE cancel: URL remained `builder.html` after 2.5s. No navigation, no error.
- OIB cancel: URL remained editor (`/app/`) after 2.5s. No navigation, no error.

**Evidence files:** `c3-01-builder-deck-loaded.png`, `c3-02-builder-after-cancel.png`,
`c3-03-editor-doc-loaded.png`, `c3-04-editor-after-cancel.png`

**Verdict:** **PASS** — Both cancel paths leave current view intact; no navigation or error.

---

## Criterion 4 — Disabled states

**Criterion verbatim:** "Switch to editor" is disabled when the builder tray is empty;
"Open in builder" is disabled when the editor has no document open. Observe both headed,
capture screenshots of both disabled states (and show the control enabling once content exists).

**Gesture performed:**
- Fresh `builder.html` load; checked `#switch-to-editor-btn` disabled.
- Fresh `index.html` load (no doc); checked `#open-in-builder-btn` disabled.
- Opened deck in builder; verified STE enabled after tray populated.
- Opened doc in editor; waited for OIB to enable (runtime ready).

**Observed result:** STE disabled on empty tray: true · OIB disabled with no doc: true ·
STE enables after deck load: true · OIB enables after runtime ready: true.

**Evidence files:** `c4-builder-empty-disabled.png`, `c4-editor-no-doc-disabled.png`,
`c4-builder-deck-loaded-enabled.png`, `c4-editor-doc-open-enabled.png`

**Verdict:** **PASS** — Both disabled states confirmed; both enable correctly.

---

## Criterion 5 — Editor regression

**Criterion verbatim:** Run `python -m pytest tests/e2e/test_g2_save_with_comments.py
tests/e2e/test_exit_smoke.py -q` from the app root. Must exit 0. Capture full pytest output.

**Gesture performed:** Ran the command from the app root with `--tb=short`.

**Observed result:** EXIT: 0, WALL_MS: 19045, `8 passed in 18.69s`

**Evidence file:** `c5-pytest-output.txt`

**Verdict:** **PASS** — Exit 0; 8 tests passed.

---

## Criterion 6 — decisions.md audit

**Criterion verbatim:** Read `decisions.md`. Confirm entries under "Decisions and Discoveries"
are decision+rationale+scope shaped — NO file-change lists, NO "N→M" count narratives, no
rewrite of a prior entry (append-only discipline).

**Gesture performed:** Read the file; extracted the "Decisions and Discoveries" section;
checked for file-change bullets and N→M narratives; counted `###` entries and verified
Decision+Rationale+Scope fields per entry.

**Observed result:** 5 entries (ADX-2, ADX-3, ADX-1, D-asset-colocation,
D-bridge-runtime-ready). File-change bullets: 0. N→M narratives: 0. Decision fields: 5/5.
Rationale: 5/5. Scope: 5/5.

**Evidence file:** `c6-decisions-audit.txt`

**Verdict:** **PASS** — No prohibited narratives; all 5 entries have Decision+Rationale+Scope.

---

## Criterion 7 — Enable-on-ready latency

**Criterion verbatim:** The editor's "Open in builder" button is disabled from the moment a
document open starts and enables only when the editor's iframe runtime signals ready. Measure
the gap from document content becoming visible to button enabling. PASS if gap ≤ ~1000ms.

**Gesture performed:**
- Dialog path: navigated to editor, injected deck via seam, clicked `#open-btn`. Timestamped content visible; polled `#open-in-builder-btn.disabled` until enabled.
- File-param path: navigated to `editor/?file=<deck_path>`. Same timing.

**Observed result:**

| Open path | Content→button gap | Total open→button |
|-----------|-------------------|-------------------|
| dialog | **155 ms** | 233 ms |
| file-param | **187 ms** | 265 ms |

**Evidence files:** `c7-latency-log.json`, `c7-latency-dialog.png`, `c7-latency-file-param.png`

**Verdict:** **PASS** — 155ms and 187ms; both well under 1000ms.

---

## Summary verdict table

| Criterion | Verdict |
|-----------|---------|
| 1 — Round trip at the floor | [YOUR VERDICT] |
| 2 — New-file guarantee | **PASS** |
| 3 — Cancel semantics | **PASS** |
| 4 — Disabled states | **PASS** |
| 5 — Editor regression | **PASS** |
| 6 — decisions.md audit | **PASS** |
| 7 — Enable-on-ready latency | **PASS** |

## Notes for the conductor

1. [YOUR session-2 notes, including the measured order/marker assertions]
2. C7 timing is machine-specific: 155ms / 187ms on Windows 11 / SSD / localhost — a favorable
   environment, not a cross-machine floor benchmark. (session 1)
3. No `failed` or `unexercisable` rows. [adjust if your C1 verdict differs]
<<<END findings-p4.md>>>

## RETURN SCHEMA (your final reply — exactly these five fields)

- **status:** EXACTLY one of `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`.
- **landed:** the files you created (evidence files + `findings-p4.md`). NO code changes, NO commit.
- **validation:** each command/exercise run — command, `EXIT`, `WALL_MS`, `SKIPPED_COUNT` (with
  per-skip reasons if > 0). Include your headed driver run and the explicit order-match and
  marker-present assertion results (true/false).
- **concerns:** anything worth the conductor's attention.
- **open_questions:** anything unresolved bearing on this or downstream work.

**Bottom line in your reply:** one line — `criterion 1 | <verdict>` — plus the order-match
boolean, the marker-in-thumbnail boolean, and whether `findings-p4.md` was written.
