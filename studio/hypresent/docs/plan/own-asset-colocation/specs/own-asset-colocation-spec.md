# Spec — Own-Asset Colocation on Save

## Goal

The owner restructures a deck in the builder and saves it to a DIFFERENT directory than its source; the deck's own (non-library) slide images render when the saved deck is reopened in the builder AND when it is opened in the editor — because every own `assets/*` file the saved deck still references is copied into the destination's `assets/` folder, with name collisions resolved so no slide ever renders the wrong image.

## Context Snapshot

**The gap being closed.** `handle_deck_save` (`server/deck_api.py`) today copies ONLY the assets referenced by added LIBRARY fragments (its loop over `resolved_fragments`). The source deck's OWN slides are spliced back by `recompose` with their `<section>` spans preserved byte-for-byte (ADX-2), so relative refs like `<img src="assets/logo.png">` ride into the saved file unchanged. When `out_path` is in a different directory than `source_path`, those files are not beside the saved deck → the images break. Ruling `D-asset-colocation` (`docs/plan/builder-open-deck/decisions.md`) recorded this as an accepted v1 limitation; THIS feature removes it.

**Current asset machinery to reuse** (`server/deck_api.py`):
- `_ASSET_RE` — matches `assets/…` paths in `src=`, `href=`, and `url(…)` forms.
- `_find_referenced_assets(html) -> list[str]` — unique relative `assets/…` paths in an HTML string.
- The library copy loop pattern: `src_asset = lib_root / rel_path`; skip if missing; `dst_asset = out_dir / rel_path`; **skip if `dst_asset` exists** (→ `assets_skipped`); else `dst_asset.parent.mkdir(parents=True, exist_ok=True)` + `shutil.copy2`, append to `assets_copied`.

**Recompose mapping** (`server/recompose.py`): `recompose(html, items)` emits exactly one output `<section>` per item, in item order — `existing`→the source section span (verbatim), `fragment`→the library fragment HTML, `blank`→`BLANK_SECTION`. The handler builds `recompose_items` in the same order as the request `items`. A library fragment is a single top-level `<section>` (`split_sections` on a fragment returns one span; the e2e suite asserts `len(frag_spans) == 1`). Separator selection in `recompose` is keyed on the `existing` item's `index` (`_sep_for`) — any mechanism MUST preserve that, so inter-slide separators stay byte-identical.

**Own-asset root** = `pathlib.Path(source_path).resolve().parent`. **Destination** = `pathlib.Path(out_path).parent` (`out_dir`).

**Response contract today:** `{"ok": true, "path": out_path, "assets_copied": [...]}` (+ `"assets_skipped": [...]` when a library asset collided). This feature ADDS `"assets_renamed": [{"from": "assets/x.png", "to": "assets/x-1.png"}, ...]` when an own-asset is colocated under a new name to dodge a collision.

