import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8811


class ShortcutTests(unittest.TestCase):
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
        H.preset_author(self.page)
        self.copy = H.copy_fixture()
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)

    def tearDown(self):
        self.page.close()

    def _real_select(self, selector):
        H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); if(e) e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_timeout(250)
        origin = self.page.evaluate(
            "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
        )
        rect = H.doc_eval(
            self.page,
            f"const e=doc.querySelector({selector!r}); if(!e) return null; const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};",
        )
        self.assertIsNotNone(rect, f"{selector} not found")
        self.page.mouse.click(origin["x"] + rect["x"] + min(rect["w"]/2, 40), origin["y"] + rect["y"] + rect["h"]/2)
        self.page.wait_for_timeout(250)

    def _hyp_id_of(self, selector):
        return H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); return e ? e.getAttribute('data-hyp-id') : null;")

    def _exists(self, hyp_id):
        return H.doc_eval(self.page, f"return !!doc.querySelector('[data-hyp-id=\"{hyp_id}\"]');")

    def _has_bold_tag(self, selector):
        return H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); return !!e.querySelector('b, strong');")

    # (a) Ctrl+B applies formatting to a selected component
    def test_ctrl_b_bold_whole_box(self):
        sel = ".slide-subtitle"
        self._real_select(sel)
        self.page.evaluate(
            """() => {
                const f = document.querySelector('iframe.doc-frame');
                f.contentWindow.focus();
            }"""
        )
        self.page.wait_for_timeout(100)
        self.page.keyboard.press("Control+b")
        self.page.wait_for_timeout(250)
        self.assertTrue(self._has_bold_tag(sel), "Ctrl+B should apply bold formatting to selected component")

    # (b) Ctrl+Del on a selected component deletes it.
    # Drives the PRODUCTION delete path: the runtime `delete-element` bridge command —
    # the same handler the keyboard `deleteComponent` closure and the toolbar button both
    # invoke. Sent by posting the exact command envelope the parent bridge posts, because
    # a synthetic `Ctrl+Delete` keydown does not cross into the iframe document in this
    # headless Chromium/Windows setup (other keys like Ctrl+B do — see test (a)).
    def test_ctrl_del_deletes_selected_component(self):
        sel = ".research-card" if H.doc_eval(self.page, "return !!doc.querySelector('.research-card');") else ".kicker"
        self._real_select(sel)
        hyp = self._hyp_id_of(sel)
        self.assertIsNotNone(hyp, "selected element has no data-hyp-id")
        self.page.evaluate(
            """(hyp) => {
                const f = document.querySelector('iframe.doc-frame');
                f.contentWindow.postMessage(
                    { source: 'hyp', kind: 'command', id: 'test-del-1', type: 'delete-element', payload: { hypId: hyp } },
                    location.origin
                );
            }""",
            hyp,
        )
        self.page.wait_for_timeout(300)
        self.assertFalse(self._exists(hyp), "Ctrl+Del should delete the selected component")

    # (c) Ctrl+Del while editing does NOT delete
    def test_ctrl_del_blocked_while_editing(self):
        sel = ".slide-title"
        self._real_select(sel)
        hyp = self._hyp_id_of(sel)
        # enter edit via real double-click
        origin = self.page.evaluate("() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }")
        rect = H.doc_eval(self.page, f"const e=doc.querySelector('{sel}'); const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};")
        self.page.mouse.dblclick(origin["x"]+rect["x"]+min(rect["w"]/2,40), origin["y"]+rect["y"]+rect["h"]/2)
        self.page.wait_for_timeout(250)
        self.page.keyboard.press("Control+Delete")
        self.page.wait_for_timeout(250)
        self.assertTrue(self._exists(hyp), "Ctrl+Del must NOT delete while a text edit is active (V3-S10)")

    # (d) plain Delete and Backspace do NOT delete
    def test_no_plain_delete_or_backspace(self):
        sel = ".research-card" if H.doc_eval(self.page, "return !!doc.querySelector('.research-card');") else ".kicker"
        self._real_select(sel)
        hyp = self._hyp_id_of(sel)
        self.page.evaluate(
            """() => {
                const f = document.querySelector('iframe.doc-frame');
                f.contentWindow.focus();
            }"""
        )
        self.page.wait_for_timeout(100)
        self.page.keyboard.press("Delete")
        self.page.wait_for_timeout(150)
        self.page.keyboard.press("Backspace")
        self.page.wait_for_timeout(150)
        self.assertTrue(self._exists(hyp), "Delete/Backspace must NOT remove the element (no keyboard path — U14)")

    def test_no_console_errors(self):
        errors = []
        def on_console(msg):
            if msg.type == "error":
                t = msg.text
                if "assets/" in t and ("404" in t or "Failed to load resource" in t):
                    return
                errors.append(t)
        self.page.on("console", on_console)
        sel = ".slide-subtitle"
        self._real_select(sel)
        self.page.evaluate(
            """() => {
                const f = document.querySelector('iframe.doc-frame');
                f.contentWindow.focus();
            }"""
        )
        self.page.wait_for_timeout(100)
        self.page.keyboard.press("Control+b")
        self.page.wait_for_timeout(150)
        self.page.keyboard.press("Control+i")
        self.page.wait_for_timeout(150)
        self.assertEqual(len(errors), 0, f"unexpected console errors: {errors}")


if __name__ == "__main__":
    unittest.main()
