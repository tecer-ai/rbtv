"""e2e test — builder srcdoc previews carry a <base> tag so relative assets/ render.

Guard: this test MUST FAIL against the old (no-<base>) behavior and pass after the fix.
"""
import os
import sys
import struct
import zlib
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8820

# ---------------------------------------------------------------------------
# Minimal 1×1 red PNG (stdlib only — no Pillow)
# ---------------------------------------------------------------------------

def _make_1x1_red_png() -> bytes:
    """Return the bytes of a valid 1×1 red (255,0,0) PNG."""
    def _png_chunk(tag: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return length + tag + data + crc

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    # IDAT: filter byte 0x00, then R G B = 255 0 0
    raw_row = b"\x00\xff\x00\x00"
    idat = _png_chunk(b"IDAT", zlib.compress(raw_row, 9))
    iend = _png_chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


# ---------------------------------------------------------------------------
# Synthetic deck fixture builder
# ---------------------------------------------------------------------------

_DECK_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ margin: 0; }}
.slide {{ width: 1200px; padding: 40px; box-sizing: border-box; }}
</style>
</head>
<body>
<section class="slide" id="slide-1">
  <h1>Slide with relative asset</h1>
  <img id="test-asset-img" src="assets/test-img.png" alt="test asset" style="width:100px;height:100px;">
</section>
<section class="slide" id="slide-2">
  <h1>Slide two — no asset</h1>
  <p>Plain text only.</p>
</section>
</body>
</html>
"""


def _make_deck_with_assets() -> str:
    """Create a temp dir containing deck.html + assets/test-img.png; return deck path."""
    d = tempfile.mkdtemp()
    assets_dir = os.path.join(d, "assets")
    os.makedirs(assets_dir)
    png_path = os.path.join(assets_dir, "test-img.png")
    with open(png_path, "wb") as f:
        f.write(_make_1x1_red_png())
    deck_path = os.path.join(d, "deck.html")
    with open(deck_path, "w", encoding="utf-8") as f:
        f.write(_DECK_TEMPLATE)
    return deck_path


def _make_deck_missing_assets() -> str:
    """Create a temp dir with deck.html referencing assets/missing.png — no actual file."""
    d = tempfile.mkdtemp()
    # Write a deck that references an asset that does NOT exist
    html = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>body{margin:0;}.slide{width:1200px;padding:40px;}</style></head>
<body>
<section class="slide" id="slide-1">
  <img id="missing-asset-img" src="assets/missing.png" alt="missing">
</section>
</body>
</html>
"""
    deck_path = os.path.join(d, "deck.html")
    with open(deck_path, "w", encoding="utf-8") as f:
        f.write(html)
    return deck_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_doc_root_for_deck(base: str, deck_path: str):
    """Call /api/open to point the server's /doc/ route at the deck's directory.

    This simulates what a proper builder-mode deck-open would do if
    handle_deck_load called set_doc_root — see open_questions in the done-gate
    sheet.  The test seam is this explicit call in setUp; it does NOT stub the
    builder's actual gesture (the fake dialog + click still happen normally).
    """
    H.post_json(base, "/api/open", {"path": deck_path})


