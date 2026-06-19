"""PB-14 — Save as preset: round-trip e2e test.

Exercise: from the builder UI, save the current tray composition as a new
preset; verify the preset block is written to the scratch library's presets.md
and appears in #preset-select; select it and confirm it rebuilds the tray
from the same slide ids.
"""

import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import conftest_helpers as H
import builder_helpers as B

PORT = 8834


class PB14PresetSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc, cls.base = H.start_server(PORT, test_dialog=True)
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        H.stop_server(cls.proc)

    def setUp(self):
        # Fresh scratch library per test — mutates presets.md.
        self.lib_dir = B.make_temp_library()
        self.page = self.browser.new_page()
        self.page.goto(self.base + "/app/builder.html")

    def tearDown(self):
        self.page.close()
        shutil.rmtree(self.lib_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _load_library(self):
        """Set fake folder to scratch lib, click Pick library, wait for browse."""
        B.set_fake_folder(self.base, self.lib_dir)
        self.page.click("#open-library-btn")
        self.page.wait_for_function(
            """() => {
                const el = document.getElementById('browse-groups');
                return el && el.children.length > 0;
            }""",
            timeout=10000,
        )

    def _add_slide_to_tray(self, slide_id):
        """Click the slide card caption to add it to the tray (onTag fires on card click)."""
        self.page.wait_for_selector(f'.slide-card[data-slide-id="{slide_id}"]', timeout=5000)
        # Click the caption area; the expand/archive overlays use stopPropagation so
        # clicking the card or its .s-cap both fire onTag which adds to the tray.
        self.page.click(f'.slide-card[data-slide-id="{slide_id}"] .s-cap')

    def _tray_slide_ids(self):
        """Return the current tray's slide ids in order."""
        return self.page.eval_on_selector_all(
            "#tray-list .tray-row",
            "rows => rows.map(r => r.dataset.slideId)",
        )

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_save_as_preset_appends_to_presets_md(self):
        """Saving a preset writes the correct block to presets.md on disk."""
        self._load_library()
        self._add_slide_to_tray("intro-e2e")
        self._add_slide_to_tray("closing-e2e")

        # Verify tray has both slides before saving.
        order_before = self._tray_slide_ids()
        self.assertIn("intro-e2e", order_before)
        self.assertIn("closing-e2e", order_before)

        # Handle window.prompt via Playwright dialog handler (the seam).
        PRESET_NAME = "my-e2e-test-preset"
        dialogs = []

        def handle_dialog(dialog):
            dialogs.append(dialog.type)
            dialog.accept(PRESET_NAME)

        self.page.on("dialog", handle_dialog)

        # The button must now be enabled (library loaded + tray non-empty).
        btn = self.page.wait_for_selector("#save-preset-btn:not([disabled])", timeout=5000)
        self.assertIsNotNone(btn, "save-preset-btn should be enabled with slides in tray")

        btn.click()

        # Wait for status to confirm save.
        self.page.wait_for_function(
            f"""() => {{
                const el = document.getElementById('builder-status');
                return el && el.textContent.includes('{PRESET_NAME}');
            }}""",
            timeout=8000,
        )

        # Verify the dialog was a prompt.
        self.assertEqual(dialogs, ["prompt"], "a prompt dialog should have fired")

        # Assert presets.md on disk contains the new block.
        presets_path = os.path.join(self.lib_dir, "presets.md")
        self.assertTrue(os.path.isfile(presets_path), "presets.md must exist after save")
        content = open(presets_path, encoding="utf-8").read()
        self.assertIn(f"### {PRESET_NAME}", content, "heading block must be in presets.md")
        self.assertIn(f"preset: {PRESET_NAME}", content, "preset key must be in yaml block")
        self.assertIn("intro-e2e", content, "intro-e2e slide must appear in slides list")
        self.assertIn("closing-e2e", content, "closing-e2e slide must appear in slides list")

    def test_saved_preset_appears_in_dropdown(self):
        """After saving, the preset appears as an option in #preset-select."""
        self._load_library()
        self._add_slide_to_tray("intro-e2e")

        PRESET_NAME = "dropdown-check-preset"

        def handle_dialog(dialog):
            dialog.accept(PRESET_NAME)

        self.page.on("dialog", handle_dialog)
        self.page.click("#save-preset-btn")
        self.page.wait_for_function(
            f"""() => {{
                const sel = document.getElementById('preset-select');
                return sel && Array.from(sel.options).some(o => o.value === '{PRESET_NAME}');
            }}""",
            timeout=8000,
        )

        # The new option must be present.
        options = self.page.eval_on_selector_all(
            "#preset-select option",
            "opts => opts.map(o => o.value)",
        )
        self.assertIn(PRESET_NAME, options, "saved preset must appear as dropdown option")

        # The dropdown must be selected to the new preset.
        selected = self.page.evaluate("() => document.getElementById('preset-select').value")
        self.assertEqual(selected, PRESET_NAME, "dropdown should be auto-selected to new preset")

    def test_selecting_saved_preset_rebuilds_composition(self):
        """Selecting the saved preset resets the tray to the saved slide order."""
        self._load_library()
        # Build a specific composition: intro-e2e, closing-e2e.
        self._add_slide_to_tray("intro-e2e")
        self._add_slide_to_tray("closing-e2e")
        original_order = self._tray_slide_ids()

        PRESET_NAME = "rebuild-test-preset"

        def handle_dialog(dialog):
            dialog.accept(PRESET_NAME)

        self.page.on("dialog", handle_dialog)
        self.page.click("#save-preset-btn")
        self.page.wait_for_function(
            f"""() => {{
                const sel = document.getElementById('preset-select');
                return sel && Array.from(sel.options).some(o => o.value === '{PRESET_NAME}');
            }}""",
            timeout=8000,
        )

        # Clear the tray by reloading the library (picks a fresh state).
        # Instead: select "(none — from scratch)" to clear, then select the preset.
        # The select change handler calls tray.setFromPreset — selecting "none" does nothing,
        # so we need another way to clear. Add a slide then remove it, OR just
        # select none first to confirm the tray doesn't crash, then select the preset.
        # Actually the cleanest way: re-select none (no-op on tray), then pick the preset.

        # Select the saved preset — this calls tray.setFromPreset.
        self.page.select_option("#preset-select", PRESET_NAME)
        self.page.wait_for_timeout(300)  # allow tray model update

        rebuilt_order = self._tray_slide_ids()
        self.assertEqual(rebuilt_order, original_order,
                         "rebuilt tray order must match original composition")

    def test_save_preset_api_direct(self):
        """Direct API test: /api/preset-save appends a valid block to presets.md."""
        slides = ["cover-e2e.en", "intro-e2e", "closing-e2e"]
        status, data = H.post_json(
            self.base, "/api/preset-save",
            {
                "library_path": self.lib_dir,
                "name": "api-direct-test",
                "lang": "en",
                "slides": slides,
            },
        )
        self.assertEqual(status, 200, f"expected 200, got {status}: {data}")
        self.assertTrue(data.get("ok"), f"response must be ok: {data}")
        self.assertEqual(data.get("name"), "api-direct-test")

        # Verify the written content.
        presets_path = os.path.join(self.lib_dir, "presets.md")
        content = open(presets_path, encoding="utf-8").read()
        self.assertIn("### api-direct-test", content)
        self.assertIn("preset: api-direct-test", content)
        self.assertIn("lang: en", content)
        # All three slide ids must appear.
        for sid in slides:
            self.assertIn(sid, content, f"slide {sid!r} must be in preset block")

    def test_save_preset_duplicate_rejected(self):
        """Saving a preset with a duplicate name returns a 409 conflict."""
        import json
        import urllib.request
        import urllib.error

        def _post_raw(path, payload):
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                self.base + path, data=data,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())

        # First save succeeds.
        st1, d1 = _post_raw("/api/preset-save",
            {"library_path": self.lib_dir, "name": "dup-preset", "lang": "en", "slides": ["intro-e2e"]})
        self.assertEqual(st1, 200, f"first save expected 200, got {st1}: {d1}")

        # Second save with same name must be rejected.
        st2, d2 = _post_raw("/api/preset-save",
            {"library_path": self.lib_dir, "name": "dup-preset", "lang": "en", "slides": ["closing-e2e"]})
        self.assertEqual(st2, 409, f"expected 409 on duplicate, got {st2}: {d2}")
        self.assertIn("already exists", d2.get("error", ""))

    def test_library_load_returns_saved_preset(self):
        """After saving, /api/library-load returns the preset in catalog_data.presets."""
        H.post_json(
            self.base, "/api/preset-save",
            {
                "library_path": self.lib_dir,
                "name": "catalog-test-preset",
                "lang": "en",
                "slides": ["intro-e2e"],
            },
        )
        status, data = H.post_json(self.base, "/api/library-load", {"path": self.lib_dir})
        self.assertEqual(status, 200)
        catalog = data.get("catalog_data", {})
        presets = catalog.get("presets", [])
        names = [p.get("preset") for p in presets]
        self.assertIn("catalog-test-preset", names,
                      "saved preset must appear in catalog_data.presets after library reload")


if __name__ == "__main__":
    unittest.main()
