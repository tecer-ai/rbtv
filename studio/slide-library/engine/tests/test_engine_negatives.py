#!/usr/bin/env python3
"""PB-T4 — Engine suite: §I negative matrix (fixture-spec §I, 24 rows)."""

import importlib.util
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


class TestEngineNegatives(unittest.TestCase):
    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_temp_library(self):
        tmp_parent = tempfile.mkdtemp()
        dst_fixture = os.path.join(tmp_parent, "fixture-library")
        dst_shared = os.path.join(tmp_parent, "shared-brand")
        shutil.copytree(FIXTURE_LIBRARY, dst_fixture)
        shutil.copytree(FIXTURE_SHARED_BRAND, dst_shared)
        shutil.copy2(ENGINE, os.path.join(dst_fixture, "assemble.py"))
        return dst_fixture

    def _run_engine(self, tmp_lib, args):
        cmd = [sys.executable, os.path.join(tmp_lib, "assemble.py")] + args
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return result.returncode, result.stdout, result.stderr

    def _read_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_file(self, path, content):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _import_engine_module(self, path=None):
        target = path or ENGINE
        spec = importlib.util.spec_from_file_location("assemble", target)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # ═══════════════════════════════════════════════════════════════════════════
    # §I  Negative-case matrix
    # ═══════════════════════════════════════════════════════════════════════════

    def test_negative_01_delete_theme_css(self):
        """Rule 1 — Delete theme.css → ERROR containing 'theme.css not found'."""
        tmp_lib = self._make_temp_library()
        os.remove(os.path.join(tmp_lib, "theme.css"))
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1, f"Expected exit 1, got {rc}")
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any("theme.css not found" in e for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_02a_lowercase_slides_heading(self):
        """Rule 2a — Lowercase ## Slides → ERROR with slides/heading message."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        text = text.replace("## Slides", "## slides")
        self._write_file(manifest_path, text)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"(?i)slides .*heading|section heading|Slides section", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_02b_header_id_to_Id(self):
        """Rule 2b — Rename header id→Id → ERROR 'header mismatch'."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        text = text.replace("| id | file |", "| Id | file |")
        self._write_file(manifest_path, text)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any("header" in e.lower() and "mismatch" in e.lower() for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_04_delete_one_cell(self):
        """Rule 4 — Delete one cell from a slide row (→9 cells) → ERROR expected 10 or 11."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        lines = text.splitlines()
        new_lines = []
        for line in lines:
            if "| intro-pillars |" in line:
                parts = line.split("|")
                new_parts = parts[:4] + parts[5:]
                line = "|".join(new_parts)
            new_lines.append(line)
        self._write_file(manifest_path, "\n".join(new_lines))
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"expected 10 or 11 columns|line \d+", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_05_pipe_in_summary(self):
        """Rule 5 — Insert literal | into cover-nimbus.en summary → ERROR."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        text = text.replace(
            "Co-branded cover (Nimbus x counterparty) with headline, subtitle and date over a dark background (English).",
            "Co-branded cover (Nimbus x counterparty) with headline, subtitle and date over a dark background (English) | extra."
        )
        self._write_file(manifest_path, text)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"pipe.*cover-nimbus\.en|line \d+|expected 10 or 11 columns|invalid status", e, re.IGNORECASE) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_06_blank_title_cell(self):
        """Rule 6 — Blank intro-pillars title cell → ERROR empty required."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        text = text.replace(
            "| intro-pillars | slides/intro-pillars.html | intro | Three pillars | general | en | ready |",
            "| intro-pillars | slides/intro-pillars.html | intro |  | general | en | ready |"
        )
        self._write_file(manifest_path, text)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"empty.*required.*intro-pillars|title", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_07_kind_Template(self):
        """Rule 7 — Set cover-nimbus.pt kind to Template → ERROR invalid kind."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        text = text.replace(
            "| cover-nimbus.pt | slides/cover-nimbus.pt.html | opening | Capa Nimbus | prospect | pt | template |",
            "| cover-nimbus.pt | slides/cover-nimbus.pt.html | opening | Capa Nimbus | prospect | pt | Template |"
        )
        self._write_file(manifest_path, text)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"kind.*Template.*not in .*ready.*template|invalid kind.*Template", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_08_lang_EN(self):
        """Rule 8 — Set intro-pillars lang to EN → ERROR invalid lang."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        text = text.replace(
            "| intro-pillars | slides/intro-pillars.html | intro | Three pillars | general | en | ready |",
            "| intro-pillars | slides/intro-pillars.html | intro | Three pillars | general | EN | ready |"
        )
        self._write_file(manifest_path, text)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"lang.*EN", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_09_section_proofs(self):
        """Rule 9 — Set proof-metrics section to proofs → ERROR unknown section."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        text = text.replace(
            "| proof-metrics | slides/proof-metrics.html | proof |",
            "| proof-metrics | slides/proof-metrics.html | proofs |"
        )
        self._write_file(manifest_path, text)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"section.*proofs.*not declared|unknown section.*proofs", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_10_duplicate_id(self):
        """Rule 10 — Duplicate intro-pillars id → ERROR duplicate id."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        lines = text.splitlines()
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if "| intro-pillars |" in line and "----|" not in line:
                new_lines.append(line)
        self._write_file(manifest_path, "\n".join(new_lines))
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"(?i)duplicate.*id.*intro-pillars", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_11_delete_fragment_file(self):
        """Rule 11 — Delete slides/proof-metrics.html → ERROR fragment missing."""
        tmp_lib = self._make_temp_library()
        os.remove(os.path.join(tmp_lib, "slides", "proof-metrics.html"))
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"fragment.*missing.*proof-metrics|not found", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_12_style_block_in_fragment(self):
        """Rule 12 — Add <style> inside intro-pillars.html → ERROR forbidden tag."""
        tmp_lib = self._make_temp_library()
        frag_path = os.path.join(tmp_lib, "slides", "intro-pillars.html")
        text = self._read_file(frag_path)
        text = text.replace("</section>", "<style>body{}</style>\n</section>")
        self._write_file(frag_path, text)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"(?i)fragment.*<style|purity|forbidden tag.*<style", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_13_delete_asset_file(self):
        """Rule 13 — Delete assets/nimbus-mark.png → ERROR asset not found."""
        tmp_lib = self._make_temp_library()
        os.remove(os.path.join(tmp_lib, "assets", "nimbus-mark.png"))
        out_path = os.path.join(tmp_lib, "deck.html")
        client_logo = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en", "--out", out_path,
            "--client-logo", client_logo, "--json"
        ])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"asset.*not found.*nimbus-mark\.png|nimbus-mark.*not found", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_14_root_asset_null_extra(self):
        """Rule 14 — Add @root/x.png with extra_asset_root: null → ERROR."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        text = text.replace(
            "| intro-pillars | slides/intro-pillars.html | intro | Three pillars | general | en | ready | Nimbus one-liner plus three product pillars; ships verbatim with no tokens. | - | fixture (2026-06-06) |",
            "| intro-pillars | slides/intro-pillars.html | intro | Three pillars | general | en | ready | Nimbus one-liner plus three product pillars; ships verbatim with no tokens. | @root/x.png | fixture (2026-06-06) |"
        )
        self._write_file(manifest_path, text)
        lib_json = os.path.join(tmp_lib, "library.json")
        with open(lib_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["extra_asset_root"] = None
        with open(lib_json, "w", encoding="utf-8") as f:
            json.dump(data, f)
        out_path = os.path.join(tmp_lib, "deck.html")
        client_logo = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en", "--out", out_path,
            "--client-logo", client_logo, "--json"
        ])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"@root.*extra_asset_root|no extra_asset_root", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_15_no_client_logo(self):
        """Rule 15 — Assemble {client-logo} cover without --client-logo → ERROR."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "deck.html")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en", "--out", out_path, "--json"
        ])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"\{client-logo\}.*--client-logo", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_16_comma_in_asset_filename(self):
        """Rule 16 — Comma inside asset filename → ERROR asset not found."""
        tmp_lib = self._make_temp_library()
        os.rename(
            os.path.join(tmp_lib, "assets", "nimbus-mark.png"),
            os.path.join(tmp_lib, "assets", "nim,bus-mark.png")
        )
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        text = text.replace("nimbus-mark.png", "nim,bus-mark.png")
        self._write_file(manifest_path, text)
        out_path = os.path.join(tmp_lib, "deck.html")
        client_logo = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en", "--out", out_path,
            "--client-logo", client_logo, "--json"
        ])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"asset.*comma|not found", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_17_remove_asset_table_row(self):
        """Rule 17 — Remove nimbus-mark.png from Assets table (file stays) → WARNING, proceeds."""
        tmp_lib = self._make_temp_library()
        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)
        lines = text.splitlines()
        new_lines = []
        for line in lines:
            if "`nimbus-mark.png`" in line:
                continue
            new_lines.append(line)
        self._write_file(manifest_path, "\n".join(new_lines))
        out_path = os.path.join(tmp_lib, "deck.html")
        client_logo = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en", "--out", out_path,
            "--client-logo", client_logo, "--json"
        ])
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. errors={json.loads(stdout).get('errors')}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        self.assertTrue(
            any(re.search(r"(?i)assets.*row.*nimbus-mark|nimbus-mark.*Assets table", e) for e in envelope["warnings"]),
            f"warnings={envelope['warnings']}"
        )
        self.assertTrue(os.path.exists(out_path))

    def test_negative_18_delete_slides_marker(self):
        """Rule 18 — Delete <!-- {{SLIDES}} --> from base.html → ERROR missing marker."""
        tmp_lib = self._make_temp_library()
        base_path = os.path.join(tmp_lib, "base.html")
        text = self._read_file(base_path)
        text = text.replace("<!-- {{SLIDES}} -->", "")
        self._write_file(base_path, text)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"base\.html.*missing.*marker.*SLIDES", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_19_delete_theme_css_duplicate(self):
        """Rule 19 — Delete theme.css (covered by rule 1) → ERROR theme.css not found."""
        tmp_lib = self._make_temp_library()
        os.remove(os.path.join(tmp_lib, "theme.css"))
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any("theme.css not found" in e for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_20_convention_2_0(self):
        """Rule 20 — convention_version: 2.0 → ERROR unsupported major version."""
        tmp_lib = self._make_temp_library()
        lib_json = os.path.join(tmp_lib, "library.json")
        with open(lib_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["convention_version"] = "2.0"
        with open(lib_json, "w", encoding="utf-8") as f:
            json.dump(data, f)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"convention.*2\.0.*unsupported|major", e) for e in envelope["errors"]),
            f"errors={envelope['errors']}"
        )

    def test_negative_21_convention_1_9(self):
        """Rule 21 — convention_version: 1.9 → WARNING, assembly proceeds."""
        tmp_lib = self._make_temp_library()
        lib_json = os.path.join(tmp_lib, "library.json")
        with open(lib_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["convention_version"] = "1.9"
        with open(lib_json, "w", encoding="utf-8") as f:
            json.dump(data, f)
        out_path = os.path.join(tmp_lib, "deck.html")
        client_logo = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en", "--out", out_path,
            "--client-logo", client_logo, "--json"
        ])
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        self.assertTrue(
            any(re.search(r"(?i)minor", e) for e in envelope["warnings"]),
            f"warnings={envelope['warnings']}"
        )
        self.assertTrue(os.path.exists(out_path))

    def test_negative_22_engine_version_9_9(self):
        """Rule 22 — engine_version: 9.9 → WARNING, assembly proceeds."""
        tmp_lib = self._make_temp_library()
        lib_json = os.path.join(tmp_lib, "library.json")
        with open(lib_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["engine_version"] = "9.9"
        with open(lib_json, "w", encoding="utf-8") as f:
            json.dump(data, f)
        out_path = os.path.join(tmp_lib, "deck.html")
        client_logo = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en", "--out", out_path,
            "--client-logo", client_logo, "--json"
        ])
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        self.assertTrue(
            any(re.search(r"(?i)engine.*version.*drift|stamp|mismatch", e) for e in envelope["warnings"]),
            f"warnings={envelope['warnings']}"
        )
        self.assertTrue(os.path.exists(out_path))

    def test_negative_23_flow_colon(self):
        """Rule 23 — Hand-write deviations: [modified: x] → parse error on colon in flow."""
        mod = self._import_engine_module()
        with self.assertRaises(ValueError) as ctx:
            mod.parse_yaml_subset("deviations: [modified: x]")
        self.assertIn(":", str(ctx.exception))

    def test_negative_24_check_unfilled_seed(self):
        """Rule 24 — Assemble seed, --check it → exit 1 listing template tokens."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "deck.html")
        client_logo = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en", "--out", out_path,
            "--client-logo", client_logo, "--json"
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(out_path))

        rc2, stdout2, stderr2 = self._run_engine(tmp_lib, [
            "--check", out_path, "--json"
        ])
        self.assertEqual(rc2, 1)
        envelope = json.loads(stdout2)
        self.assertFalse(envelope["ok"])
        expected_tokens = {
            "{{CLIENT_LOGO_SRC}}", "{{CLIENT_NAME}}", "{{COVER_TITLE}}",
            "{{COVER_SUBTITLE}}", "{{COVER_DATE}}",
            "{{PROBLEM_KICKER}}", "{{PROBLEM_TITLE}}", "{{PROBLEM_SUBTITLE}}",
            "{{PROBLEM_1_TITLE}}", "{{PROBLEM_1_DESC}}",
            "{{PROBLEM_2_TITLE}}", "{{PROBLEM_2_DESC}}",
            "{{PROBLEM_3_TITLE}}", "{{PROBLEM_3_DESC}}", "{{PROBLEM_ASIDE}}",
            "{{PROOF_KICKER}}", "{{PROOF_TITLE}}",
            "{{METRIC_1_VALUE}}", "{{METRIC_1_DESC}}",
            "{{METRIC_2_VALUE}}", "{{METRIC_2_DESC}}",
            "{{METRIC_3_VALUE}}", "{{METRIC_3_DESC}}", "{{SOURCES_LINE}}",
            "{{TOKEN}}",
        }
        actual_tokens = set(envelope["unfilled_tokens"])
        self.assertEqual(actual_tokens, expected_tokens,
                         f"Token mismatch: {actual_tokens ^ expected_tokens}")


if __name__ == "__main__":
    unittest.main()
