# Hypresent v3 — Test Plan (Session 2, improvements-2026-06-r2)

Two-layer automated test design for the Session-2 fixes (R1–R9 + EXIT). Layer 1 = Python stdlib `unittest` (server endpoints; the R1 OS-z-order ctypes test). Layer 2 = Playwright (Python, sync API, headless Chromium) behavioral suites. Tests are scenario DESIGNS — Kimi writes the code from them. Every suite maps to a scorecard ID.

Grounding: `docs/improvements-2026-06-r2/spec.md` (V3-S decisions), `docs/improvements-2026-06-r2/diagnosis.md` (§Cross-cutting test mandates), the v2 test-plan (`docs/improvements-2026-06/test-plan.md`) and its conventions (`conftest_helpers.py`, fixture-copy, fail-loud `setUpClass`, port-per-suite). The six cross-cutting mandates below are implemented IN FULL.

---

## 0. The six cross-cutting mandates (diagnosis §Cross-cutting) — how each is enforced

| # | Mandate | Enforcement in this plan |
|---|---------|--------------------------|
| 1 | **Assert outcomes, not artifacts.** | Every interaction test asserts a MEASURED state change: resize → `getComputedStyle(el).width/height` delta; move → `el.style.translate`; delete → DOM node count / `querySelector` null; font-size → the SAME span's `font-size` +6px and zero empty siblings; align → the written CSS property value; copy-hex → clipboard readback. Presence of `.moveable-*`/buttons is NEVER sufficient. |
| 2 | **Real input only for interaction.** | All interaction/selection in NEW or CHANGED suites uses `page.mouse.*` / `page.keyboard.*` / real `.click()` on a Playwright locator. `element.dispatchEvent(MouseEvent)` for selection/interaction is BANNED. The existing synthetic-click selections in `test_f2_select_guides.py` (E-F2-4 line ~117, E-F2-5 line ~158, E-F2-7 line ~254) are REPLACED with real `page.mouse.click()` at the element's on-screen center (computed via the iframe rect + the element rect, the `screen_xy_of` helper already in that file). |
| 3 | **No skip-as-green.** | The `self.skipTest(...)` calls in `test_f2_select_guides.py` E-F2-4/5 (the guideline-render skips and the resize-handle-missing skip) are CONVERTED to hard outcome assertions: a real drag that produces no geometry change is a FAIL (it is the R2 bug). A missing handle is a FAIL. The only permitted skip in the whole suite is the R1 ctypes test's documented headless-CI skip — and only when no interactive desktop session exists (which on this machine it does, so it does NOT skip here). |
| 4 | **N≥2 repeat coverage.** | Font-size: the load-bearing test presses A+ THREE times on one selection (R8). Resize: the R2 suite drags the SAME handle TWICE (idempotency). |
| 5 | **elementFromPoint hittability guard.** | The R2 suite asserts `document.elementFromPoint(handleCenter)` returns a `.moveable-*` element (not `null`) AFTER selection — the direct lock on the R2 root cause. |
| 6 | **OS-boundary real test.** | R1's z-order is tested with stdlib `ctypes` Win32 against the REAL dialog endpoint (D23): run the real `_run_ps_dialog_default` in a background thread so a genuine OS dialog appears; `EnumWindows` finds it by title; assert `GetForegroundWindow()`==its HWND OR its extended style has `WS_EX_TOPMOST`; `PostMessage(WM_CLOSE)` tears it down. Documented skip-if-headless ONLY when no interactive desktop session is present — NOT the case on this machine, so it runs. |

---

## 1. Tooling, runner, ports

**Zero extra deps beyond Playwright + stdlib.** `ctypes` is stdlib (the R1 OS test needs no new dependency). pytest is OUT — stdlib `unittest` discovery only.

Run ALL tests from the `hypresent/` root:
```
python -m unittest discover -s tests -p "test_*.py" -v
```
Unit-only: `python -m unittest discover -s tests/unit -p "test_*.py" -v`
e2e-only: `python -m unittest discover -s tests/e2e -p "test_*.py" -v`

