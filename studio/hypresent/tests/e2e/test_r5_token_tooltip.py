import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8795
EXPECT_TITLE = "Changing a palette token recolors every element using that color across the whole document."


class R5TokenTooltipTests(unittest.TestCase):
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
        H.expand_colors(self.page)
        self.page.wait_for_selector(".hyp-token-row", timeout=5000)

    def tearDown(self):
        self.page.close()

    def test_tooltip_present_with_exact_title(self):
        infos = self.page.query_selector_all(".hyp-color-popover-container .hyp-token-info")
        self.assertEqual(len(infos), 1, f"expected exactly ONE header info icon, got {len(infos)}")
        self.assertEqual(infos[0].get_attribute("title"), EXPECT_TITLE, "info title must match D18 wording exactly")

    def test_tooltip_in_palette_header(self):
        # the ⓘ must be inside the header whose text contains "Palette Tokens"
        in_header = self.page.evaluate(
            "() => { const i=document.querySelector('.hyp-token-info'); if(!i) return false;"
            " const h=i.closest('.hyp-color-header'); return !!h && h.textContent.includes('Palette Tokens'); }"
        )
        self.assertTrue(in_header, "the info icon must live in the Palette Tokens header")

    def test_single_not_per_row(self):
        n_rows = len(self.page.query_selector_all(".hyp-token-row"))
        n_info = len(self.page.query_selector_all(".hyp-token-info"))
        self.assertGreater(n_rows, 0)
        self.assertEqual(n_info, 1, "the tooltip must be header-level (one), not per token row")


if __name__ == "__main__":
    unittest.main()
