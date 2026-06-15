#!/usr/bin/env python3
"""Status-column tests — back-compat, 11-column parse, missing→ready, invalid enum, mixed-width.

Pre-resolution ruling D-A (2026-06-15):
  - assemble.py accepts 10 OR 11 columns; 11th = status, missing/blank → ready.
  - Invalid status enum → die().
  - Shared fixture manifest.md stays 10-column (back-compat).
  - New tests build their own 11-column content (never mutate shared fixture rows).
"""

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


class TestEngineStatus(unittest.TestCase):
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

    def _import_engine_module(self):
        spec = importlib.util.spec_from_file_location("assemble", ENGINE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _read_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_file(self, path, content):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _append_status_row_to_manifest(self, tmp_lib, status_value):
        """Append a new intro-extra slide row to the manifest with the given status value.

        The row is an 11-column row added after the existing 9 rows.
        We copy the intro-pillars fragment file as intro-extra.html so assembly works.
        """
        # Copy intro-pillars.html as intro-extra.html
        src = os.path.join(tmp_lib, "slides", "intro-pillars.html")
        dst = os.path.join(tmp_lib, "slides", "intro-extra.html")
        shutil.copy2(src, dst)

        manifest_path = os.path.join(tmp_lib, "manifest.md")
        text = self._read_file(manifest_path)

        # Build an 11-column row for the new slide
        # status_value may be "to-review", "ready", blank "", or invalid
        new_row = (
            f"| intro-extra | slides/intro-extra.html | intro | Extra slide | general "
            f"| en | ready | Extra slide for status testing. | - | fixture (2026-06-15) | {status_value} |"
        )

        # Insert before "## Assets"
        text = text.replace("\n## Assets", f"\n{new_row}\n\n## Assets")
        self._write_file(manifest_path, text)
        return manifest_path

    def _make_11col_manifest(self, status_value):
        """Return manifest text with header + 1 row, all 11-column, status=status_value."""
        return (
            "# test manifest\n\n"
            "## Slides\n\n"
            "| id | file | section | title | audience | lang | kind | summary | assets | provenance | status |\n"
            "|----|------|---------|-------|----------|------|------|---------|--------|------------|--------|\n"
            f"| slide-a | slides/slide-a.html | opening | Slide A | general | en | ready | Test slide. | - | test (2026-06-15) | {status_value} |\n\n"
            "## Assets\n\n"
            "| file | description | used-by |\n"
            "|------|-------------|--------|\n"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # C1 — Back-compat: 10-column fixture assembles byte-identically
    # ═══════════════════════════════════════════════════════════════════════════

    def test_status_01_backcompat_10col_assembly_succeeds(self):
        """C1 — 10-column fixture assembles without error after engine change."""
        tmp_lib = self._make_temp_library()
        out_path = os.path.join(tmp_lib, "d_backcompat.html")
        client_logo = os.path.join(os.path.dirname(tmp_lib), "shared-brand", "partner-mark.png")
        rc, stdout, stderr = self._run_engine(tmp_lib, [
            "--preset", "nimbus-intro-en",
            "--out", out_path,
            "--client-logo", client_logo,
            "--no-log", "--json",
        ])
        self.assertEqual(rc, 0, f"Expected exit 0. stdout={stdout}, stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"], f"Assembly failed: {envelope.get('errors')}")
        self.assertTrue(os.path.exists(out_path), "Output file not created")

    def test_status_02_backcompat_catalog_data_reports_9_slides(self):
        """C1 — catalog-data on 10-col fixture returns 9 slides, all with status=ready."""
        tmp_lib = self._make_temp_library()
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 0)
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        slides = envelope["catalog_data"]["slides"]
        self.assertEqual(len(slides), 9)
        for slide in slides:
            self.assertEqual(
                slide.get("status"), "ready",
                f"Slide {slide['id']} has status={slide.get('status')}, expected 'ready' (missing→ready default)"
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # C2 — 11-column parse: status to-review and ready are parsed correctly
    # ═══════════════════════════════════════════════════════════════════════════

    def test_status_03_parse_to_review(self):
        """C2 — Engine parses status=to-review from an 11-column row."""
        mod = self._import_engine_module()
        manifest_text = self._make_11col_manifest("to-review")

        import io
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "manifest.md"
            md_path.write_text(manifest_text, encoding="utf-8")
            rows = mod.parse_manifest(md_path)

        self.assertEqual(len(rows), 1)
        cells = rows[0]["cells"]
        self.assertEqual(len(cells), 11)
        self.assertEqual(cells[10], "to-review")

    def test_status_04_parse_ready(self):
        """C2 — Engine parses status=ready from an 11-column row."""
        mod = self._import_engine_module()
        manifest_text = self._make_11col_manifest("ready")

        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "manifest.md"
            md_path.write_text(manifest_text, encoding="utf-8")
            rows = mod.parse_manifest(md_path)

        self.assertEqual(len(rows), 1)
        cells = rows[0]["cells"]
        self.assertEqual(len(cells), 11)
        self.assertEqual(cells[10], "ready")

    def test_status_05_11col_assembly_succeeds(self):
        """C2 — An 11-column manifest assembles successfully."""
        tmp_lib = self._make_temp_library()
        self._append_status_row_to_manifest(tmp_lib, "to-review")
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 0, f"Expected exit 0. stdout={stdout}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"], f"Assembly failed: {envelope.get('errors')}")
        slides = envelope["catalog_data"]["slides"]
        # 9 original rows (status=ready) + 1 new row (status=to-review)
        self.assertEqual(len(slides), 10)
        extra = next((s for s in slides if s["id"] == "intro-extra"), None)
        self.assertIsNotNone(extra, "intro-extra slide not found")
        self.assertEqual(extra["status"], "to-review")

    # ═══════════════════════════════════════════════════════════════════════════
    # C3 — Missing status defaults to ready
    # ═══════════════════════════════════════════════════════════════════════════

    def test_status_06_missing_status_defaults_ready(self):
        """C3 — 10-column row (no status cell) → status reported as 'ready'."""
        tmp_lib = self._make_temp_library()
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 0)
        envelope = json.loads(stdout)
        slides = envelope["catalog_data"]["slides"]
        # Every 10-col slide must default to ready
        for slide in slides:
            self.assertEqual(slide["status"], "ready",
                             f"Expected status=ready for 10-col row {slide['id']}")

    def test_status_07_blank_status_cell_defaults_ready(self):
        """C3 — 11-column row with blank status cell → status defaults to 'ready'."""
        tmp_lib = self._make_temp_library()
        # Add a row with an empty status cell (11 cols, status cell is blank)
        self._append_status_row_to_manifest(tmp_lib, "")
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 0, f"Expected exit 0. stdout={stdout}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        slides = envelope["catalog_data"]["slides"]
        extra = next((s for s in slides if s["id"] == "intro-extra"), None)
        self.assertIsNotNone(extra, "intro-extra slide not found")
        self.assertEqual(extra["status"], "ready",
                         f"Blank status cell should default to 'ready', got {extra['status']}")

    # ═══════════════════════════════════════════════════════════════════════════
    # C4 — Invalid status enum is rejected clearly
    # ═══════════════════════════════════════════════════════════════════════════

    def test_status_08_invalid_status_rejected(self):
        """C4 — status=bogus → engine errors clearly, does not silently compose."""
        tmp_lib = self._make_temp_library()
        self._append_status_row_to_manifest(tmp_lib, "bogus")
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1, f"Expected exit 1 for invalid status. stdout={stdout}")
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"invalid status.*bogus|status.*bogus", e, re.IGNORECASE)
                for e in envelope["errors"]),
            f"Expected 'invalid status' error, got: {envelope['errors']}"
        )

    def test_status_09_invalid_status_To_Review_rejected(self):
        """C4 — status=To-Review (wrong case) → engine errors (exact lowercase required)."""
        tmp_lib = self._make_temp_library()
        self._append_status_row_to_manifest(tmp_lib, "To-Review")
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 1, f"Expected exit 1 for wrong-case status. stdout={stdout}")
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any(re.search(r"invalid status", e, re.IGNORECASE) for e in envelope["errors"]),
            f"Expected 'invalid status' error, got: {envelope['errors']}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Mixed-width (10 and 11 col rows in same manifest)
    # ═══════════════════════════════════════════════════════════════════════════

    def test_status_10_mixed_width_10_and_11_col(self):
        """Mixed manifest: 9 existing 10-col rows + 1 new 11-col row → assembles ok."""
        tmp_lib = self._make_temp_library()
        self._append_status_row_to_manifest(tmp_lib, "ready")
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--catalog-data", "--json"])
        self.assertEqual(rc, 0, f"Expected exit 0. stdout={stdout}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        slides = envelope["catalog_data"]["slides"]
        self.assertEqual(len(slides), 10)
        # Original rows default to ready; new row explicitly ready
        for slide in slides:
            self.assertEqual(slide["status"], "ready")

    def test_status_11_11col_header_accepted(self):
        """An 11-column header (with 'status') is accepted by parse_manifest."""
        mod = self._import_engine_module()
        manifest_text = self._make_11col_manifest("ready")

        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "manifest.md"
            md_path.write_text(manifest_text, encoding="utf-8")
            # Should not raise / die
            try:
                rows = mod.parse_manifest(md_path)
            except SystemExit as e:
                self.fail(f"parse_manifest died with 11-col header: exit {e}")
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