class BuilderPreviewAssetsTests(unittest.TestCase):
    """Test that builder tray srcdoc iframes carry a resolving <base> tag."""

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

    # ── helper ──────────────────────────────────────────────────────────────

    def _open_deck_in_builder(self, deck_path: str):
        """Navigate to the builder and open a deck via the fake dialog."""
        H.set_fake_dialog(self.base, deck_path)
        self.page.goto(self.base + "/app/builder.html")
        self.page.click("#open-deck-btn")
        self.page.wait_for_selector(".tray-row", timeout=10000)

    # ── BPA-1: srcdoc carries <base href> pointing at /doc/ ─────────────────

    def test_tray_srcdoc_has_base_tag(self):
        """Each tray iframe srcdoc must contain a <base href> element
        resolving to the server's /doc/ route.

        This test FAILS against the old (no-<base>) behavior."""
        deck_path = _make_deck_with_assets()
        # Set doc_root so /doc/ serves the deck's directory.
        _set_doc_root_for_deck(self.base, deck_path)

        self._open_deck_in_builder(deck_path)

        rows = self.page.locator(".tray-row").all()
        self.assertGreater(len(rows), 0, "tray must have at least one row")

        for i, row in enumerate(rows):
            # Target the thumbnail iframe specifically — each row now also
            # carries a lazy-load expand-panel preview iframe (.tray-expand-preview),
            # so a bare row.locator("iframe") matches 2 and trips strict mode.
            iframe = row.locator(".t-thumb iframe")
            # Wait for srcdoc to be populated
            self.page.wait_for_function(
                "(el) => el.srcdoc && el.srcdoc.includes('<base')",
                arg=iframe.element_handle(),
                timeout=5000,
            )
            srcdoc = iframe.get_attribute("srcdoc")
            self.assertIsNotNone(srcdoc, f"row {i + 1} must have srcdoc")
            self.assertIn(
                "<base",
                srcdoc,
                f"row {i + 1} srcdoc must contain a <base> tag; got no <base> in: "
                + srcdoc[:200],
            )
            self.assertIn(
                "/doc/",
                srcdoc,
                f"row {i + 1} <base> href must reference /doc/; srcdoc head: "
                + srcdoc[:200],
            )

    # ── BPA-2: relative asset renders (naturalWidth > 0) ────────────────────

    def test_relative_asset_renders_in_tray(self):
        """With doc_root pointing at the deck's directory, an assets/ image
        referenced by a deck section must render inside the tray iframe
        (naturalWidth > 0).

        This test FAILS against the old (no-<base>) behavior because without
        <base>, assets/test-img.png resolves to /app/assets/test-img.png
        (404), leaving naturalWidth == 0."""
        deck_path = _make_deck_with_assets()
        _set_doc_root_for_deck(self.base, deck_path)

        self._open_deck_in_builder(deck_path)

        rows = self.page.locator(".tray-row").all()
        self.assertGreater(len(rows), 0, "deck must have tray rows")

        # The first section has #test-asset-img — find it in the first tray's
        # thumbnail iframe (.t-thumb iframe; the row also has an expand-panel iframe).
        first_row = rows[0]
        iframe = first_row.locator(".t-thumb iframe")

        # Wait for srcdoc to be populated with the section content.
        self.page.wait_for_function(
            "(el) => el.srcdoc && el.srcdoc.includes('test-asset-img')",
            arg=iframe.element_handle(),
            timeout=8000,
        )

        # Wait for the image inside the iframe to load (or timeout waiting).
        self.page.wait_for_timeout(1500)

        natural_width = self.page.evaluate(
            """(iframeEl) => {
                const doc = iframeEl.contentDocument;
                if (!doc) return -1;
                const img = doc.getElementById('test-asset-img');
                if (!img) return -2;
                return img.naturalWidth;
            }""",
            iframe.element_handle(),
        )

        self.assertGreater(
            natural_width,
            0,
            f"#test-asset-img naturalWidth must be > 0 with <base> fix; got {natural_width}. "
            "This fails pre-fix because assets/ resolves to /app/assets/ (404).",
        )

    # ── BPA-3: missing asset shows normal broken-image state (no crash) ──────

    def test_missing_asset_shows_broken_state(self):
        """A deck referencing a non-existent assets/missing.png must show the
        normal missing-image state — no crash, no fabricated image."""
        deck_path = _make_deck_missing_assets()
        _set_doc_root_for_deck(self.base, deck_path)

        self._open_deck_in_builder(deck_path)

        rows = self.page.locator(".tray-row").all()
        self.assertGreater(len(rows), 0, "deck must have tray rows")

        first_row = rows[0]
        iframe = first_row.locator(".t-thumb iframe")

        self.page.wait_for_function(
            "(el) => el.srcdoc && el.srcdoc.includes('missing-asset-img')",
            arg=iframe.element_handle(),
            timeout=8000,
        )
        self.page.wait_for_timeout(1000)

        result = self.page.evaluate(
            """(iframeEl) => {
                const doc = iframeEl.contentDocument;
                if (!doc) return {found: false, naturalWidth: -1, complete: false};
                const img = doc.getElementById('missing-asset-img');
                if (!img) return {found: false, naturalWidth: -1, complete: false};
                return {found: true, naturalWidth: img.naturalWidth, complete: img.complete};
            }""",
            iframe.element_handle(),
        )

        self.assertTrue(result["found"], "missing-asset-img element must be present in DOM")
        self.assertEqual(
            result["naturalWidth"],
            0,
            f"missing asset must have naturalWidth==0 (broken image); got {result['naturalWidth']}",
        )
        # No JavaScript error should have been thrown — verify no console error
        # by checking the page is still functional (tray row is still there).
        rows_after = self.page.locator(".tray-row").all()
        self.assertGreater(len(rows_after), 0, "page must not crash on missing asset")


