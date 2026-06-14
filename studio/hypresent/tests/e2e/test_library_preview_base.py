"""e2e test — library-mode previews resolve relative assets through /lib/."""
import os
import sys
import unittest
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8832


class LibraryPreviewBaseTests(unittest.TestCase):
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
        self.page.goto(self.base + "/app/builder.html")

    def tearDown(self):
        self.page.close()

    def test_library_preview_base_serves_relative_assets(self):
        lib_path = B.e2e_lib_path()
        B.pick_library_ui(self.page, self.base, lib_path)

        iframe = self.page.locator(".slide-thumb-wrapper iframe").first
        iframe.scroll_into_view_if_needed()
        self.page.wait_for_function(
            "(el) => el.srcdoc && el.srcdoc.includes('<base')",
            arg=iframe.element_handle(),
            timeout=5000,
        )
        srcdoc = iframe.get_attribute("srcdoc") or ""
        self.assertIn('/lib/', srcdoc, "library preview <base> must point at /lib/")
        self.assertNotIn('/doc/', srcdoc, "library preview <base> must not use /doc/")

        with urllib.request.urlopen(self.base + "/lib/assets/cover-bg.jpg", timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            self.assertGreater(len(resp.read()), 0)


if __name__ == "__main__":
    unittest.main()