**Recommended mechanism (implementer's call).** Rewrite colliding refs on each preserved section's ISOLATED HTML *before* it is spliced — e.g. extend the `recompose` `existing` item to accept an optional `html` override that is emitted in place of the source span while `index` still drives separator selection. This keeps the rewrite scoped to exactly the owning section and avoids fragile post-`recompose` result surgery. Any mechanism that satisfies the Behavior + invariants below is acceptable.

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | A preserved source slide refs `assets/x.png`, the source dir holds that file, and `out_dir` is a DIFFERENT dir with no `assets/x.png` | The file is copied to `out_dir/assets/x.png` (relative path preserved); response lists `assets/x.png` in `assets_copied`; the saved section's ref is unchanged |
| 2 | The same own-asset is referenced by several preserved sections | The file is copied ONCE; the ref stays consistent across every referencing preserved section |
| 3 | A preserved source slide refs `assets/x.png`, AND `out_dir/assets/x.png` already exists as a DIFFERENT file (a library fragment claimed it, or a pre-existing file) | The own-asset is copied under a fresh unique name `assets/x-{n}.png`; the ref `assets/x.png` is rewritten to `assets/x-{n}.png` ONLY inside the owning preserved source section(s); response lists the rename in `assets_renamed`; the pre-existing `assets/x.png` is untouched |
| 4 | `out_path` is in the SAME directory as `source_path` | No own-asset is copied or renamed; preserved sections are byte-identical to source (files already in place) |
| 5 | A preserved source slide refs an own-asset NOT present in the source dir | That ref is left as-is; nothing copied; no error (same tolerance as the library loop) |
| 6 | An own-asset ref appears only in a slide DROPPED from the restructure (absent from `items`) | That asset is NOT copied (only assets referenced by sections present in the saved deck are colocated) |
| 7 | Library-fragment asset handling | UNCHANGED from `D-asset-colocation` — library assets copied first; library refs are NEVER rewritten |

**Invariants (bind every mechanism):**
- Only preserved SOURCE sections may have refs rewritten. Library and blank sections are never rewritten.
- When no own-asset collides, every preserved section AND every inter-slide separator is byte-identical to source (existing faithfulness tests stay green).
- One source asset → one new name, reused across all sections that reference it.

## Edge Cases & Error Behavior

| Case | Required behavior |
|------|-------------------|
| Collision where the existing `out_dir` file is byte-identical to the own-asset | MAY reuse the existing file (no rename); renaming instead is also acceptable — the rule is "no slide renders the wrong image", and identical content cannot |
| A section refs both `assets/x.png` and `assets/x.png.bak` | Rewriting `assets/x.png` MUST NOT corrupt `assets/x.png.bak` — replace only at a path terminator (`"`, `'`, `)`, `>`, or whitespace) |
| `url(assets/x.png)` CSS form collides | Rewritten the same as `src`/`href` forms |
| Unique-name generation | `x-{n}.{ext}` with the smallest `n≥1` free against BOTH existing `out_dir/assets/` files AND names already allocated in this save; a stem with no extension gets `-{n}` appended |
| The 1:1 item→output-section assumption is violated (a fragment yields ≠1 top-level section) | Detect the mismatch and REFUSE rather than rewrite the wrong section — `(500, {"error": ...})`, nothing written |
| Source deck own-asset and a same-save library fragment both ref `assets/x.png` (different files) | Library claims `assets/x.png` (copied first); the own-asset is renamed per Behavior row 3 |

## Out of Scope

- Rewriting LIBRARY fragment refs; any change to library-asset behavior (`D-asset-colocation` stays).
- Approaches (b) rewrite-all-refs and (c) warn-only (owner-rejected).
- Copying the source deck's FULL asset tree — only assets the SAVED deck still references.
- Content-hash dedup across source + library.
- Same-directory library collisions (pre-existing library-side behavior, untouched).

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | Own image colocated on save-to-new-dir | `pytest tests/test_deck_api.py` — source deck with `assets/own.png` referenced by a kept section, saved to a new `out_dir` | `out_dir/assets/own.png` exists, bytes match; `assets/own.png` in `assets_copied`; exit 0 | pytest output log |
| 2 | Dropped-slide asset NOT copied | Same suite: two sections each ref a distinct own-asset; save keeps only section 0 | Only section 0's asset in `out_dir/assets/`; section 1's absent; exit 0 | pytest output log |
| 3 | Same-dir save is a no-op for own-assets | deck-save with `out_path` in the source dir | No copy, no rename; saved section byte-identical to source; exit 0 | pytest output log |
| 4 | Collision renames + rewrites | Source own-asset `assets/logo.png`; `out_dir` already holds a DIFFERENT `assets/logo.png` | Own copied as `assets/logo-1.png`; the kept section's ref rewritten to `assets/logo-1.png`; `assets_renamed` lists it; the pre-existing `assets/logo.png` unchanged; exit 0 | pytest output log |
| 5 | Multi-section consistency | Own-asset `assets/logo.png` referenced by a section AND its duplicate, colliding | One renamed copy; BOTH sections' refs rewritten to the same new name; exit 0 | pytest output log |
| 6 | Non-colliding restructure stays byte-faithful | Full existing suite | `pytest tests/test_deck_api.py tests/test_recompose.py` and `pytest tests/e2e/test_pb11_deck_save.py` all green | pytest output logs |
| 7 | Real deck renders in builder AND editor | Headed: a real deck copy with its own images (incl. a name-collision case), restructured + saved to a NEW directory; reopen in builder; open in editor via the crossing | Own-slide `<img>`s render (`naturalWidth > 0`) in both views; the collision case shows the CORRECT image | screenshot(s) + the saved deck's `assets/` dir listing + console-log capture, under `./phase-2/done-gate-evidence/` |

> Every criterion obeys the **Fidelity floor** + **Evidence plausibility** rules stated below — exercise at the real-app floor, capture a file on disk during the exercise, and reject physically-impossible metrics.

**Fidelity floor for every criterion:** the real application running whole, on a real deck copy; UI criteria use a visible browser + real input (the builder's open/restructure/save controls and the editor crossing), never synthetic `dispatchEvent`. Evidence is a file on disk written DURING the exercise — a prose claim alone does not satisfy a criterion. A genuinely undriveable criterion is marked `unexercisable` with the concrete blocker.

**Evidence plausibility:** a browser e2e under ~1s is auto-reject + rerun. Exit 0 plus an evidence file is not proof if the metrics are impossible.

## Return Expectations

Files changed, validation commands run + their exit codes + any skips with reasons, local commit hash if committed, concerns, blockers. The report is a hint; the repo state is the truth.
