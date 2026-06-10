# DISPATCH HEADER — p5-checkpoint session 3 (B15) — COLD VERIFIER, C1 SAVE→CROSS→BACK RE-EXERCISE (claude:sonnet)

You are cold-verifier SESSION 3 for the final checkpoint of the builder-open-deck plan. Sessions 1+2 exercised the full contract; AFTER they returned, the conductor's exit probes exposed a real product defect on one leg of criterion 1, and that defect has since been FIXED. Your job is narrow and decisive: re-exercise THAT LEG on the fixed build with STRUCTURAL assertions, re-grade C1 from your own evidence, and amend the two findings sheets with honest three-session attribution.

## Background you are entitled to — [INLINED] (conductor-supplied facts; verify nothing by reading builder tests or claims)

- **The defect (now fixed):** after "Save as new file", the builder re-pointed the deck source to the new file but kept STALE tray-item indices (positions in the PRE-save deck). The NEXT save (including the editor-crossing's automatic Save-As) re-applied the old indices against the new source → one slide silently dropped, a duplicated slide gained an extra copy — SLIDE COUNT PRESERVED, so count-level checks passed. Session 2's crossback assertion was marker-presence-only and carried this corruption undetected.
- **The fix (commit `5fc186f`, already in HEAD):** the tray model is rebased to the saved deck after save-new (`tray.rebaseToSavedDeck()` wired in `builder-main.js`).
- **Your mandate:** prove, at full section-mapping level, that on the FIXED build a restructure → save-new → cross-to-editor → edit → save → cross-back loop loses NOTHING.

## Isolation — what you MUST NOT read

- `run-log.md`, `state-capsule.md`, any `_dispatch-*.md`, any `_*-run-*.log` (conductor surfaces)
- Any `findings-*.md` under `phase-1/` … `phase-4/` evidence folders
- Builder test FILES as a substitute for exercising. (You MAY open `phase-5/evidence/findings-p5.md` and the vault done-gate sheet ONLY to AMEND them at the end — never to inherit verdicts for your own exercise.)

## What you work with

- **App root (work-dir):** `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent`
- **Plan folder:** `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck`
- **Test seams** (env-gated, for native dialogs only — every other gesture is REAL): set `HYP_TEST_DIALOG=1` on the server process; `POST /api/_test/set-dialog` (native open/save file dialogs), `POST /api/_test/set-folder-dialog` (library folder picker). Server start + browser helpers: `tests/e2e/conftest_helpers.py` (`start_server`) and `tests/e2e/builder_helpers.py` — reuse the helpers to LAUNCH; the exercising gestures stay yours. Use ABSOLUTE paths in every server/dialog/file argument.
- **Gesture recipe — [INLINED] (harness mechanics learned this run; binding):** (1) target tray rows by RE-QUERIED `data-slide-id`/`data-uid` selectors immediately before EACH gesture — never reuse stale ElementHandles across gestures (the tray re-renders; stale handles mis-aim). (2) The hand-rolled drag is timing-fragile: drag the row's `.grip` with a slow stepped mouse move and VERIFY the resulting DOM order before proceeding; retry once if the drop didn't take. (3) If you add a library slide, click the `.s-cap` caption element (the `.slide-thumb-wrapper` overlay intercepts pointer events) — though the library-add gesture is NOT required for this session's mandate.
- **OWNER DATA — READ-ONLY, ABSOLUTE:** the root decks `tecer-gsmm-introduction*.html` at the app root are the owner's REAL decks. NEVER write to them or save over them. Copy `tecer-gsmm-introduction.html` to an OS temp folder and exercise on the COPY. SHA-256 hash all 4 originals BEFORE and AFTER your whole session and record both sets in an evidence file (must be identical). Ignore the `-test*/-v2/-v3` leftovers.

## The exercise — ONE CONTINUOUS HEADED session (fidelity floor binding, per the installed `rbtv-done-gate` rule)

HEADED browser (`headless=False`), REAL mouse/keyboard gestures (never synthetic in-page `dispatchEvent`), the real server, the real pages, the owner's real deck as a temp COPY. Evidence captured as FILES on disk DURING the exercise. All evidence files use the **`c1-s3-`** prefix.

1. Open the temp deck copy in the builder (10 slides expected).
2. Restructure so positional indices are thoroughly displaced: REORDER (move a later slide before an earlier one), REMOVE one slide, DUPLICATE one slide, ADD one blank. Screenshot each stage; dump the tray's DOM order (slide-ids) after each gesture.
3. **Save as a NEW file** (save-new seam path → an OS-temp output path). Immediately copy the saved file to `c1-s3-save1-frozen.html` in the evidence folder BEFORE any further gesture — this frozen artifact is your reference corpus.
4. **Cross to the editor** (the save-and-switch crossing; give the crossing's Save-As dialog a second OS-temp path). The crossing writes a second file.
5. In the editor, type a recognizable marker ` [CV-B15-S3]` into one slide's text via real keyboard; save (Save-As seam → a third temp path, or the crossing file per the app's flow — record which).
6. **Cross back to the builder.**
7. **STRUCTURAL ASSERTIONS — the heart of this session.** Write a small script that splits each HTML file into its top-level `<section>` spans and produces a FULL per-section mapping (SHA-256 of each span + extracted text). Assert and record:
   - **A. Crossing fidelity:** the crossing's saved file maps section-for-section to `c1-s3-save1-frozen.html` — same count, same order, every section hash IDENTICAL (the crossing happens with no intervening edit). Byte-identity of the whole file is the expected strongest result; report it.
   - **B. Crossback fidelity:** the post-edit saved file maps section-for-section to the frozen save — same count, same order, EXACTLY ONE section differing, and that section's text differs ONLY by the typed marker (token-level: entity-decode `&nbsp;`/`&amp;` and collapse whitespace before comparing — the editor's serializer losslessly re-encodes bare `&` as `&amp;`, and contenteditable may emit `&nbsp;`; these are NOT content diffs).
   - **C. No leakage:** no `hyp-` / `data-hyp-*` tokens in any file your session saved.
   - A bare count is NEVER sufficient — the mapping (hashes + texts, per section, in order) is the proof. Persist the mapping JSONs as evidence files.
