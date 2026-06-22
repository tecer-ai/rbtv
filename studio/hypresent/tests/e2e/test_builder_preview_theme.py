"""e2e regression — builder previews layer base theme.css + a named role-token
overlay, so selecting a pure-skin (contract-2.0) theme keeps full slide layout
instead of blanking every slide.

Reproduces the bug where buildSrcdoc injected the named theme ALONE: a 2.0 theme
is pure skin (role :root tokens, no structural selectors), so without the base
theme.css underneath, every .slide collapsed (no width/height) — a blank box. The
fix fetches base + overlay and injects base-then-overlay, matching the assembled
deck's inlined base + <style data-theme> overlay.

Covered surfaces (both funnel through getSlideSrcdoc): the browse-pane thumbnail
previews and the full-size in-place stage inspector.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8841
# themes/skin.css overrides --fg to this hex (pure-skin overlay, no structural CSS).
SKIN_MARKER = "#E74C3C"
# A structural rule that lives ONLY in the base theme.css (the named overlay has none).
BASE_MARKER = "1280px"


class BuilderPreviewThemeTests(unittest.TestCase):
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
        B.pick_library_ui(self.page, self.base, B.e2e_lib_path())

    def tearDown(self):
        self.page.close()

    def _select_theme(self, name):
        """Pick a theme in the builder Theme dropdown (real change event → rerender)."""
        self.page.wait_for_function(
            """(name) => {
                const sel = document.getElementById('theme-select');
                return sel && Array.from(sel.options).some(o => o.value === name);
            }""",
            arg=name,
            timeout=10000,
        )
        self.page.select_option("#theme-select", name)

    def _first_preview_with(self, marker):
        """Wait until a browse-pane preview iframe whose srcdoc contains `marker` has
        rendered its .slide, then return its measured geometry + srcdoc facts."""
        self.page.locator(".slide-card").first.scroll_into_view_if_needed()
        self.page.wait_for_function(
            """(marker) => {
                const frames = Array.from(document.querySelectorAll('.slide-thumb-wrapper iframe'));
                for (const f of frames) {
                    if (!f.srcdoc || !f.srcdoc.includes(marker)) continue;
                    const doc = f.contentDocument;
                    const slide = doc && doc.querySelector('.slide');
                    if (slide && slide.offsetHeight > 0) return true;
                }
                return false;
            }""",
            arg=marker,
            timeout=10000,
        )
        return self.page.evaluate(
            """(marker) => {
                const frames = Array.from(document.querySelectorAll('.slide-thumb-wrapper iframe'));
                for (const f of frames) {
                    if (!f.srcdoc || !f.srcdoc.includes(marker)) continue;
                    const doc = f.contentDocument;
                    const slide = doc && doc.querySelector('.slide');
                    if (slide && slide.offsetHeight > 0) {
                        return {
                            w: slide.offsetWidth,
                            h: slide.offsetHeight,
                            styleCount: (f.srcdoc.match(/<style>/g) || []).length,
                            baseIdx: f.srcdoc.indexOf('1280px'),
                            overlayIdx: f.srcdoc.indexOf('E74C3C'),
                        };
                    }
                }
                return null;
            }""",
            marker,
        )

    def test_named_theme_preview_keeps_layout(self):
        """Criterion 1: a named (2.0) theme renders full-size slides, layered base+overlay."""
        self._select_theme("skin")
        g = self._first_preview_with(SKIN_MARKER)
        self.assertIsNotNone(g, "a preview iframe carrying the skin overlay should render")
        # Layout survived: the .slide is full-size (base theme.css layered in), not collapsed.
        self.assertGreaterEqual(g["h"], 700, f"slide height collapsed — layout blanked (got {g['h']})")
        self.assertGreaterEqual(g["w"], 1260, f"slide width collapsed — layout blanked (got {g['w']})")
        # Both layers present and ordered: base structural css BEFORE the named overlay.
        self.assertEqual(g["styleCount"], 2, "named-theme preview must inject base + overlay as two <style> blocks")
        self.assertGreater(g["baseIdx"], -1, "base theme.css structural css must be present")
        self.assertGreater(g["overlayIdx"], -1, "named overlay css must be present")
        self.assertLess(g["baseIdx"], g["overlayIdx"], "base must be injected BEFORE the overlay (overlay wins the cascade)")

    def test_named_theme_stage_keeps_layout(self):
        """Criterion 2: the full-size stage inspector also keeps layout under a named theme."""
        self._select_theme("skin")
        ids = self.page.eval_on_selector_all(".slide-card", "els=>els.map(e=>e.dataset.slideId)")
        self.assertTrue(len(ids) > 0, "fixture should have slides")
        card = self.page.locator(f".slide-card[data-slide-id='{ids[0]}']")
        card.hover()
        card.locator(".s-expand").click()
        self.page.wait_for_selector(".slide-stage.is-open", timeout=5000)
        self.page.wait_for_function(
            """() => {
                const f = document.querySelector('.slide-stage iframe');
                const doc = f && f.contentDocument;
                const slide = doc && doc.querySelector('.slide');
                return slide && slide.offsetHeight > 0;
            }""",
            timeout=10000,
        )
        geo = self.page.evaluate(
            """() => {
                const f = document.querySelector('.slide-stage iframe');
                const slide = f.contentDocument.querySelector('.slide');
                return {w: slide.offsetWidth, h: slide.offsetHeight, srcdoc: f.srcdoc};
            }"""
        )
        self.assertGreaterEqual(geo["h"], 700, f"stage slide height collapsed — layout blanked (got {geo['h']})")
        self.assertGreaterEqual(geo["w"], 1260, f"stage slide width collapsed — layout blanked (got {geo['w']})")
        self.assertIn("E74C3C", geo["srcdoc"], "stage srcdoc must carry the named overlay")
        self.assertIn(BASE_MARKER, geo["srcdoc"], "stage srcdoc must carry the base structural css")

    def test_default_theme_preview_no_regression(self):
        """Criterion 3: the Default theme still previews full-size, with a single base layer."""
        self._select_theme("default")
        g = self._first_preview_with(BASE_MARKER)
        self.assertIsNotNone(g, "a default preview iframe should render")
        self.assertGreaterEqual(g["h"], 700, f"default slide height collapsed (got {g['h']})")
        self.assertGreaterEqual(g["w"], 1260, f"default slide width collapsed (got {g['w']})")
        self.assertEqual(g["styleCount"], 1, "default preview must inject the base theme.css as a single <style> block")


if __name__ == "__main__":
    unittest.main()
