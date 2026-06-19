"""Unit tests for builder_api.handle_library_validate_target — the lightweight,
export-correct validation behind the Export-to-library "Choose…" picker.

Regression for "Library pick failed: no assemble.py in library" (2026-06-18): the
export-target check must accept a valid library that does NOT vendor assemble.py,
because the export pipeline (handle_deck_export) never runs that engine — it needs
only library.json + a "## Slides" manifest table.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "server"))
sys.path.insert(0, SERVER_DIR)

import builder_api  # noqa: E402

FIXTURE_LIB = os.path.abspath(
    os.path.join(HERE, "..", "e2e", "fixtures", "builder-lib")
)


class LibraryValidateTargetTests(unittest.TestCase):
    def _copy_lib(self, drop_engine=False):
        tmp = tempfile.mkdtemp()
        dst = os.path.join(tmp, "lib")
        shutil.copytree(FIXTURE_LIB, dst)
        if drop_engine:
            for engine in ("assemble.py", "archive.py"):
                p = os.path.join(dst, engine)
                if os.path.exists(p):
                    os.remove(p)
        return dst

    # ── valid targets ───────────────────────────────────────────────────────
    def test_valid_library_with_engine_ok(self):
        lib = self._copy_lib(drop_engine=False)
        status, resp = builder_api.handle_library_validate_target({"path": lib})
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("ok"), resp)
        self.assertEqual(resp.get("path"), lib)

    def test_valid_library_WITHOUT_engine_ok(self):
        """The core regression: no vendored assemble.py must NOT be a rejection."""
        lib = self._copy_lib(drop_engine=True)
        self.assertFalse(os.path.exists(os.path.join(lib, "assemble.py")))
        status, resp = builder_api.handle_library_validate_target({"path": lib})
        self.assertEqual(status, 200)
        self.assertTrue(resp.get("ok"),
                        f"a library without assemble.py is a valid export target: {resp}")

    # ── rejections (ok:false, never a 500) ───────────────────────────────────
    def test_missing_library_json(self):
        lib = self._copy_lib(drop_engine=True)
        os.remove(os.path.join(lib, "library.json"))
        status, resp = builder_api.handle_library_validate_target({"path": lib})
        self.assertEqual(status, 200)
        self.assertFalse(resp.get("ok"))
        self.assertTrue(any("library.json" in e for e in resp.get("errors", [])), resp)

    def test_missing_manifest(self):
        lib = self._copy_lib(drop_engine=True)
        os.remove(os.path.join(lib, "manifest.md"))
        status, resp = builder_api.handle_library_validate_target({"path": lib})
        self.assertEqual(status, 200)
        self.assertFalse(resp.get("ok"))
        self.assertTrue(any("manifest.md" in e for e in resp.get("errors", [])), resp)

    def test_manifest_without_slides_section(self):
        lib = self._copy_lib(drop_engine=True)
        with open(os.path.join(lib, "manifest.md"), "w", encoding="utf-8") as f:
            f.write("# lib\n\n## Assets\n\n| file | description |\n|------|------|\n")
        status, resp = builder_api.handle_library_validate_target({"path": lib})
        self.assertEqual(status, 200)
        self.assertFalse(resp.get("ok"))
        self.assertTrue(any("## Slides" in e for e in resp.get("errors", [])), resp)

    def test_invalid_library_json(self):
        lib = self._copy_lib(drop_engine=True)
        with open(os.path.join(lib, "library.json"), "w", encoding="utf-8") as f:
            f.write("{ not valid json ")
        status, resp = builder_api.handle_library_validate_target({"path": lib})
        self.assertEqual(status, 200)
        self.assertFalse(resp.get("ok"))
        self.assertTrue(any("library.json" in e and "JSON" in e for e in resp.get("errors", [])), resp)

    def test_not_a_folder(self):
        tmp = tempfile.mkdtemp()
        f = os.path.join(tmp, "afile.txt")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("x")
        status, resp = builder_api.handle_library_validate_target({"path": f})
        self.assertEqual(status, 200)
        self.assertFalse(resp.get("ok"))

    def test_missing_path(self):
        status, resp = builder_api.handle_library_validate_target({})
        self.assertEqual(status, 500)
        self.assertIn("error", resp)


if __name__ == "__main__":
    unittest.main()
