import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8808
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DECK_FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction-test-v3.html")


class PB8DeckOpenTests(unittest.TestCase):
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

    def _copy_deck(self):
        """Return the absolute path of a temp copy of the test deck."""
        d = tempfile.mkdtemp()
        dst = os.path.join(d, "deck.html")
        shutil.copy(DECK_FIXTURE, dst)
        return dst

    # ── PB8-1 ──────────────────────────────────────────────────────────────
    def test_open_deck_full_tray(self):
        deck_path = self._copy_deck()
        H.set_fake_dialog(self.base, deck_path)
        self.page.goto(self.base + "/app/builder.html")
        self.page.click("#open-deck-btn")

        self.page.wait_for_selector(".tray-row", timeout=10000)
        rows = self.page.locator(".tray-row").all()
        self.assertEqual(len(rows), 10, "tray should have 10 rows for 10-section deck")

        for i, row in enumerate(rows):
            iframe = row.locator("iframe")
            srcdoc = iframe.get_attribute("srcdoc")
            self.assertIsNotNone(srcdoc, f"row {i + 1} iframe should have srcdoc")
            self.assertIn("<section", srcdoc, f"row {i + 1} srcdoc should contain section markup")

        # Deck chip visible with filename
        chip_name = self.page.locator("#deck-chip-name").text_content()
        self.assertEqual(chip_name, "deck.html", "deck chip should show filename")

    # ── PB8-2 ──────────────────────────────────────────────────────────────
    def test_thumbnails_themed(self):
        deck_path = self._copy_deck()
        H.set_fake_dialog(self.base, deck_path)
        self.page.goto(self.base + "/app/builder.html")
        self.page.click("#open-deck-btn")

        self.page.wait_for_selector(".tray-row", timeout=10000)
        rows = self.page.locator(".tray-row").all()
        self.assertEqual(len(rows), 10, "tray should have 10 rows for 10-section deck")

        for i, row in enumerate(rows):
            iframe = row.locator("iframe")
            srcdoc = iframe.get_attribute("srcdoc")
            self.assertIsNotNone(srcdoc, f"row {i + 1} iframe should have srcdoc")
            self.assertIn("<section", srcdoc, f"row {i + 1} srcdoc should contain section markup")
            # Head styles from the deck should be present (e.g., the .slide CSS rule)
            self.assertIn(".slide {", srcdoc, f"row {i + 1} srcdoc should contain deck head styles")

    # ── PB8-3 ──────────────────────────────────────────────────────────────
    def test_non_conforming_rejected(self):
        d = tempfile.mkdtemp()
        bad_path = os.path.join(d, "bad.html")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("<html><body><p>No sections here</p></body></html>")

        H.set_fake_dialog(self.base, bad_path)
        self.page.goto(self.base + "/app/builder.html")
        self.page.click("#open-deck-btn")

        # Wait for error class on status bar
        self.page.wait_for_selector(".shell-status.error", timeout=5000)
        status_text = self.page.locator("#builder-status").text_content()
        self.assertIn("section", status_text.lower(), "status should mention missing sections")

        rows = self.page.locator(".tray-row").all()
        self.assertEqual(len(rows), 0, "tray should be empty for non-conforming file")

    # ── PB8-4 ──────────────────────────────────────────────────────────────
    def test_file_param_arrival(self):
        deck_path = self._copy_deck()
        # Use forward slashes in query param to avoid backslash escaping issues
        url_path = deck_path.replace("\\", "/")
        self.page.goto(self.base + "/app/builder.html?file=" + url_path)

        self.page.wait_for_selector(".tray-row", timeout=10000)
        rows = self.page.locator(".tray-row").all()
        self.assertEqual(len(rows), 10, "tray should have 10 rows on ?file= arrival")

        chip_name = self.page.locator("#deck-chip-name").text_content()
        self.assertEqual(chip_name, "deck.html", "deck chip should show filename on arrival")


if __name__ == "__main__":
    unittest.main()
