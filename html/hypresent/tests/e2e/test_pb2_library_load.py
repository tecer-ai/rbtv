import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest, time
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8802


class PB2LibraryLoadTests(unittest.TestCase):
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

    def test_pick_and_render_groups(self):
        lib = B.e2e_lib_path()
        B.pick_library_ui(self.page, self.base, lib)

        # API envelope order
        status, data = H.post_json(self.base, "/api/library-load", {"path": lib})
        self.assertEqual(status, 200)
        catalog = data["catalog_data"]
        expected_sections = catalog["sections"]
        slides = catalog["slides"]

        groups = self.page.locator("#browse-groups .browse-group").all()
        self.assertGreaterEqual(len(groups), 2, "expected at least 2 browse groups")

        labels = [
            g.locator(".browse-group-label").text_content() for g in groups
        ]
        self.assertEqual(labels, expected_sections, "group labels should match section order")

        cards = self.page.locator(".slide-card").all()
        self.assertEqual(len(cards), len(slides), "slide-card count should match slides in catalog")

    def test_language_filter(self):
        lib = B.e2e_lib_path()
        B.pick_library_ui(self.page, self.base, lib)

        visible_before = self.page.eval_on_selector_all(
            ".slide-card", "els => els.filter(e => e.offsetParent !== null).length"
        )
        total = self.page.locator(".slide-card").count()
        self.assertEqual(visible_before, total, "before filter, all cards visible")

        self.page.select_option("#lang-filter", "pt")
        # Wait a tick for the DOM update
        self.page.wait_for_timeout(100)

        visible_after = self.page.eval_on_selector_all(
            ".slide-card", "els => els.filter(e => e.offsetParent !== null).length"
        )
        self.assertLess(visible_after, visible_before, "filter should reduce visible count")

        # cover-e2e.en has .en suffix and lang en != pt → should be hidden
        en_card = self.page.locator('.slide-card[data-slide-id="cover-e2e.en"]')
        self.assertTrue(
            en_card.evaluate("e => e.offsetParent === null"),
            "cover-e2e.en should be hidden when pt is selected",
        )

        # intro-e2e is language-neutral (no .pt suffix) → stays visible
        intro_card = self.page.locator('.slide-card[data-slide-id="intro-e2e"]')
        self.assertFalse(
            intro_card.evaluate("e => e.offsetParent === null"),
            "intro-e2e should stay visible",
        )

    def test_invalid_library_state(self):
        broken = B.make_temp_library()
        theme_path = os.path.join(broken, "theme.css")
        self.assertTrue(os.path.isfile(theme_path), "theme.css should exist before deletion")
        os.remove(theme_path)
        self.assertTrue(os.path.isfile(os.path.join(broken, "assemble.py")), "assemble.py must be present")

        B.set_fake_folder(self.base, broken)
        self.page.click("#pick-library-btn")
        self.page.wait_for_selector(".builder-invalid", timeout=5000)

        errors = self.page.locator(".builder-invalid li").all_text_contents()
        self.assertTrue(
            any("theme.css" in e for e in errors),
            f"error should mention theme.css, got: {errors}",
        )

        self.assertEqual(
            self.page.locator(".browse-group").count(), 0,
            "no browse-group should render for invalid library",
        )

    def test_library_load_envelope(self):
        lib = B.e2e_lib_path()
        status, data = H.post_json(self.base, "/api/library-load", {"path": lib})
        self.assertEqual(status, 200)
        self.assertIn("catalog_data", data, "envelope must contain catalog_data")
        catalog = data["catalog_data"]
        self.assertIn("sections", catalog, "catalog_data must have sections")
        self.assertIn("slides", catalog, "catalog_data must have slides")
        self.assertIn("presets", catalog, "catalog_data must have presets")


if __name__ == "__main__":
    unittest.main()
