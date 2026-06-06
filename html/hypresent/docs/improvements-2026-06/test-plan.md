# Hypresent v2 — Test Plan

Two-layer automated test design for features F1–F5 + blockers G1–G2. Layer 1 = Python stdlib `unittest` (server endpoints, serializer round-trips, pure reorder logic). Layer 2 = Playwright (Python, sync API, headless Chromium) behavioral suites. Tests are scenario DESIGNS — Kimi writes the code from them. Every suite maps to a scorecard ID (F1…G2, EXIT).

Grounding: `docs/spec/05-verification-plan.md` (V-* harness conventions), `spec.md` (this cycle's S-decisions), source interfaces quoted in the per-task files.

---

## 0. Tooling, deps, runner (Kimi runs these exactly)

**Zero extra deps beyond Playwright. pytest is OUT — stdlib `unittest` discovery only.**

```
pip install playwright
playwright install chromium
```

Run ALL tests (unit + Playwright) via stdlib unittest discovery from the `hypresent/` root:
```
python -m unittest discover -s tests -p "test_*.py" -v
```
Unit-only (fast, no browser): `python -m unittest discover -s tests/unit -p "test_*.py" -v`
Playwright-only: `python -m unittest discover -s tests/e2e -p "test_*.py" -v`

**e2e import mechanism (mandatory, R08).** `conftest_helpers.py` lives in `tests/e2e/`. When discovery runs from `-s tests`, Python adds `tests/` to `sys.path` but NOT `tests/e2e/`, so a bare `import conftest_helpers` fails with `ModuleNotFoundError`. The ONE chosen mechanism, applied identically in EVERY e2e test file (`test_f1_dialogs.py` through `test_exit_smoke.py`), is a 3-line `sys.path` bootstrap placed ABOVE the `import conftest_helpers` line:
```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conftest_helpers as H
```
This makes each e2e file importable under all three run commands above (`-s tests`, `-s tests/e2e`, and direct `python -m unittest tests.e2e.test_*`). The bootstrap is added by the task that CREATES each e2e file (V2-T13..T19), not deferred to V2-T20. `conftest_helpers.py` itself is a plain module (not a `test_*.py` file), so it needs no bootstrap.

Directory layout (NEW, created by test tasks):
```
hypresent/
  tests/
    __init__.py
    unit/
      __init__.py
      test_server_dialogs.py        # F1
      test_server_save.py           # F1 (Save / open-path tracking)
      test_serializer_roundtrip.py  # F5/G2 (island, agent block, escaping, guard, translate survival)
      test_serializer_border.py     # F4 (border styles survive serialize)
      test_reorder_logic.py         # F3 (pure classifyDrop/isContainer/dominantAxis)
    e2e/
      __init__.py
      conftest_helpers.py           # shared: server launch, fixture copy, iframe accessors
      test_f1_dialogs.py            # F1
      test_f2_select_guides.py      # F2
      test_f3_reorder_reparent.py   # F3
      test_f4_border.py             # F4
      test_f5_comments.py           # F5
      test_g1_panel_survival.py     # G1
      test_g2_save_with_comments.py # G2
      test_exit_smoke.py            # EXIT
    fixtures/
      (copies made per-test into tempdir; the ORIGINAL tecer-gsmm-introduction.html is NEVER mutated)
```

**Fixture strategy (mandatory):** every test that opens a document copies `hypresent/tecer-gsmm-introduction.html` into a fresh `tempfile.mkdtemp()` directory per test (`shutil.copy`), and operates on the COPY. The original at the repo root is read-only and NEVER mutated (U10a: it is gitignored; tests copy it, never stage/commit/mutate it). It is the canonical fixture per the EXIT condition. Asset folder absence is acceptable (the fixture's `assets/*` images 404; that is the fixture's own gap, per README Known Limitations).

**Fixture-absent failure mode (mandatory, R07 — fail loud, never skip-green).** The sample is present locally but is gitignored, so a fresh clone or CI checkout may lack it. A missing fixture is a PORTABILITY ERROR, not a reason to skip. Every suite (unit and e2e) guards the fixture path ONCE in `setUpClass` and FAILS LOUDLY with a message naming the required path — it MUST NOT `skipTest`:
```python
@classmethod
def setUpClass(cls):
    if not os.path.exists(FIXTURE):
        raise AssertionError(
            f"Required fixture missing: {FIXTURE} (gitignored per U10a; restore it locally before running tests)"
        )
    # ... rest of setUpClass ...
```
(`FIXTURE` is the absolute path to `hypresent/tecer-gsmm-introduction.html`.) Raising `AssertionError` from `setUpClass` reports the class as an ERROR with the path in the message — never a silent green. Do NOT use `unittest.SkipTest` for the fixture.

**Server lifecycle (Playwright suites):** one server `subprocess.Popen([sys.executable, "server/server.py", "127.0.0.1", str(PORT)])` per TestCase class (`setUpClass`/`tearDownClass`), each on a DISTINCT port to allow parallel class runs. Port allocation: base `8780` + a per-suite offset (table below); `setUpClass` polls `GET http://127.0.0.1:PORT/app/` until 200 (≤5s) before tests run; `tearDownClass` terminates the process.

| Suite | Port |
|-------|------|
| test_f1_dialogs | 8781 |
| test_f2_select_guides | 8782 |
| test_f3_reorder_reparent | 8783 |
| test_f4_border | 8784 |
| test_f5_comments | 8785 |
| test_g1_panel_survival | 8786 |
| test_g2_save_with_comments | 8787 |
| test_exit_smoke | 8788 |

**Iframe access pattern (Playwright):** the document loads in `iframe.doc-frame`. Tests reach it via `page.frame_locator("iframe.doc-frame")` for interactions and `page.evaluate` with `document.querySelector('iframe.doc-frame').contentWindow`/`.contentDocument` for assertions (same-origin). Wait for runtime ready via `page.wait_for_function` polling `contentWindow.hyp` presence or a `ready`-driven DOM signal.

**F1 dialogs in headless runs (the seam):** the native PowerShell dialog CANNOT run headless. Playwright F1 tests start the server with an environment flag the server reads to install a FAKE dialog launcher at boot, OR (preferred, no server code branch) the test process imports `server.api` is NOT possible across the subprocess boundary — therefore the server exposes a TEST-ONLY endpoint `POST /api/_test/set-dialog` (guarded: only routed when env `HYP_TEST_DIALOG=1` is set) that calls `api.set_dialog_launcher` to return a fixed path (or None for cancel). The Playwright suite launches the server with `HYP_TEST_DIALOG=1`, POSTs the desired fake path before clicking Open/Save As, then drives the UI. The unit layer (test_server_dialogs) tests `api.set_dialog_launcher` directly in-process (no endpoint, no env flag). A real-dialog manual smoke is listed in §3 but is NOT in the automated suite.

---

## Layer 1 — stdlib `unittest`

### test_server_dialogs.py — F1 (in-process, dialog seam)
Imports `server.api` directly; uses `api.set_dialog_launcher` to inject. No HTTP, no subprocess.

| # | Given | When | Then |
|---|-------|------|------|
| U-DLG-1 | `set_dialog_launcher(lambda kind: r"<tmp>/copy.html")` and a temp copy exists | `handle_dialog_open()` | returns `(200, {...})` with `html`, `dir`, `name` of the temp file; `api.get_open_path()` == that path |
| U-DLG-2 | `set_dialog_launcher(lambda kind: None)` | `handle_dialog_open()` | returns `(200, {"cancelled": True})`; `get_open_path()` unchanged |
| U-DLG-3 | launcher returns a temp save path; html string given | `handle_dialog_save_as({"html": "<html>x</html>"})` | file written at the path; `(200,{"ok":True,"path":...})`; bytes on disk == html |
| U-DLG-4 | launcher returns None | `handle_dialog_save_as({"html":"x"})` | `(200,{"cancelled":True})`; no file written |
| U-DLG-5 | `set_open_path(<tmp>/copy.html)` first | `handle_save({"html":"<new/>"})` | overwrites that file silently; `(200,{"ok":True})`; disk == new html |
| U-DLG-6 | no open path set (`set_open_path(None)`) | `handle_save({"html":"x"})` | `(200,{"no_open_file":True})`; nothing written |
| U-DLG-7 | filter constant inspected | read `api`'s open/save PowerShell script constants | both contain `*.html;*.htm` |
| U-DLG-8 | `handle_dialog_open` reuses `handle_open` | open a real temp copy via launcher | response `html` equals `Path(copy).read_text()` (proves no duplicated read logic) |
| U-DLG-9 | launcher arg contract inspected (R02) | call `api._ps_args("pwsh", "X")` | returns a list containing `"-STA"`, `"-NoProfile"`, `"-NonInteractive"`, and ending `["-Command", "X"]`; confirms the exact flag list shared with the spec |

Maps to: **F1**. (U-DLG-9 locks the R02 subprocess argument contract without spawning PowerShell.)

### test_server_save.py — F1 (HTTP-level open-path tracking)
Launches the server subprocess on port 8789; uses `urllib.request` for POSTs. Does NOT exercise native dialogs (those need the seam); exercises `/api/open` → `/api/save` round-trip.

| # | Given | When | Then |
|---|-------|------|------|
| U-SAVE-1 | server up; temp copy on disk | `POST /api/open {path:copy}` then `POST /api/save {html:"<edited/>"}` | save returns `{ok:true,path:copy}`; disk file == edited html |
| U-SAVE-2 | a FRESHLY-STARTED server subprocess on its own port that has NEVER received `/api/open` | `POST /api/save {html:"x"}` | returns `(200, {no_open_file:true})`; no file written |
| U-SAVE-3 | open file A, then open file B (two temp copies) | `POST /api/save {html:"<b/>"}` | writes to B (the most recently opened), not A |

**U-SAVE-2 is exercised at the HTTP level (R15 — no skip).** Server open-path state is process-global, so a "no file open" assertion is order-dependent on a shared server. To make it deterministic AND genuinely HTTP-level (validating the `/api/save` → `no_open_file` route, not just the in-process function), U-SAVE-2 launches its OWN server subprocess on a distinct port (e.g. 8790) in its own `setUp`/`tearDown`, issues exactly one `POST /api/save` against it (no prior `/api/open`), asserts `(200, {"no_open_file": true})`, and tears the subprocess down. This requires no new server code. The in-process U-DLG-6 remains as the fast deterministic mirror; U-SAVE-2 is the HTTP-route lock and is NOT skipped.

Maps to: **F1**.

### test_serializer_roundtrip.py — F5 / G2
The serializer runs in-browser, so "unit" here means a Node-free DOM harness is NOT available; instead this suite is a **JSDOM-free pure-logic extraction**: the agent-block generator (`buildAgentBlock`) and the escaping helper are pure string functions. Kimi extracts `buildAgentBlock` and `escapeBlock` so they are importable WITHOUT a DOM (they take a `threadStore` array argument in the extracted form, defaulting to the module store in the browser form). The test drives them via a tiny Node invocation captured by Python `subprocess` running `node -e`? — NO, Node is not a dependency. **Resolution:** these string-logic assertions move to the Playwright layer (test_f5_comments) where a real DOM exists; this unit file instead asserts the SERIALIZER GUARD MATH as a pure Python re-implementation contract check is not possible either. Therefore test_serializer_roundtrip.py is REMOVED as a unit file; its scenarios are covered in Playwright test_g2 + test_f5 (which have a real DOM). This is stated explicitly so Kimi does not create an empty/fake unit file.

> Rationale (fail-loud): the serializer and comment generator are browser-DOM modules; there is no stdlib-only way to exercise them without a DOM. Forcing them into `unittest` would require vendoring a DOM (violates A9/A10 dev-dep limit beyond Playwright). Their round-trips are fully covered by Playwright (real DOM). The ONLY pure, DOM-free serializer logic is the guard ARITHMETIC, which is validated behaviorally in test_g2.

Maps to: (covered in Playwright) **F5, G2**.

### test_serializer_border.py — F4
Same DOM constraint as above → border-style survival is verified in Playwright test_f4 (real DOM serialize + reopen). This unit file is NOT created. Stated to prevent a hollow file.

Maps to: (covered in Playwright) **F4**.

### test_reorder_logic.py — F3 (the ONE genuinely extractable pure-logic unit suite)
`reorder.js` exports `classifyDrop`, `isContainer`, `dominantAxis` as pure DOM-reading functions. These DO need a DOM (they read `getBoundingClientRect`, `getComputedStyle`, `closest`). Therefore they too require a browser. **Resolution:** the truly DOM-free kernel is the midpoint decision and the axis-from-display-string mapping. Kimi extracts a pure helper `midpointBefore(axis, rect, x, y)→bool` and `axisFromDisplay(display, flexDirection)→'x'|'y'` with NO DOM access (plain math/string). This unit file tests THOSE two kernels via Playwright? No — they are pure JS. **Final resolution:** run these two pure JS kernels through Playwright's `page.evaluate` in test_f3 (a browser is already up there). The stdlib `unittest` layer therefore has exactly ONE real unit suite: the SERVER (test_server_dialogs + test_server_save), which is genuinely stdlib-testable.

> Honest scope statement (fail-loud, no fake green): the runtime is browser-only ES modules with no Node build; the only code unit-testable under pure stdlib `unittest` is the Python server. ALL runtime-module logic (serializer math, reorder classification, border auto-1px, agent-block strings) is verified in the Playwright layer against a real DOM. This is a deliberate, correct boundary — not a coverage gap — because adding a JS unit runner would breach the "zero extra deps beyond Playwright / app stays dependency-free" constraint (A9/A10, U9).

Maps to: (server only) **F1**.

### Layer-1 summary
The stdlib `unittest` layer covers the SERVER (F1) end-to-end and in-process. All browser-runtime logic is covered by Layer 2. No hollow unit files are created.

---

## Layer 2 — Playwright (Python, sync API, headless Chromium)

Every suite: `setUpClass` launches the server subprocess on its port; per-test copies the fixture to a tempdir; opens via the appropriate path. Selectors are exact. Assertions read live DOM.

### test_f1_dialogs.py — F1
Uses the `HYP_TEST_DIALOG=1` seam + `POST /api/_test/set-dialog`.

| ID | Given | When | Then |
|----|-------|------|------|
| E-F1-1 | server up with `HYP_TEST_DIALOG=1`; fake set to a temp copy path | click `#open-btn` | `iframe.doc-frame` src becomes `/doc/<name>`; runtime `ready` (poll `contentWindow.hyp`); toolbar enabled |
| E-F1-2 | fake set to None (cancel) | click `#open-btn` | iframe src unchanged; no console error; status empty |
| E-F1-3 | doc open; fake save path = temp `out.html`; an edit made (double-click a `.slide-title`, type) | click `#save-as-btn` | `out.html` exists on disk; its bytes parse as HTML; contains the edited text |
| E-F1-4 | doc open from path P (via fake); edit made | click `#save-btn` (NEW) | P on disk overwritten silently (no second dialog POST observed); bytes contain the edit |
| E-F1-5 | fresh server, no doc open; fake save path set | click `#save-btn` | falls back to Save As dialog flow → writes to the fake path |
| E-F1-6 | toolbar inspected after load | `page.query_selector` for `#open-path-input`, `#save-as-path-input` | both are NULL (inputs removed, S25); `#open-btn`, `#save-btn`, `#save-as-btn` present |

Maps to: **F1**. (Real-dialog smoke: §3, manual only.)

### test_f2_select_guides.py — F2
| ID | Given | When | Then |
|----|-------|------|------|
| E-F2-1 | doc open | click a `.slide-title` in the iframe | `#hyp-interaction-wrapper` exists in iframe doc; Moveable control box (`.moveable-control-box`) present; a `.hyp-selection-ring` present |
| E-F2-2 | element selected | inspect the Moveable instance via `page.evaluate` reading `contentWindow` interaction state | both draggable and resizable handles rendered (control box has resize handles `.moveable-direction` AND the area is draggable) |
| E-F2-3 | element A selected, then click element B | — | the single Moveable's target switched to B (no second wrapper created; exactly one `#hyp-interaction-wrapper`); guidelines reassigned (no error) |
| E-F2-4 | a slide with ≥2 sibling cards; select one card | drag it slowly until its left edge aligns with a sibling's left edge (use `page.mouse` move sequence over the iframe) | during drag a `.moveable-line` (dashed/bold guideline) appears; assert `.moveable-line` count ≥1 mid-drag |
| E-F2-5 | same card selected | drag a RESIZE handle until an edge aligns with a sibling | a `.moveable-line` appears during resize too (guides on BOTH drag and resize) |
| E-F2-6 | element selected | double-click it | handles suspend (control box hidden or draggable=false); `contenteditable="true"` on the element; on blur, handles resume |
| E-F2-7 | element selected | press `Escape` (no active edit) OR click empty slide background | selection cleared; `#hyp-interaction-wrapper` removed; no `.hyp-selection-ring` |
| E-F2-8 | after any select | `list_console_messages` | zero editor-origin uncaught exceptions |

Maps to: **F2**.

### test_f3_reorder_reparent.py — F3
Includes the verbatim 3-box example AND the pure-kernel checks via `page.evaluate`.

**3-box example (verbatim):** the test injects, into the open document's body via `page.evaluate`, a controlled flex-row container `<div id="t3box" style="display:flex;gap:10px"><div class="bx">A</div><div class="bx">B</div><div class="bx">C</div></div>`, then triggers `tag()` re-run (or selects to force tagging). Boxes A,B,C get `data-hyp-id`. (Using an injected deterministic container avoids depending on the fixture's exact layout for the reorder math, while still running against the real runtime in the real document.)

