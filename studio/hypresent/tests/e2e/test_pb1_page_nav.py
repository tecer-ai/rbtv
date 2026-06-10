import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest, time
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8801


class PB1PageNavTests(unittest.TestCase):
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
        self.page = self.browser.new_page()

    def tearDown(self):
        self.page.close()

    def test_builder_page_serves(self):
        self.page.goto(self.base + "/app/builder.html")
        self.assertTrue(
            self.page.locator("#builder-browse").count() > 0,
            "#builder-browse should be present",
        )
        self.assertTrue(
            self.page.locator("#builder-tray-pane").count() > 0,
            "#builder-tray-pane should be present",
        )

    def test_nav_round_trip(self):
        self.page.goto(self.base + "/app/")
        self.page.click("#nav-builder")
        self.page.wait_for_url("**/app/builder.html")
        self.assertTrue(self.page.url.endswith("/app/builder.html"))

        self.page.click("#nav-editor")
        self.page.wait_for_url("**/app/")
        self.assertTrue(self.page.url.endswith("/app/"))

    def test_editor_boot_unregressed(self):
        if not os.path.exists(H.FIXTURE):
            self.skipTest(
                f"Required fixture missing: {H.FIXTURE} (gitignored per U10a; restore it locally before running tests)"
            )
        self.page.goto(self.base + "/app/")
        copy = H.copy_fixture()
        H.open_via_dialog_ui(self.page, self.base, copy)
        # Reassert runtime is ready — the editor still boots after nav/param changes.
        H.wait_runtime_ready(self.page)
        self.assertTrue(True, "editor booted successfully")

    def test_handoff_param_branch_present(self):
        errors = []

        def on_console(msg):
            if msg.type == "error":
                text = msg.text
                if "assets/" in text and ("404" in text or "Failed to load resource" in text):
                    return
                errors.append(text)

        self.page.on("console", on_console)
        self.page.goto(self.base + "/app/?file=")
        self.assertTrue(
            self.page.locator("#open-btn").count() > 0,
            "#open-btn should exist when ?file= is empty",
        )
        self.assertEqual(len(errors), 0, f"unexpected console errors: {errors}")


if __name__ == "__main__":
    unittest.main()
