import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8807


class PB7SlideExpandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc, cls.base = H.start_server(PORT, test_dialog=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        H.stop_server(cls.proc)

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 720})

    def tearDown(self):
        self.page.close()

    def _open_first(self):
        self.page.goto(self.base + "/app/builder.html")
        B.pick_library_ui(self.page, self.base, B.e2e_lib_path())
        ids = self.page.eval_on_selector_all(".slide-card", "els=>els.map(e=>e.dataset.slideId)")
        self.assertTrue(len(ids) > 0)
        # hover then click the expand button on the first card
        card = self.page.locator(f".slide-card[data-slide-id='{ids[0]}']")
        card.hover()
        card.locator(".s-expand").click()
        self.page.wait_for_selector(".slide-stage.is-open", timeout=5000)
        return ids

    # ── PB7-1 ──────────────────────────────────────────────────────────────
    def test_expand_opens_without_adding(self):
        ids = self._open_first()
        stage = self.page.locator(".slide-stage.is-open")
        self.assertTrue(stage.count() > 0, "stage should be open")
        tray_rows = self.page.eval_on_selector_all(".tray-row", "els=>els.length")
        self.assertEqual(tray_rows, 0, "tray should still be empty after expand")

    # ── PB7-2 ──────────────────────────────────────────────────────────────
    def test_close_returns(self):
        self._open_first()
        self.page.keyboard.press("Escape")
        self.page.wait_for_selector(".slide-stage.is-open", state="detached", timeout=5000)
        stage = self.page.locator(".slide-stage.is-open")
        self.assertEqual(stage.count(), 0, "stage should be closed after Escape")

    # ── PB7-3 ──────────────────────────────────────────────────────────────
    def test_next_prev(self):
        ids = self._open_first()
        # Assert on first slide: Prev disabled
        prev = self.page.locator(".ss-prev")
        self.assertTrue(prev.is_disabled(), "Prev should be disabled on first slide")

        # Click Next → should show second slide
        self.page.click(".ss-next")
        self.page.wait_for_timeout(200)
        title = self.page.locator(".ss-title")
        self.assertEqual(title.get_attribute("data-slide-id"), ids[1], "should show second slide after Next")

        # Prev should now be enabled; click it → back to first
        self.assertFalse(prev.is_disabled(), "Prev should be enabled after moving to second slide")
        prev.click()
        self.page.wait_for_timeout(200)
        self.assertEqual(title.get_attribute("data-slide-id"), ids[0], "should show first slide after Prev")

    # ── PB7-4 ──────────────────────────────────────────────────────────────
    def test_add_from_stage(self):
        ids = self._open_first()
        add_btn = self.page.locator(".ss-add")
        self.assertFalse(add_btn.is_disabled(), "Add button should be enabled initially")

        add_btn.click()
        self.page.wait_for_timeout(200)

        tray_rows = self.page.eval_on_selector_all(".tray-row", "els=>els.length")
        self.assertEqual(tray_rows, 1, "tray should have 1 slide after Add")

        # Button should now show added state
        self.assertTrue(add_btn.evaluate("el => el.classList.contains('is-added')"), "Add button should have is-added class")
        self.assertEqual(add_btn.text_content().strip(), "Added", "Add button text should be 'Added'")


if __name__ == "__main__":
    unittest.main()
