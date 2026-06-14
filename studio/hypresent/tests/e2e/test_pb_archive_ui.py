import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest, shutil
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8809


class PBArchiveUITests(unittest.TestCase):
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
        self.page.goto(self.base + "/app/builder.html")

    def tearDown(self):
        self.page.close()

    def _pick_temp_library(self):
        lib = B.make_temp_library()
        self.addCleanup(lambda d=os.path.dirname(lib): shutil.rmtree(d, ignore_errors=True))
        B.pick_library_ui(self.page, self.base, lib)
        return lib

    def _archive_intro_e2e_via_ui(self):
        card = self.page.locator(".slide-card[data-slide-id='intro-e2e']")
        card.hover()
        card.locator(".s-archive").click()
        self.page.wait_for_selector(".slide-card[data-slide-id='intro-e2e']", state='detached', timeout=10000)

    def test_archive_removes_slide_from_catalog(self):
        lib = self._pick_temp_library()

        before = self.page.locator('.slide-card').count()
        self.assertEqual(
            self.page.locator(".slide-card[data-slide-id='intro-e2e']").count(),
            1,
            "target slide should be present before archive",
        )

        self._archive_intro_e2e_via_ui()

        after = self.page.locator('.slide-card').count()
        self.assertEqual(after, before - 1, "archive should remove one slide from the catalog")
        self.assertEqual(
            self.page.locator(".slide-card[data-slide-id='intro-e2e']").count(),
            0,
            "archived slide card should no longer render",
        )

        status, data = H.post_json(self.base, '/api/archive-list', {'path': lib})
        self.assertEqual(status, 200)
        self.assertTrue(data.get('ok'), data.get('error'))
        archived_ids = [e['id'] for e in data.get('archived', [])]
        self.assertIn('intro-e2e', archived_ids)

    def test_show_archived_and_restore(self):
        lib = self._pick_temp_library()
        self._archive_intro_e2e_via_ui()

        self.page.click("#show-archived-btn")
        self.page.wait_for_selector(".slide-card[data-slide-id='intro-e2e'] .s-restore", timeout=10000)

        self.page.click(".slide-card[data-slide-id='intro-e2e'] .s-restore")

        # Toggle back to the live grid and wait for the restored slide.
        self.page.click("#show-archived-btn")
        self.page.wait_for_selector(".slide-card[data-slide-id='intro-e2e']", timeout=10000)

        status, data = H.post_json(self.base, '/api/archive-list', {'path': lib})
        self.assertEqual(status, 200)
        self.assertTrue(data.get('ok'), data.get('error'))
        archived_ids = [e['id'] for e in data.get('archived', [])]
        self.assertNotIn('intro-e2e', archived_ids)


if __name__ == "__main__":
    unittest.main()
