import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8812


class CheatsheetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc, cls.base = H.start_server(PORT)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        H.stop_server(cls.proc)

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.goto(self.base + "/app/")

    def tearDown(self):
        self.page.close()

    def _open_overlay(self):
        self.page.click("#shortcuts-btn")
        self.page.wait_for_timeout(150)

    def _assert_overlay_open(self):
        scrim = self.page.locator(".shortcuts-scrim")
        self.assertTrue(scrim.is_visible(), "scrim should be visible")
        self.assertIn("is-open", scrim.get_attribute("class") or "")

    def _assert_overlay_closed(self):
        scrim = self.page.locator(".shortcuts-scrim")
        self.assertFalse(
            "is-open" in (scrim.get_attribute("class") or ""),
            "scrim should not have is-open"
        )

    def test_click_button_opens_overlay_with_groups(self):
        self._open_overlay()
        self._assert_overlay_open()
        headings = self.page.locator(".shortcuts-group-heading")
        self.assertEqual(headings.count(), 3, "should have three group headings")
        texts = [h.text_content() for h in headings.all()]
        self.assertIn("Text", texts)
        self.assertIn("Components", texts)
        self.assertIn("Editing", texts)

    def test_escape_closes_overlay(self):
        self._open_overlay()
        self._assert_overlay_open()
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(150)
        self._assert_overlay_closed()

    def test_click_scrim_outside_card_closes_overlay(self):
        self._open_overlay()
        self._assert_overlay_open()
        # click on the scrim at a corner well outside the card
        self.page.mouse.click(10, 10)
        self.page.wait_for_timeout(150)
        self._assert_overlay_closed()

    def test_ctrl_slash_opens_overlay(self):
        self.page.keyboard.press("Control+/")
        self.page.wait_for_timeout(150)
        self._assert_overlay_open()

    def test_overlay_receives_focus_on_open(self):
        self._open_overlay()
        self._assert_overlay_open()
        active = self.page.evaluate("() => document.activeElement.classList.contains('shortcuts-scrim')")
        self.assertTrue(active, "activeElement should be the shortcuts-scrim overlay")


if __name__ == "__main__":
    unittest.main()
