# C1 Debug Diagnosis — multi-step deck-save defect

**Date:** 2026-06-10
**Role:** DEBUG (orchestration)
**Verdict:** **H3 — verifier-driver targeting drift (HARNESS ARTIFACT). NO product bug.**

## Defect as reported

Verifier drove (headed, `slow_mo=300`) on a temp copy of `tecer-gsmm-introduction.html`
(10 sections): open → reorder swap 0↔1 → remove pos2 → duplicate pos0 → add blank →
(lib add failed, ignored) → save new. Saved file: orig sec0 ABSENT, orig sec1 appears
THREE times, orig sec2 absent. Isolated reorder-only save was correct.

## Evidence gathered

All on temp copies of the OWNER deck; server `HYP_TEST_DIALOG=1` on :9788.

| Run | Driver / targeting | Saved sections (mapped to orig index) | Correct? |
|-----|--------------------|---------------------------------------|----------|
| Original verifier (`tmpw6ydk74u`) | cv_b15, positional rows[n] | `[1,1,1,3,4,5,6,7,8,9,blank]` | ✗ sec0 gone, sec1 ×3 |
| cv_b15 re-run (`tmpouoii7ko`) | cv_b15, positional rows[n] | `[1,1,1,3,4,5,6,7,8,9,blank]` | ✗ same |
| **c1-debug-repro** | content-aware, fresh snapshot per gesture | `[1,1,0,3,4,5,6,7,8,9,blank]` | ✓ **byte-for-byte intended** |
| c1-debug-driver-trace | cv_b15 positional, drag DID NOT take | `[0,0,1,...]` | drag flaked off → different transient |

Captured `/api/deck-save` payload `items` in c1-debug-repro: `[1,1,0,3,4,5,6,7,8,9,blank]`.
Saved bytes hashes == payload-predicted hashes == intended arrangement, **exactly**.

## Why each hypothesis resolves

- **H1 (tray-model stale positional identity) — REFUTED.** The tray records carry a stable
  `uid` and a frozen source `index` set at deck-open (`builder-main.js` `loadDeckIntoTray` →
  `tray.setFromPreset`, each record `index: idx`). Reorder (`tray.js` sorter `onReorder`)
  only permutes the `model` array; it never rewrites `index`. `duplicate(uid)` copies the
  source record's `index` verbatim. `getItems()` emits `m.index` for each existing record.
  In every instrumented run the emitted indices matched the DOM rows actually present — no
  stale/positional identity ever surfaced. The model is faithful.
- **H2 (server recompose mis-splice) — REFUTED.** In all runs the saved bytes equal the
  POSTed payload mapped through `recompose` (`server/recompose.py` copies `spans[index]`
  verbatim). Saved == payload in c1-debug-repro (`[1,1,0,...]`) and in the verifier runs
  (`[1,1,1,...]` faithfully serializes whatever payload the broken gesture state produced).
  The server splices exactly what it is given.
- **H3 (driver targeting drift) — CONFIRMED.** The defect appears ONLY under the verifier's
  positional `query_selector_all(...)[n]` targeting combined with the flaky hand-rolled
  pointer-drag (`tray-sorter.js`) under `slow_mo=300`. The drag leaves the DOM/model in a
  transient state at the moment the driver snapshots `rows_now[2]`/`rows_now2[0]`, so the
  rows clicked diverge from the uids the driver *logs*. The model faithfully records the
  mis-aimed gestures; the save faithfully serializes them. Content-aware targeting (re-query
  by `data-slide-id`/`data-uid` immediately before each click, no stale snapshot) produces
  the correct intended save byte-for-byte.

## Root cause (harness)

1. **Stale ElementHandle snapshots across a flaky async gesture.** `rows_now =
   query_selector_all(...)` is captured, then `rows_now[2]` is clicked after the drag's
   rAF-driven `insertBefore` reflow may still be settling. Positional index 2 no longer maps
   to the logged uid.
2. **Positional (nth) targeting after a reorder is inherently ambiguous** — the whole point
   of the reorder is to move rows, so "row at position N" is exactly the unstable coordinate.

The product is correct. No `tray.js` / `builder-main.js` / `deck-save.js` / `deck_api.py` /
`recompose.py` change is warranted.

## Corrected gesture-targeting recipe for the C1 re-exercise

Drive by **identity, not position**, and **re-query immediately before every click** (never
reuse an ElementHandle captured before an intervening mutation):

1. **Open deck**, wait for `#tray-list .tray-row` count > 0 and a settle (`wait_for_timeout(800)`).
2. **Record the uid↔slideId map** from the DOM now (uid `N` ⇔ `deck-section-(N-1)` at open).
3. **Reorder (swap 0↔1):** perform the grip drag, then **assert the reorder took** before
   proceeding — `wait_for_function` that `rows[0].dataset.uid === <uid originally at 1>`.
   If it did not flip, retry the drag (headed pointer-drag is flaky). Do NOT continue on an
   un-taken drag.
4. **Remove a specific slide by identity:** decide the target by `data-slide-id` (e.g.
   "remove `deck-section-2`"), then
   `page.click("#tray-list .tray-row[data-slide-id='deck-section-2'] .tray-remove")`.
   Re-query by selector at click time; never `rows_now[2]`.
5. **Duplicate a specific slide by identity:** likewise
   `page.click("#tray-list .tray-row[data-uid='<uid>'] .tray-duplicate")`, choosing the uid
   you intend (e.g. the row now at position 0 = the post-swap uid), re-queried at click time.
6. **Add blank**, **save new** as before.
7. **Assert content, not counts:** map saved top-level `<section>` hashes back to the source
   deck's section hashes and compare to the intended index list
   `[1,1,0,3,4,5,6,7,8,9] + blank` (for swap0↔1, remove sec2, duplicate the post-swap pos0
   row which is sec1... — recompute the intended list from the identities actually chosen).

Equivalently and more robustly: assert intermediate model state after EACH gesture (the DOM
row uids/slideIds) and only proceed when it matches the intended post-gesture arrangement.
The content-aware `c1-debug-repro.py` in this folder is a working reference.

## Files produced (this debug)

- `c1-debug-repro.py` — content-aware reproduction + payload capture + saved-byte comparison
- `c1-debug-repro-log.txt`, `c1-debug-repro-result.json` — its per-gesture dumps + verdict inputs
- `c1-debug-driver-trace.py` — verifier-style positional driver with payload capture
- `c1-debug-driver-trace-log.txt`, `c1-debug-driver-trace-payload.json`
- `c1-debug-diagnosis.md` — this file