8. Grade **C1** from THIS evidence: `held` / `held-surprising` / `failed` / `unexercisable` + reason. Do not fix defects you find — report them; a `failed` verdict with evidence is a valid return.

## Sheet amendments (after the exercise, from your own evidence)

1. **`phase-5/evidence/findings-p5.md`** — amend the C1 row/section with THREE-SESSION attribution: s1 (C1 graded failed; root-caused later as a harness artifact), s2 (C1 graded held on identity-targeted re-exercise, BUT its crossback assertion was marker-only and carried the then-undiscovered stale-items corruption undetected), s3 (this session: save→cross→back leg re-exercised on the fixed build with full structural mapping — your verdict). Update the `## Human Review Presentation` section to reflect the final C1 state for a reader with zero session context. Preserve the existing sheet's voice and the opus-audit annotations; amend, never rewrite history.
2. **Vault done-gate sheet** `C:/Users/henri/Documents/second-brain/1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-10-builder-open-deck.md` — same amendment in the done-gate table shape; cite your evidence files by vault-root-relative paths (`3-resources/tools/rbtv/studio/hypresent/docs/plan/builder-open-deck/phase-5/evidence/c1-s3-...`).

## Bounds

- Write ONLY: `phase-5/evidence/c1-s3-*` files + the TWO sheets above + OS-temp working copies. NEVER app/server/test source, never task/plan/decisions files, never the owner decks, never any other evidence file.
- NO git operations (no staging/commit/push) — do not invoke any commit skill. NO web work.

## Return — EXACTLY these five named fields as your final reply (MANDATORY — a prose report is a contract violation)

- `status`: EXACTLY one of `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`. (`DONE`/`DONE_WITH_NOTES` = the exercise COMPLETED — even with a `failed` C1 verdict; the verdict lives in the sheets.)
- `landed`: every file you created/modified (evidence files + the two sheets), with your C1 verdict.
- `validation`: each command/exercise run — command, `EXIT`, `WALL_MS`, `SKIPPED_COUNT: 0` (any skip needs a per-skip reason). Include the hash brackets and the structural-mapping assertions.
- `concerns`: honest residual doubts, surprising observations, anything the owner should weigh.
- `open_questions`: unresolved items (empty if none).

Your final text IS the parse surface — the five fields, nothing before or after them.
