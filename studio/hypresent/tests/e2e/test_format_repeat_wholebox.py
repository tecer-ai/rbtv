import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8810


class FormatRepeatWholeboxTests(unittest.TestCase):
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
        self.page.mouse.click(origin["x"] + rect["x"] + min(rect["w"] / 2, 40), origin["y"] + rect["y"] + rect["h"] / 2)
        self.page.wait_for_timeout(250)

    def _enter_edit_and_select_word(self, selector=".slide-title"):
        H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); if(e) e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_timeout(300)
        origin = self.page.evaluate(
            "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
        )
        rect = H.doc_eval(
            self.page,
            f"const e=doc.querySelector({selector!r}); const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};",
        )
        cx = origin["x"] + rect["x"] + min(rect["w"] / 2, 40)
        cy = origin["y"] + rect["y"] + rect["h"] / 2
        self.page.mouse.dblclick(cx, cy)
        self.page.wait_for_timeout(300)

    def _press(self, btn_id, times=1):
        for _ in range(times):
            self.page.click(f"#{btn_id}")
            self.page.wait_for_timeout(150)

    def _has_bold_tag(self, selector):
        return H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); return !!e.querySelector('b, strong');")

    # C1a — whole-box bold toggles all text and repeats without re-selecting
    def test_whole_box_bold_repeat(self):
        # Use .slide-subtitle because .slide-title is already CSS-bold (700);
        # execCommand("bold") on CSS-bold text toggles OFF instead of ON.
        sel = ".slide-subtitle"
        self._real_select(sel)
        self._press("fmt-bold", 1)
        self.assertTrue(self._has_bold_tag(sel), "whole box should have bold tags after first bold")
        self._press("fmt-bold", 1)
        self.assertFalse(self._has_bold_tag(sel), "whole box should have no bold tags after second bold (toggle off)")

    # C1b — whole-box italic toggles all text and repeats
    def test_whole_box_italic_repeat(self):
        sel = ".slide-title"
        self._real_select(sel)
        self._press("fmt-italic", 1)
        has_italic = H.doc_eval(self.page, f"const e=doc.querySelector({sel!r}); return !!e.querySelector('i, em');")
        self.assertTrue(has_italic, "whole box should have italic tags after first italic")
        self._press("fmt-italic", 1)
        has_italic = H.doc_eval(self.page, f"const e=doc.querySelector({sel!r}); return !!e.querySelector('i, em');")
        self.assertFalse(has_italic, "whole box should have no italic tags after second italic")

    # C1c — whole-box A+ scales proportionally, preserving ratio
    def test_whole_box_font_inc_proportional(self):
        sel = ".slide-title"
        # Inject mixed-size spans for a clean ratio test
        H.doc_eval(
            self.page,
            f"const e=doc.querySelector({sel!r}); e.innerHTML = '<span style=\"font-size:20px\">Big</span><span style=\"font-size:10px\">Small</span>';",
        )
        self._real_select(sel)
        sizes_before = H.doc_eval(
            self.page,
            f"const e=doc.querySelector({sel!r}); const spans=Array.from(e.querySelectorAll('span')); return spans.map(s => parseFloat(getComputedStyle(s).fontSize));",
        )
        self.assertEqual(len(sizes_before), 2, "should have two spans")
        ratio_before = sizes_before[0] / sizes_before[1]

        self._press("fmt-font-inc", 1)

        sizes_after = H.doc_eval(
            self.page,
            f"const e=doc.querySelector({sel!r}); const spans=Array.from(e.querySelectorAll('span')); return spans.map(s => parseFloat(getComputedStyle(s).fontSize));",
        )
        self.assertEqual(len(sizes_after), 2, "should still have two spans")
        ratio_after = sizes_after[0] / sizes_after[1]
        self.assertAlmostEqual(
            ratio_after, ratio_before, delta=0.1,
            msg=f"ratio should be preserved: before={ratio_before}, after={ratio_after}",
        )
        self.assertGreater(sizes_after[0], sizes_before[0], "big span should grow")
        self.assertGreater(sizes_after[1], sizes_before[1], "small span should grow")

    # C2 — editing-path bold on selected word toggles and repeats
    def test_edit_path_bold_repeat(self):
        # Use .slide-subtitle because .slide-title is already CSS-bold (700);
        # execCommand("bold") on CSS-bold text toggles OFF instead of ON.
        sel = ".slide-subtitle"
        self._enter_edit_and_select_word(sel)
        self._press("fmt-bold", 1)
        self.assertTrue(self._has_bold_tag(sel), "selected word should be bold after first bold")
        self._press("fmt-bold", 1)
        self.assertFalse(self._has_bold_tag(sel), "selected word should be unbold after second bold")

    def test_no_console_errors(self):
        errors = []
        def on_console(msg):
            if msg.type == "error":
                t = msg.text
                if "assets/" in t and ("404" in t or "Failed to load resource" in t):
                    return
                errors.append(t)
        self.page.on("console", on_console)
        sel = ".slide-title"
        self._real_select(sel)
        self._press("fmt-bold", 2)
        self._press("fmt-italic", 2)
        self._press("fmt-font-inc", 1)
        self.assertEqual(len(errors), 0, f"unexpected console errors: {errors}")


if __name__ == "__main__":
    unittest.main()
