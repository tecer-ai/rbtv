import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H


def set_border(page, hex_value):
    inp = page.query_selector('.hyp-color-popover-container .hyp-coloris-input[data-prop="border-color"]')
    assert inp is not None, "Border row input not found"
    page.eval_on_selector(
        '.hyp-color-popover-container .hyp-coloris-input[data-prop="border-color"]',
        f"(el) => {{ el.value = {hex_value!r}; el.dispatchEvent(new Event('change', {{bubbles:true}})); }}"
    )
    page.wait_for_timeout(150)


class F4BorderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(H.FIXTURE):
            raise AssertionError(f"Required fixture missing: {H.FIXTURE} (gitignored per U10a; restore it locally before running tests)")
        cls.proc, cls.base = H.start_server(8784, test_dialog=True)
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

    def tearDown(self):
        self.page.close()

    def _open_and_click(self, selector=".slide-title"):
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        frame = self.page.frame_locator("iframe.doc-frame")
        frame.locator(selector).first.click()
        self.page.wait_for_timeout(300)

    def test_f4_1_popover_rows(self):
        self._open_and_click()
        inp = self.page.query_selector('.hyp-color-popover-container .hyp-coloris-input[data-prop="border-color"]')
        self.assertIsNotNone(inp)
        labels = self.page.eval_on_selector_all(
            '.hyp-element-body .hyp-color-row label',
            "els => els.map(e => e.textContent.trim())"
        )
        self.assertEqual(labels, ['Text', 'Background', 'Border'])

    def test_f4_2_auto_1px_red(self):
        self._open_and_click()
        set_border(self.page, "#ff0000")
        ok = H.doc_eval(self.page, """
            const e = doc.querySelector('.slide-title');
            const cs = getComputedStyle(e);
            return cs.borderTopStyle === 'solid'
                && Math.round(parseFloat(cs.borderTopWidth)) === 1
                && cs.borderTopColor === 'rgb(255, 0, 0)';
        """)
        self.assertTrue(ok)

    def test_f4_3_preserve_width(self):
        self._open_and_click()
        H.doc_eval(self.page, """
            const e = doc.querySelector('.slide-title');
            e.style.border = '3px solid blue';
            return true;
        """)
        frame = self.page.frame_locator("iframe.doc-frame")
        frame.locator(".slide-title").first.click()
        self.page.wait_for_timeout(300)
        set_border(self.page, "#00ff00")
        ok = H.doc_eval(self.page, """
            const e = doc.querySelector('.slide-title');
            const cs = getComputedStyle(e);
            return Math.round(parseFloat(cs.borderTopWidth)) === 3
                && cs.borderTopColor === 'rgb(0, 255, 0)';
        """)
        self.assertTrue(ok)

    def test_f4_4_undo_removes_border(self):
        self._open_and_click()
        set_border(self.page, "#ff0000")
        ok = H.doc_eval(self.page, """
            const e = doc.querySelector('.slide-title');
            const cs = getComputedStyle(e);
            return cs.borderTopStyle === 'solid';
        """)
        self.assertTrue(ok)
        self.page.keyboard.press("Control+z")
        self.page.wait_for_timeout(300)
        has_border = H.doc_eval(self.page, """
            const e = doc.querySelector('.slide-title');
            const s = e.getAttribute('style') || '';
            return s.includes('border');
        """)
        self.assertFalse(has_border)

    def test_f4_5_mixed_placeholder(self):
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        # Inject mixed borders BEFORE first click so selection-changed sees them.
        H.doc_eval(self.page, """
            const e = doc.querySelector('.slide-title');
            e.style.borderTopColor = 'red';
            e.style.borderRightColor = 'green';
            e.style.borderBottomColor = 'blue';
            e.style.borderLeftColor = 'yellow';
            return true;
        """)
        frame = self.page.frame_locator("iframe.doc-frame")
        frame.locator(".slide-title").first.click()
        self.page.wait_for_timeout(300)
        sel = '.hyp-color-popover-container .hyp-coloris-input[data-prop="border-color"]'
        placeholder = self.page.get_attribute(sel, "placeholder") or ""
        value = self.page.eval_on_selector(sel, "el => el.value")
        self.assertEqual(placeholder, "mixed")
        self.assertEqual(value, "")

    def test_f4_6_mixed_to_uniform(self):
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        # Inject mixed borders BEFORE first click so selection-changed sees them.
        H.doc_eval(self.page, """
            const e = doc.querySelector('.slide-title');
            e.style.borderTopColor = 'red';
            e.style.borderRightColor = 'green';
            e.style.borderBottomColor = 'blue';
            e.style.borderLeftColor = 'yellow';
            return true;
        """)
        frame = self.page.frame_locator("iframe.doc-frame")
        frame.locator(".slide-title").first.click()
        self.page.wait_for_timeout(300)
        set_border(self.page, "#123456")
        colors = H.doc_eval(self.page, """
            const e = doc.querySelector('.slide-title');
            const cs = getComputedStyle(e);
            return [
                cs.borderTopColor,
                cs.borderRightColor,
                cs.borderBottomColor,
                cs.borderLeftColor
            ];
        """)
        self.assertEqual(colors, ['rgb(18, 52, 86)', 'rgb(18, 52, 86)', 'rgb(18, 52, 86)', 'rgb(18, 52, 86)'])

    def test_f4_7_serialize_survival(self):
        self._open_and_click()
        set_border(self.page, "#ff0000")
        out = os.path.join(os.path.dirname(self.copy), "out.html")
        H.set_fake_dialog(self.base, out)
        self.page.click("#save-as-btn")
        self.page.wait_for_function("() => true")
        self.page.wait_for_timeout(500)
        self.assertTrue(os.path.exists(out))
        with open(out, encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn("slide-title", html)
        # Browser serialization may convert #ff0000 to rgb(255, 0, 0)
        self.assertTrue(
            'border-color:#ff0000' in html
            or 'border-color: #ff0000' in html
            or 'border:1px solid #ff0000' in html
            or 'border: 1px solid #ff0000' in html
            or 'border:1px solid rgb(255, 0, 0)' in html
            or 'border: 1px solid rgb(255, 0, 0)' in html
            or 'border-color:rgb(255, 0, 0)' in html
            or 'border-color: rgb(255, 0, 0)' in html,
            "Expected inline border or border-color with red color in saved HTML"
        )


if __name__ == "__main__":
    unittest.main()
