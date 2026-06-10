import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8810
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DECK_FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction-test-v3.html")


class PB10DeckAddTests(unittest.TestCase):
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
        d = tempfile.mkdtemp()
        dst = os.path.join(d, "deck.html")
        shutil.copy(DECK_FIXTURE, dst)
        return dst

    def _open_deck(self):
        deck_path = self._copy_deck()
        H.set_fake_dialog(self.base, deck_path)
        self.page.goto(self.base + "/app/builder.html")
        self.page.click("#open-deck-btn")
        self.page.wait_for_selector(".tray-row", timeout=10000)
        return deck_path

    def _pick_lib(self):
        lib = B.e2e_lib_path()
        B.pick_library_ui(self.page, self.base, lib)
        return lib

    def _tray_kinds(self):
        return self.page.eval_on_selector_all(
            ".tray-row",
            "els=>els.map(e=>e.querySelector('.tray-badge').textContent)"
        )

    # ── PB10-1: mixed add ──────────────────────────────────────────────────
    def test_mixed_add(self):
        self._open_deck()
        lib = self._pick_lib()

        # Add a library slide
        card_ids = self.page.eval_on_selector_all(".slide-card", "els=>els.map(e=>e.dataset.slideId)")
        self.assertTrue(len(card_ids) >= 1, "fixture needs at least 1 card")
        card_id = card_ids[0]
        self.page.click(f".slide-card[data-slide-id='{card_id}']")
        self.page.wait_for_timeout(100)

        # Add a blank slide
        self.page.click("#add-blank-btn")
        self.page.wait_for_timeout(100)

        rows = self.page.locator(".tray-row").all()
        self.assertEqual(len(rows), 12, "deck 10 + library 1 + blank 1 = 12 rows")

        kinds = self._tray_kinds()
        self.assertIn("deck", kinds)
        self.assertIn("lib", kinds)
        self.assertIn("blank", kinds)

        # Verify the library slide card is badged
        card = self.page.locator(f".slide-card[data-slide-id='{card_id}']")
        self.assertTrue(
            card.evaluate("e => e.classList.contains('is-added')"),
            "card should be badged as added"
        )

    # ── PB10-2: library toggle in deck mode ────────────────────────────────
    def test_library_toggle_in_deck_mode(self):
        self._open_deck()
        lib = self._pick_lib()

        card_ids = self.page.eval_on_selector_all(".slide-card", "els=>els.map(e=>e.dataset.slideId)")
        self.assertTrue(len(card_ids) >= 1, "fixture needs at least 1 card")
        card_id = card_ids[0]

        # Click to add
        self.page.click(f".slide-card[data-slide-id='{card_id}']")
        self.page.wait_for_timeout(100)

        rows = self.page.locator(".tray-row").all()
        self.assertEqual(len(rows), 11, "deck 10 + library 1")

        lib_rows = [r for r in rows if r.locator(".tray-badge").text_content() == "lib"]
        self.assertEqual(len(lib_rows), 1, "one library row should exist")

        # Card should be badged
        card = self.page.locator(f".slide-card[data-slide-id='{card_id}']")
        self.assertTrue(
            card.evaluate("e => e.classList.contains('is-added')"),
            "card should be badged after add"
        )

        # Click same card to remove
        self.page.click(f".slide-card[data-slide-id='{card_id}']")
        self.page.wait_for_timeout(100)

        rows_after = self.page.locator(".tray-row").all()
        self.assertEqual(len(rows_after), 10, "library row removed")

        lib_rows_after = [r for r in rows_after if r.locator(".tray-badge").text_content() == "lib"]
        self.assertEqual(len(lib_rows_after), 0, "no library rows should remain")

        # Card badge should be cleared
        self.assertFalse(
            card.evaluate("e => e.classList.contains('is-added')"),
            "card should not be badged after remove"
        )

    # ── PB10-3: library-first then deck-open clears stale browse cards ──────
    def test_library_then_deck_clears_browse(self):
        # Reverse order of the spec's primary flow: load a library FIRST, then
        # open a deck. Opening a deck nulls the tray library; stale browse cards
        # must be cleared so a click cannot create a library row with a null
        # libraryPath (which would corrupt the deck-save items contract).
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib()

        cards_before = self.page.eval_on_selector_all(".slide-card", "els=>els.length")
        self.assertTrue(cards_before >= 1, "library should render browse cards")

        deck_path = self._copy_deck()
        H.set_fake_dialog(self.base, deck_path)
        self.page.click("#open-deck-btn")
        self.page.wait_for_selector(".tray-row", timeout=10000)

        # Browse pane must be emptied of the stale library cards.
        cards_after = self.page.eval_on_selector_all(".slide-card", "els=>els.length")
        self.assertEqual(cards_after, 0, "browse cards must clear when a deck opens")

        # Tray holds the deck's existing rows only — no null library rows.
        kinds = self._tray_kinds()
        self.assertEqual(len(kinds), 10, "deck 10 existing rows")
        self.assertNotIn("lib", kinds, "no library rows from stale cards")


if __name__ == "__main__":
    unittest.main()
