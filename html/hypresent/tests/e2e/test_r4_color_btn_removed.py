import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8794


class R4ColorBtnRemovedTests(unittest.TestCase):
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

    def tearDown(self):
        self.page.close()

    # E-R4-1 — button gone
    def test_color_btn_absent(self):
        self.assertIsNone(self.page.query_selector("#color-btn"), "#color-btn must be removed")

    # E-R4-2 — no empty toolbar group, no 🎨 glyph
    def test_no_empty_group_no_glyph(self):
        # No toolbar-group should contain zero buttons (the #color-btn group is gone, not emptied).
        empty_groups = self.page.evaluate(
            "() => Array.from(document.querySelectorAll('.shell-toolbar .toolbar-group'))"
            ".filter(g => g.querySelectorAll('button').length === 0).length"
        )
        self.assertEqual(empty_groups, 0, "no empty toolbar-group should remain after removing #color-btn")
        toolbar_text = self.page.evaluate("() => document.querySelector('.shell-toolbar').textContent")
        self.assertNotIn("🎨", toolbar_text, "the 🎨 glyph must be gone from the toolbar")

    # E-R4-3 — color UI still works
    def test_color_ui_intact(self):
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        # Palette Tokens container present
        self.assertIsNotNone(
            self.page.query_selector(".hyp-color-popover-container"),
            "the color popover container must still render",
        )
        # at least one token row eventually renders (fixture has :root color tokens)
        self.page.wait_for_selector(".hyp-token-row", timeout=5000)
        self.assertGreater(
            len(self.page.query_selector_all(".hyp-token-row")), 0,
            "Palette Tokens list must still render (color UI intact without #color-btn)",
        )


if __name__ == "__main__":
    unittest.main()
