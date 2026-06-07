You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

D29 EVIDENCE-METRICS BLOCK (binding): every evidence file records measured WALL_MS + EXIT + ran/passed/failed/SKIPPED + SKIPPED_LINES_COUNT + each skip's exact reason string. Implausible WALL_MS (browser e2e <1s) or unexpected skip → BUG section + STOP, never report green.

Edit-anchoring rule: locate code by exact strings, NEVER line numbers.

# PB-T12 — e2e: builder helpers + e2e fixture lib + page/nav suite (+ editor regression)

## Objective
Create the shared builder e2e helpers, a small self-contained e2e fixture library (with the engine vendored into it), and the page+nav suite including the editor-zero-regression case. Playwright via Python unittest, real server subprocess, port 8801.

## FILE ALLOWLIST
- ✚ create `html/hypresent/tests/e2e/builder_helpers.py`
- ✚ create `html/hypresent/tests/e2e/test_pb1_page_nav.py`
- ✚ create `html/hypresent/tests/e2e/fixtures/builder-lib/**` (a small valid library + a sibling `builder-shared/` if you use an `@root` asset; keep it self-contained)
- ✗ do NOT edit `conftest_helpers.py` (reuse it) or any product file.

## The live harness you reuse (facts — import, do not duplicate)
`tests/e2e/conftest_helpers.py` exports:
```
start_server(port, test_dialog=False) -> (proc, base_url)   # spawns server/server.py on 127.0.0.1:port
stop_server(proc)
post_json(base, path, payload) -> (status, data)
set_fake_dialog(base, path_or_none)   # POST /api/_test/set-dialog (needs HYP_TEST_DIALOG=1)
wait_runtime_ready(page, timeout=15000)   # waits for iframe.doc-frame contentWindow.hyp
doc_eval(page, expr)   # eval a JS function body (doc, win) against the iframe doc
open_via_dialog_ui(page, base, file_path)   # sets fake dialog + clicks #open-btn + waits runtime
```
A suite's standard scaffold (match this idiom):
```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest, time
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8801

class PB1PageNavTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc, cls.base = H.start_server(PORT, test_dialog=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop(); H.stop_server(cls.proc)
    def setUp(self): self.page = self.browser.new_page()
    def tearDown(self): self.page.close()
```
NOTE the existing editor fixture `tecer-gsmm-introduction.html` is GITIGNORED (see `test_f2_select_guides.py` setUpClass which asserts `H.FIXTURE` exists and raises a clear message otherwise) — for the editor-regression case, guard the same way: if `H.FIXTURE` is missing, SKIP that one case with the exact reason string (D25), do NOT fail.

## builder_helpers.py — new shared helpers for builder suites
Provide:
- `set_fake_folder(base, path_or_none)` → `H.post_json(base, "/api/_test/set-folder-dialog", {"path": path_or_none})` (the seam PB-T7 added).
- `e2e_lib_path()` → absolute path to `tests/e2e/fixtures/builder-lib` (resolved relative to this file).
- `make_temp_library()` → copy `builder-lib` (and any sibling extra-root) into a fresh tempdir, ensure the engine is present at `{tmp}/builder-lib/assemble.py` (copy from `html/slide-library/engine/assemble.py`), return the temp library abs path. (Tests that assemble must use a temp copy — a sibling assets/ collision otherwise.)
- `pick_library_ui(page, base, lib_path)` → `set_fake_folder(base, lib_path)` then `page.click('#pick-library-btn')` then wait for `#browse-groups` to have children (`page.wait_for_function`).

## The e2e fixture library (tests/e2e/fixtures/builder-lib/)
Build a SMALL valid library conforming to the convention (3–5 fragments, ≥2 sections, both langs, ≥1 preset, self-contained assets so previews work offline). Reuse the SHAPE of the main fixture (`html/slide-library/docs/fixture-spec.md`) but smaller; OR simplest: copy a subset. It MUST be a valid library (the engine `--catalog-data --json` returns `ok:true`). Vendor the engine into it: copy `html/slide-library/engine/assemble.py` to `tests/e2e/fixtures/builder-lib/assemble.py`. Keep assets to bare filenames in the library's `assets/` (avoid `@root` here to stay self-contained, OR include a sibling `builder-shared/` if you exercise `@root`). Verify with: `python tests/e2e/fixtures/builder-lib/assemble.py --catalog-data --json` → `ok:true`.

## test_pb1_page_nav.py — the suite
1. `test_builder_page_serves`: `page.goto(base + "/app/builder.html")`; assert `page.locator('#builder-browse')` and `#builder-tray-pane` are present.
2. `test_nav_round_trip`: REAL navigation — `page.goto(base + "/app/")`; click the `#nav-builder` link; assert `page.url` ends with `/app/builder.html`; click `#nav-editor`; assert `page.url` ends with `/app/`.
3. `test_editor_boot_unregressed`: (guard: skip with exact reason if `H.FIXTURE` missing) — `page.goto(base + "/app/")` with NO `?file=`; open the editor fixture via the existing path `H.open_via_dialog_ui(page, base, copy)` (copy via `H.copy_fixture()`); assert `H.wait_runtime_ready(page)` succeeds (the editor still boots — the nav + the new param-branch did not break it). This is the zero-regression proof (build-spec S-B1.3/S-B10.3).
4. `test_handoff_param_branch_present`: `page.goto(base + "/app/?file=" + "")` (empty param) → assert the editor still boots its toolbar (the empty/absent param does not run the open branch) — assert `#open-btn` exists and no console error. (Full handoff is PB-T14.)

## Acceptance criteria
Run: `python -m unittest tests.e2e.test_pb1_page_nav -v` from the hypresent repo root (cwd = `html/hypresent`). ALL pass (case 3 may SKIP with the exact reason if the gitignored fixture is absent — that is allowed, record it). Record the D29 block. WALL_MS for a browser suite MUST be ≥1s (implausible if <1s → BUG + STOP).

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/e2e-page-nav-result.md`: the D29 block + a confirmation that `tests/e2e/fixtures/builder-lib/assemble.py --catalog-data --json` returned `ok:true`.

DONE means: helpers + fixture lib + suite created, suite green (case 3 skip allowed), D29 evidence written. Failure/implausible metric → BLOCKED/BUG + stop.
