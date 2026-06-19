# Done-Gate Evidence — Hypresent close-guard (unsaved-changes tab-close warning)

- Date: 2026-06-18
- Repo / app: rbtv → `studio/hypresent`
- Tier: Full
- Task: Add a browser tab-close / refresh / navigate-away confirmation that fires the native "Leave site? Changes you made may not be saved" dialog when the open document has unsaved changes, and stays silent when it is clean (freshly opened or just saved).

## Criteria (owner-confirmed 2026-06-18)

- **C1** — With unsaved edits, pressing Ctrl+W / closing / refreshing the tab makes the browser show its "Leave site? Changes may not be saved" confirmation; choosing Cancel keeps the document and all edits open.
- **C2** — With nothing unsaved (freshly opened, no edits), closing / refreshing the tab shows no confirmation.
- **C3** — After editing then Saving (Ctrl+Shift+Q) so the top bar reads "Saved", closing / refreshing shows no confirmation (save clears the guard).

## Drivability rows (Contract phase)

| Criterion | Surface | Verdict | Seam built |
|-----------|---------|---------|------------|
| C1 | Browser-native `beforeunload` confirmation (Chrome chrome) | `drivable` — real close-with-unsaved-changes in headed Chrome; the prompt is observable as a Playwright `dialog` event (type `beforeunload`). The literal dialog wording is browser chrome → optional owner-UAT backstop. | none (no app seam) |
| C2 | Same | `drivable` — close-with-runBeforeUnload on a clean doc; assert no dialog event | none |
| C3 | Same | `drivable` — edit → Save (Ctrl+Shift+Q = silent overwrite, no native dialog) → close; assert no dialog event | none |

## Exercise (Exhibit phase)

**Floor:** headed Chromium, real gestures (real element click to select, real `#comment-btn` click, real typing, real Ctrl+Enter submit, real Save click, real refresh). The owner's gitignored sample (`tecer-gsmm-introduction.html`) is absent locally (verified via `Test-Path` → False), so the exercise uses the self-contained synthetic fixture `agent-comments.html`.
**Method:** committed regression test `tests/e2e/test_close_guard.py`, run headed (`HYP_HEADED=1 HYP_SHOT_DIR=<this folder>`). Per-criterion machine results in `results.json`.

| Criterion | Gesture performed | Observed result | Evidence file | Verdict |
|-----------|-------------------|-----------------|---------------|---------|
| C1 | Opened the fixture; clicked a heading + `#comment-btn`, typed a comment, Ctrl+Enter (chip → "Unsaved"); registered a dialog listener that dismisses (== Cancel); pressed refresh (`page.reload`). | Browser raised a `beforeunload` dialog (`results.json` → `C1.dialog="beforeunload"`); dismissing it (Cancel) abandoned the refresh — the comment thread survived and the chip stayed "Unsaved" (`thread_present=true`, `chip="Unsaved"`). | `c1-unsaved-chip.png`, `results.json` | `held` |
| C2 | Opened the fixture (clean, chip "Saved"); attempted a real tab close running beforeunload. | No dialog fired; the tab closed silently (`C2.dialog=null`, `page_closed=true`). | `c2-saved-chip.png`, `results.json` | `held` |
| C3 | Opened; added a comment (chip "Unsaved"); clicked Save (silent overwrite → chip "Saved"); attempted a real tab close running beforeunload. | No dialog fired; the tab closed silently (`C3.dialog=null`, `page_closed=true`). | `c3-saved-after-edit-chip.png`, `results.json` | `held` |

**Verdict summary: 3/3 `held`.** No `failed` / `unexercisable` / `held-surprising` rows.

## Notes

- **One handler, all exits.** A single `beforeunload` listener on the editor shell page covers Ctrl+W, the window's X, refresh, and address-bar navigation identically (they are the same browser event).
- **Why C1 is proven via refresh, not literal Ctrl+W.** Playwright's `page.close(run_before_unload=True)` force-closes the page regardless of the dialog choice, so it can prove the prompt *fires* but not that *Cancel keeps the work*. Refresh (a named C1 trigger) proves both: dismiss → navigation abandoned → work survives. The prompt-on-close was independently observed during development (`page.close` → `beforeunload` dialog event).
- **Browser-native residue → optional owner-UAT.** The literal Chrome dialog wording, and the visual of clicking "Cancel" on an actual Ctrl+W, are browser chrome we cannot restyle or screenshot; the refresh-cancel test is the automated analogue. 15-sec owner check: open a file, add a comment, press Ctrl+W → click **Cancel** (tab stays) → press Ctrl+W again → click **Leave** (it closes).
- **Activation nuance.** C2 (no prior interaction) would not prompt regardless of dirtiness; C3 isolates the dirty-check by having real activation (edit + save) yet staying silent because the document is clean.
- **Build.** `docDirty` mirror added in `setDocState` (`app/js/main.js`, the single Saved/Unsaved choke point); `beforeunload` guard registered in the shell boot (`app/js/main.js`); `window.__hypSuppressUnloadPrompt` set before the "Open in builder" navigation (`app/js/shell/file-controls.js`) so that intentional, already-saved in-app switch does not show a spurious leave-prompt.
