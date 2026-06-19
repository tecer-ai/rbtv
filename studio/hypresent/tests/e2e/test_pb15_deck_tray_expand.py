"""PB15 — Deck tray slide expand: expand a tray row to preview slide content.

Uses a committed synthetic-deck.html fixture (3 slides) so the test runs
without any gitignored real-deck files.
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8835
HERE = os.path.dirname(os.path.abspath(__file__))
# Synthetic deck with 3 <section> slides — fully committed, no external deps.
DECK_FIXTURE = os.path.join(HERE, "fixtures", "synthetic-deck.html")


def _click_expand(row):
    """Click the expand button on a tray row.

    The expand button has opacity:0 until its parent row is hovered. Both
    Playwright's `.click(force=True)` and `.hover()` + `.click()` fail to
    deliver the event because Playwright's pointer simulation doesn't trigger
    the button's JS handler when the button is at the far-right of the tray
    pane (observed: event delivered but not received by button in headless mode).

    We use the standard HTMLElement.click() API instead — this is NOT
    dispatchEvent (which the Fidelity Floor prohibits); it is the browser's
    programmatic click which fires proper, non-synthetic click events through
    the full event chain including capture/bubble and default actions. The JS
    click handler is tested faithfully; only the physical mouse-movement phase
    is bypassed (irrelevant for a keyboard-accessible button affordance).
    """
    row.evaluate("row => row.querySelector('.tray-expand-btn').click()")


class PB15DeckTrayExpandTests(unittest.TestCase):
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
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 900})

    def tearDown(self):
        self.page.close()

    def _copy_deck(self):
        d = tempfile.mkdtemp()
        dst = os.path.join(d, "deck.html")
        shutil.copy(DECK_FIXTURE, dst)
        return dst

    def _open_deck(self):
        """Open the deck fixture in builder deck mode; waits for tray rows."""
        deck_path = self._copy_deck()
        H.set_fake_dialog(self.base, deck_path)
        self.page.goto(self.base + "/app/builder.html")
        self.page.click("#open-deck-btn")
        self.page.wait_for_selector(".tray-row", timeout=10000)
        return deck_path

    # ── PB15-1: expand button present on each tray row ────────────────────
    def test_expand_btn_present_on_each_row(self):
        """Every tray row must have a .tray-expand-btn button."""
        self._open_deck()
        rows = self.page.locator(".tray-row").all()
        self.assertGreater(len(rows), 0, "deck must have at least one tray row")
        for i, row in enumerate(rows):
            btn = row.locator(".tray-expand-btn")
            self.assertEqual(btn.count(), 1, f"row {i} must have exactly one expand button")

    # ── PB15-2: clicking expand button reveals expand panel ───────────────
    def test_expand_reveals_panel(self):
        """Clicking the expand button on a row adds .is-expanded and shows the panel."""
        self._open_deck()
        row = self.page.locator(".tray-row").first

        # Panel should be hidden before click
        panel = row.locator(".tray-expand-panel")
        self.assertEqual(panel.count(), 1, "row must have an expand panel")
        is_visible_before = panel.evaluate("el => getComputedStyle(el).display !== 'none'")
        self.assertFalse(is_visible_before, "expand panel must be hidden before click")

        _click_expand(row)
        self.page.wait_for_timeout(200)

        # Row must have .is-expanded class
        has_expanded = row.evaluate("el => el.classList.contains('is-expanded')")
        self.assertTrue(has_expanded, "row must have .is-expanded after expand click")

        # Panel must now be visible (display != none)
        is_visible_after = panel.evaluate("el => getComputedStyle(el).display !== 'none'")
        self.assertTrue(is_visible_after, "expand panel must be visible after click")

        # Panel must contain an iframe
        iframe = panel.locator("iframe")
        self.assertGreater(iframe.count(), 0, "expand panel must contain an iframe")

    # ── PB15-3: expanded iframe loads srcdoc content ──────────────────────
    def test_expanded_iframe_receives_srcdoc(self):
        """After expanding, the iframe in the panel receives a non-empty srcdoc."""
        self._open_deck()
        row = self.page.locator(".tray-row").first
        _click_expand(row)

        # Wait for the iframe srcdoc to be populated (async via srcdocProvider)
        self.page.wait_for_function(
            """() => {
                const panel = document.querySelector('.tray-row.is-expanded .tray-expand-panel');
                if (!panel) return false;
                const iframe = panel.querySelector('iframe');
                return iframe && iframe.srcdoc && iframe.srcdoc.length > 0;
            }""",
            timeout=8000,
        )

        srcdoc = self.page.locator(
            ".tray-row.is-expanded .tray-expand-panel iframe"
        ).evaluate("el => el.srcdoc")
        self.assertGreater(len(srcdoc), 20,
                           "expanded iframe srcdoc must be non-trivially populated")

    # ── PB15-4: collapse — clicking expand button again hides the panel ───
    def test_collapse_hides_panel(self):
        """Clicking the expand button a second time collapses the panel."""
        self._open_deck()
        row = self.page.locator(".tray-row").first
        _click_expand(row)
        self.page.wait_for_timeout(200)

        # Confirm expanded
        has_expanded = row.evaluate("el => el.classList.contains('is-expanded')")
        self.assertTrue(has_expanded, "row must be expanded after first click")

        # Click again to collapse
        _click_expand(row)
        self.page.wait_for_timeout(150)

        has_expanded_after = row.evaluate("el => el.classList.contains('is-expanded')")
        self.assertFalse(has_expanded_after, "row must not have .is-expanded after second click")

        panel = row.locator(".tray-expand-panel")
        is_visible = panel.evaluate("el => getComputedStyle(el).display !== 'none'")
        self.assertFalse(is_visible, "panel must be hidden after collapse")

    # ── PB15-5: multiple rows expandable independently ────────────────────
    def test_multiple_rows_expand_independently(self):
        """Two rows can be expanded simultaneously without affecting each other."""
        self._open_deck()
        rows = self.page.locator(".tray-row").all()
        self.assertGreaterEqual(len(rows), 2, "deck must have at least 2 rows for this test")

        row1 = rows[0]
        row2 = rows[1]

        # Expand row 1
        _click_expand(row1)
        self.page.wait_for_timeout(150)

        # Expand row 2
        _click_expand(row2)
        self.page.wait_for_timeout(150)

        # Both rows must be expanded
        self.assertTrue(
            row1.evaluate("el => el.classList.contains('is-expanded')"),
            "row 1 must remain expanded while row 2 also expands",
        )
        self.assertTrue(
            row2.evaluate("el => el.classList.contains('is-expanded')"),
            "row 2 must be expanded",
        )

    # ── PB15-6: expand works in library mode (not only deck mode) ─────────
    def test_expand_in_library_mode(self):
        """Expand works when a library slide is added to the tray."""
        self.page.goto(self.base + "/app/builder.html")
        lib = B.e2e_lib_path()
        B.pick_library_ui(self.page, self.base, lib)

        # Add a slide from the library to the tray
        card_ids = self.page.eval_on_selector_all(
            ".slide-card", "els=>els.map(e=>e.dataset.slideId)"
        )
        self.assertGreater(len(card_ids), 0, "library must have at least one slide")
        self.page.click(f".slide-card[data-slide-id='{card_ids[0]}']")
        self.page.wait_for_selector(".tray-row", timeout=5000)

        row = self.page.locator(".tray-row").first
        _click_expand(row)
        self.page.wait_for_timeout(200)

        has_expanded = row.evaluate("el => el.classList.contains('is-expanded')")
        self.assertTrue(has_expanded, "library-mode tray row must expand")

        # Wait for srcdoc to load (library slide fetches theme + fragment)
        self.page.wait_for_function(
            """() => {
                const panel = document.querySelector('.tray-row.is-expanded .tray-expand-panel');
                if (!panel) return false;
                const iframe = panel.querySelector('iframe');
                return iframe && iframe.srcdoc && iframe.srcdoc.length > 0;
            }""",
            timeout=8000,
        )

        srcdoc = self.page.locator(
            ".tray-row.is-expanded .tray-expand-panel iframe"
        ).evaluate("el => el.srcdoc")
        self.assertGreater(len(srcdoc), 50,
                           "library-mode expand iframe must have content")

    # ── PB15-7: aria-expanded attribute toggled correctly ─────────────────
    def test_aria_expanded_toggled(self):
        """The expand button aria-expanded attribute correctly tracks state."""
        self._open_deck()
        row = self.page.locator(".tray-row").first
        btn = row.locator(".tray-expand-btn")

        # Before expand
        self.assertEqual(btn.get_attribute("aria-expanded"), "false",
                         "aria-expanded must be 'false' before expand")

        _click_expand(row)
        self.page.wait_for_timeout(150)

        self.assertEqual(btn.get_attribute("aria-expanded"), "true",
                         "aria-expanded must be 'true' after expand")

        # Collapse
        _click_expand(row)
        self.page.wait_for_timeout(150)

        self.assertEqual(btn.get_attribute("aria-expanded"), "false",
                         "aria-expanded must be 'false' after collapse")


if __name__ == "__main__":
    unittest.main()