**e2e import bootstrap (mandatory, unchanged from v2/R08):** every e2e file begins with the 3-line `sys.path` bootstrap above `import conftest_helpers as H`:
```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conftest_helpers as H
```
`conftest_helpers.py` (already exists) provides `start_server`, `stop_server`, `copy_fixture`, `post_json`, `set_fake_dialog`, `open_via_dialog_ui`, `wait_runtime_ready`, `doc_eval`, `preset_author`, `FIXTURE`. `preset_author(page)` adds an `addInitScript` pre-seeding the author name in localStorage — it MUST be called BEFORE `page.goto(...)` so the script fires before the first navigation (suppresses the one-time author-name prompt); any suite that adds a comment uses it (RV13). New suites REUSE these helpers (no new helper file unless a new shared helper is needed; if a shared real-input click helper is added, it goes into `conftest_helpers.py` and that file is in the test task's allowlist).

**Fixture (mandatory, unchanged):** every suite copies `hypresent/tecer-gsmm-introduction.html` into a fresh tempdir per test (`H.copy_fixture()`) and operates on the COPY. The original is read-only and gitignored (U10a) — never staged/committed/mutated.

**Fail-loud fixture guard (mandatory, R07 — never skip-green):** every suite's `setUpClass` raises `AssertionError(f"Required fixture missing: {H.FIXTURE} …")` if the fixture is absent. NEVER `skipTest` for a missing fixture.

**Server lifecycle:** one `H.start_server(PORT, test_dialog=True)` per TestCase class (`setUpClass`/`tearDownClass`); poll `GET /app/` until 200 (≤6s) before tests; terminate in teardown.

### Port allocation (avoid 8765, 8781–8790 already used by v2 + unit)

Existing in-use ports (verified by grep): 8765 (default server), 8781 (f1), 8782 (f2), 8783 (f3), 8784 (f4), 8785 (f5), 8786 (g1), 8787 (g2), 8788 (exit), 8789 (unit save), 8790 (unit no-open). NEW v3 e2e suites use **8792–8799** (8791 was a transient diagnosis repro port, not a test; skipped for cleanliness). Changed suites keep their existing ports.

| Suite | Port | Status |
|-------|------|--------|
| test_r1_dialog_zorder (unit, ctypes) | n/a (no HTTP server; drives the real PS dialog) | NEW |
| test_r1_dialog_seam (unit, in-process) | n/a (in-process `api` calls) | NEW |
| test_r2_resize_real | 8792 | NEW |
| test_r3_delete | 8793 | NEW |
| test_r4_color_btn_removed | 8794 | NEW |
| test_r5_token_tooltip | 8795 | NEW |
| test_r6_copy_hex | 8796 | NEW |
| test_r7_alignment | 8797 | NEW |
| test_r8_font_size_repeat | 8798 | NEW |
| test_r9_outline_removed | 8799 | NEW |
| test_f2_select_guides | 8782 | CHANGED (rewrite — real input, no skip) |
| test_exit_smoke | 8788 | CHANGED (add R2/R3/R8 real ops + R4/R9 absence) |

---

## 2. Suite delta (which existing v2 tests change or are deleted; the rest of the 67 stay green)

| File | Action | Why |
|------|--------|-----|
| `tests/e2e/test_f2_select_guides.py` | **CHANGED (rewrite)** | Replace the 3 synthetic `dispatchEvent` selections with real `page.mouse.click()`; convert the 3 `skipTest` calls (E-F2-4/5) to hard outcome assertions (a no-effect drag = FAIL); ADD a geometry-delta assertion to E-F2-4 (drag changes `translate`) and E-F2-5 (resize changes `width/height`). Mandates 2 + 3. |
| `tests/e2e/test_exit_smoke.py` | **CHANGED** | E-EXIT-2 adds a REAL resize (R2), a REAL delete (R3), and a REAL 3-press font-size (R8); E-EXIT-3 additionally asserts `#outline-list` is absent (R9) and `#color-btn` is absent (R4). |
| `tests/e2e/test_g1_panel_survival.py` | **CHANGED** | Remove the three outline assertions (`#outline-list` existence/population/order — lines ~38-39, 47-48, 55, 67, 74-75, 89). G1 now asserts only the color popover container + comment panels survive a second open (the outline no longer exists per R9). The G1 INVARIANT (popover never wipes siblings) is preserved with the comment panel as the sibling witness. |
| All other v2 suites (f1, f3, f4, f5, g2, unit dialogs/save) | **UNCHANGED** | Their features are untouched by v3; they MUST stay green. No port changes. |

**No v2 test file is DELETED.** v2 had no dedicated outline test (the outline was only asserted inside `test_g1_panel_survival.py`), so R9 removes assertions from g1 rather than deleting a file. Net suite count: 67 v2 tests (minus the 3 outline assertions folded out of g1, which were sub-assertions not separate tests, so the TEST count is unchanged at the test-method granularity) + the new v3 suites. The exact final count is reported by `test_exit_smoke`/the full run.

---

## Layer 1 — stdlib `unittest`

### test_r1_dialog_zorder.py — R1 (OS z-order, REAL dialog, ctypes — mandate 6 / D23)

Drives the REAL `_run_ps_dialog_default` (NOT the seam) so a genuine OS dialog appears, then uses stdlib `ctypes` Win32 to assert it is foreground/top-most and tears it down. NO HTTP server.

**Headless-CI skip condition (documented, the ONLY permitted skip):** skip with a clear message ONLY when no interactive desktop session is available. Detection: `sys.platform != "win32"` OR `ctypes.windll.user32.GetForegroundWindow()` returns 0 at module setup (no foreground window ⇒ no interactive session). On this machine an interactive desktop session IS present, so the test RUNS (does not skip).

```python
import ctypes
import sys
import threading
import time
import unittest

# import api in-process (server/ on sys.path)
# ... HERE/REPO/sys.path bootstrap, import api ...

OPEN_TITLE = "Open Presentation"

def _enum_find_by_title(substr):
    """EnumWindows → return (hwnd, ex_style) of the first visible top-level window whose title contains substr."""
    user32 = ctypes.windll.user32
    found = {"hwnd": None, "ex": 0}
    GWL_EXSTYLE = -20
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _l):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        if substr.lower() in buf.value.lower():
            found["hwnd"] = hwnd
            found["ex"] = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            return False
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found["hwnd"], found["ex"]


@unittest.skipUnless(sys.platform == "win32", "R1 z-order test is Windows-only")
class DialogZOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Documented headless skip: only when no interactive desktop session exists.
        if ctypes.windll.user32.GetForegroundWindow() == 0:
            raise unittest.SkipTest(
                "No interactive desktop session (headless CI) — R1 real-dialog z-order requires a desktop. "
                "On an interactive Windows 11 + Chrome session this test runs."
            )

    def test_real_open_dialog_is_topmost_and_foreground(self):
        WS_EX_TOPMOST = 0x00000008
        WM_CLOSE = 0x0010
        result = {"path": "__unset__"}

        def run_dialog():
            # Real PowerShell -STA dialog with the TopMost owner form (V3-S1).
            result["path"] = api._run_ps_dialog_default("open")

        t = threading.Thread(target=run_dialog, daemon=True)
        t.start()

        # Poll up to ~8s for the dialog window to appear.
        hwnd, ex = None, 0
        deadline = time.time() + 8
        while time.time() < deadline:
            hwnd, ex = _enum_find_by_title(OPEN_TITLE)
            if hwnd:
                break
            time.sleep(0.2)

        self.assertIsNotNone(hwnd, "real Open dialog window did not appear (title 'Open Presentation')")

        # MEASURED z-order: foreground HWND match OR the TopMost extended-style band.
        fg = ctypes.windll.user32.GetForegroundWindow()
        is_topmost = bool(ex & WS_EX_TOPMOST)
        self.assertTrue(
            fg == hwnd or is_topmost,
            f"dialog not on top: foreground={fg} dialog={hwnd} ws_ex_topmost={is_topmost}",
        )

        # Teardown: close the dialog so the PS process returns (cancel → None).
        ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        t.join(timeout=8)
        self.assertFalse(t.is_alive(), "PowerShell dialog process did not exit after WM_CLOSE")
        self.assertIsNone(result["path"], "closing the dialog should cancel → None")
```

| # | Given | When | Then |
|---|-------|------|------|
| U-R1Z-1 | interactive desktop; real `_run_ps_dialog_default("open")` on a background thread | poll `EnumWindows` for "Open Presentation" | a visible top-level window with that title appears within 8s |
| U-R1Z-2 | the found dialog HWND + ex-style | read `GetForegroundWindow()` + `WS_EX_TOPMOST` | foreground==HWND OR `WS_EX_TOPMOST` set (the owner-inherited top-most band) |
| U-R1Z-3 | dialog open | `PostMessage(WM_CLOSE)` | the PS thread returns; launcher returns `None` (cancel) |

Maps to: **R1**. (Documented skip ONLY on headless CI; runs on this machine.)

### test_r1_dialog_seam.py — R1 (in-process seam regression; locks the unchanged F1 routes)

In-process `api` calls with an injected fake launcher (no PowerShell). Re-locks the routes R1's PS edit must not break.

| # | Given | When | Then |
|---|-------|------|------|
| U-R1S-1 | `set_dialog_launcher(lambda k: <temp copy>)` | `handle_dialog_open()` | `(200,{html,dir,name})`; `get_open_path()`==that path |
| U-R1S-2 | `set_dialog_launcher(lambda k: None)` | `handle_dialog_open()` | `(200,{"cancelled":True})` |
| U-R1S-3 | launcher returns a save path; html given | `handle_dialog_save_as({"html":"<x/>"})` | file written; `(200,{"ok":True,"path":...})`; disk bytes == html |
| U-R1S-4 | no open path (`set_open_path(None)`) | `handle_save({"html":"x"})` | `(200,{"no_open_file":True})` |
| U-R1S-5 | both PS script constants inspected | read `api._OPEN_PS`/`api._SAVE_PS` | each contains `ShowDialog($owner)` AND a `TopMost` owner-Form creation; AND NEITHER contains `ShowHelp` (the removed hack) |

> U-R1S-5 is a STATIC contract lock on the V3-S1 fix shape (owner Form present, ShowHelp removed) without spawning PowerShell. It is a string assertion on the script constants.

Maps to: **R1**.

### Layer-1 note
The only stdlib-testable units remain the Python server (R1 seam) and the R1 OS z-order ctypes test. ALL runtime-module behavior (R2/R3/R6/R7/R8/R9) is verified in Layer 2 against a real DOM (the runtime is browser-only ES modules; adding a JS unit runner would breach the dependency fence A9/A10/U9). This is the same deliberate boundary as v2 — not a coverage gap.

---

## Layer 2 — Playwright (Python, sync API, headless Chromium)

Every suite: `setUpClass` launches the server (its port, `test_dialog=True`); per-test `H.copy_fixture()`; open via `H.open_via_dialog_ui(page, base, copy)`. Selectors exact. Assertions read live DOM via `H.doc_eval`. Selection/interaction uses REAL input (mandate 2).

**Shared real-input click helper (used by R2/R3/R7/R8 suites):** select an element by computing its on-screen center from the iframe rect + the element rect and issuing a real `page.mouse.click(x,y)` (NOT `dispatchEvent`). This mirrors the `screen_xy_of` helper already in `test_f2_select_guides.py`; if reused across suites it is added to `conftest_helpers.py` as `click_element(page, selector)` (and that file joins the relevant test task's allowlist).

### test_r2_resize_real.py — R2 (port 8792)
Locks the R2 fix with the hittability guard (mandate 5), a resize-geometry outcome (mandate 1), and a twice-drag idempotency (mandate 4).

| ID | Given | When | Then |
|----|-------|------|------|
| E-R2-1 (hittability) | open; REAL-click a `.research-card` to select | compute the SE/E handle center from its `getBoundingClientRect`; `document.elementFromPoint(cx,cy)` in the iframe | the returned element matches `[class*="moveable-"]` (NOT null) — the direct R2 root-cause lock |
| E-R2-2 (resize outcome) | card selected; record `getComputedStyle(card).width/height` BEFORE | real `mouse.move(handle)`→`down()`→ 10×`move(+6,+4)` →`up()` | AFTER width AND height changed by ~+60/+40px (tolerance ≤20px for snapping); both deltas non-zero and same sign as the drag |
| E-R2-3 (twice — idempotency, N≥2) | after E-R2-2 (card already resized once) | a SECOND independent real handle drag on the same card | width/height change AGAIN (not a one-shot); deltas non-zero |
| E-R2-4 (MOVE delta — orchestrator add) | select a body-draggable element; record `style.translate` BEFORE | real body drag with a cumulative delta (+48,+32) → magnitude ~58px (≥40px) | `el.style.translate` AFTER changed by ~the drag delta (Δx≈+48, Δy≈+32; tolerance ±15px for snapping) — proves the body-drag MOVE is LIVE (it produced no translate pre-fix, RV07) |
| E-R2-5 (REORDER — orchestrator add) | open; find a parent with ≥2 `[data-hyp-id]` siblings; record the first sibling's DOM child-index | REAL-click the first sibling, then real-drag it onto the second sibling's center (overlap) and drop | the first sibling's DOM child-index CHANGED (the v2 F3 reorder-on-overlap, now exercised under REAL pointer input) |
| E-R2-6 (no console errors) | select + drag | `list_console_messages` | zero editor-origin errors (deck `assets/*` 404s allowed) |

> **Orchestrator-mandated R2 coverage extension:** E-R2-4 (MOVE translate-delta) and E-R2-5 (REORDER DOM-index change) are added beyond the reviewer's required fixes. Both are fail-loud, measured outcomes under REAL input (no `dispatchEvent`, no skip). E-R2-4 measures the `translate` delta magnitude (not mere non-emptiness); E-R2-5 measures the DOM child-index change of the dragged sibling. The note for the `_scroll_into_view` helper: it uses `page.wait_for_function` (event-driven viewport check), never a fixed `wait_for_timeout` after `scrollIntoView` (RV14).

Maps to: **R2** (resize hittability + geometry, MOVE delta, REORDER index — all real input).

### test_r3_delete.py — R3 (port 8793)
Delete/undo outcomes (mandate 1), thread fate, both guards, no-keyboard-path.

| ID | Given | When | Then |
|----|-------|------|------|
| E-R3-1 (delete outcome) | open; REAL-click a non-last body-level element with a known `data-hyp-id`; record body child count | click `#delete-btn` | `doc.querySelector('[data-hyp-id="<id>"]')` is null; body `[data-hyp-id]`-child count decreased by exactly 1 |
| E-R3-2 (undo) | after E-R3-1 | click Undo | the element exists again with the SAME `data-hyp-id`; its previous/next siblings match the pre-delete neighbors |
| E-R3-3 (thread fate) | add a comment to an element (composer), then select+delete that element | read `comments-read` | the thread is present with `unanchored:true` (not lost); thread count unchanged vs pre-delete |
| E-R3-4 (thread re-anchor on undo — RV10) | after E-R3-3 | Undo (re-inserts element) | `#comment-unanchored .comment-thread` count == 0 (the thread is re-anchored, NOT merely still-present); `#comment-threads .comment-thread` count ≥ 1; total thread count unchanged (never lost) |
| E-R3-5 (last-region block — RV01) | `doc_eval` DOM surgery on the TEMP fixture copy reduces the body to exactly ONE body-level `[data-hyp-id]` region (remove all siblings but the first; the survivor keeps its boot registry entry); fail-loud preconditions (≥2 before, ==1 after); select the survivor | click `#delete-btn` | the survivor STILL exists; `#shell-status` text contains "Cannot delete the last remaining region" (the runtime returns `{blocked:"last-region"}` and the shell surfaces the status) |
| E-R3-6 (edit guard) | double-click an element to enter text-edit (contenteditable active); click `#delete-btn` | — | the element STILL exists (`{blocked:"editing"}`); no deletion mid-edit |
| E-R3-7 (no keyboard path) | select an element (NOT editing) | press `Delete`, then `Backspace` (real `page.keyboard.press`) | the element STILL exists (no keydown handler — U14); DOM unchanged |
| E-R3-8 (Moveable teardown) | select an element; click `#delete-btn` | — | after delete, `#hyp-interaction-wrapper` is absent (selection cleared → unmount) |
| E-R3-9 (no console errors) | delete + undo | `list_console_messages` | zero editor-origin errors |

> E-R3-5 setup (RV01 — no longer omitted): the fixture body has multiple `section.slide` regions, so the test performs `doc_eval` DOM surgery on the in-iframe document of the TEMP copy — it removes every body-level `[data-hyp-id]` sibling except the first, leaving exactly one. The survivor keeps its boot-time registry entry (only siblings are removed), so selection + `byId` still resolve it. Fail-loud preconditions assert ≥2 regions before and exactly 1 after the surgery. The assertion is on the BLOCK behavior (survivor persists + status message), against the real runtime. The original gitignored fixture file is never mutated — the surgery is on the live iframe DOM of the temp copy only.

Maps to: **R3**.

### test_r4_color_btn_removed.py — R4 (port 8794)

| ID | Given | When | Then |
|----|-------|------|------|
| E-R4-1 (button gone) | app loaded | `document.getElementById("color-btn")` (parent doc) | null |
| E-R4-2 (no empty group) | app loaded | count `.shell-toolbar .toolbar-group` | equals the expected post-removal count (the group that held only `#color-btn` is gone — assert the specific group is absent by checking no `.toolbar-group` contains zero buttons, and no group contains the 🎨 glyph) |
| E-R4-3 (color UI intact) | open a doc; select an element | inspect the color popover | Palette Tokens list + Selected-Element rows render; changing a token color still dispatches `apply-color` (token still recolors) |

Maps to: **R4**.

### test_r5_token_tooltip.py — R5 (port 8795)

| ID | Given | When | Then |
|----|-------|------|------|
| E-R5-1 (tooltip present) | open a doc (tokens render) | query `.hyp-color-popover-container .hyp-token-info` | exactly one such element; its `title` EQUALS "Changing a palette token recolors every element using that color across the whole document." |
| E-R5-2 (placement) | tokens rendered | check the ⓘ ancestor | it is inside the header whose text contains "Palette Tokens" |
| E-R5-3 (single, not per-row) | tokens rendered (N rows) | count `.hyp-token-info` | exactly 1 (header-level, not per row) |

Maps to: **R5**.

### test_r6_copy_hex.py — R6 (port 8796)
Clipboard readback requires granting clipboard permission to the Playwright context (`context.grant_permissions(["clipboard-read","clipboard-write"])`).

| ID | Given | When | Then |
|----|-------|------|------|
| E-R6-1 (button per row) | open a doc with palette tokens; clipboard permission granted | query `.hyp-token-row` | each row has exactly one `.hyp-token-copy` whose `data-hex` matches `^#[0-9a-f]{6}$` |
| E-R6-2 (copy writes hex) | a token row's copy button | real `.click()` then `navigator.clipboard.readText()` | the readback EQUALS that button's `data-hex` |
| E-R6-3 (normalization) | a token whose `:root` value is a NAMED color or `rgb(...)` (inject one if the fixture lacks it: set `documentElement.style.setProperty('--probe','red')` then re-read palette) | click its copy button; readback | the copied value is the normalized `#rrggbb` (e.g. `#ff0000` for `red`), NOT the raw string |
| E-R6-4 (transient affordance) | a copy button | click; immediately inspect | `title` is "Copied!" or the button has class `hyp-token-copied`; after ~1300ms it reverts |

Maps to: **R6**.

### test_r7_alignment.py — R7 (port 8797)
Display-branched outcomes + capability payload + disabled-state. Uses injected controlled elements (a block, a flex-row, a flex-column, a grid, a table-cell, a fixed-height block) via `page.evaluate` after `tag()` so the matrix is deterministic against the real runtime; REAL-click to select each; align via the toolbar buttons.

| ID | Given | When | Then |
|----|-------|------|------|
| E-R7-1 (H on block) | inject + select a plain block text element | click `#align-center` | `getComputedStyle(el).textAlign === "center"`; one `align` history entry |
| E-R7-2 (H undo) | after E-R7-1 | Undo | `text-align` restored to its prior value |
| E-R7-3 (V on flex-row) | inject + select a `display:flex;flex-direction:row` container | click `#align-middle` | `getComputedStyle(el).alignItems === "center"` (NOT `text-align`) |
| E-R7-4 (H on flex-row) | same flex-row | click `#align-right` | `getComputedStyle(el).justifyContent === "flex-end"` |
| E-R7-5 (flex-column mapping) | inject + select `display:flex;flex-direction:column` | `#align-right` then `#align-bottom` | horizontal→`alignItems:flex-end`; vertical→`justifyContent:flex-end` |
| E-R7-6 (grid) | inject + select `display:grid` | `#align-center` then `#align-middle` | `justifyItems:center`; `alignItems:center` |
| E-R7-7 (table-cell V) | inject + select a `display:table-cell` element | `#align-bottom` | `getComputedStyle(el).verticalAlign === "bottom"` |
| E-R7-8 (plain block V disabled) | select a plain auto-height block | inspect `#align-top/#align-middle/#align-bottom` | all three `button.disabled === true` with the hint `title`; the 3 horizontal buttons enabled |
| E-R7-9 (fixed-height block V) | inject + select a block with inline `height:200px` | `#align-middle` | `getComputedStyle(el).display === "flex"` and `justifyContent === "center"`; Undo restores `display` to its pre-press value |
| E-R7-10 (caps payload) | select the flex-row vs the plain block | read the `selection-changed` payload (via a captured event or a `get-selection` that includes `alignCaps`) | flex-row → `alignCaps.vertical===true`; plain block → `alignCaps.vertical===false`; both `horizontal===true` |
| E-R7-11 (no console errors) | run the matrix | `list_console_messages` | zero editor-origin errors |

Maps to: **R7**.

### test_r8_font_size_repeat.py — R8 (port 8798)
The load-bearing repeat test (mandates 1 + 4). Real dblclick to edit + real word selection + real toolbar clicks. Rationale (RV04 / SNAPSHOT-ALWAYS-WINS): presses 2 and 3 are exactly the regression the v2 suite missed. They pass ONLY because the runtime restores the mousedown snapshot range unconditionally when it is valid — NOT because it detects a collapsed live selection (Chromium collapses to the first text node after `focus()`, so any `commonAncestorContainer === el` detection would never fire and presses 2+ would each wrap a fresh empty span). The "ONE span / zero empty siblings" outcome is therefore the direct behavioral proof that the snapshot-restore path (not a brittle collapse check) is what runs on every press.

| ID | Given | When | Then |
|----|-------|------|------|
| E-R8-1 (3 presses → ONE span, +6px, zero empties) | open; real `mouse.dblclick()` on a `.slide-title` word (selects the word) | click `#fmt-font-inc` THREE times WITHOUT re-selecting (real `.click()`) | the edited element contains EXACTLY ONE span with inline `font-size`; that span's `font-size` is base+6px; ZERO empty sibling spans (`<span style="font-size:…"></span>` with empty textContent) |
| E-R8-2 (decrease symmetry) | word selected (fresh element) | `#fmt-font-dec` three times | the single span's `font-size` is base−6px (floored at 8px); one span, zero empties |
| E-R8-3 (mix grows monotonically) | word selected | A+ , A+ , A− (three presses) | one span; `font-size` = base+2px; no empty siblings |
| E-R8-4 (lifecycle clear) | edit element X (press A+ once), click away to commit; then dblclick element Y and press A+ once | — | Y gets its OWN single span (no carry-over of X's tracked span); X retains its span unchanged |
| E-R8-5 (no console errors) | the press sequence | `list_console_messages` | zero editor-origin errors |

> The "ONE span / zero empty siblings" assertion is the precise R8 acceptance from the spec. The base is read once before the first press; the delta is asserted exactly.

Maps to: **R8**.

### test_r9_outline_removed.py — R9 (port 8799)

| ID | Given | When | Then |
|----|-------|------|------|
| E-R9-1 (panel gone) | app loaded | `document.getElementById("outline-list")` + `document.querySelector(".outline-panel")` (parent doc) | both null |
| E-R9-2 (ready payload) | open a doc; capture the `ready` event payload (via a bridge event hook or a probe) | inspect payload | has `tokens`, has NO `sections` key |
| E-R9-3 (panels survive) | open document A (add a comment so the comment panel has a card); open document B (second copy) | after B loads | `#comment-threads` + the `.hyp-color-popover-container` STILL exist (G1 invariant holds without the outline) |
| E-R9-4 (no console errors) | open + select an element | `list_console_messages` | zero editor-origin errors (the removed `setActiveOutline` wiring cannot throw) |

Maps to: **R9**.

### test_f2_select_guides.py — F2 (port 8782, REWRITTEN — mandates 2 + 3)
The CHANGED v2 suite. All synthetic `dispatchEvent` selections replaced with REAL `page.mouse.click()` at the element's on-screen center; the `skipTest` calls converted to hard assertions; geometry-delta assertions ADDED.

| ID | Change from v2 |
|----|----------------|
| E-F2-1/2/3/6/7/8 | Selection via REAL `frame.locator(...).click()` (already real in most) — verify NONE use `dispatchEvent`. E-F2-7's `doc.body.dispatchEvent(... 'click' ...)` for the empty-click path is replaced with a real `page.mouse.click()` on a DYNAMICALLY DISCOVERED empty point: a `doc_eval` probe sweeps candidate iframe points (right/bottom margins, corners, a coarse grid) and accepts the first whose `elementFromPoint` has no `[data-hyp-id]` ancestor (html/body/null); the test FAILs (never skips) if no empty point exists (RV05). A hard-coded (3,3) offset is forbidden — the deck's top-left is content. |
| E-F2-4 (drag guides + OUTCOME) | Select the card with a REAL `page.mouse.click()` at its center (NOT `dispatchEvent`). Drag it; assert a `.moveable-line` appears AND assert the card's `style.translate` changed (geometry outcome). REMOVE the `skipTest` — no guideline / no translate change = FAIL (it is the R2 bug). |
| E-F2-5 (resize guides + OUTCOME) | Select via real click; find the E/SE handle; assert it is found (no `skipTest` — a missing handle is a FAIL); drag it; assert a `.moveable-line` appears AND `getComputedStyle(card).width` changed. REMOVE both `skipTest` calls. |

Maps to: **F2** (and re-locks R2 at the guide-render + geometry level).

### test_exit_smoke.py — EXIT (port 8788, CHANGED)

| ID | Change from v2 |
|----|----------------|
| E-EXIT-1 | UNCHANGED (`/app/` + runtime served, 200). |
| E-EXIT-2 | Add to the "one of each" op sequence a REAL resize (drag a handle, assert size delta — R2), a REAL delete of an element then undo (R3), and a REAL 3-press font-size on a word (assert one span +6px — R8). Save As → reopen → renders without collapse; zero editor console errors throughout. ALL coordinate math uses `iframe_origin + doc_eval getBoundingClientRect` — NO `frame_locator.bounding_box()` (RV09). |
| E-EXIT-3 | Additionally assert: `#outline-list` absent (R9); `#color-btn` absent (R4); plus the existing chrome-free gate. |

Maps to: **EXIT**.

---

## 3. Manual smoke (NOT in the automated suite)

The R1 z-order ctypes test (test_r1_dialog_zorder) AUTOMATES the OS-boundary check that was manual-only in v2. The remaining manual smokes are belt-and-suspenders:

| ID | Steps | Expected |
|----|-------|----------|
| M-DLG-1 | `python server/server.py`; open `http://127.0.0.1:8765/app/`; click Open… | a REAL native dialog appears ON TOP of Chrome (R1) |
| M-DLG-2 | Edit; Save As… | a REAL save dialog appears on top; confirming writes the file |
| M-R6-1 | Click a token copy-HEX button; paste elsewhere | the clipboard holds the normalized `#rrggbb` |

Run once per release on Windows 11 + Chrome.

---

## 4. Scorecard → suite traceability

| Scorecard ID | Unit suites | Playwright suites |
|--------------|-------------|-------------------|
| R1 | test_r1_dialog_zorder (ctypes, real dialog), test_r1_dialog_seam | — |
| R2 | — | test_r2_resize_real, test_f2_select_guides (re-locks guides+geometry) |
| R3 | — | test_r3_delete |
| R4 | — | test_r4_color_btn_removed |
| R5 | — | test_r5_token_tooltip |
| R6 | — | test_r6_copy_hex |
| R7 | — | test_r7_alignment |
| R8 | — | test_r8_font_size_repeat |
| R9 | — | test_r9_outline_removed |
| EXIT | (all unit pass) | test_exit_smoke |

Every interaction assertion is a measured outcome (mandate 1); all selection/interaction in new/changed suites is real input (mandate 2); no behavioral test reports green on a skip (mandate 3 — the only permitted skip is the R1 ctypes headless-CI condition, which does NOT trigger on this machine); font-size and resize have N≥2 repeat coverage (mandate 4); R2 has the elementFromPoint hittability guard (mandate 5); R1 has the real-dialog ctypes OS-boundary test (mandate 6).
