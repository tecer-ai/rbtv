import os, sys, time, json, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8805


class PB5AssembleHandoffTests(unittest.TestCase):
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
        self.dest_dir = tempfile.mkdtemp()

    def tearDown(self):
        self.page.close()
        shutil.rmtree(self.dest_dir, ignore_errors=True)

    def _pick_lib(self, lib_path=None):
        if lib_path is None:
            lib_path = B.e2e_lib_path()
        B.pick_library_ui(self.page, self.base, lib_path)
        return lib_path

    def _tag_slide(self, slide_id):
        self.page.click(f".slide-card[data-slide-id='{slide_id}']")
        self.page.wait_for_timeout(100)

    def _set_destination(self):
        B.set_fake_folder(self.base, self.dest_dir)
        self.page.click("#pick-dest-btn")
        self.page.wait_for_timeout(100)

    def _fill_filename(self, name):
        self.page.fill("#deck-filename", name)

    def _trigger_assemble(self):
        # Compose now runs through the unified "New file…" button (build-new mode).
        self.page.click("#save-new-btn")

    # ── PB5-1 ──────────────────────────────────────────────────────────────
    def test_assemble_produces_deck_file(self):
        lib = B.make_temp_library()
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(lib), ignore_errors=True))
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib(lib)
        self._tag_slide("intro-e2e")
        self._set_destination()
        self._fill_filename("test-deck")
        self._trigger_assemble()

        # Wait for navigation to /app/?file=...
        self.page.wait_for_function(
            "() => location.search.includes('file=')", timeout=10000
        )
        self.assertIn("/app/?file=", self.page.url)

        file_param = self.page.evaluate(
            "() => new URLSearchParams(location.search).get('file')"
        )
        self.assertIsNotNone(file_param)
        self.assertTrue(
            os.path.exists(file_param),
            f"assembled deck should exist on disk: {file_param}"
        )

    # ── PB5-2 ──────────────────────────────────────────────────────────────
    def test_handoff_percent_encoding(self):
        lib = B.make_temp_library()
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(lib), ignore_errors=True))
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib(lib)
        self._tag_slide("intro-e2e")
        self._set_destination()
        self._fill_filename("deck%test")
        self._trigger_assemble()

        self.page.wait_for_function(
            "() => location.search.includes('file=')", timeout=10000
        )
        url = self.page.url
        self.assertIn("/app/?file=", url)

        query = url.split("?")[1]
        # Single encode: literal % must become %25
        self.assertIn("%25", query, "percent sign must be single-encoded as %25")
        # Must not contain raw unencoded % followed by test
        self.assertNotIn(
            "deck%test", query,
            "raw percent must not appear in query string"
        )

        file_param = self.page.evaluate(
            "() => new URLSearchParams(location.search).get('file')"
        )
        self.assertIn("deck%test", file_param, "decoded path must retain literal percent sign")

    # ── PB5-3 ──────────────────────────────────────────────────────────────
    def test_invalid_assemble_passthrough(self):
        lib = B.make_temp_library()
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(lib), ignore_errors=True))
        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib(lib)
        self._tag_slide("intro-e2e")
        self._set_destination()
        self._fill_filename("bad-deck")

        # Mock assemble API to return an error envelope
        def _handler(route, request):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"ok": False, "errors": ["Simulated assembly failure"]}),
            )

        self.page.route("**/api/assemble", _handler)
        self._trigger_assemble()
        self.page.wait_for_timeout(500)

        status_locator = self.page.locator(".shell-status")
        text = (status_locator.text_content() or "").strip()
        self.assertTrue(
            "simulated assembly failure" in text.lower() or "error" in text.lower(),
            f"expected assembly error in status, got: {text}"
        )
        # Error styling
        self.assertTrue(
            status_locator.evaluate("el => el.classList.contains('error')"),
            "status must have error class on failed assembly"
        )

    # ── PB5-4 ──────────────────────────────────────────────────────────────
    def test_client_logo_payload(self):
        """API-level test: handle_assemble must pass client_logo to the engine."""
        lib = B.make_temp_library()
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(lib), ignore_errors=True))

        # Replace engine with a spy that echoes argv
        spy = (
            "import sys, json\n"
            "print(json.dumps({"
            "  'ok': True, "
            "  'output': 'spy.html', "
            "  'assets_copied': [], "
            "  'unfilled_tokens': [], "
            "  'as_built_entry': None, "
            "  'spy_args': sys.argv"
            "}))\n"
        )
        spy_path = os.path.join(lib, "assemble.py")
        with open(spy_path, "w", encoding="utf-8") as f:
            f.write(spy)

        out_path = os.path.join(self.dest_dir, "spy.html").replace("\\", "/")
        status, data = H.post_json(self.base, "/api/assemble", {
            "path": lib,
            "slides": ["intro-e2e"],
            "out": out_path,
            "client_logo": "logo.png",
        })
        self.assertEqual(status, 200, f"assemble API returned {status}: {data}")
        self.assertTrue(data.get("ok"), f"spy engine returned ok=false: {data}")
        spy_args = data.get("spy_args", [])
        self.assertIn("--client-logo", spy_args, "engine must receive --client-logo flag")
        idx = spy_args.index("--client-logo")
        self.assertEqual(spy_args[idx + 1], "logo.png", "engine must receive client_logo value")

    # ── PB5-5 ──────────────────────────────────────────────────────────────
    def test_assemble_lang_metadata(self):
        """UI-selected lang must be recorded in as_built_entry, not library default."""
        lib = B.make_temp_library()
        self.addCleanup(lambda: shutil.rmtree(os.path.dirname(lib), ignore_errors=True))

        # Patch the temp library's assemble.py to return structured as_built_entry with lang
        orig_engine = B.ENGINE_SRC
        with open(orig_engine, "r", encoding="utf-8") as f:
            engine_src = f.read()
        engine_src = engine_src.replace(
            '"as_built_entry": entry.strip(),',
            '"as_built_entry": {"lang": lang or "en", "entry": entry.strip()},'
        )
        patched_path = os.path.join(lib, "assemble.py")
        with open(patched_path, "w", encoding="utf-8") as f:
            f.write(engine_src)

        self.page.goto(self.base + "/app/builder.html")
        self._pick_lib(lib)

        # Set UI language to 'pt' (different from library default 'en')
        self.page.evaluate("() => { document.documentElement.lang = 'pt'; }")

        self._tag_slide("intro-e2e")
        self._set_destination()
        self._fill_filename("lang-test")

        # Intercept assemble API to capture response envelope
        envelope = {}
        def handle_route(route, request):
            if request.url.endswith("/api/assemble"):
                response = route.fetch()
                try:
                    envelope["data"] = response.json()
                except Exception:
                    pass
                route.fulfill(response=response)
            else:
                route.continue_()
        self.page.route("**/api/assemble", handle_route)

        self._trigger_assemble()
        self.page.wait_for_function(
            "() => location.search.includes('file=')", timeout=10000
        )

        self.assertIn("data", envelope, "assemble envelope not captured")
        as_built = envelope["data"].get("as_built_entry")
        self.assertIsInstance(as_built, dict, "as_built_entry should be a dict")
        self.assertEqual(as_built.get("lang"), "pt",
                         "as_built_entry.lang must match UI-selected lang, not library default")


if __name__ == "__main__":
    unittest.main()
