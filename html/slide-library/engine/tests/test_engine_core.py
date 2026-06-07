#!/usr/bin/env python3
"""PB-T3 — Engine unit suite (core: self-check, happy-path, round-trip, --json)"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "..", "assemble.py")
FIXTURE_PARENT = os.path.abspath(os.path.join(HERE, "..", "..", "tests"))

FIXTURE_LIBRARY = os.path.join(FIXTURE_PARENT, "fixture-library")
FIXTURE_SHARED_BRAND = os.path.join(FIXTURE_PARENT, "shared-brand")


class TestEngineCore(unittest.TestCase):
    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_temp_library(self):
        """Copy fixture-library/ + shared-brand/ into a temp parent and drop
        assemble.py into the temp fixture-library root.  Return the temp
        fixture-library path."""
        tmp_parent = tempfile.mkdtemp()
        dst_fixture = os.path.join(tmp_parent, "fixture-library")
        dst_shared = os.path.join(tmp_parent, "shared-brand")
        shutil.copytree(FIXTURE_LIBRARY, dst_fixture)
        shutil.copytree(FIXTURE_SHARED_BRAND, dst_shared)
        shutil.copy2(ENGINE, os.path.join(dst_fixture, "assemble.py"))
        return dst_fixture

    def _run_engine(self, tmp_lib, args):
        """Run assemble.py in tmp_lib with the given CLI args list.
        Returns (returncode, stdout, stderr)."""
        cmd = [sys.executable, os.path.join(tmp_lib, "assemble.py")] + args
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8"
        )
        return result.returncode, result.stdout, result.stderr

    def _import_engine_module(self, path=None):
        """Import the engine module via spec_from_file_location."""
        target = path or ENGINE
        spec = importlib.util.spec_from_file_location("assemble", target)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _read_fixture_manifest(self):
        with open(os.path.join(FIXTURE_LIBRARY, "manifest.md"), "r", encoding="utf-8") as f:
            return f.read()

    def _read_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _split_row(self, line):
        cells = line.strip().split("|")
        if cells and cells[0].strip() == "":
            cells = cells[1:]
        if cells and cells[-1].strip() == "":
            cells = cells[:-1]
        return [c.strip() for c in cells]

    # ═══════════════════════════════════════════════════════════════════════════
    # §1.1  Fixture self-check
    # ═══════════════════════════════════════════════════════════════════════════

    def test_fixture_01_manifest_rows_and_columns(self):
        """9 data rows × 10 cells each."""
        text = self._read_fixture_manifest()
        lines = text.splitlines()
        in_slides = False
        rows = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                in_slides = stripped == "## Slides"
                continue
            if in_slides and "|" in line and "id | file" not in line and "----|" not in line:
                rows.append(line)
        # Should have exactly 9 data rows
        self.assertEqual(len(rows), 9, f"Expected 9 manifest rows, got {len(rows)}")
        for line in rows:
            cells = self._split_row(line)
            self.assertEqual(len(cells), 10, f"Expected 10 columns, got {len(cells)} in: {line}")

    def test_fixture_02_slide_files_exist(self):
        """9 slide fragment files exist."""
        text = self._read_fixture_manifest()
        lines = text.splitlines()
        in_slides = False
        count = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                in_slides = stripped == "## Slides"
                continue
            if in_slides and "|" in line and "id | file" not in line and "----|" not in line:
                cells = self._split_row(line)
                if len(cells) == 10:
                    file_path = os.path.join(FIXTURE_LIBRARY, cells[1])
                    self.assertTrue(os.path.exists(file_path), f"Missing slide file: {cells[1]}")
                    count += 1
        self.assertEqual(count, 9)

    def test_fixture_03_bare_assets_exist(self):
        """Assets listed in the Assets table exist on disk."""
        text = self._read_fixture_manifest()
        lines = text.splitlines()
        in_assets = False
        asset_files = set()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                in_assets = stripped == "## Assets"
                continue
            if in_assets and "|" in line and "file | description" not in line and "-----|" not in line:
                cells = self._split_row(line)
                if cells:
                    asset_files.add(cells[0].strip("`"))
        for name in asset_files:
            path = os.path.join(FIXTURE_LIBRARY, "assets", name)
            self.assertTrue(os.path.exists(path), f"Missing asset: {name}")

    def test_fixture_04_shared_brand_png_exists(self):
        """shared-brand/partner-mark.png exists."""
        path = os.path.join(FIXTURE_SHARED_BRAND, "partner-mark.png")
        self.assertTrue(os.path.exists(path))

    def test_fixture_05_presets_and_as_built_blocks(self):
        """2 yaml preset blocks + 1 as-built block."""
        with open(os.path.join(FIXTURE_LIBRARY, "presets.md"), "r", encoding="utf-8") as f:
            presets_text = f.read()
        preset_blocks = re.findall(r"```ya?ml\s*\n(.*?)```", presets_text, re.DOTALL)
        self.assertEqual(len(preset_blocks), 2, f"Expected 2 preset blocks, got {len(preset_blocks)}")

        with open(os.path.join(FIXTURE_LIBRARY, "as-built.md"), "r", encoding="utf-8") as f:
            as_built_text = f.read()
        as_built_blocks = re.findall(r"```ya?ml\s*\n(.*?)```", as_built_text, re.DOTALL)
        self.assertEqual(len(as_built_blocks), 1, f"Expected 1 as-built block, got {len(as_built_blocks)}")

    def test_fixture_06_fragment_purity(self):
        """No fragment contains forbidden tags."""
        forbidden = ("<head", "<style", "<script", "<html", "<body")
        slides_dir = os.path.join(FIXTURE_LIBRARY, "slides")
        for fname in os.listdir(slides_dir):
            if fname.endswith(".html"):
                path = os.path.join(slides_dir, fname)
                text = self._read_file(path)
                for tag in forbidden:
                    self.assertNotIn(tag, text, f"{fname} contains forbidden tag {tag}")

    def test_fixture_07_slide_number_coverage(self):
        """Covers unnumbered + 7 numbered slides."""
        slides_dir = os.path.join(FIXTURE_LIBRARY, "slides")
        unnumbered = 0
        numbered = 0
        for fname in sorted(os.listdir(slides_dir)):
            if fname.endswith(".html"):
                path = os.path.join(slides_dir, fname)
                text = self._read_file(path)
                if '<div class="slide-number">{{N}}</div>' in text:
                    numbered += 1
                else:
                    unnumbered += 1
        self.assertEqual(unnumbered, 2, "Expected 2 unnumbered slides (covers)")
        self.assertEqual(numbered, 7, "Expected 7 numbered slides")

    def test_fixture_08_exact_case_headings(self):
        """Manifest header is exact-case."""
        text = self._read_fixture_manifest()
        expected_header = "| id | file | section | title | audience | lang | kind | summary | assets | provenance |"
        self.assertIn(expected_header, text)

    def test_fixture_09_no_in_cell_pipe(self):
        """No data cell contains a pipe character."""
        text = self._read_fixture_manifest()
        lines = text.splitlines()
        in_slides = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                in_slides = stripped == "## Slides"
                continue
            if in_slides and "|" in line and "id | file" not in line and "----|" not in line:
                cells = self._split_row(line)
                for cell in cells:
                    self.assertNotIn("|", cell, f"Cell contains pipe: {cell}")

    def test_fixture_10_required_cells_non_empty(self):
        """Required cells (id, file, section, title, lang, kind, summary) are non-empty."""
        text = self._read_fixture_manifest()
        lines = text.splitlines()
        in_slides = False
        required_indices = [0, 1, 2, 3, 5, 6, 7]  # id, file, section, title, lang, kind, summary
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                in_slides = stripped == "## Slides"
                continue
            if in_slides and "|" in line and "id | file" not in line and "----|" not in line:
                cells = self._split_row(line)
                if len(cells) == 10:
                    for idx in required_indices:
                        self.assertTrue(cells[idx], f"Empty required cell at index {idx} in row {cells[0]}")

    def test_fixture_11_seed_and_preset_round_trip(self):
        """Seed entry and presets parse and have correct 7-id slide lists."""
        mod = self._import_engine_module()

        # Seed entry
        with open(os.path.join(FIXTURE_LIBRARY, "as-built.md"), "r", encoding="utf-8") as f:
            as_built_text = f.read()
        m = re.search(r"### 2026-06-06-seed-demo\s*\n\s*```ya?ml\s*\n(.*?)```", as_built_text, re.DOTALL)
        self.assertIsNotNone(m, "Seed entry not found in as-built.md")
        seed = mod.parse_yaml_subset(m.group(1))
        self.assertEqual(seed.get("engine_version"), "1.0")
        expected_7 = [
            "cover-nimbus.en", "intro-pillars", "problem-cards",
            "how-nimbus-works", "nimbus-divider", "proof-metrics", "closing-nimbus",
        ]
        self.assertEqual(seed.get("slides"), expected_7)

        # Presets
        with open(os.path.join(FIXTURE_LIBRARY, "presets.md"), "r", encoding="utf-8") as f:
            presets_text = f.read()
        preset_blocks = re.findall(r"```ya?ml\s*\n(.*?)```", presets_text, re.DOTALL)
        self.assertEqual(len(preset_blocks), 2)
        for block in preset_blocks:
            p = mod.parse_yaml_subset(block)
            self.assertEqual(len(p.get("slides", [])), 7)

    # ═══════════════════════════════════════════════════════════════════════════
    # §1.2  Happy-path
    # ═══════════════════════════════════════════════════════════════════════════

    def test_happy_preset_nimbus_intro_en(self):
        """--preset nimbus-intro-en produces ok:true with correct metadata."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "d.html")
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

        expected_slides = [
            "cover-nimbus.en", "intro-pillars", "problem-cards",
            "how-nimbus-works", "nimbus-divider", "proof-metrics", "closing-nimbus",
        ]
        self.assertEqual(envelope["as_built_entry"]["slides"], expected_slides)
        self.assertIn("partner-mark.png", envelope["assets_copied"])
        self.assertEqual(envelope["as_built_entry"]["client_logo"], "partner-mark.png")

        # Sequential slide numbers
        deck_text = self._read_file(out_path)
        numbers = re.findall(r'<div class="slide-number">(\d+)</div>', deck_text)
        self.assertEqual(numbers, ["1", "2", "3", "4", "5", "6"])

        # theme.css inlined
        self.assertIn(".slide--cover", deck_text)

        # unfilled_tokens
        expected_tokens = sorted(set(re.findall(r"\{\{[A-Z_0-9]+\}\}", deck_text)))
        self.assertEqual(sorted(envelope["unfilled_tokens"]), expected_tokens)
        # Ensure no {{N}}, {{LANG}}, {{TITLE}} remain
        for token in ("{{N}}", "{{LANG}}", "{{TITLE}}"):
            self.assertNotIn(token, envelope["unfilled_tokens"])

        # as-built.md gained a new block
        with open(os.path.join(tmp_lib, "as-built.md"), "r", encoding="utf-8") as f:
            as_built_text = f.read()
        heading = f"### {envelope['as_built_entry']['date']}-d"
        self.assertIn(heading, as_built_text)

    def test_happy_slides_explicit(self):
        """--slides cover-nimbus.en,intro-pillars,closing-nimbus produces ok:true."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "d2.html")
        client_logo_path = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--slides", "cover-nimbus.en,intro-pillars,closing-nimbus",
            "--out", out_path,
            "--client-logo", client_logo_path,
            "--json",
        ])
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stdout={stdout}, stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        self.assertEqual(len(envelope["as_built_entry"]["slides"]), 3)
        self.assertEqual(envelope["as_built_entry"]["lang"], "en")
        self.assertEqual(envelope["as_built_entry"]["preset"], "-")
        self.assertIn("partner-mark.png", envelope["assets_copied"])
        self.assertEqual(envelope["as_built_entry"]["client_logo"], "partner-mark.png")

    def test_happy_preset_nimbus_intro_pt(self):
        """--preset nimbus-intro-pt sets lang to pt."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "d3.html")
        client_logo_path = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-pt",
            "--out", out_path,
            "--client-logo", client_logo_path,
            "--json",
        ])
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stdout={stdout}, stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["as_built_entry"]["lang"], "pt")
        self.assertIn("partner-mark.png", envelope["assets_copied"])
        self.assertEqual(envelope["as_built_entry"]["client_logo"], "partner-mark.png")

    # ═══════════════════════════════════════════════════════════════════════════
    # §1.4  library-YAML round-trip property
    # ═══════════════════════════════════════════════════════════════════════════

    def test_yaml_roundtrip_seed_entry(self):
        """Seed entry parses with correct field values."""
        mod = self._import_engine_module()
        with open(os.path.join(FIXTURE_LIBRARY, "as-built.md"), "r", encoding="utf-8") as f:
            as_built_text = f.read()
        m = re.search(r"### 2026-06-06-seed-demo\s*\n\s*```ya?ml\s*\n(.*?)```", as_built_text, re.DOTALL)
        self.assertIsNotNone(m)
        seed = mod.parse_yaml_subset(m.group(1))
        self.assertEqual(seed.get("deviations"), "-")
        self.assertEqual(seed.get("engine_version"), "1.0")
        expected_7 = [
            "cover-nimbus.en", "intro-pillars", "problem-cards",
            "how-nimbus-works", "nimbus-divider", "proof-metrics", "closing-nimbus",
        ]
        self.assertEqual(seed.get("slides"), expected_7)

    def test_yaml_roundtrip_preset_slides(self):
        """Both presets parse to 7-id slide lists."""
        mod = self._import_engine_module()
        with open(os.path.join(FIXTURE_LIBRARY, "presets.md"), "r", encoding="utf-8") as f:
            presets_text = f.read()
        blocks = re.findall(r"```ya?ml\s*\n(.*?)```", presets_text, re.DOTALL)
        self.assertEqual(len(blocks), 2)
        for block in blocks:
            p = mod.parse_yaml_subset(block)
            self.assertEqual(len(p.get("slides", [])), 7)

    def test_yaml_roundtrip_custom_entry(self):
        """Custom entry with accent and deviations round-trips field-for-field."""
        mod = self._import_engine_module()
        entry = {
            "accent": "#B8875A",
            "deviations": [
                "removed: proof-metrics",
                "modified: x \u2014 y",
            ],
        }
        written = mod.write_yaml_subset(entry)
        parsed_back = mod.parse_yaml_subset(written)
        self.assertEqual(parsed_back["accent"], entry["accent"])
        self.assertEqual(parsed_back["deviations"], entry["deviations"])

    def test_yaml_negative_flow_colon(self):
        """Colon inside a flow element is rejected."""
        mod = self._import_engine_module()
        with self.assertRaises(Exception):
            mod.parse_yaml_subset("deviations: [modified: x]")

    # ═══════════════════════════════════════════════════════════════════════════
    # §1.7  --json envelope shape
    # ═══════════════════════════════════════════════════════════════════════════

    def test_json_envelope_success(self):
        """Successful assemble populates all expected envelope keys."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "d.html")
        client_logo_path = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en",
            "--out", out_path,
            "--client-logo", client_logo_path,
            "--json",
        ])
        # We only assert envelope shape; if the product bug blocks this,
        # the assertion on rc will surface it.
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["mode"], "assemble")
        self.assertIsNotNone(envelope["output"])
        self.assertTrue(envelope["assets_copied"])
        self.assertIn("partner-mark.png", envelope["assets_copied"])
        self.assertIsNotNone(envelope["as_built_entry"])
        self.assertEqual(envelope["as_built_entry"]["client_logo"], "partner-mark.png")

    def test_json_envelope_die(self):
        """Die case produces ok:false, exit 1, single valid JSON on stdout."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "x.html")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--slides", "nonexistent-id",
            "--out", out_path,
            "--json",
        ])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(envelope["errors"])

    def test_json_catalog_data(self):
        """--catalog-data --json returns correct catalog_data."""
        tmp_lib = self._make_temp_library()
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 0)
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["mode"], "catalog-data")
        cd = envelope["catalog_data"]
        self.assertEqual(len(cd["sections"]), 6)
        self.assertEqual(len(cd["slides"]), 9)
        self.assertEqual(len(cd["presets"]), 2)

    def test_json_drift_warning(self):
        """Engine version drift produces a warning but ok:true."""
        tmp_lib = self._make_temp_library()
        lib_json_path = os.path.join(tmp_lib, "library.json")
        with open(lib_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["engine_version"] = "9.9"
        with open(lib_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 0)
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        self.assertTrue(
            any("drift" in w.lower() or "version mismatch" in w.lower() for w in envelope["warnings"]),
            f"Expected drift warning, got: {envelope['warnings']}"
        )


if __name__ == "__main__":
    unittest.main()
