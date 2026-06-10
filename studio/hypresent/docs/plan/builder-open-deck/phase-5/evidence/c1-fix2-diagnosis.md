# c1-fix2 — code-level diagnosis + fix for the stale-index crossing-save defect

**Role:** DEBUG-FIX (top-tier). **Date:** 2026-06-10. **Status:** DONE.
Confirms the conductor's data-derived root cause in code, fixes at the root, adds one regression test, proves the defect is gone end-to-end.

Reads on: `ep-crossing-stale-items-derivation.md` (conductor derivation).

## Mechanism confirmed in code

The defect is a **post-save state inconsistency** in the builder: after a `new-file` save, the deck *source* is re-pointed to the freshly written file, but the tray *model* keeps its PRE-save `index` values. The next save re-applies those stale indices against the new source, so `recompose` mis-maps sections — a duplicate gains an extra copy and another slide is silently dropped.

Exact call chain (pre-fix):

- `app/js/builder/builder-main.js:508-513` (`doSave`, `new-file` branch): on save success it set `state.deck.path = result.path` (re-point to the new file) and updated the deck chip — but did NOT touch the tray model. The tray rows still carried `index` values that were positions in the ORIGINAL opened deck.
- `app/js/builder/tray.js:213-223` (`getItems`): emits `{kind:'existing', index: m.index}` per row — those stale indices verbatim.
- `app/js/builder/deck-save.js:43-48`: posts `source_path: deck.path` (now the NEW file) together with those stale `items`.
- `server/deck_api.py:194-203` + `server/recompose.py:104-123`: `recompose` does `spans[idx]` against the NEW file's sections. With the new file's section order `[sec1, sec1, sec0, sec2..sec9]` and stale items `[1,1,0,2,3,4,5,6,7,8,9]`, indices re-apply as `new[1],new[1],new[0]=sec1×3, new[2..9]=sec0,sec2..sec8`, and `new[10]` (sec9, "Obrigado") is never referenced → DROPPED. Section count stays 11, masking the loss. Byte-exact to the conductor's `ep-probe-save.html`.

The trigger surface is the "Switch to editor" crossing (`builder-main.js:531-556`), which fires a SECOND `new-file` save via `saveDeck(... mode:'new-file')` after a prior save-new — exactly the two-save sequence no suite test exercised.

## Fix — direction (a): rebase the tray model to identity against the saved file

**Why (a), not (b):** after a save-new the builder TREATS the newly saved file as the current deck — it re-points `state.deck.path`, renames the deck chip, and (for the crossing) navigates to `/app/?file=<new path>`. The app's state model says "the current deck IS the new file." Keeping the original source as the recompose base (direction b) would contradict the displayed/edited state and break the crossing navigation, which loads the new file. So the model must be reconciled to the new file.

Recompose writes one `<section>` per tray row in tray order, so after a save every row maps to the saved file's section at its OWN position. The fix collapses each row to `{kind:'existing', index: <its position>}` (identity), discarding stale pre-save indices and library/blank provenance — matching what a fresh open of the saved file already produces (PB11-1 asserts "all rows are deck kind after reopen"). The NEXT save then performs an identity recompose, which ADX-2 guarantees is byte-faithful — and save-#1 behavior is untouched (the original source + original indices map is unchanged), so save-#1 stays byte-identical.

Files changed (allowlist only):

| File | Change | Size |
|------|--------|------|
| `app/js/builder/tray.js` | `+rebaseToSavedDeck()` (`tray.js:209-227`): rewrites every model row to `existing` kind with identity index = position; exported in the return object (`tray.js:256`) | +20 / -2 |
| `app/js/builder/builder-main.js` | `+rebaseDeckToSavedFile(savedPath)` (`builder-main.js:361-374`): reloads the saved file's head+sections via `loadDeckByPath`, re-installs the srcdoc provider against them, calls `tray.rebaseToSavedDeck()`. Wired into the `new-file` branch of `doSave` with `await rebaseDeckToSavedFile(result.path)` (`builder-main.js:535`) | +25 (net) |
| `tests/e2e/test_pb11_deck_save.py` | `+test_second_save_after_restructure_faithful` (PB11-8) + `_reorder_first_two` drag helper | +133 |

The "Switch to editor" handler itself is unchanged: by the time its second save fires, `doSave`'s rebase has already run (after P3's first save), so its items carry identity indices → faithful. (When switch-to-editor is the user's FIRST save, it maps against the original source correctly, then navigates away — no second in-page save, so no rebase needed before navigation.)

## Regression test (PB11-8) — content/order/identity, never count-only

`test_second_save_after_restructure_faithful`: open deck copy → drag-reorder sec1 before sec0 (real pointer-event drag through the hand-rolled sorter, with the probe's retry) → duplicate sec1 → save-new (#1, frozen as the faithful reference) → save AGAIN to a second path. Asserts the second save's bytes:

- 11 sections; the dropped slide "Obrigado." PRESENT (the exact defect signature was its silent loss);
- the sec1 duplicate at EXACTLY positions 0 and 1, NOT leaked to a third (`s2_secs[1] != s2_secs[2]`);
- sec0 (cover, `slide--cover`) at position 2;
- **decisive:** the second save's section list is identical to the frozen save-#1 (EOL-normalized).

**Catches-the-defect proof:** with the fix temporarily disabled, the test FAILS with `AssertionError: 'Obrigado.' not found in [second save]` — the precise silent-drop signature. With the fix, it passes 3/3.

## Validation (un-piped exit codes)

| Command | EXIT | Notes |
|---------|------|-------|
| `node --check` × tray.js, builder-main.js, deck-save.js | 0, 0, 0 | all three touched/allowlisted files |
| PB11-8 regression × 3 | green, green, green | ~5s each (drag takes on first attempt) |
| Full builder suites × 3 (`pb5,8,9,10,11,12`) | 0, 0, 0 | 30 passed each; ~51–55s |
| Conductor probe driver (temp deck, OS-temp out) | P1/P2/P3/P4 HELD | P5 FAILED = known probe-script miscalibration (byte-identity-through-editor), per dispatch |

**Decisive end-to-end signal:** the probe's SECOND save file (`c1-fix2-probe-second-save.html`) is **byte-identical** to the frozen save-#1 (`c1-fix2-probe-save1-frozen.html`) — same SHA256 `40523b4f851a17d4587dc894204fd8a0d644bec516ea68e13d97765c9b99c759`, both 94922 bytes, all 11 sections matching, "Obrigado." present in both. See `c1-fix2-temp-probe-comparison.txt`. Before the fix the second save dropped "Obrigado." and tripled sec1; after the fix the intended restructure `[sec1, sec1, sec0, sec2..sec9]` survives the crossing save intact.

## Evidence files (this fix)

- `c1-fix2-diagnosis.md` — this note
- `c1-fix2-temp-probe-comparison.txt` — SHA256 byte-identity proof (second save == frozen save-#1)
- `c1-fix2-probe-second-save.html` / `c1-fix2-probe-save1-frozen.html` — the two probe save files (identical)
- `c1-fix2-probe-log.txt` / `c1-fix2-probe-result.json` — probe driver run output
