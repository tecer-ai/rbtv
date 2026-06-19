"""PB Archive Stage — archive a library slide from the expanded stage view.

Tests:
  1. Archive button present in stage view.
  2. Archiving from stage: stage closes + slide leaves live grid.
  3. Archived slide appears under "Show archived".
  4. Card-level archive still works (no regression).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest, shutil
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8833


class PBArchiveStageTests(unittest.TestCase):
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

    def _pick_temp_library(self):
        lib = B.make_temp_library()
        self.addCleanup(lambda d=os.path.dirname(lib): shutil.rmtree(d, ignore_errors=True))
        B.pick_library_ui(self.page, self.base, lib)
        return lib

    def _open_stage(self, slide_id="intro-e2e"):
        """Hover a card and click its expand button; return when stage is open."""
        card = self.page.locator(f".slide-card[data-slide-id='{slide_id}']")
        card.hover()
        card.locator(".s-expand").click()
        self.page.wait_for_selector(".slide-stage.is-open", timeout=5000)

    # ── AS-1: archive button present in stage ──────────────────────────────
    def test_archive_btn_present_in_stage(self):
        self._pick_temp_library()
        self._open_stage()
        btn = self.page.locator(".slide-stage.is-open .ss-archive")
        self.assertEqual(btn.count(), 1, "archive button should be present in the stage bar")

    # ── AS-2: archive from stage closes stage and removes slide from grid ──
    def test_archive_from_stage_closes_and_removes(self):
        lib = self._pick_temp_library()
        before = self.page.locator(".slide-card").count()
        self.assertEqual(
            self.page.locator(".slide-card[data-slide-id='intro-e2e']").count(),
            1,
            "target slide should be present before stage-archive",
        )

        self._open_stage("intro-e2e")

        # Click the in-stage archive button
        self.page.locator(".slide-stage.is-open .ss-archive").click()

        # Stage should close
        self.page.wait_for_selector(".slide-stage.is-open", state="detached", timeout=10000)

        # Slide should leave the live grid
        self.page.wait_for_selector(
            ".slide-card[data-slide-id='intro-e2e']", state="detached", timeout=10000
        )
        after = self.page.locator(".slide-card").count()
        self.assertEqual(after, before - 1, "archive should remove one slide from the catalog")

    # ── AS-3: archived slide appears under Show archived ──────────────────
    def test_archived_slide_appears_in_archived_view(self):
        lib = self._pick_temp_library()
        self._open_stage("intro-e2e")
        self.page.locator(".slide-stage.is-open .ss-archive").click()
        self.page.wait_for_selector(".slide-stage.is-open", state="detached", timeout=10000)
        self.page.wait_for_selector(
            ".slide-card[data-slide-id='intro-e2e']", state="detached", timeout=10000
        )

        # Switch to archived view
        self.page.click("#show-archived-btn")
        self.page.wait_for_selector(
            ".slide-card[data-slide-id='intro-e2e']", timeout=10000
        )
        self.assertEqual(
            self.page.locator(".slide-card[data-slide-id='intro-e2e']").count(),
            1,
            "archived slide should appear in the archived view",
        )

        # Also confirm via API
        status, data = H.post_json(self.base, "/api/archive-list", {"path": lib})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"), data.get("error"))
        archived_ids = [e["id"] for e in data.get("archived", [])]
        self.assertIn("intro-e2e", archived_ids)

    # ── AS-4: card-level archive regression (existing behaviour intact) ────
    def test_card_level_archive_still_works(self):
        lib = self._pick_temp_library()
        before = self.page.locator(".slide-card").count()

        card = self.page.locator(".slide-card[data-slide-id='intro-e2e']")
        card.hover()
        card.locator(".s-archive").click()
        self.page.wait_for_selector(
            ".slide-card[data-slide-id='intro-e2e']", state="detached", timeout=10000
        )

        after = self.page.locator(".slide-card").count()
        self.assertEqual(after, before - 1, "card-level archive should still remove slide")

        status, data = H.post_json(self.base, "/api/archive-list", {"path": lib})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"), data.get("error"))
        archived_ids = [e["id"] for e in data.get("archived", [])]
        self.assertIn("intro-e2e", archived_ids)


if __name__ == "__main__":
    unittest.main()
