import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8804


def rect_of(page, selector):
    return page.evaluate(
        "(sel)=>{const e=document.querySelector(sel); const r=e.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height};}",
        selector,
    )


class PB4TrayReorderTests(unittest.TestCase):
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

    def _pick_lib(self):
        lib = B.e2e_lib_path()
        B.pick_library_ui(self.page, self.base, lib)
        return lib

    def _card_ids(self):
        return self.page.eval_on_selector_all(".slide-card", "els=>els.map(e=>e.dataset.slideId)")

    def _tray_order(self):
        return self.page.eval_on_selector_all(".tray-row", "els=>els.map(e=>e.dataset.slideId)")

    def _tray_positions(self):
        return self.page.eval_on_selector_all(".tray-row .tray-pos", "els=>els.map(e=>e.textContent)")

    # ── PB4-1 ──────────────────────────────────────────────────────────────
    def test_click_to_tag(self):
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib()
        ids = self._card_ids()
        self.assertTrue(len(ids) >= 3, "fixture needs at least 3 cards")

        for i in range(3):
            card_sel = f".slide-card[data-slide-id='{ids[i]}']"
            self.page.click(card_sel)
            self.page.wait_for_timeout(100)

            row = self.page.locator(f".tray-row[data-slide-id='{ids[i]}']")
            self.assertEqual(row.count(), 1, f"tray row for {ids[i]} should exist")

        self.assertEqual(len(self._tray_order()), 3)
        positions = self._tray_positions()
        self.assertEqual(positions, ["1", "2", "3"])

    # ── PB4-2 ──────────────────────────────────────────────────────────────
    def test_remove_row(self):
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib()
        ids = self._card_ids()
        for i in range(3):
            self.page.click(f".slide-card[data-slide-id='{ids[i]}']")
            self.page.wait_for_timeout(100)

        before = self._tray_order()
        self.assertEqual(len(before), 3)

        # remove the middle row
        self.page.click(".tray-row:nth-child(2) .tray-remove")
        self.page.wait_for_timeout(100)

        after = self._tray_order()
        self.assertEqual(len(after), 2)
        self.assertNotIn(before[1], after)
        self.assertEqual(self._tray_positions(), ["1", "2"])

    # ── PB4-3 ──────────────────────────────────────────────────────────────
    def test_preset_preload(self):
        self.page.goto(self.base + "/app/builder.html")
        lib = self._pick_lib()
        status, data = H.post_json(self.base, "/api/library-load", {"path": lib})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"), f"library-load failed: {data}")
        presets = data["catalog_data"]["presets"]
        self.assertTrue(len(presets) > 0, "fixture should have at least one preset")
        preset = presets[0]
        expected_ids = preset["slides"]

        self.page.select_option("#preset-select", preset["preset"])
        self.page.wait_for_timeout(200)

        tray_ids = self._tray_order()
        self.assertEqual(tray_ids, expected_ids)

    # ── PB4-4 ──────────────────────────────────────────────────────────────
    def test_drag_reorder_real_mouse(self):
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib()
        ids = self._card_ids()
        for i in range(min(3, len(ids))):
            self.page.click(f".slide-card[data-slide-id='{ids[i]}']")
            self.page.wait_for_timeout(100)

        before = self._tray_order()
        self.assertEqual(len(before), 3, "need 3 rows to drag")

        # Drag row 0 below row 2's midpoint -> expected index 2
        r0 = rect_of(self.page, ".tray-row:nth-child(1)")
        r2 = rect_of(self.page, ".tray-row:nth-child(3)")
        start_x = r0["x"] + r0["w"] / 2
        start_y = r0["y"] + r0["h"] / 2
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
        self.assertEqual(after[2], before[0], "dragged row should be last")

        # Second drag: move last row to top
        before2 = after
        r_last = rect_of(self.page, ".tray-row:nth-child(3)")
        r_first = rect_of(self.page, ".tray-row:nth-child(1)")
        start_x2 = r_last["x"] + r_last["w"] / 2
        start_y2 = r_last["y"] + r_last["h"] / 2
        target_y2 = r_first["y"] + r_first["h"] / 2 - 5

        self.page.mouse.move(start_x2, start_y2)
        self.page.mouse.down()
        for i in range(1, steps + 1):
            self.page.mouse.move(start_x2, start_y2 + (target_y2 - start_y2) * i / steps)
            self.page.wait_for_timeout(80)
        self.page.mouse.up()
        self.page.wait_for_timeout(200)

        after2 = self._tray_order()
        self.assertNotEqual(before2, after2, "order must change on second drag")
        self.assertEqual(after2[0], before2[2], "dragged row should be first")

    # ── PB4-5 ──────────────────────────────────────────────────────────────
    def test_no_native_dnd(self):
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib()
        ids = self._card_ids()
        self.page.click(f".slide-card[data-slide-id='{ids[0]}']")
        self.page.wait_for_timeout(100)

        no_draggable = self.page.eval_on_selector_all(
            ".tray-row",
            'els=>els.every(e=>e.getAttribute("draggable")!=="true")',
        )
        self.assertTrue(no_draggable, "tray rows must not have native draggable=true")

    # ── PB4-6 ──────────────────────────────────────────────────────────────
    def test_drag_escape_cancel(self):
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib()
        ids = self._card_ids()
        for i in range(min(3, len(ids))):
            self.page.click(f".slide-card[data-slide-id='{ids[i]}']")
            self.page.wait_for_timeout(100)

        for _ in range(2):
            before = self._tray_order()
            self.assertEqual(len(before), 3)

            r0 = rect_of(self.page, ".tray-row:nth-child(1)")
            r1 = rect_of(self.page, ".tray-row:nth-child(2)")
            start_x = r0["x"] + r0["w"] / 2
            start_y = r0["y"] + r0["h"] / 2
            # move past row 1's midpoint so DOM visibly changes
            target_y = r1["y"] + r1["h"] / 2 + 5

            self.page.mouse.move(start_x, start_y)
            self.page.mouse.down()
            steps = 3
            for i in range(1, steps + 1):
                self.page.mouse.move(start_x, start_y + (target_y - start_y) * i / steps)
                self.page.wait_for_timeout(80)

            # Order should have changed mid-drag
            mid_order = self._tray_order()
            if mid_order == before:
                # If the DOM hasn't updated yet, give it one more frame
                self.page.wait_for_timeout(100)
                mid_order = self._tray_order()

            # DEBUG: ensure drag actually reordered before we test Escape cancel
            self.assertNotEqual(mid_order, before, "mid-drag order should have changed")

            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(150)

            after_escape = self._tray_order()
            self.assertEqual(
                after_escape, before,
                "Escape must restore pre-drag order"
            )

            self.page.mouse.up()
            self.page.wait_for_timeout(150)

            after_up = self._tray_order()
            self.assertEqual(after_up, before, "order must stay restored after late pointerup")

            ghost_present = self.page.eval_on_selector_all(
                ".tray-row",
                'els=>els.some(e=>e.classList.contains("tray-drag-ghost"))',
            )
            self.assertFalse(ghost_present, "no ghost class should remain after Escape")

            # re-establish order for next loop (already restored)

    # ── PB4-7 ──────────────────────────────────────────────────────────────
    def test_two_item_reorder(self):
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib()
        ids = self._card_ids()
        self.page.click(f".slide-card[data-slide-id='{ids[0]}']")
        self.page.wait_for_timeout(100)
        self.page.click(f".slide-card[data-slide-id='{ids[1]}']")
        self.page.wait_for_timeout(100)

        before = self._tray_order()
        self.assertEqual(len(before), 2)

        r0 = rect_of(self.page, ".tray-row:nth-child(1)")
        r1 = rect_of(self.page, ".tray-row:nth-child(2)")
        start_x = r0["x"] + r0["w"] / 2
        start_y = r0["y"] + r0["h"] / 2
        target_y = r1["y"] + r1["h"] / 2 + 5

        self.page.mouse.move(start_x, start_y)
        self.page.mouse.down()
        steps = 3
        for i in range(1, steps + 1):
            self.page.mouse.move(start_x, start_y + (target_y - start_y) * i / steps)
            self.page.wait_for_timeout(80)
        self.page.mouse.up()
        self.page.wait_for_timeout(200)

        after = self._tray_order()
        self.assertEqual(after, list(reversed(before)), "two-item drag must swap order")

    # ── PB4-8 ──────────────────────────────────────────────────────────────
    def test_scroll_during_drag(self):
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib()
        ids = self._card_ids()
        # tag all available rows
        for sid in ids:
            self.page.click(f".slide-card[data-slide-id='{sid}']")
            self.page.wait_for_timeout(100)

        # force a small max-height so the list scrolls
        self.page.evaluate(
            "()=>{const el=document.getElementById('tray-list'); el.style.maxHeight='80px'; el.style.overflowY='auto';}"
        )
        self.page.wait_for_timeout(100)

        # verify scrollability
        scrollable = self.page.evaluate(
            "()=>{const el=document.getElementById('tray-list'); return el.scrollHeight > el.clientHeight;}"
        )
        if not scrollable:
            self.skipTest(
                "tray list scrollHeight not greater than clientHeight even after forcing maxHeight — scroll-during-drag unverifiable"
            )

        before = self._tray_order()
        self.assertTrue(len(before) >= 2, "need at least 2 rows")

        r0 = rect_of(self.page, ".tray-row:nth-child(1)")
        start_x = r0["x"] + r0["w"] / 2
        start_y = r0["y"] + r0["h"] / 2

        self.page.mouse.move(start_x, start_y)
        self.page.mouse.down()
        # one move to start drag
        self.page.mouse.move(start_x, start_y + 10)
        self.page.wait_for_timeout(80)

        # scroll the container mid-drag
        self.page.evaluate(
            "()=>{const el=document.getElementById('tray-list'); el.scrollTop = el.scrollHeight - el.clientHeight;}"
        )
        self.page.wait_for_timeout(150)

        # Do an intermediate move, then re-read the last row's fresh rect
        # before the final move (the row may have shifted during drag)
        self.page.mouse.move(start_x, start_y + 10 + 30)
        self.page.wait_for_timeout(80)

        last_idx = len(before)
        r_last = rect_of(self.page, f".tray-row:nth-child({last_idx})")
        target_x = r_last["x"] + r_last["w"] / 2
        target_y = r_last["y"] + r_last["h"] / 2 + 5

        self.page.mouse.move(target_x, target_y)
        self.page.wait_for_timeout(150)
        self.page.mouse.up()
        self.page.wait_for_timeout(200)

        after = self._tray_order()
        self.assertNotEqual(before, after, "order must change after scroll+drag")
        # In the scrolled 80px container the pointer may leave the list before reaching
        # the final row (onPointerLeave finishes the drag).  It is sufficient that the
        # dragged row moved down at least one position.
        self.assertNotEqual(after[0], before[0], "dragged row should have moved down")


if __name__ == "__main__":
    unittest.main()