class BuilderDeckLoadDocRootTests(unittest.TestCase):
    """Test that opening a deck via the builder deck-load path (no /api/open)
    sets the server /doc/ root so relative assets/ images render.

    Guard: BPA-4 MUST FAIL against the pre-fix behavior (before set_doc_root
    is called in server.py's /api/deck-load branch).
    """

    @classmethod
    def setUpClass(cls):
        cls.proc, cls.base = H.start_server(8821, test_dialog=True)
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

    def _open_deck_in_builder_only(self, deck_path: str):
        """Navigate to the builder and open a deck via the fake dialog.

        Critically: does NOT call /api/open or _set_doc_root_for_deck.
        The only doc-root setter must be the /api/deck-load handler itself.
        """
        H.set_fake_dialog(self.base, deck_path)
        self.page.goto(self.base + "/app/builder.html")
        self.page.click("#open-deck-btn")
        self.page.wait_for_selector(".tray-row", timeout=10000)

    # ── BPA-4: builder-first open sets doc-root via deck-load ───────────────

    def test_relative_asset_renders_via_deck_load(self):
        """After opening a deck via the builder deck-load path WITHOUT any
        /api/open call, relative assets/ images must render (naturalWidth > 0).

        This test FAILS against the pre-fix behavior: before the fix,
        /api/deck-load does not call set_doc_root, so _doc_root stays None
        and the /doc/ route returns 404 for all asset requests.
        """
        deck_path = _make_deck_with_assets()
        # NOTE: no _set_doc_root_for_deck call — that is the whole point.
        # The fix must make /api/deck-load set the doc root.
        self._open_deck_in_builder_only(deck_path)

        rows = self.page.locator(".tray-row").all()
        self.assertGreater(len(rows), 0, "deck must have tray rows")

        first_row = rows[0]
        iframe = first_row.locator(".t-thumb iframe")

        # Wait for srcdoc to be populated with the section content.
        self.page.wait_for_function(
            "(el) => el.srcdoc && el.srcdoc.includes('test-asset-img')",
            arg=iframe.element_handle(),
            timeout=8000,
        )

        # Allow image load time.
        self.page.wait_for_timeout(1500)

        natural_width = self.page.evaluate(
            """(iframeEl) => {
                const doc = iframeEl.contentDocument;
                if (!doc) return -1;
                const img = doc.getElementById('test-asset-img');
                if (!img) return -2;
                return img.naturalWidth;
            }""",
            iframe.element_handle(),
        )

        self.assertGreater(
            natural_width,
            0,
            f"#test-asset-img naturalWidth must be > 0 after builder-first deck-load; "
            f"got {natural_width}. Pre-fix: /api/deck-load never called set_doc_root, "
            f"so /doc/ returned 404 and naturalWidth was 0.",
        )


if __name__ == "__main__":
    unittest.main()
