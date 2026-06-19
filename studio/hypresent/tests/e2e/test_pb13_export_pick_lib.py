"""PB13 — Export-to-library "Choose…" target picker (regression for the
"Library pick failed: no assemble.py in library" bug, observed 2026-06-18).

Root cause: the export-target picker reused pickAndLoadLibrary(), which runs the
picked library's vendored engine (assemble.py --catalog-data) to load the full
slide catalog. The export pipeline (/api/deck-export) never invokes that engine —
it needs only library.json + a "## Slides" manifest — so a valid export target
that does NOT vendor assemble.py was wrongly rejected and export was impossible.

Fix: the picker validates the target via /api/library-validate-target (path-only,
export-correct) instead of the full catalog load. The left-rail "Pick library…"
still uses the full catalog load (it needs the parsed catalog to render the grid).

These tests assemble a deck from the builder-lib fixture into a tempdir, open it in
the builder via ?file=, then drive the real "Choose…" gesture through the
HYP_TEST_DIALOG folder-dialog seam (the native OS folder dialog is un-automatable;
the seam supplies the chosen path while the click stays a real gesture).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8813
BUILDER_LIB = B.BUILDER_LIB


def _assemble_deck(out_dir):
    """Assemble a 3-slide deck from the builder-lib fixture into out_dir/deck.html.
    Returns the deck's absolute path. Uses the fixture's own vendored engine."""
    out_path = os.path.join(out_dir, "deck.html")
    engine = os.path.join(BUILDER_LIB, "assemble.py")
    proc = subprocess.run(
        [sys.executable, engine,
         "--slides", "cover-e2e.en,intro-e2e,closing-e2e",
         "--out", out_path, "--json"],
        cwd=BUILDER_LIB, capture_output=True, text=True, encoding="utf-8",
    )
    assert proc.returncode == 0, f"assemble failed: {proc.stderr or proc.stdout}"
    data = json.loads(proc.stdout)
    assert data.get("ok"), f"assemble not ok: {data}"
    return out_path


def _make_no_engine_library():
    """Copy the builder-lib fixture into a tempdir but REMOVE the vendored engine
    binaries (assemble.py / archive.py). This is a structurally valid slide library
    (library.json + manifest.md + slides/) that does NOT vendor the engine — the
    exact shape that triggered the original bug. Returns the library abs path."""
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "no-engine-lib")
    shutil.copytree(BUILDER_LIB, dst)
    for engine in ("assemble.py", "archive.py"):
        p = os.path.join(dst, engine)
        if os.path.exists(p):
            os.remove(p)
    return dst


class PB13ExportPickLibTests(unittest.TestCase):
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

    def _open_deck(self):
        """Assemble a deck and open it in the builder via ?file=. Wait for the
        export pane to be present (deck-mode reached)."""
        deck_dir = tempfile.mkdtemp()
        deck_path = _assemble_deck(deck_dir)
        url_path = deck_path.replace("\\", "/")
        self.page.goto(self.base + "/app/builder.html?file=" + url_path)
        # deck-mode shows the export pane; wait until it is no longer hidden
        self.page.wait_for_function(
            """() => {
                const p = document.getElementById('deck-export-pane');
                return p && !p.hidden;
            }""",
            timeout=10000,
        )
        return deck_path

    # ── PB13-1 — regression: pick a NO-ENGINE library succeeds ──────────────
    def test_pick_no_engine_library_sets_target_no_error(self):
        """The exact bug: picking a valid library that does not vendor assemble.py
        must set the export target with NO error (previously threw
        'Library pick failed: no assemble.py in library')."""
        self._open_deck()
        lib = _make_no_engine_library()

        B.set_fake_folder(self.base, lib)
        self.page.click("#export-pick-lib-btn")

        # Wait until the export-target path element reflects the picked library.
        self.page.wait_for_function(
            """() => {
                const el = document.getElementById('export-target-path');
                return el && el.classList.contains('has-path');
            }""",
            timeout=10000,
        )

        target = self.page.locator("#export-target-path")
        self.assertTrue(
            "has-path" in (target.get_attribute("class") or ""),
            "export target should be marked set (has-path)",
        )
        self.assertEqual(
            target.text_content(), lib,
            "export target path text should equal the picked library path",
        )

        # Status must NOT be an error (the old failure left a 'shell-status error').
        status = self.page.locator("#builder-status")
        status_class = status.get_attribute("class") or ""
        self.assertNotIn("error", status_class,
                         f"status should not be an error after a valid pick; got class={status_class!r} text={status.text_content()!r}")
        self.assertNotIn("Library pick failed", status.text_content() or "",
                         "the old swallowed-failure message must not appear")

    # ── PB13-2 — Export button enables after target + selection ─────────────
    def test_export_enables_after_pick_and_selection(self):
        """After picking a (no-engine) target AND selecting slides, the Export
        button must enable — proving the picked target is usable end-to-end."""
        self._open_deck()
        lib = _make_no_engine_library()

        B.set_fake_folder(self.base, lib)
        self.page.click("#export-pick-lib-btn")
        self.page.wait_for_function(
            """() => {
                const el = document.getElementById('export-target-path');
                return el && el.classList.contains('has-path');
            }""",
            timeout=10000,
        )

        # Export still disabled until slides are selected.
        self.assertTrue(
            self.page.locator("#export-cta-btn").is_disabled(),
            "Export should be disabled before any slide is selected",
        )

        # Select all slides via the real 'All' button, then Export must enable.
        self.page.click("#export-sel-all-btn")
        self.page.wait_for_function(
            """() => {
                const b = document.getElementById('export-cta-btn');
                return b && !b.disabled;
            }""",
            timeout=10000,
        )
        self.assertFalse(
            self.page.locator("#export-cta-btn").is_disabled(),
            "Export should enable once a target is set and slides are selected",
        )

    # ── PB13-3 — invalid folder rejected cleanly (no thrown failure) ────────
    def test_pick_non_library_folder_rejected_cleanly(self):
        """Picking a folder that is NOT a slide library shows a clear
        'Invalid export target' message and does NOT set a target — and is a clean
        rejection (ok:false), never a thrown 'Library pick failed'."""
        self._open_deck()
        # A folder with no library.json / manifest.md.
        not_a_lib = tempfile.mkdtemp()

        B.set_fake_folder(self.base, not_a_lib)
        self.page.click("#export-pick-lib-btn")
        self.page.wait_for_function(
            """() => {
                const el = document.getElementById('builder-status');
                return el && /Invalid export target/.test(el.textContent || '');
            }""",
            timeout=10000,
        )

        status = self.page.locator("#builder-status")
        self.assertIn("Invalid export target", status.text_content() or "")
        self.assertNotIn("Library pick failed", status.text_content() or "",
                         "rejection must be the clean validated message, not a thrown failure")
        # Target must remain unset.
        target = self.page.locator("#export-target-path")
        self.assertNotIn("has-path", target.get_attribute("class") or "",
                         "an invalid pick must not set the export target")


if __name__ == "__main__":
    unittest.main()
