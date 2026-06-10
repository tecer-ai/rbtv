import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8812
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DECK_FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction-test-v3.html")
EDITOR_BASE = "/app/"
BUILDER_BASE = "/app/builder.html"


class PB12BridgeTests(unittest.TestCase):
    """Save-and-switch bridge, both directions (spec Test Plan rows 1-4)."""

    @classmethod
    def setUpClass(cls):
        cls.proc, cls.base = H.start_server(PORT, test_dialog=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=False)

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
        """Return the absolute path of a temp copy of the test deck."""
        d = tempfile.mkdtemp()
        dst = os.path.join(d, "deck.html")
        shutil.copy(DECK_FIXTURE, dst)
        return dst

    def _open_deck_in_builder(self, deck_path):
        """Open a deck in the builder via the dialog and wait for tray to populate."""
        H.set_fake_dialog(self.base, deck_path)
        self.page.goto(self.base + BUILDER_BASE)
        self.page.click("#open-deck-btn")
        self.page.wait_for_selector(".tray-row", timeout=10000)

    def _tray_count(self):
        return self.page.eval_on_selector_all(".tray-row", "els=>els.length")

    # ── PB12-1: Builder→editor crossing ───────────────────────────────────
    def test_builder_to_editor_crossing(self):
        """Spec row 1: Switch to editor writes new file, editor opens it with doc chip."""
        deck_path = self._copy_deck()
        self._open_deck_in_builder(deck_path)
        count_before = self._tray_count()
        self.assertGreater(count_before, 0, "tray should have slides")

        # Inject the save dialog to return a temp path
        save_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(save_dir, ignore_errors=True))
        save_path = os.path.join(save_dir, "restructured.html")
        H.set_fake_dialog(self.base, save_path)

        # Click "Switch to editor"
        self.page.click("#switch-to-editor-btn")

        # Wait for navigation to editor with ?file=
        self.page.wait_for_function(
            "() => location.pathname === '/app/' && location.search.includes('file=')",
            timeout=10000,
        )
        self.assertIn("/app/?file=", self.page.url)

        # Verify the file exists on disk
        file_param = self.page.evaluate(
            "() => new URLSearchParams(location.search).get('file')"
        )
        self.assertIsNotNone(file_param)
        self.assertTrue(
            os.path.exists(file_param),
            f"crossing deck should exist on disk: {file_param}"
        )

        # Doc chip should show the new name
        self.page.wait_for_selector("#doc-chip", timeout=5000)
        doc_name = self.page.locator("#doc-name").text_content()
        self.assertEqual(doc_name, "restructured.html", "doc chip should show the new file name")

    # ── PB12-2: Editor→builder crossing ───────────────────────────────────
    def test_editor_to_builder_crossing(self):
        """Spec row 2: Open in builder writes new file, builder opens it with tray filled."""
        deck_path = self._copy_deck()
        # First open in the builder to create a copy, then open that copy in the editor
        self._open_deck_in_builder(deck_path)

        # Save a copy to a temp dir for the editor to open
        save_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(save_dir, ignore_errors=True))
        editor_deck_path = os.path.join(save_dir, "editor-deck.html")
        H.set_fake_dialog(self.base, editor_deck_path)
        self.page.click("#save-new-btn")
        self.page.wait_for_selector(".shell-status.success", timeout=10000)

        # Now open the saved copy in the editor
        self.page.goto(self.base + EDITOR_BASE)
        H.set_fake_dialog(self.base, editor_deck_path)
        self.page.click("#open-btn")
        self.page.wait_for_function(
            "() => !document.getElementById('doc-chip').hidden",
            timeout=10000,
        )

        # "Open in builder" enables only when the runtime emits 'ready' (serialize()
        # will answer) — NOT merely when the doc chip appears. On the dialog-open
        # (#open-btn) path the runtime <script> is injected into the iframe AFTER
        # open resolves, so the doc chip can show while the runtime is still booting.
        # Under suite load that boot lags; clicking on the bridge-exists-but-not-ready
        # window made serialize() time out → no crossing → the old flake. Gate the
        # click on the button becoming enabled — the product's true readiness signal.
        self.page.wait_for_function(
            "() => { const b = document.getElementById('open-in-builder-btn'); "
            "return b && !b.disabled; }",
            timeout=10000,
        )

        # Inject a new save path for the crossing
        crossing_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(crossing_dir, ignore_errors=True))
        crossing_path = os.path.join(crossing_dir, "crossed-to-builder.html")
        H.set_fake_dialog(self.base, crossing_path)

        # Click "Open in builder"
        self.page.click("#open-in-builder-btn")

        # Wait for navigation to builder with ?file=
        self.page.wait_for_function(
            "() => location.pathname === '/app/builder.html' && location.search.includes('file=')",
            timeout=10000,
        )
        self.assertIn("/app/builder.html?file=", self.page.url)

        # Verify the file exists on disk
        file_param = self.page.evaluate(
            "() => new URLSearchParams(location.search).get('file')"
        )
        self.assertIsNotNone(file_param)
        self.assertTrue(
            os.path.exists(file_param),
            f"crossing file should exist on disk: {file_param}"
        )

        # Builder tray should be filled
        self.page.wait_for_selector(".tray-row", timeout=10000)
        tray_count = self._tray_count()
        self.assertGreater(tray_count, 0, "builder tray should have slides after crossing")

    # ── PB12-3: Cancel leaves view intact ─────────────────────────────────
    def test_cancel_builder_to_editor_no_navigation(self):
        """Spec row 3: Cancel in builder→editor dialog leaves builder view intact."""
        deck_path = self._copy_deck()
        self._open_deck_in_builder(deck_path)
        initial_url = self.page.url

        # Set dialog to cancel
        H.set_fake_dialog(self.base, None)
        self.page.click("#switch-to-editor-btn")
        self.page.wait_for_timeout(500)

        # Should still be on builder page
        self.assertIn("builder.html", self.page.url, "should remain on builder after cancel")
        self.assertEqual(self.page.url, initial_url, "URL should be unchanged after cancel")

        # No success status should appear
        status_class = self.page.get_attribute("#builder-status", "class") or ""
        self.assertNotIn("success", status_class, "no success status after cancel")

    def test_cancel_editor_to_builder_no_navigation(self):
        """Spec row 3 (editor side): Cancel in editor→builder dialog leaves editor intact."""
        # Open a deck in the editor
        deck_path = self._copy_deck()

        # First get a copy through the builder save
        self._open_deck_in_builder(deck_path)
        save_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(save_dir, ignore_errors=True))
        editor_deck_path = os.path.join(save_dir, "editor-deck.html")
        H.set_fake_dialog(self.base, editor_deck_path)
        self.page.click("#save-new-btn")
        self.page.wait_for_selector(".shell-status.success", timeout=10000)

        # Open in editor
        self.page.goto(self.base + EDITOR_BASE)
        H.set_fake_dialog(self.base, editor_deck_path)
        self.page.click("#open-btn")
        self.page.wait_for_function(
            "() => !document.getElementById('doc-chip').hidden",
            timeout=10000,
        )
        # Wait for the button to be ENABLED (runtime ready) before clicking. Without
        # this, a click during the bridge-exists-but-runtime-not-ready window lands on
        # a disabled button and no-ops — the test would then "pass" because nothing
        # happened, NOT because the dialog was cancelled (a false pass masking the very
        # crossing this row must exercise). Gating on enabled forces the click to reach
        # the real handler, where the cancelled save-as dialog is what halts navigation.
        self.page.wait_for_function(
            "() => { const b = document.getElementById('open-in-builder-btn'); "
            "return b && !b.disabled; }",
            timeout=10000,
        )
        initial_url = self.page.url

        # Set dialog to cancel
        H.set_fake_dialog(self.base, None)
        self.page.click("#open-in-builder-btn")
        self.page.wait_for_timeout(500)

        # Should still be on editor page
        self.assertIn("/app/", self.page.url, "should remain on editor after cancel")
        self.assertNotIn("builder.html", self.page.url, "should NOT navigate to builder after cancel")

    # ── PB12-4: Round-trip preserves work ─────────────────────────────────
    def test_round_trip_preserves_order(self):
        """Spec row 4: Builder reorder → editor → builder; final tray order matches."""
        deck_path = self._copy_deck()
        self._open_deck_in_builder(deck_path)

        # Reorder: remove slide 2, then duplicate slide 1
        self.page.locator(".tray-row:nth-child(2) .tray-remove").click()
        self.page.wait_for_timeout(150)
        self.page.click(".tray-row:nth-child(1) .tray-duplicate")
        self.page.wait_for_timeout(150)

        count_after_reorder = self._tray_count()
        self.assertEqual(count_after_reorder, 10, "should have 10 slides after reorder")

        # The reorder is: remove slide 2, duplicate slide 1. Slide 1 is the cover
        # section (top-level <section class="… slide--cover">); slide 2 carries the
        # unique text "plataforma inteligente". So the new SECTION ORDER is:
        # cover, cover, slide3, … slide10 — exactly two cover SECTIONS leading the
        # deck and slide-2 content gone. Tray titles are positional ("Slide N") and
        # cannot prove this; the saved-file section sequence is the only honest
        # order-survival signal across the round trip.
        REMOVED_TEXT = "plataforma inteligente"

        # Cross to editor
        save_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(save_dir, ignore_errors=True))
        editor_path = os.path.join(save_dir, "reordered.html")
        H.set_fake_dialog(self.base, editor_path)
        self.page.click("#switch-to-editor-btn")

        # Wait for editor
        self.page.wait_for_function(
            "() => location.pathname === '/app/' && location.search.includes('file=')",
            timeout=10000,
        )
        self.assertIn("/app/?file=", self.page.url)

        # The editor's ?file= arrival opens the doc and builds the bridge
        # ASYNChronously, then enables "Open in builder". Clicking before that
        # completes finds bridge=null → no crossing (correct product behavior) and
        # the next navigation wait times out. Gate on the button becoming enabled —
        # the arrival handler enables it only after openFile + ensureBridge resolve.
        self.page.wait_for_function(
            "() => { const b = document.getElementById('open-in-builder-btn'); "
            "return b && !b.disabled; }",
            timeout=10000,
        )

        # Cross back to builder
        crossing_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(crossing_dir, ignore_errors=True))
        builder_path = os.path.join(crossing_dir, "reopened-in-builder.html")
        H.set_fake_dialog(self.base, builder_path)
        self.page.click("#open-in-builder-btn")

        # Wait for builder
        self.page.wait_for_function(
            "() => location.pathname === '/app/builder.html' && location.search.includes('file=')",
            timeout=10000,
        )

        # Verify tray is filled and order is preserved
        self.page.wait_for_selector(".tray-row", timeout=10000)
        final_count = self._tray_count()
        self.assertEqual(
            final_count, count_after_reorder,
            f"final tray count ({final_count}) should match pre-crossing count ({count_after_reorder})"
        )

        # ORDER survival (not merely count): the final saved file is what the
        # builder re-opened. Split it into its top-level <section> blocks and assert
        # the SPECIFIC reorder survived builder → editor → builder: slide 1 (cover)
        # duplicated into the first two section positions, slide 2 removed, 10
        # sections total. A reset-to-original (cover only at index 0, slide-2 text
        # present) or a scrambled order (covers off positions 0/1) fails these even
        # though the deck still has 10 sections.
        self.assertTrue(
            os.path.exists(builder_path),
            f"final round-trip file should exist on disk: {builder_path}"
        )
        final_html = open(builder_path, encoding="utf-8").read()
        # Section chunks: text after each '<section' up to the next one. chunk[0:tag]
        # is the section's own open-tag (carries its class), so slide--cover in a
        # chunk's open tag identifies a cover SECTION (not a CSS rule elsewhere).
        section_chunks = final_html.split("<section")[1:]
        self.assertEqual(
            len(section_chunks), 10,
            f"round-tripped file must carry exactly 10 sections, got {len(section_chunks)}",
        )
        cover_section_indexes = [
            i for i, chunk in enumerate(section_chunks)
            if "slide--cover" in chunk.split(">", 1)[0]
        ]
        self.assertEqual(
            cover_section_indexes, [0, 1],
            "slide 1 (cover) must be duplicated into the first two section positions "
            f"after the round trip; cover sections were at {cover_section_indexes}",
        )
        self.assertNotIn(
            REMOVED_TEXT, final_html,
            "removed slide 2 (unique text 'plataforma inteligente') must be absent "
            "from the round-tripped file",
        )


if __name__ == "__main__":
    unittest.main()
