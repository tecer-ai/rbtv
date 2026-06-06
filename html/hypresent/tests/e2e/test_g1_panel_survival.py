import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H


PORT = 8786


class G1PanelSurvivalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(H.FIXTURE):
            raise AssertionError(f"Required fixture missing: {H.FIXTURE} (gitignored per U10a; restore it locally before running tests)")
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

    def tearDown(self):
        self.page.close()

    def test_g1_survival_across_two_opens(self):          # E-G1-1
        self.page.goto(self.base + "/app/")
        copyA = H.copy_fixture()
        copyB = H.copy_fixture()
        H.open_via_dialog_ui(self.page, self.base, copyA)
        # add a comment so #comment-threads has a card
        frame = self.page.frame_locator("iframe.doc-frame")
        frame.locator(".slide-title").first.click()
        self.page.click("#comment-btn")
        self.page.fill(".hyp-composer-textarea", "note A")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_selector("#comment-threads .comment-thread")
        # OPEN document B
        H.open_via_dialog_ui(self.page, self.base, copyB)
        self.page.wait_for_timeout(400)
        # the panel containers must STILL EXIST (not wiped by the color popover)
        self.assertIsNotNone(self.page.query_selector("#comment-threads"))
        self.assertIsNotNone(self.page.query_selector("#comment-unanchored"))
        self.assertIsNotNone(self.page.query_selector(".hyp-color-popover-container"))

    def test_g1_panel_dom_structure(self):                # E-G1-2
        self.page.goto(self.base + "/app/")
        copyA = H.copy_fixture()
        H.open_via_dialog_ui(self.page, self.base, copyA)
        order = self.page.eval_on_selector_all(
            ".shell-panel > *",
            "els => els.map(e => e.className)"
        )
        self.assertEqual(order[0], "hyp-color-popover-container")
        self.assertNotIn("outline-panel", order)
        self.assertIn("comment-panel", order)

    def test_g1_popover_rerender(self):                   # E-G1-3
        self.page.goto(self.base + "/app/")
        copyA = H.copy_fixture()
        H.open_via_dialog_ui(self.page, self.base, copyA)
        # add a comment so #comment-threads has a card
        frame = self.page.frame_locator("iframe.doc-frame")
        frame.locator(".slide-title").first.click()
        self.page.click("#comment-btn")
        self.page.fill(".hyp-composer-textarea", "note A")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_selector("#comment-threads .comment-thread")
        # select another element to force popover re-render
        before_threads = len(self.page.query_selector_all("#comment-threads .comment-thread"))
        self.page.frame_locator("iframe.doc-frame").locator(".kicker").first.click()
        self.page.wait_for_timeout(200)
        after_threads = len(self.page.query_selector_all("#comment-threads .comment-thread"))
        self.assertEqual(before_threads, after_threads)


if __name__ == "__main__":
    unittest.main()
