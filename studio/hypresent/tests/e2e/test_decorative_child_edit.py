"""E2E: boxes with an empty/decorative block child are still text-editable.

Regression for the canEditText bug: a registered element that has its own text
was wrongly blocked from inline editing whenever it ALSO contained a non-inline
child — even a purely decorative empty one (a connector dot <div>, a <br>, a
data-hyp-decorative node). Only a NON-empty block child should still block it.

Exercises the real runtime via real Playwright double-click gestures.
"""
import os, sys, re, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8821
FIXTURE = "decorative-child-edit.html"


class DecorativeChildEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(os.path.join(H.SYN_DIR, FIXTURE)):
            raise AssertionError(f"Required synthetic fixture missing: {FIXTURE}")
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
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic(FIXTURE))

    def tearDown(self):
        self.page.close()

    # ---- helpers ----

    def _dblclick(self, selector, dx=40, frac_y=0.5):
        H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); if(e) e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_timeout(150)
        origin = self.page.evaluate(
            "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
        )
        rect = H.doc_eval(
            self.page,
            f"const e=doc.querySelector({selector!r}); if(!e) return null; const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};",
        )
        self.assertIsNotNone(rect, f"{selector} not found")
        cx = origin["x"] + rect["x"] + min(rect["w"] / 2, dx)
        cy = origin["y"] + rect["y"] + rect["h"] * frac_y
        self.page.mouse.dblclick(cx, cy)
        self.page.wait_for_timeout(250)

    def _editable(self, selector):
        return H.doc_eval(
            self.page,
            f"const e=doc.querySelector({selector!r}); return e ? e.getAttribute('contenteditable') : null;",
        )

    def _save_to_temp(self, suffix=".html"):
        out = tempfile.mktemp(suffix=suffix)
        H.set_fake_dialog(self.base, out)
        self.page.click("#save-as-btn")
        self.page.wait_for_timeout(600)
        return out

    # ---- tests ----

    def test_node_with_empty_dot_child_is_editable(self):
        self._dblclick("#node-dot", dx=30, frac_y=0.5)
        self.assertEqual(self._editable("#node-dot"), "true",
                         "node with an empty decorative <div> dot must enter edit mode")

    def test_node_with_br_child_is_editable(self):
        self._dblclick("#node-br", dx=30, frac_y=0.4)
        self.assertEqual(self._editable("#node-br"), "true",
                         "node with a <br> child must enter edit mode")

    def test_node_with_explicit_decorative_child_is_editable(self):
        self._dblclick("#node-decorative", dx=30, frac_y=0.5)
        self.assertEqual(self._editable("#node-decorative"), "true",
                         "node with a data-hyp-decorative child must enter edit mode")

    def test_plain_node_still_editable_no_regression(self):
        self._dblclick("#node-plain", dx=40, frac_y=0.5)
        self.assertEqual(self._editable("#node-plain"), "true",
                         "plain text node must still enter edit mode")

    def test_node_with_nonempty_block_child_not_editable(self):
        # Click the node's OWN leading text ("Header text"), above the nested
        # .inner block, so the dblclick resolves to #node-container itself.
        self._dblclick("#node-container", dx=30, frac_y=0.15)
        self.assertIsNone(self._editable("#node-container"),
                          "node with a NON-empty block child must NOT enter edit mode")

    def test_edit_then_save_preserves_decorative_dot(self):
        self._dblclick("#node-dot", dx=30, frac_y=0.5)
        self.assertEqual(self._editable("#node-dot"), "true")
        # Real edit: place caret at end and type.
        self.page.keyboard.press("End")
        self.page.keyboard.type(" EDITED")
        self.page.keyboard.press("Escape")  # commit
        self.page.wait_for_timeout(300)
        out = self._save_to_temp("-decor.html")
        with open(out, encoding="utf-8") as f:
            saved = f.read()
        self.assertIn("EDITED", saved, "edited text must persist in the saved file")
        self.assertTrue(
            re.search(r'<div class="dot"></div>', saved),
            "the decorative dot <div> must survive the save intact",
        )


if __name__ == "__main__":
    unittest.main()
