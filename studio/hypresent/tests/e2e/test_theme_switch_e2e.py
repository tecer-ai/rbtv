import html.parser
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

PORT = 8825
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
RBTV_ROOT = os.path.abspath(os.path.join(REPO, "..", ".."))
GRAPHITE_MARKER = "#79D4C8"
SLIDES = "cover-e2e.en,intro-e2e,closing-e2e"


class StampParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.html_attrs = {}
        self.theme_style_attrs = None
        self._in_theme_style = False
        self.theme_style_text = ""

    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs)
        if tag == "html":
            self.html_attrs = attr_map
        if tag == "style" and "data-theme" in attr_map:
            self.theme_style_attrs = attr_map
            self._in_theme_style = True

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_theme_style = False

    def handle_data(self, data):
        if self._in_theme_style:
            self.theme_style_text += data


def parse_stamps(html):
    parser = StampParser()
    parser.feed(html)
    return parser


class ThemeSwitchE2ETests(unittest.TestCase):
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
        self._tmp_roots = []

    def tearDown(self):
        self.page.close()
        for path in reversed(self._tmp_roots):
            shutil.rmtree(path, ignore_errors=True)

    def _tmpdir(self):
        root = tempfile.mkdtemp(prefix="theme-switch-e2e-", dir=RBTV_ROOT)
        self._tmp_roots.append(root)
        return root

    def _repo_ref(self, path):
        return os.path.relpath(path, RBTV_ROOT).replace("\\", "/")

    def _copy_library(self):
        dst = os.path.join(self._tmpdir(), "builder-lib")
        shutil.copytree(B.e2e_lib_path(), dst)
        return dst

    def _make_deck(self, library_path=None, theme="default"):
        library_path = library_path or B.e2e_lib_path()
        out_dir = self._tmpdir()
        deck_path = os.path.join(out_dir, "deck.html")
        library_ref = self._repo_ref(library_path)
        cmd = [
            sys.executable,
            os.path.join(library_path, "assemble.py"),
            "--slides",
            SLIDES,
            "--out",
            deck_path,
            "--json",
            "--theme",
            theme,
            "--library-ref",
            library_ref,
        ]
        proc = subprocess.run(
            cmd,
            cwd=library_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertTrue(result.get("ok"), result)

        stamps = parse_stamps(open(deck_path, encoding="utf-8").read())
        self.assertEqual(stamps.html_attrs.get("data-theme"), theme)
        self.assertEqual(stamps.html_attrs.get("data-theme-contract"), "1.0")
        self.assertEqual(stamps.html_attrs.get("data-theme-library"), library_ref)
        self.assertIsNotNone(stamps.theme_style_attrs)
        self.assertEqual(stamps.theme_style_attrs.get("data-theme"), theme)
        self.assertEqual(stamps.theme_style_attrs.get("data-theme-contract"), "1.0")
        return deck_path, library_ref

    def _open_editor(self, deck_path):
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, deck_path)

    def _wait_themes(self, required=("default", "graphite")):
        required_json = json.dumps(list(required))
        self.page.wait_for_function(
            f"""() => {{
                const select = document.getElementById('theme-select');
                if (!select || select.disabled) return false;
                const values = Array.from(select.options).map((option) => option.value);
                const required = {required_json};
                return required.every((name) => values.includes(name));
            }}""",
            timeout=10000,
        )

    def _live_theme(self):
        return H.doc_eval(
            self.page,
            """
            const style = doc.querySelector('style[data-theme]');
            return {
              htmlTheme: doc.documentElement.getAttribute('data-theme'),
              htmlContract: doc.documentElement.getAttribute('data-theme-contract'),
              htmlLibrary: doc.documentElement.getAttribute('data-theme-library'),
              styleTheme: style ? style.getAttribute('data-theme') : null,
              styleContract: style ? style.getAttribute('data-theme-contract') : null,
              css: style ? style.textContent : '',
            };
            """,
        )

    def test_theme_switch_save_round_trips_all_stamps(self):
        deck_path, library_ref = self._make_deck()
        self._open_editor(deck_path)
        self._wait_themes()

        self.page.locator("#theme-select").select_option("graphite")
        self.page.wait_for_function(
            f"""() => {{
                const frame = document.querySelector('iframe.doc-frame');
                const doc = frame && frame.contentDocument;
                const style = doc && doc.querySelector('style[data-theme]');
                const message = document.getElementById('theme-message');
                return style
                  && doc.documentElement.getAttribute('data-theme') === 'graphite'
                  && style.getAttribute('data-theme') === 'graphite'
                  && style.textContent.includes('{GRAPHITE_MARKER}')
                  && (!message || message.hidden || !/failed|mismatch|blocked/i.test(message.textContent));
            }}""",
            timeout=10000,
        )
        live = self._live_theme()
        self.assertEqual(live["htmlTheme"], "graphite")
        self.assertEqual(live["styleTheme"], "graphite")
        self.assertIn(GRAPHITE_MARKER, live["css"])

        self.page.click("#save-btn")
        self.page.wait_for_function(
            "() => document.getElementById('doc-state')?.textContent === 'Saved'",
            timeout=10000,
        )

        saved = parse_stamps(open(deck_path, encoding="utf-8").read())
        self.assertEqual(saved.html_attrs.get("data-theme"), "graphite")
        self.assertEqual(saved.html_attrs.get("data-theme-contract"), "1.0")
        self.assertEqual(saved.html_attrs.get("data-theme-library"), library_ref)
        self.assertIsNotNone(saved.theme_style_attrs)
        self.assertEqual(saved.theme_style_attrs.get("data-theme"), "graphite")
        self.assertEqual(saved.theme_style_attrs.get("data-theme-contract"), "1.0")
        self.assertIn(GRAPHITE_MARKER, saved.theme_style_text)

    def test_legacy_unstamped_deck_disables_theme_switching(self):
        deck_path = os.path.join(self._tmpdir(), "legacy.html")
        with open(deck_path, "w", encoding="utf-8") as f:
            f.write(
                "<!doctype html><html><head><title>Legacy</title>"
                "<style>.slide{width:1280px;height:720px}</style></head>"
                "<body><section class='slide'><h1>Legacy</h1></section></body></html>"
            )

        self._open_editor(deck_path)
        self.page.wait_for_function(
            """() => {
                const switcher = document.getElementById('theme-switcher');
                const select = document.getElementById('theme-select');
                const message = document.getElementById('theme-message');
                return switcher && !switcher.hidden
                  && select && select.disabled
                  && message && !message.hidden
                  && message.textContent.includes('predates theme-switching');
            }""",
            timeout=10000,
        )

    def test_incompatible_major_theme_hidden_from_switch_list(self):
        """A theme whose contract major differs from the deck's is hidden from the
        theme-select — it must not appear as a clickable option at all."""
        library = self._copy_library()
        library_json_path = os.path.join(library, "library.json")
        with open(library_json_path, encoding="utf-8") as f:
            data = json.load(f)
        for theme in data["themes"]:
            if theme["name"] == "graphite":
                theme["contract_version"] = "2.0"
        # A theme with a blank contract is NOT blocked by the runtime apply-theme
        # guard (which only blocks when both majors are non-null and differ), so
        # the switch-list filter must keep it visible — same compatibility notion.
        data["themes"].append(
            {"name": "blankcontract", "file": "themes/blankcontract.css",
             "label": "Blank", "contract_version": ""}
        )
        with open(library_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Deck is built with contract 1.0; graphite is now 2.0 → incompatible major.
        deck_path, _library_ref = self._make_deck(library)
        self._open_editor(deck_path)
        # Wait for the library to resolve and the select to be enabled with the
        # compatible themes; only 'default' (1.0) should appear — graphite must not.
        self._wait_themes(required=("default",))

        # Graphite must not be in the option list at all.
        option_values = self.page.evaluate(
            """() => Array.from(document.getElementById('theme-select').options).map((o) => o.value)"""
        )
        self.assertNotIn("graphite", option_values, "graphite (v2.0) must not appear in a v1.0 deck's theme list")
        self.assertIn("default", option_values, "default (v1.0) must remain in the theme list")
        self.assertIn(
            "blankcontract", option_values,
            "a blank-contract theme is not blocked by the runtime guard, so it must stay visible",
        )

        # Deck theme and CSS must be unchanged (graphite never applied).
        live = self._live_theme()
        self.assertEqual(live["htmlTheme"], "default")
        self.assertNotIn(GRAPHITE_MARKER, live["css"])


if __name__ == "__main__":
    unittest.main()