| ID | Given | When | Then |
|----|-------|------|------|
| E-F3-1 (3-box) | flex-row A,B,C; select A | drag A so the pointer is past the midpoint of C (to C's right half) and drop | DOM order becomes B,C,A; A's `style.translate` is `''` (cleared); exactly one `"reorder"` history entry |
| E-F3-2 (3-box) | order B,C,A from E-F3-1 | Ctrl+Z | order returns to A,B,C; A's translate restored to pre-drop (`''`) |
| E-F3-3 (3-box) | select B | drag B left past A's midpoint, drop | order becomes B,A,C (insertBefore A) |
| E-F3-4 (reparent) | two flex containers `#L` (children A,B) and `#R` (children X,Y) injected; select A | drag A over X's right half in `#R`, drop | A is now a child of `#R` positioned after X; A removed from `#L`; translate cleared; one `"reparent"` entry; `A.dataset.hypId` unchanged (stable id) |
| E-F3-5 (reparent undo) | post E-F3-4 | Ctrl+Z | A back in `#L` at original index; `#R` unchanged |
| E-F3-6 (empty space) | select A in `#L` | drag A into empty padding area of a non-container leaf / blank region and drop where `elementsFromPoint` finds no `[data-hyp-id]` sibling/container | A keeps its `style.translate` (non-empty); `out-of-flow` badge logic fired; one `"move"` entry (not reorder/reparent) |
| E-F3-7 (leaf guard) | a `<p data-hyp-id>` leaf inside `#R`; select A | drag A directly over that `<p>`'s text and drop | A re-parents into the `<p>`'s PARENT (`#R`), never INTO the `<p>` (assert `A.parentElement !== thatP`) |
| E-F3-8 (translate property) | select A; small drag, drop in empty space | assert `A.getAttribute('style')` contains `translate:` and does NOT contain `transform: translate` (S1 migration) |
| E-F3-9 (transform preserved) | give A inline `transform:rotate(10deg)` first; drag A, drop empty | after drop, `A.style.transform` still contains `rotate(10deg)` (translate did not clobber it) |
| E-F3-10 (anchor rewrite) | add a comment to A; then reorder A | after move, the comment marker re-renders at A's new position; the thread's stored `anchor.path` reflects A's new DOM path (read island JSON, compare) |
| E-F3-11 (pure kernels) | — | `page.evaluate` calling `reorder` kernel `midpointBefore('x', {left:0,right:100,...}, 40, y)` → true; `(…,60,…)`→false; `dominantAxis` on a `display:flex;flex-direction:row` div → 'x'; on `display:grid` → 'y' |
| E-F3-12 (zero-distance no-op, R05) | select a real registered sibling element | a single CLICK (`page.mouse.down` then `page.mouse.up` at the SAME point, no move) on the selected element | DOM sibling order is UNCHANGED; the element's `style.translate` is unchanged (no spurious translate write); zero `"reorder"`/`"reparent"`/`"move"` history entries added by the click |

Maps to: **F3**. (E-F3-12 locks the R05 zero-distance guard — a click must never reorder.)

### test_f4_border.py — F4
| ID | Given | When | Then |
|----|-------|------|------|
| E-F4-1 | doc open; select an element with NO border; open color popover | the popover shows a third row `<input data-prop="border-color">` (label "Border") | row present after Text and Background |
| E-F4-2 | borderless element selected | set Border to `#ff0000` via the input (set value + dispatch `change`) | element gains inline `border: 1px solid` with red color (auto-1px, U6); `getComputedStyle().borderTopWidth` ≈ 1px, color red |
| E-F4-3 | element with existing `border:3px solid blue` | set Border to `#00ff00` | width stays 3px; color becomes green (only `border-color` written, not width) |
| E-F4-4 | after E-F4-2 | Ctrl+Z | border inline state fully restored to pre-apply (no `border` shorthand, no `border-color`) |
| E-F4-5 (mixed) | element given four different per-side colors via inline style | select it | Border input is empty with placeholder `mixed` (S15) |
| E-F4-6 (mixed apply) | mixed element selected | set Border to `#123456` | all four computed side colors equal `#123456` |
| E-F4-7 (serialize survival) | apply a border color; Save As to temp; reopen the saved file in a plain page | the saved HTML's element carries the inline `border`/`border-color`; renders with the border |

Maps to: **F4**.

### test_f5_comments.py — F5
Covers composer, agent toggle, saved-file head block content, escaping (the string-logic moved here per Layer-1 note).

| ID | Given | When | Then |
|----|-------|------|------|
| E-F5-1 | doc open; select an element; (author preset in localStorage to skip name prompt) | click `#comment-btn` | a `.hyp-comment-composer` popover appears (NOT a `prompt()`); contains a `<textarea>`, a "For agents" checkbox, Save + Cancel buttons |
| E-F5-2 | composer open | type text, press `Escape` | composer closes; no thread added (`comment-threads` empty) |
| E-F5-3 | composer open | type "do X", press `Enter` | a newline is inserted in the textarea (no submit); composer still open |
| E-F5-4 | composer open with text | press `Ctrl+Enter` | thread created; appears in `#comment-threads`; marker in iframe |
| E-F5-5 | composer open; check "For agents"; text "Replace bullets" | `Ctrl+Enter` | thread created with `agentInstruction:true` (read island JSON) |
| E-F5-6 | an existing non-agent thread in panel | click its "For agents" checkbox | island JSON for that thread flips `agentInstruction` to true; toggling again flips back |
| E-F5-7 (head block present) | one agent-tagged unresolved thread exists | Save As to temp; read saved file text | `<head>` first child is the comment block; contains `===== HYPRESENT AGENT INSTRUCTIONS =====`, the preamble line, `[agent:<id>]`, `anchor:` with path+id+quote, `instruction: Replace bullets`, `author:`, `date:` |
| E-F5-8 (head block absent) | no agent-tagged threads (or the only one resolved) | Save As; read saved file | NO `HYPRESENT AGENT INSTRUCTIONS` substring in the file |
| E-F5-9 (escaping) | agent thread body literally contains `a --> b` | Save As; read file | the block contains `a --&gt; b` (no raw `-->` inside the comment) and the comment is well-formed (closes once) |
| E-F5-10 (replies) | agent thread with one unresolved reply "also bold it" | Save As; read file | block has a `reply: also bold it — <author>` continuation line under that entry |
| E-F5-11 (regen) | Save As once (block present); resolve the agent thread; Save As again | second saved file has NO block (regenerated from island, D7) |
| E-F5-12 (round-trip flag) | agent thread; Save As; reopen saved file in editor | the reopened thread still shows `agentInstruction:true` (panel checkbox checked); marker re-anchored |
| E-F5-13 (markers unaffected) | tag a thread for agents | in-editor marker position/visibility unchanged vs pre-tag (U8 condition a) |

Maps to: **F5**.

### test_g1_panel_survival.py — G1
| ID | Given | When | Then |
|----|-------|------|------|
| E-G1-1 | open document A; add a comment (so `#comment-threads` has a card); confirm `#outline-list` populated | open document B (second temp copy) via the dialog seam | after B loads, `#comment-threads`, `#comment-unanchored`, `#outline-list` STILL EXIST in the DOM (not wiped); the color popover container `.hyp-color-popover-container` also present |
| E-G1-2 | document open, color popover mounted | inspect `.shell-panel` children order | `.hyp-color-popover-container` is firstChild; `.outline-panel` and `.comment-panel` follow and are intact (matches spec §G1 DOM structure) |
| E-G1-3 | select an element (color popover re-renders the Selected Element body) | — | `#comment-threads` / `#outline-list` untouched by the popover re-render (still present with prior content) |

Maps to: **G1**.

### test_g2_save_with_comments.py — G2
| ID | Given | When | Then |
|----|-------|------|------|
| E-G2-1 | doc open; add ONE comment (no agent tag) | click `#save-as-btn` → temp file | save SUCCEEDS (status success; file written); the serialize did NOT return null |
| E-G2-2 | saved file from E-G2-1 | read file | exactly one `<script type="application/json" id="hyp-comments">` island; `JSON.parse` of its text == the thread state |
| E-G2-3 | doc open; add a comment AND tag it for agents | Save As → temp | save SUCCEEDS; file has BOTH the island AND the head agent block (guard accounts for the extra node, §G2) |
| E-G2-4 | re-open the E-G2-3 saved file in the editor; Save As again to a new temp | second file has exactly ONE agent block in `<head>` (no duplication — prior block stripped then regenerated) |
| E-G2-5 | doc open; NO comments | Save As | save SUCCEEDS; no island; no block; chrome-free (`data-hyp-`=0, `hyp-` class tokens=0) |

Maps to: **G2**.

### test_exit_smoke.py — EXIT
The clean-run + full-feature smoke on the sample. Mirrors the EXIT scorecard ("clean, error-free server run + automated tests pass on sample HTML").

| ID | Given | When | Then |
|----|-------|------|------|
| E-EXIT-1 | server launched fresh on its port | `GET /app/` and `GET /runtime/js/runtime-main.js` | both 200; runtime served with a JS content-type |
| E-EXIT-2 | open the sample (temp copy); do one of EACH: edit text, resize (drag handle), move (drag body, drop empty), recolor a token, add a comment, tag it agent | Save As → temp | save succeeds; reopen the saved file in a plain page renders without layout collapse; `list_console_messages` shows zero editor-origin uncaught errors throughout (DECK `assets/*` 404s allowed) |
| E-EXIT-3 | the E-EXIT-2 saved file | assert chrome-free gate (05 §4): zero `[id^="hyp-"]`/`hyp-` class tokens/`data-hyp-*` EXCEPT one `#hyp-comments` island; the head agent block is a comment node (allowed); the sample's own inline `onerror` handlers preserved | all hold |

Maps to: **EXIT**.

---

## 3. Manual smoke (NOT in the automated suite)

| ID | Steps | Expected |
|----|-------|----------|
| M-DLG-1 | Run `python server/server.py` (no test flag); open `http://127.0.0.1:8765/app/`; click Open… | a REAL native Windows file-open dialog appears (filter HTML files *.html;*.htm); selecting the sample loads it |
| M-DLG-2 | Edit, click Save As… | a REAL native save dialog appears with default name = current file name, default dir = current dir; confirming writes the file |
| M-DLG-3 | Edit again, click Save | file overwritten silently, no dialog |

These exercise the actual PowerShell `-STA` subprocess that headless CI cannot. Run once per release on Windows 11 + Chrome.

---

## 4. Scorecard → suite traceability

| Scorecard ID | Unit suites | Playwright suites |
|--------------|-------------|-------------------|
| F1 | test_server_dialogs, test_server_save | test_f1_dialogs |
| F2 | — | test_f2_select_guides |
| F3 | — (pure kernels run in-browser via page.evaluate) | test_f3_reorder_reparent |
| F4 | — | test_f4_border |
| F5 | — | test_f5_comments |
| G1 | — | test_g1_panel_survival |
| G2 | — | test_g2_save_with_comments |
| EXIT | (all unit pass) | test_exit_smoke |

Layer-1 deliberately covers only the Python server (the only stdlib-testable unit); all runtime-module behavior is covered in Layer 2 against a real DOM, honoring the dependency fence (A9/A10, U9). No suite reports green on a skipped or hollow assertion (fail-loud).

### Save-with-no-open coverage (R15 — explicit)
The `/api/save` route returning `{no_open_file:true}` when no file is open is exercised at THREE levels: U-DLG-6 (in-process function call, fast deterministic), U-SAVE-2 (HTTP route against a fresh dedicated-port server subprocess — locks the server routing end-to-end), and the client fallback branch in `main.js` `#save-btn` (which, on `no_open_file`, invokes `dialogSaveAs`). The HTTP-level U-SAVE-2 closes the gap the prior plan left by skipping it.
