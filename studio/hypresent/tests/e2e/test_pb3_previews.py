import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest, time
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8803
MOUNT_CAP = 24


class PB3PreviewsTests(unittest.TestCase):
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
        self.page = self.browser.new_page(viewport={"width": 800, "height": 400})
        self.page.goto(self.base + "/app/builder.html")

    def tearDown(self):
        self.page.close()

    def _load_library(self):
        B.pick_library_ui(self.page, self.base, B.e2e_lib_path())

    def _load_overcap_library(self):
        overcap = B.make_overcap_library(min_slides=MOUNT_CAP + 6)
        B.pick_library_ui(self.page, self.base, overcap)

    def test_io_gated_mount(self):
        self._load_library()
        total = self.page.locator(".slide-card").count()
        self.assertGreater(total, 0, "fixture should have slides")

        mounted = self.page.eval_on_selector_all(
            ".slide-thumb-wrapper iframe",
            "els => els.filter(e => e.srcdoc && e.srcdoc.length > 0).length",
        )
        self.assertLess(
            mounted, total,
            f"not all {total} iframes should be mounted initially (got {mounted})",
        )

        cards = self.page.locator(".slide-card").all()
        # Scroll last card into view
        last_card = cards[-1]
        last_card.scroll_into_view_if_needed()
        self.page.wait_for_timeout(300)

        iframe = last_card.locator(".slide-thumb-wrapper iframe")
        self.page.wait_for_function(
            """(el) => el.srcdoc && el.srcdoc.length > 0""",
            arg=iframe.element_handle(),
            timeout=5000,
        )
        mounted_attr = iframe.evaluate("e => e.dataset.mounted")
        self.assertEqual(mounted_attr, "true", "scrolled card iframe should be mounted")

        # N>=2: repeat for second card lower in the list
        if len(cards) >= 2:
            second_card = cards[-2]
            second_card.scroll_into_view_if_needed()
            self.page.wait_for_timeout(300)
            iframe2 = second_card.locator(".slide-thumb-wrapper iframe")
            self.page.wait_for_function(
                """(el) => el.srcdoc && el.srcdoc.length > 0""",
                arg=iframe2.element_handle(),
                timeout=5000,
            )
            mounted_attr2 = iframe2.evaluate("e => e.dataset.mounted")
            self.assertEqual(mounted_attr2, "true", "second scrolled card iframe should be mounted")

    def test_renderable_unit_no_runtime(self):
        self._load_library()
        cards = self.page.locator(".slide-card").all()
        self.assertGreater(len(cards), 0, "fixture should have slides")

        # Mount the last card by scrolling it into view
        last_card = cards[-1]
        last_card.scroll_into_view_if_needed()
        self.page.wait_for_timeout(300)
        iframe = last_card.locator(".slide-thumb-wrapper iframe")
        self.page.wait_for_function(
            """(el) => el.srcdoc && el.srcdoc.length > 0""",
            arg=iframe.element_handle(),
            timeout=5000,
        )
        srcdoc = iframe.evaluate("e => e.srcdoc || ''")
        self.assertIn(".slide", srcdoc, "srcdoc should contain .slide class")
        self.assertNotIn(
            "runtime-main.js", srcdoc,
            "preview srcdoc must not contain runtime-main.js",
        )

    def test_mount_cap(self):
        self._load_overcap_library()
        total = self.page.locator(".slide-card").count()
        self.assertGreaterEqual(
            total, MOUNT_CAP + 6,
            f"over-cap library should have >= {MOUNT_CAP + 6} slides (got {total})",
        )
        # Scroll through all cards and count mounted iframes
        cards = self.page.locator(".slide-card").all()
        max_mounted = 0
        for card in cards:
            card.scroll_into_view_if_needed()
            self.page.wait_for_timeout(150)
            mounted = self.page.eval_on_selector_all(
                ".slide-thumb-wrapper iframe",
                "els => els.filter(e => e.srcdoc && e.srcdoc.length > 0).length",
            )
            max_mounted = max(max_mounted, mounted)
        self.assertLessEqual(
            max_mounted, MOUNT_CAP,
            f"mounted iframes ({max_mounted}) should never exceed MOUNT_CAP ({MOUNT_CAP})",
        )

    def test_no_inview_blanking(self):
        self._load_overcap_library()
        total = self.page.locator(".slide-card").count()
        self.assertGreaterEqual(
            total, MOUNT_CAP + 6,
            f"over-cap library should have >= {MOUNT_CAP + 6} slides (got {total})",
        )

        cards = self.page.locator(".slide-card").all()
        steps = min(3, len(cards))
        for i in range(steps):
            card = cards[i * len(cards) // steps]
            card.scroll_into_view_if_needed()
            # Wait until every currently-in-view iframe has non-empty srcdoc
            self.page.wait_for_function(
                """() => {
                    const iframes = document.querySelectorAll('.slide-thumb-wrapper iframe');
                    const vh = window.innerHeight;
                    const vw = window.innerWidth;
                    let inViewCount = 0;
                    for (const e of iframes) {
                        const r = e.getBoundingClientRect();
                        const inView = r.top < vh && r.bottom > 0 && r.left < vw && r.right > 0;
                        if (inView) {
                            inViewCount++;
                            if (!e.srcdoc || e.srcdoc.length === 0) return false;
                        }
                    }
                    return inViewCount > 0;
                }""",
                timeout=10000,
            )

            in_view_data = self.page.eval_on_selector_all(
                ".slide-thumb-wrapper iframe",
                """els => els.map(e => {
                    const r = e.getBoundingClientRect();
                    const vh = window.innerHeight;
                    const vw = window.innerWidth;
                    const inView = r.top < vh && r.bottom > 0 && r.left < vw && r.right > 0;
                    return {inView, hasSrcdoc: !!(e.srcdoc && e.srcdoc.length > 0)};
                })""",
            )
            in_view = [d for d in in_view_data if d["inView"]]
            self.assertGreater(len(in_view), 0, f"step {i}: in-view set should be non-empty")
            for d in in_view:
                self.assertTrue(
                    d["hasSrcdoc"],
                    "every in-view iframe must have non-empty srcdoc",
                )

    def test_scale_applied(self):
        self._load_library()
        wrapper = self.page.locator(".slide-thumb-wrapper").first
        overflow = wrapper.evaluate("e => window.getComputedStyle(e).overflow")
        self.assertEqual(overflow, "hidden", "thumb wrapper should have overflow:hidden")

        iframe = wrapper.locator("iframe").first
        # Use CSS Typed OM when available to preserve authored function name
        transform = iframe.evaluate("""e => {
            if (e.computedStyleMap) {
                const t = e.computedStyleMap().get('transform');
                if (t && t.toString) return t.toString();
            }
            return window.getComputedStyle(e).transform;
        }""")
        self.assertIn("scale(", transform, f"iframe transform should include scale(: got {transform}")


if __name__ == "__main__":
    unittest.main()
