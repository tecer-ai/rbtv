#!/usr/bin/env python3
"""Archive tool suite — archive/unarchive lossless round-trip + engine invisibility.

Exercises archive.py against the conformance fixture: a fragment archived
disappears from assembly/catalog with NO engine change, and unarchive restores
it byte-identical with its manifest row verbatim.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "..", "assemble.py")
ARCHIVE = os.path.join(HERE, "..", "archive.py")
FIXTURE_PARENT = os.path.abspath(os.path.join(HERE, "..", "..", "tests"))
FIXTURE_LIBRARY = os.path.join(FIXTURE_PARENT, "fixture-library")
FIXTURE_SHARED_BRAND = os.path.join(FIXTURE_PARENT, "shared-brand")

TARGET_ID = "nimbus-divider"  # a no-asset ready fragment — clean assembly target


class TestEngineArchive(unittest.TestCase):

    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_temp_library(self):
        tmp_parent = tempfile.mkdtemp()
        dst_fixture = os.path.join(tmp_parent, "fixture-library")
        dst_shared = os.path.join(tmp_parent, "shared-brand")
        shutil.copytree(FIXTURE_LIBRARY, dst_fixture)
        shutil.copytree(FIXTURE_SHARED_BRAND, dst_shared)
        shutil.copy2(ENGINE, os.path.join(dst_fixture, "assemble.py"))
        shutil.copy2(ARCHIVE, os.path.join(dst_fixture, "archive.py"))
        return dst_fixture

    def _run(self, tmp_lib, script, args):
        cmd = [sys.executable, os.path.join(tmp_lib, script)] + args
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return result.returncode, result.stdout, result.stderr

    def _read(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _read_bytes(self, path):
        with open(path, "rb") as f:
            return f.read()

    def _manifest_ids(self, tmp_lib):
        text = self._read(os.path.join(tmp_lib, "manifest.md"))
        ids = []
        in_slides = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                in_slides = stripped == "## Slides"
                continue
            if in_slides and "|" in line and "id | file" not in line and "----|" not in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) == 10:
                    ids.append(cells[0])
        return ids

    def _row_for(self, tmp_lib, slide_id):
        text = self._read(os.path.join(tmp_lib, "manifest.md"))
        for line in text.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 10 and cells[0] == slide_id:
                return line
        return None

    # ── archive removes from active set + logs (criterion 1) ──────────────────

    def test_archive_removes_row_moves_file_and_logs(self):
        tmp = self._make_temp_library()
        self.assertIn(TARGET_ID, self._manifest_ids(tmp))
        self.assertTrue(os.path.exists(os.path.join(tmp, "slides", f"{TARGET_ID}.html")))

        rc, out, err = self._run(tmp, "archive.py", [
            TARGET_ID, "--reason", "superseded by v2", "--superseded-by", "intro-pillars", "--json",
        ])
        self.assertEqual(rc, 0, f"stderr={err}")
        env = json.loads(out)
        self.assertTrue(env["ok"])
        self.assertEqual(env["op"], "archive")

        # Row gone, fragment moved, log written with verbatim row + metadata.
        self.assertNotIn(TARGET_ID, self._manifest_ids(tmp))
        self.assertFalse(os.path.exists(os.path.join(tmp, "slides", f"{TARGET_ID}.html")))
        self.assertTrue(os.path.exists(os.path.join(tmp, "archive", f"{TARGET_ID}.html")))
        log = self._read(os.path.join(tmp, "archive", "archive.md"))
        self.assertIn(f"- id: {TARGET_ID}", log)
        self.assertIn("- reason: superseded by v2", log)
        self.assertIn("- superseded-by: intro-pillars", log)
        self.assertIn("- restored: -", log)
        self.assertIn(f"slides/{TARGET_ID}.html", log)  # verbatim row carries the file path

    def test_archived_slide_invisible_to_engine(self):
        """No engine change: an archived id cannot be assembled and drops from catalog-data."""
        tmp = self._make_temp_library()
        # Catalog before: 9 slides.
        rc, out, _ = self._run(tmp, "assemble.py", ["--catalog-data", "--json"])
        self.assertEqual(json.loads(out)["catalog_data"]["slides"].__len__(), 9)

        rc, out, err = self._run(tmp, "archive.py", [TARGET_ID, "--json"])
        self.assertEqual(rc, 0, f"stderr={err}")

        # Catalog after: 8 slides, target absent.
        rc, out, _ = self._run(tmp, "assemble.py", ["--catalog-data", "--json"])
        cd = json.loads(out)["catalog_data"]
        self.assertEqual(len(cd["slides"]), 8)
        self.assertNotIn(TARGET_ID, [s["id"] for s in cd["slides"]])

        # Requesting the archived id in assembly is a loud failure.
        out_path = os.path.join(tmp, "d.html")
        rc, out, err = self._run(tmp, "assemble.py", ["--slides", TARGET_ID, "--out", out_path, "--json"])
        self.assertEqual(rc, 1)
        self.assertFalse(json.loads(out)["ok"])

    # ── unarchive lossless round-trip (criterion 2) ───────────────────────────

    def test_unarchive_restores_byte_identical_and_row_verbatim(self):
        tmp = self._make_temp_library()
        frag_path = os.path.join(tmp, "slides", f"{TARGET_ID}.html")
        original_bytes = self._read_bytes(frag_path)
        original_row = self._row_for(tmp, TARGET_ID)
        self.assertIsNotNone(original_row)

        rc, out, err = self._run(tmp, "archive.py", [TARGET_ID, "--reason", "r", "--json"])
        self.assertEqual(rc, 0, f"stderr={err}")

        rc, out, err = self._run(tmp, "archive.py", ["--unarchive", TARGET_ID, "--json"])
        self.assertEqual(rc, 0, f"stderr={err}")
        env = json.loads(out)
        self.assertTrue(env["ok"])

        # Fragment byte-identical.
        self.assertTrue(os.path.exists(frag_path))
        self.assertEqual(self._read_bytes(frag_path), original_bytes)
        # Manifest row back verbatim.
        self.assertEqual(self._row_for(tmp, TARGET_ID), original_row)
        # archive/ no longer holds the fragment; log entry stamped restored.
        self.assertFalse(os.path.exists(os.path.join(tmp, "archive", f"{TARGET_ID}.html")))
        log = self._read(os.path.join(tmp, "archive", "archive.md"))
        self.assertNotIn("- restored: -", log)

    def test_round_trip_deck_assembly_holds(self):
        """A deck assembles with target, fails without it, assembles again after restore."""
        tmp = self._make_temp_library()
        out_path = os.path.join(tmp, "d.html")
        slides = f"intro-pillars,{TARGET_ID},closing-nimbus"

        rc, _, err = self._run(tmp, "assemble.py", ["--slides", slides, "--out", out_path, "--json"])
        self.assertEqual(rc, 0, f"stderr={err}")

        self._run(tmp, "archive.py", [TARGET_ID, "--json"])
        rc, _, _ = self._run(tmp, "assemble.py", ["--slides", slides, "--out", out_path, "--json"])
        self.assertEqual(rc, 1, "archived slide should break the deck request")

        self._run(tmp, "archive.py", ["--unarchive", TARGET_ID, "--json"])
        rc, _, err = self._run(tmp, "assemble.py", ["--slides", slides, "--out", out_path, "--json"])
        self.assertEqual(rc, 0, f"deck should assemble again after restore; stderr={err}")

    # ── --list + negative cases (loud + atomic) ───────────────────────────────

    def test_list_reports_archived(self):
        tmp = self._make_temp_library()
        rc, out, _ = self._run(tmp, "archive.py", ["--list", "--json"])
        self.assertEqual(json.loads(out)["archived"], [])
        self._run(tmp, "archive.py", [TARGET_ID, "--json"])
        rc, out, _ = self._run(tmp, "archive.py", ["--list", "--json"])
        self.assertEqual([e["id"] for e in json.loads(out)["archived"]], [TARGET_ID])

    def test_archive_nonexistent_id_dies_no_mutation(self):
        tmp = self._make_temp_library()
        before = self._read(os.path.join(tmp, "manifest.md"))
        rc, out, err = self._run(tmp, "archive.py", ["no-such-id", "--json"])
        self.assertEqual(rc, 1)
        self.assertFalse(json.loads(out)["ok"])
        self.assertEqual(self._read(os.path.join(tmp, "manifest.md")), before)
        self.assertFalse(os.path.exists(os.path.join(tmp, "archive")))

    def test_double_archive_dies(self):
        tmp = self._make_temp_library()
        self._run(tmp, "archive.py", [TARGET_ID, "--json"])
        rc, out, _ = self._run(tmp, "archive.py", [TARGET_ID, "--json"])
        self.assertEqual(rc, 1)
        self.assertFalse(json.loads(out)["ok"])

    def test_unarchive_without_entry_dies(self):
        tmp = self._make_temp_library()
        rc, out, _ = self._run(tmp, "archive.py", ["--unarchive", TARGET_ID, "--json"])
        self.assertEqual(rc, 1)
        self.assertFalse(json.loads(out)["ok"])

    def test_mode_exclusivity(self):
        tmp = self._make_temp_library()
        rc, out, _ = self._run(tmp, "archive.py", [TARGET_ID, "--unarchive", "x", "--json"])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
