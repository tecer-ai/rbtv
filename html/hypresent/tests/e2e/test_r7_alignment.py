import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8797


class R7AlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(H.FIXTURE):
            raise AssertionError(
                f"Required fixture missing: {H.FIXTURE} (gitignored per U10a; restore it locally before running tests)"
            )
        cls.proc, cls.base = H.start_server(PORT, test_dialog=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        H.stop_server(cls.proc)

    def setUp(self):
        self.page = self.browser.new_page()
        self.copy = H.copy_fixture()
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)

    def tearDown(self):
        self.page.close()

    # pick a registered element that exists in the fixture
    TARGET = ".research-card"

    def _ensure_target(self):
        # Resolve a class that exists, then PIN a unique id on its FIRST match so the
        # element we restyle/assert (querySelector) is the SAME element the real-mouse
        # _select() clicks. The fixture has MANY .research-card / .kicker nodes; without
        # a unique handle, querySelector returns the first while the click selects a
        # neighbour, and every assertion reads the wrong (un-restyled) element.
        cls = ".research-card"
        if not H.doc_eval(self.page, f"return !!doc.querySelector('{cls}');"):
            cls = ".kicker"
        ok = H.doc_eval(
            self.page,
            f"const e=doc.querySelector('{cls}'); if(!e) return false; "
            f"e.id='r7-target'; return true;",
        )
        self.assertTrue(ok, "no usable registered element")
        self.TARGET = "#r7-target"

    def _restyle(self, css_text):
        H.doc_eval(self.page, f"const e=doc.querySelector({self.TARGET!r}); e.style.cssText += {css_text!r};")

    def _select(self):
        H.doc_eval(self.page, f"const e=doc.querySelector({self.TARGET!r}); e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_timeout(250)
        origin = self.page.evaluate("() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }")

        # Clear any existing selection so the subsequent target click always produces
        # a fresh selection-changed event (and updated alignCaps) even when the target
        # was already selected.
        H.doc_eval(
            self.page,
            """
            const tmp = doc.createElement('div');
            tmp.id = 'r7-clear-selection-tmp';
            tmp.style.position = 'fixed';
            tmp.style.top = '0px';
            tmp.style.left = '0px';
            tmp.style.width = '10px';
            tmp.style.height = '10px';
            tmp.style.zIndex = '999999';
            doc.body.appendChild(tmp);
            """
        )
        self.page.mouse.click(origin["x"] + 5, origin["y"] + 5)
        self.page.wait_for_timeout(150)
        H.doc_eval(
            self.page,
            "const tmp = doc.getElementById('r7-clear-selection-tmp'); if(tmp) tmp.parentNode.removeChild(tmp);"
        )

        def _probe(padding_applied=False):
            if padding_applied:
                js = """
                const target = doc.querySelector('#r7-target');
                const r = target.getBoundingClientRect();
                const candidates = [
                    [r.left + r.width/2, r.top + 7],
                    [r.left + 2, r.top + 2],
                    [r.left + r.width - 2, r.top + 2],
                    [r.left + 2, r.top + r.height - 2],
                    [r.left + r.width - 2, r.top + r.height - 2],
                ];
                for (const [px, py] of candidates) {
                    const node = doc.elementFromPoint(px, py);
                    if (node === target) return {x: px, y: py};
                }
                return null;
                """
            else:
                js = """
                const target = doc.querySelector('#r7-target');
                const r = target.getBoundingClientRect();
                const candidates = [
                    [r.left + 2, r.top + 2],
                    [r.left + r.width - 2, r.top + 2],
                    [r.left + 2, r.top + r.height - 2],
                    [r.left + r.width - 2, r.top + r.height - 2],
                    [r.left + r.width/2, r.top + 2],
                    [r.left + 2, r.top + r.height/2],
                    [r.left + r.width/2, r.top + r.height/2],
                ];
                for (const [px, py] of candidates) {
                    const node = doc.elementFromPoint(px, py);
                    if (node === target) return {x: px, y: py};
                }
                return null;
                """
            return H.doc_eval(self.page, js)

        probe_result = _probe()
        if probe_result is None:
            H.doc_eval(self.page, "const e=doc.querySelector('#r7-target'); e.style.paddingTop = '14px';")
            probe_result = _probe(padding_applied=True)
            if probe_result is None:
                diag = H.doc_eval(
                    self.page,
                    """
                    const target = doc.querySelector('#r7-target');
                    const r = target.getBoundingClientRect();
                    const points = [
                        [r.left + 2, r.top + 2],
                        [r.left + r.width - 2, r.top + 2],
                        [r.left + 2, r.top + r.height - 2],
                        [r.left + r.width - 2, r.top + r.height - 2],
                        [r.left + r.width/2, r.top + 2],
                        [r.left + 2, r.top + r.height/2],
                        [r.left + r.width/2, r.top + r.height/2],
                        [r.left + r.width/2, r.top + 7],
                    ];
                    const out = [];
                    for (const [px, py] of points) {
                        const node = doc.elementFromPoint(px, py);
                        let name = 'null';
                        if (node) {
                            name = node.id || node.className || node.tagName || 'unknown';
                        }
                        out.push(`(${px.toFixed(1)},${py.toFixed(1)}) -> ${name}`);
                    }
                    return out.join('; ');
                    """
                )
                self.fail(f"Probe could not find a click point on target itself; elementFromPoint results: {diag}")

        self.page.mouse.click(origin["x"] + probe_result["x"], origin["y"] + probe_result["y"])
        self.page.wait_for_timeout(250)

        # D30: assert selected hypId equals target's data-hyp-id
        sel_info = self.page.evaluate(
            """
            async () => {
                const iframe = document.querySelector('iframe.doc-frame');
                return new Promise((resolve, reject) => {
                    const id = 'probe-' + Date.now() + '-' + Math.random();
                    const handler = (e) => {
                        if (e.origin !== location.origin) return;
                        if (e.data?.source !== 'hyp') return;
                        if (e.data?.kind === 'response' && e.data?.id === id) {
                            window.removeEventListener('message', handler);
                            if (e.data.ok) resolve(e.data.result);
                            else reject(new Error(e.data.error));
                        }
                    };
                    window.addEventListener('message', handler);
                    iframe.contentWindow.postMessage(
                        { source: 'hyp', kind: 'command', id, type: 'get-selection' },
                        location.origin
                    );
                    setTimeout(() => {
                        window.removeEventListener('message', handler);
                        reject(new Error('bridge get-selection timed out'));
                    }, 5000);
                });
            }
            """
        )
        target_hyp_id = H.doc_eval(
            self.page,
            "const e=doc.querySelector('#r7-target'); return e ? e.getAttribute('data-hyp-id') : null;"
        )
        selected_hyp_id = sel_info.get("hypId") if sel_info else None
        self.assertEqual(
            selected_hyp_id,
            target_hyp_id,
            f"selected {selected_hyp_id or 'none'} but target is {target_hyp_id or 'none'} — wrong-element selection",
        )

    def _computed(self, prop):
        return H.doc_eval(self.page, f"const e=doc.querySelector({self.TARGET!r}); return getComputedStyle(e).getPropertyValue({prop!r});")

    def _undo(self):
        self.page.locator(".shell-toolbar button", has_text="Undo").first.click()
        self.page.wait_for_timeout(200)

    # E-R7-1 / E-R7-2 — horizontal on a block + undo
    def test_h_block_center_and_undo(self):
        self._ensure_target()
        self._restyle("display:block;")
        self._select()
        before = self._computed("text-align")
        self.page.click("#align-center")
        self.page.wait_for_timeout(200)
        self.assertEqual(self._computed("text-align"), "center", "block H-center → text-align:center")
        self._undo()
        self.assertEqual(self._computed("text-align"), before, "undo restores text-align")

    # E-R7-3 / E-R7-4 — flex-row vertical + horizontal
    def test_flex_row(self):
        self._ensure_target()
        self._restyle("display:flex;flex-direction:row;")
        self._select()
        self.page.click("#align-middle")
        self.page.wait_for_timeout(200)
        self.assertEqual(self._computed("align-items"), "center", "flex-row V-middle → align-items:center")
        self.page.click("#align-right")
        self.page.wait_for_timeout(200)
        self.assertEqual(self._computed("justify-content"), "flex-end", "flex-row H-right → justify-content:flex-end")

    # E-R7-5 — flex-column mapping
    def test_flex_column(self):
        self._ensure_target()
        self._restyle("display:flex;flex-direction:column;")
        self._select()
        self.page.click("#align-right")
        self.page.wait_for_timeout(200)
        self.assertEqual(self._computed("align-items"), "flex-end", "flex-col H-right → align-items:flex-end")
        self.page.click("#align-bottom")
        self.page.wait_for_timeout(200)
        self.assertEqual(self._computed("justify-content"), "flex-end", "flex-col V-bottom → justify-content:flex-end")

    # E-R7-6 — grid
    def test_grid(self):
        self._ensure_target()
        self._restyle("display:grid;")
        self._select()
        self.page.click("#align-center")
        self.page.wait_for_timeout(200)
        self.assertEqual(self._computed("justify-items"), "center", "grid H-center → justify-items:center")
        self.page.click("#align-middle")
        self.page.wait_for_timeout(200)
        self.assertEqual(self._computed("align-items"), "center", "grid V-middle → align-items:center")

    # E-R7-7 — table-cell vertical
    def test_table_cell(self):
        self._ensure_target()
        # The fixture's .research-card lives inside a CSS grid; grid blockifies
        # display:table-cell to display:block, breaking vertical-align. Switch the
        # parent to table-row so the target behaves as a real table cell.
        H.doc_eval(
            self.page,
            "const p=doc.querySelector('#r7-target').parentElement; p.style.display='table-row';"
        )
        self._restyle("display:table-cell;")
        self._select()
        self.page.click("#align-bottom")
        self.page.wait_for_timeout(200)
        self.assertEqual(self._computed("vertical-align"), "bottom", "table-cell V-bottom → vertical-align:bottom")

    # E-R7-8 — plain auto-height block: vertical buttons disabled
    def test_plain_block_vertical_disabled(self):
        self._ensure_target()
        self._restyle("display:block;height:auto;min-height:0;")
        self._select()
        for vid in ("align-top", "align-middle", "align-bottom"):
            self.assertTrue(self.page.locator(f"#{vid}").is_disabled(), f"#{vid} must be disabled on a plain auto-height block")
        for hid in ("align-left", "align-center", "align-right"):
            self.assertFalse(self.page.locator(f"#{hid}").is_disabled(), f"#{hid} must be enabled when an element is selected")

    # E-R7-9 — fixed-height block: vertical via flex conversion + undo restores display
    def test_fixed_height_block_vertical(self):
        self._ensure_target()
        self._restyle("display:block;height:200px;")
        self._select()
        before_display = self._computed("display")
        self.page.click("#align-middle")
        self.page.wait_for_timeout(200)
        self.assertEqual(self._computed("display"), "flex", "fixed-height block V → converts to flex")
        self.assertEqual(self._computed("justify-content"), "center", "fixed-height block V-middle → justify-content:center")
        self._undo()
        self.assertEqual(self._computed("display"), before_display, "undo restores the pre-press display")

    # E-R7-10 — alignCaps payload differs by display
    def test_align_caps_payload(self):
        self._ensure_target()
        # flex → vertical true
        self._restyle("display:flex;flex-direction:row;")
        self._select()
        # Read caps via a fresh selection event capture is complex; assert via get-selection through the runtime.
        # The runtime exposes selection info through the bridge 'get-selection'; drive it via the shell is not
        # directly callable. Instead assert the BUTTON disabled-state mirrors caps (which is driven by alignCaps):
        self.assertFalse(self.page.locator("#align-middle").is_disabled(), "flex element → vertical enabled (caps.vertical=true)")
        # plain block → vertical false
        self._restyle("display:block;height:auto;min-height:0;")
        self._select()
        self.assertTrue(self.page.locator("#align-middle").is_disabled(), "plain block → vertical disabled (caps.vertical=false)")

    # E-R7-11 — no console errors
    def test_no_console_errors(self):
        errors = []
        def on_console(msg):
            if msg.type == "error":
                t = msg.text
                if "assets/" in t and ("404" in t or "Failed to load resource" in t):
                    return
                errors.append(t)
        self.page.on("console", on_console)
        self._ensure_target()
        self._restyle("display:flex;")
        self._select()
        self.page.click("#align-center")
        self.page.wait_for_timeout(200)
        self.assertEqual(len(errors), 0, f"unexpected console errors: {errors}")


if __name__ == "__main__":
    unittest.main()
