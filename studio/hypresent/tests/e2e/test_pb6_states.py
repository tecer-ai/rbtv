import os, sys, time, json, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8806


class PB6StateTests(unittest.TestCase):
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

    def _pick_lib(self, lib_path=None):
        if lib_path is None:
            lib_path = B.e2e_lib_path()
        B.pick_library_ui(self.page, self.base, lib_path)
        return lib_path

    # ── PB6-1 ──────────────────────────────────────────────────────────────
    def test_empty_tray_assemble_disabled(self):
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib()
        # Do not tag any slides
        tray_rows = self.page.eval_on_selector_all(".tray-row", "els=>els.length")
        self.assertEqual(tray_rows, 0, "tray should be empty initially")

        assemble_btn = self.page.locator("#save-new-btn")
        self.assertTrue(
            assemble_btn.is_disabled(),
            "compose 'New file…' button must be disabled when tray is empty"
        )

    # ── PB6-2 ──────────────────────────────────────────────────────────────
    def test_zero_presets(self):
        lib = B.make_temp_library()
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(lib), ignore_errors=True))

        # Overwrite presets.md with an empty presets section
        with open(os.path.join(lib, "presets.md"), "w", encoding="utf-8") as f:
            f.write("# presets\n\n## Presets\n\n")

        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib(lib)

        options = self.page.eval_on_selector_all(
            "#preset-select option",
            "els=>els.map(o=>o.textContent)"
        )
        self.assertEqual(options, ["(none — from scratch)"], "preset select should only have the none option when zero presets")

    # ── PB6-3 ──────────────────────────────────────────────────────────────
    def test_engine_spawn_error(self):
        lib = B.make_temp_library()
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(lib), ignore_errors=True))

        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib(lib)
        ids = self.page.eval_on_selector_all(".slide-card", "els=>els.map(e=>e.dataset.slideId)")
        self.assertTrue(len(ids) > 0, "fixture needs at least one slide")
        self.page.click(f".slide-card[data-slide-id='{ids[0]}']")
        self.page.wait_for_timeout(100)

        # Delete engine after library is loaded to simulate spawn failure on assemble
        engine_path = os.path.join(lib, "assemble.py")
        os.remove(engine_path)

        dest_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(dest_dir, ignore_errors=True))
        B.set_fake_folder(self.base, dest_dir)
        self.page.click("#pick-dest-btn")
        self.page.wait_for_timeout(100)

        self.page.fill("#deck-filename", "fail-deck")
        self.page.click("#save-new-btn")
        self.page.wait_for_timeout(500)

        status = self.page.locator(".shell-status")
        text = (status.text_content() or "").strip()
        self.assertTrue(
            "Assembly failed" in text or "error" in text.lower() or "no assemble.py" in text.lower(),
            f"expected engine spawn error in status, got: {text}"
        )
        self.assertTrue(
            status.evaluate("el => el.classList.contains('error')"),
            "status must have error class on engine spawn failure"
        )

    # ── PB6-4 ──────────────────────────────────────────────────────────────
    def test_invalid_library_full_errors(self):
        lib = B.make_temp_library()
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(lib), ignore_errors=True))

        # Corrupt the manifest header so validation fails
        manifest_path = os.path.join(lib, "manifest.md")
        with open(manifest_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith("| id |"):
                lines[i] = "| bad | header |\n"
                break
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        self.page.goto(self.base + "/app/builder.html")
        B.set_fake_folder(self.base, lib)
        self.page.click("#open-library-btn")
        self.page.wait_for_timeout(500)

        invalid = self.page.locator(".builder-invalid")
        self.assertTrue(invalid.count() > 0, "invalid library should render .builder-invalid block")

        heading = invalid.locator("p").text_content() or ""
        self.assertIn("Invalid library", heading)

        errors = invalid.locator("ul li")
        self.assertTrue(errors.count() > 0, "full error list must be rendered")


if __name__ == "__main__":
    unittest.main()
