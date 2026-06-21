#!/usr/bin/env python3
"""PB-T3b — Engine unit suite (themes: multi-theme assemble, contract lint, back-compat)"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "..", "assemble.py")
FIXTURE_PARENT = os.path.abspath(os.path.join(HERE, "..", "..", "tests"))

FIXTURE_LIBRARY = os.path.join(FIXTURE_PARENT, "fixture-library")
FIXTURE_SHARED_BRAND = os.path.join(FIXTURE_PARENT, "shared-brand")


class TestEngineThemes(unittest.TestCase):
    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_temp_library(self, strip_themes=False):
        """Copy fixture-library/ + shared-brand/ into a temp parent and drop
        assemble.py into the temp fixture-library root.  Return the temp
        fixture-library path."""
        tmp_parent = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_parent)
        dst_fixture = os.path.join(tmp_parent, "fixture-library")
        dst_shared = os.path.join(tmp_parent, "shared-brand")
        shutil.copytree(FIXTURE_LIBRARY, dst_fixture)
        shutil.copytree(FIXTURE_SHARED_BRAND, dst_shared)
        shutil.copy2(ENGINE, os.path.join(dst_fixture, "assemble.py"))

        if strip_themes:
            lib_json_path = os.path.join(dst_fixture, "library.json")
            with open(lib_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.pop("themes", None)
            data.pop("default_theme", None)
            with open(lib_json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")

        return dst_fixture

    def _run_engine(self, tmp_lib, args):
        """Run assemble.py in tmp_lib with the given CLI args list.
        Returns (returncode, stdout, stderr)."""
        cmd = [sys.executable, os.path.join(tmp_lib, "assemble.py")] + args
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8"
        )
        return result.returncode, result.stdout, result.stderr

    def _read_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # ═══════════════════════════════════════════════════════════════════════════
    # §2.1  Multi-theme assemble + deck stamps
    # ═══════════════════════════════════════════════════════════════════════════

    def test_theme_graphite_assemble_stamps(self):
        """--theme graphite assembles and stamps the deck correctly."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "graphite.html")
        client_logo_path = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        library_ref = "studio/slide-library/tests/fixture-library"
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--theme", "graphite",
            "--preset", "nimbus-intro-en",
            "--out", out_path,
            "--client-logo", client_logo_path,
            "--library-ref", library_ref,
            "--json",
        ])
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stdout={stdout}, stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])

        deck_text = self._read_file(out_path)
        self.assertIn('data-theme="graphite"', deck_text)
        self.assertIn('data-theme-contract="1.0"', deck_text)
        self.assertIn(f'data-theme-library="{library_ref}"', deck_text)
        # Both <html> and <style> stamps present
        self.assertRegex(deck_text, r'<html[^>]*data-theme="graphite"')
        self.assertRegex(deck_text, r'<style[^>]*data-theme="graphite"')

    def test_default_assemble_stamps_default(self):
        """Default assemble (no --theme) stamps data-theme="default"."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "default.html")
        client_logo_path = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en",
            "--out", out_path,
            "--client-logo", client_logo_path,
            "--json",
        ])
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stdout={stdout}, stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])

        deck_text = self._read_file(out_path)
        self.assertIn('data-theme="default"', deck_text)
        self.assertIn('data-theme-contract="1.0"', deck_text)
        self.assertIn('data-theme-library=""', deck_text)

    # ═══════════════════════════════════════════════════════════════════════════
    # §2.2  Contract lint
    # ═══════════════════════════════════════════════════════════════════════════

    def test_contract_lint_pass(self):
        """The intact fixture passes --check (no contract violations, no tokens)."""
        tmp_lib = self._make_temp_library()
        theme_css_path = os.path.join(tmp_lib, "theme.css")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--check", theme_css_path,
            "--json",
        ])
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stdout={stdout}, stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])

    def test_contract_lint_fail(self):
        """A deliberately incomplete theme fails --check-themes and names the missing selector."""
        tmp_lib = self._make_temp_library()
        graphite_path = os.path.join(tmp_lib, "themes", "graphite.css")
        broken_path = os.path.join(tmp_lib, "themes", "broken.css")
        shutil.copy2(graphite_path, broken_path)

        broken_css = self._read_file(broken_path)
        # Remove the .divider-statement rule entirely
        broken_css = re.sub(
            r"\.divider-statement\s*\{[^}]*\}\s*\n?",
            "",
            broken_css,
        )
        with open(broken_path, "w", encoding="utf-8") as f:
            f.write(broken_css)

        lib_json_path = os.path.join(tmp_lib, "library.json")
        with open(lib_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["themes"].append({
            "name": "broken",
            "file": "themes/broken.css",
            "label": "Broken",
            "contract_version": "1.0",
        })
        with open(lib_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        rc, stdout, stderr = self._run_engine(tmp_lib, ["--check-themes", "--json"])
        self.assertNotEqual(rc, 0, f"Expected non-zero exit, got {rc}. stdout={stdout}, stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(any(".divider-statement" in e for e in envelope["errors"]),
                        f"Expected missing .divider-statement in errors: {envelope['errors']}")

    # ═══════════════════════════════════════════════════════════════════════════
    # §2.3  Back-compat: no themes[]
    # ═══════════════════════════════════════════════════════════════════════════

    def test_back_compat_no_themes(self):
        """A library with no themes[] validates and assembles without contract lint."""
        tmp_lib = self._make_temp_library(strip_themes=True)
        theme_css_path = os.path.join(tmp_lib, "theme.css")

        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--check", theme_css_path,
            "--json",
        ])
        self.assertEqual(rc, 0, f"Check failed: {stdout} {stderr}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])

        out_path = os.path.join(tmp_lib, "legacy.html")
        client_logo_path = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en",
            "--out", out_path,
            "--client-logo", client_logo_path,
            "--json",
        ])
        self.assertEqual(rc, 0, f"Assemble failed: {stdout} {stderr}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])

    def test_back_compat_single_theme_default_output_matches_multi_theme_default(self):
        """Removing themes[] leaves default assembly output byte-for-byte unchanged."""
        multi_theme_lib = self._make_temp_library()
        single_theme_lib = self._make_temp_library(strip_themes=True)

        for tmp_lib in (multi_theme_lib, single_theme_lib):
            out_path = os.path.join(tmp_lib, "same-default.html")
            client_logo_path = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
            rc, stdout, stderr = self._run_engine(tmp_lib, [
                "--preset", "nimbus-intro-en",
                "--out", out_path,
                "--client-logo", client_logo_path,
                "--no-log",
                "--json",
            ])
            self.assertEqual(rc, 0, f"Default assemble failed: {stdout} {stderr}")
            self.assertTrue(json.loads(stdout)["ok"])

        multi_text = self._read_file(os.path.join(multi_theme_lib, "same-default.html"))
        single_text = self._read_file(os.path.join(single_theme_lib, "same-default.html"))
        self.assertEqual(single_text, multi_text)
        self.assertIn('data-theme="default"', single_text)
        self.assertIn('data-theme-contract="1.0"', single_text)
        self.assertRegex(single_text, r"<style[^>]*data-theme=\"default\"")

    def test_back_compat_old_unmarked_style_assembles_unswitchable_default(self):
        """An old base.html with an unmarked style block still assembles."""
        tmp_lib = self._make_temp_library(strip_themes=True)
        base_path = os.path.join(tmp_lib, "base.html")
        old_base = """<!DOCTYPE html>
