# V3-T2 Bug Report — R2 resize/move/reorder still dead after V3-T1

## Date
2026-06-04

## Blocking issue (D14)
Real-input resize, move, and reorder do **not** produce geometry or DOM changes.
The rewritten test suites (F2 + R2) now exercise the product with real `page.mouse` events and hard assertions, and they fail on the same root cause: the resize handle (`.moveable-se` / `.moveable-e`) is **not hittable** via `elementFromPoint`.

## Failing assertions

### `test_r2_resize_real.py` (port 8792)
| Test | Assertion | Failure |
|------|-----------|---------|
| `test_handle_is_hittable` | `elementFromPoint(handleCenter)` returns a `.moveable-` element | `elementFromPoint` returns **null** — handle is not hittable (direct R2 root cause) |
| `test_resize_changes_geometry` | width/height change by >2 px after a real handle drag | width stays **198 → 198**; height unchanged (R2 still dead) |
| `test_resize_twice` | two independent resize drags both change width | first resize **198 → 198** (no effect) |
| `test_move_changes_translate_by_delta` | `style.translate` written after a ≥40 px body drag | translate is **empty string** (move dead) |
| `test_reorder_changes_dom_index` | dragging a sibling over its neighbour changes DOM child index | index stays **0 → 0** (reorder dead) |
| `test_no_console_errors` | no unexpected console errors | **PASS** |

### `test_f2_select_guides.py` (port 8782, rewritten)
| Test | Assertion | Failure |
|------|-----------|---------|
| `test_drag_shows_guidelines` | real body drag changes `style.translate` | translate stays **'' → ''** |
| `test_resize_shows_guidelines` | real handle drag changes computed width | width stays **198 → 198** |
| `test_escape_and_empty_click_deselect` | discovers an empty point and clicks it | no empty point found (fixture fills viewport) — **test limitation, not the blocking bug** |

## Root-cause hypothesis
V3-T1 fixed pointer-event forwarding for the **iframe document**, but the `.moveable-control-box` handles are rendered inside `#hyp-interaction-wrapper` which sits **outside** the iframe (in the parent document). The handle elements therefore receive no forwarded pointer events, so:
- `elementFromPoint` on the iframe document cannot see them (they are in a different document).
- Real mouse drags on the handle coordinates hit nothing / the iframe content underneath, so Moveable never receives the drag start.
- Body-drag (move) may also be swallowed because the selection logic does not correctly map parent-document pointer coordinates to the iframe-local element.

## Required fix (product code — NOT in test allowlist)
1. Ensure pointer events on `#hyp-interaction-wrapper` and its `.moveable-direction` handles are correctly wired so Moveable can initiate resize.
2. Verify that body-drag (move) and sibling-drag (reorder) translate real pointer deltas into geometry/DOM changes.

## Do not patch tests
The tests are correctly detecting the bug. Lowering assertions or re-introducing `skipTest` would hide the defect.
