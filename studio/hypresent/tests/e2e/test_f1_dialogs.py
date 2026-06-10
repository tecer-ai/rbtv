import os
import sys
import unittest

# e2e import bootstrap (R08): make this file's own dir importable so `conftest_helpers`
# resolves under `python -m unittest discover -s tests` (which adds tests/ but not tests/e2e/).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8781


class F1DialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Fail loud if the canonical fixture is absent (gitignored per U10a; never skip-green, R07).
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
        self.page = cls_page = self.browser.new_page()
        self.copy = H.copy_fixture()

    def tearDown(self):
        self.page.close()

    def test_open_via_dialog(self):                  # E-F1-1
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        src = self.page.get_attribute("iframe.doc-frame", "src")
        self.assertIn("/doc/", src)

    def test_open_cancel(self):                      # E-F1-2
        self.page.goto(self.base + "/app/")
        H.set_fake_dialog(self.base, None)
        self.page.click("#open-btn")
        # iframe should not navigate to /doc/
        self.page.wait_for_timeout(500)
        src = self.page.get_attribute("iframe.doc-frame", "src") or ""
        self.assertNotIn("/doc/", src)

    def test_inputs_removed(self):                   # E-F1-6
        self.page.goto(self.base + "/app/")
        self.assertIsNone(self.page.query_selector("#open-path-input"))
        self.assertIsNone(self.page.query_selector("#save-as-path-input"))
        self.assertIsNotNone(self.page.query_selector("#save-btn"))

    def test_save_as_writes(self):                   # E-F1-3
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        out = os.path.join(os.path.dirname(self.copy), "out.html")
        # make an edit: double-click a slide title and type
        frame = self.page.frame_locator("iframe.doc-frame")
        title = frame.locator(".slide-title").first
        title.dblclick()
        self.page.keyboard.type(" EDITED")
        self.page.keyboard.press("Escape")
        H.set_fake_dialog(self.base, out)
        self.page.click("#save-as-btn")
        self.page.wait_for_function("() => true")  # let the POST resolve
        self.page.wait_for_timeout(500)
        self.assertTrue(os.path.exists(out))
        with open(out, encoding="utf-8") as fh:
            self.assertIn("EDITED", fh.read())

    def test_save_overwrites_open(self):             # E-F1-4
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        frame = self.page.frame_locator("iframe.doc-frame")
        title = frame.locator(".slide-title").first
        title.dblclick()
        self.page.keyboard.type(" SAVEME")
        self.page.keyboard.press("Escape")
        self.page.click("#save-btn")
        self.page.wait_for_timeout(500)
        with open(self.copy, encoding="utf-8") as fh:
            self.assertIn("SAVEME", fh.read())

    def test_save_fallback_to_dialog_when_no_open(self):  # E-F1-5
        self.page.goto(self.base + "/app/")
        # No document opened. Save should fall back to Save As (dialog).
        # Without an open doc there is no bridge -> serializeDoc returns null and
        # nothing is written; this asserts the no-crash + status path.
        self.page.click("#save-btn")
        self.page.wait_for_timeout(300)
        # status should reflect "No document open." (serializeDoc guard)
        status = self.page.text_content("#shell-status") or ""
        self.assertIn("No document open", status)


if __name__ == "__main__":
    unittest.main()