<html lang="{{LANG}}">
<head>
<meta charset="UTF-8">
<title>{{TITLE}}</title>
<style>
/* {{ACCENT_CSS}} */
/* {{THEME_CSS}} */
</style>
</head>
<body>
<!-- {{SLIDES}} -->
</body>
</html>
"""
        with open(base_path, "w", encoding="utf-8") as f:
            f.write(old_base)

        out_path = os.path.join(tmp_lib, "legacy-unmarked.html")
        client_logo_path = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en",
            "--out", out_path,
            "--client-logo", client_logo_path,
            "--json",
        ])
        self.assertEqual(rc, 0, f"Assemble failed: {stdout} {stderr}")
        self.assertTrue(json.loads(stdout)["ok"])

        deck_text = self._read_file(out_path)
        self.assertIn("<style>", deck_text)
        self.assertIn("--bg:", deck_text)
        self.assertIn(".slide--cover", deck_text)
        self.assertNotIn("data-theme=", deck_text)
        self.assertNotIn("{{THEME_NAME}}", deck_text)

    def test_named_theme_assemble_stamps_requested_theme_and_contract(self):
        """--theme graphite stamps the requested theme identity on html and style."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "named-graphite.html")
        client_logo_path = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--theme", "graphite",
            "--preset", "nimbus-intro-en",
            "--out", out_path,
            "--client-logo", client_logo_path,
            "--library-ref", "libs/nimbus",
            "--json",
        ])
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stdout={stdout}, stderr={stderr}")
        self.assertTrue(json.loads(stdout)["ok"])

        deck_text = self._read_file(out_path)
        self.assertRegex(deck_text, r'<html[^>]*data-theme="graphite"')
        self.assertRegex(deck_text, r'<html[^>]*data-theme-contract="1.0"')
        self.assertRegex(deck_text, r'<style[^>]*data-theme="graphite"')
        self.assertRegex(deck_text, r'<style[^>]*data-theme-contract="1.0"')
        self.assertIn('data-theme-library="libs/nimbus"', deck_text)

    # ═══════════════════════════════════════════════════════════════════════════
    # §2.4  No stray theme markers
    # ═══════════════════════════════════════════════════════════════════════════

    def test_no_stray_theme_markers(self):
        """Assembled decks contain no unfilled {{THEME_*}} markers."""
        tmp_lib = self._make_temp_library()
        client_logo_path = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")

        for name, extra_args in (
            ("default", []),
            ("graphite", ["--theme", "graphite"]),
        ):
            out_path = os.path.join(tmp_lib, f"{name}.html")
            rc, stdout, stderr = self._run_engine(tmp_lib, [
                "--preset", "nimbus-intro-en",
                "--out", out_path,
                "--client-logo", client_logo_path,
                "--library-ref", "some/ref",
                "--json",
            ] + extra_args)
            self.assertEqual(rc, 0, f"{name} assemble failed: {stdout} {stderr}")
            deck_text = self._read_file(out_path)
            for token in ("{{THEME_NAME}}", "{{THEME_CONTRACT}}", "{{THEME_LIBRARY}}"):
                self.assertNotIn(token, deck_text, f"{name} deck still contains {token}")


if __name__ == "__main__":
    unittest.main()
