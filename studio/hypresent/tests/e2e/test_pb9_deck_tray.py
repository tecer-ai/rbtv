import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8809
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DECK_FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction-test-v3.html")


def rect_of(page, selector):
    return page.evaluate(
        "(sel)=>{const e=document.querySelector(sel); const r=e.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height};}",
        selector,
    )


class PB9DeckTrayTests(unittest.TestCase):
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

    def _tray_uids(self):
        return self.page.eval_on_selector_all(".tray-row", "els=>els.map(e=>e.dataset.uid)")

    def _tray_kinds(self):
        return self.page.eval_on_selector_all(
            ".tray-row",
            "els=>els.map(e=>e.querySelector('.tray-badge').textContent)"
        )

    def _tray_order(self):
        return self.page.eval_on_selector_all(".tray-row", "els=>els.map(e=>e.dataset.uid)")

    def _tray_positions(self):
        return self.page.eval_on_selector_all(".tray-row .tray-pos", "els=>els.map(e=>e.textContent)")

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

    # ── PB9-1 ──────────────────────────────────────────────────────────────
    def test_mixed_tray_reorder(self):
        self._open_deck()
        lib = self._pick_lib()

        # Add a library slide
        card_ids = self.page.eval_on_selector_all(".slide-card", "els=>els.map(e=>e.dataset.slideId)")
        self.assertTrue(len(card_ids) >= 1, "fixture needs at least 1 card")
        self.page.click(f".slide-card[data-slide-id='{card_ids[0]}']")
        self.page.wait_for_timeout(100)

        # Add a blank slide
        self.page.click("#add-blank-btn")
        self.page.wait_for_timeout(100)

        before = self._tray_order()
        self.assertEqual(len(before), 12, "deck 10 + library 1 + blank 1 = 12 rows")

        kinds = self._tray_kinds()
        self.assertIn("deck", kinds)
        self.assertIn("lib", kinds)
        self.assertIn("blank", kinds)

        # Drag row 0 by its grip below row 2's midpoint -> expected index 2
        grip = rect_of(self.page, ".tray-row:nth-child(1) .grip")
        r2 = rect_of(self.page, ".tray-row:nth-child(3)")
        start_x = grip["x"] + grip["w"] / 2
        start_y = grip["y"] + grip["h"] / 2
        target_y = r2["y"] + r2["h"] / 2 + 5

        self.page.mouse.move(start_x, start_y)
        self.page.mouse.down()
        steps = 4
        for i in range(1, steps + 1):
            self.page.mouse.move(start_x, start_y + (target_y - start_y) * i / steps)
            self.page.wait_for_timeout(80)
        self.page.mouse.up()
        self.page.wait_for_timeout(200)

        after = self._tray_order()
        self.assertNotEqual(before, after, "order must change after drag")
        self.assertEqual(after[2], before[0], "dragged row should be at index 2")

        # Verify positions renumbered
        positions = self._tray_positions()
        self.assertEqual(positions, [str(i + 1) for i in range(len(positions))])

    # ── PB9-2 ──────────────────────────────────────────────────────────────
    def test_duplicate_existing_row(self):
        self._open_deck()
        self.page.wait_for_selector(".tray-row", timeout=10000)

        before = self._tray_order()
        self.assertEqual(len(before), 10, "deck should have 10 rows")

        # Click duplicate on first row (existing)
        self.page.click(".tray-row:nth-child(1) .tray-duplicate")
        self.page.wait_for_timeout(150)

        after = self._tray_order()
        self.assertEqual(len(after), 11, "duplicate adds one row")

        # The original row should stay at position 0; copy should be at position 1
        self.assertEqual(after[0], before[0], "original row should stay in place")
        self.assertNotEqual(after[1], before[0], "duplicate should have a new uid")

        # Titles should match
        titles = self.page.eval_on_selector_all(".tray-row .tray-title", "els=>els.map(e=>e.textContent)")
        self.assertEqual(titles[0], titles[1], "duplicate should have same title")

        # Duplicate badge should show 'deck' for both
        kinds = self._tray_kinds()
        self.assertEqual(kinds[0], "deck")
        self.assertEqual(kinds[1], "deck")

    # ── PB9-3 ──────────────────────────────────────────────────────────────
    def test_duplicate_then_remove_original(self):
        self._open_deck()
        self.page.wait_for_selector(".tray-row", timeout=10000)

        before = self._tray_order()
        self.assertEqual(len(before), 10)

        # Duplicate first row
        self.page.click(".tray-row:nth-child(1) .tray-duplicate")
        self.page.wait_for_timeout(150)

        after_dup = self._tray_order()
        self.assertEqual(len(after_dup), 11)

        # Remove the original first row
        self.page.click(".tray-row:nth-child(1) .tray-remove")
        self.page.wait_for_timeout(150)

        after_remove = self._tray_order()
        self.assertEqual(len(after_remove), 10, "one row removed -> 10 rows")

        # The copy should survive (uid identity)
        self.assertEqual(after_remove[0], after_dup[1], "copy should survive after original removed")

        # Verify positions renumbered
        positions = self._tray_positions()
        self.assertEqual(positions, [str(i + 1) for i in range(len(positions))])

    # ── PB9-4 ──────────────────────────────────────────────────────────────
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

        # Click same card to remove
        self.page.click(f".slide-card[data-slide-id='{card_id}']")
        self.page.wait_for_timeout(100)

        rows_after = self.page.locator(".tray-row").all()
        self.assertEqual(len(rows_after), 10, "library row removed")

        lib_rows_after = [r for r in rows_after if r.locator(".tray-badge").text_content() == "lib"]
        self.assertEqual(len(lib_rows_after), 0, "no library rows should remain")


if __name__ == "__main__":
    unittest.main()
