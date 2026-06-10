#!/usr/bin/env python3
"""PB-T4 — DT5-procedure self-test + install-engine test."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "..", "assemble.py")
INSTALL_ENGINE = os.path.join(HERE, "..", "install-engine.py")
FIXTURE_PARENT = os.path.abspath(os.path.join(HERE, "..", "..", "tests"))
FIXTURE_LIBRARY = os.path.join(FIXTURE_PARENT, "fixture-library")
FIXTURE_SHARED_BRAND = os.path.join(FIXTURE_PARENT, "shared-brand")

SEED_SLIDES = [
    "cover-nimbus.en", "intro-pillars", "problem-cards",
    "how-nimbus-works", "nimbus-divider", "proof-metrics", "closing-nimbus",
]

EXPECTED_TOKENS = {
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


class _SkeletonParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skeleton = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = sorted(attrs_dict.get("class", "").split())
        self.skeleton.append((tag, classes))

    def handle_startendtag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = sorted(attrs_dict.get("class", "").split())
        self.skeleton.append((tag, classes))


class TestEngineDT5(unittest.TestCase):
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

    def _run_install_engine(self, args):
        cmd = [sys.executable, INSTALL_ENGINE] + args
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return result.returncode, result.stdout, result.stderr

    def _read_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_skeleton(self, html_text):
        parser = _SkeletonParser()
        parser.feed(html_text)
        return parser.skeleton

    def _get_asset_set(self, deck_dir):
        assets_dir = os.path.join(deck_dir, "assets")
        if not os.path.isdir(assets_dir):
            return set()
        return set(f for f in os.listdir(assets_dir) if os.path.isfile(os.path.join(assets_dir, f)))

    def _asset_refs_in_html(self, html_text):
        return set(re.findall(r' src="assets/([^"]+)"', html_text))

    # ═══════════════════════════════════════════════════════════════════════════
    # §1.5  DT5-procedure self-test (convention-spec §4.4 checks 1–4)
    # ═══════════════════════════════════════════════════════════════════════════

    def test_dt5_procedure_self_test(self):
        """Re-assemble seed twice; assert order, skeleton, assets, tokens."""
        tmp_lib_a = self._make_temp_library()
        tmp_lib_b = self._make_temp_library()
        out_a = os.path.join(tmp_lib_a, "deck_a.html")
        out_b = os.path.join(tmp_lib_b, "deck_b.html")
        client_logo = os.path.join(os.path.dirname(tmp_lib_a), "shared-brand", "partner-mark.png")

        # Assemble both decks (Check 1 — order identity is implicit in preset)
        results = []
        for tmp_lib, out in ((tmp_lib_a, out_a), (tmp_lib_b, out_b)):
            rc, stdout, stderr = self._run_engine(tmp_lib, [
                "--preset", "nimbus-intro-en", "--out", out,
                "--client-logo", client_logo, "--json", "--no-log"
            ])
            self.assertEqual(rc, 0, f"Assembly failed: {stdout} {stderr}")
            envelope = json.loads(stdout)
            self.assertEqual(envelope["as_built_entry"]["slides"], SEED_SLIDES)
            results.append((tmp_lib, out, envelope))

        # Check 2 — per-slide skeleton equality (excluding text content)
        text_a = self._read_file(out_a)
        text_b = self._read_file(out_b)
        skel_a = self._parse_skeleton(text_a)
        skel_b = self._parse_skeleton(text_b)
        self.assertEqual(skel_a, skel_b, "HTML skeletons differ between reproductions")

        # Check 3 — asset parity + references resolve
        assets_a = self._get_asset_set(os.path.dirname(out_a))
        assets_b = self._get_asset_set(os.path.dirname(out_b))
        self.assertEqual(assets_a, assets_b, "Asset filename sets differ")

        refs_a = self._asset_refs_in_html(text_a)
        refs_b = self._asset_refs_in_html(text_b)
        self.assertEqual(refs_a, refs_b, "Asset references in HTML differ")
        for name in assets_a:
            self.assertTrue(
                os.path.exists(os.path.join(os.path.dirname(out_a), "assets", name)),
                f"Asset missing on disk: {name}"
            )
        for name in refs_a:
            self.assertIn(name, assets_a, f"Referenced asset not in assets/: {name}")

        # Check 4 — clean token report
        rc, stdout, stderr = self._run_engine(tmp_lib_a, ["--check", out_a, "--json"])
        self.assertEqual(rc, 1)
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        actual_tokens = set(envelope["unfilled_tokens"])
        self.assertEqual(actual_tokens, EXPECTED_TOKENS,
                         f"Token mismatch: {actual_tokens ^ EXPECTED_TOKENS}")

    # ═══════════════════════════════════════════════════════════════════════════
    # §1.6  install-engine test
    # ═══════════════════════════════════════════════════════════════════════════

    def test_install_engine(self):
        """install-engine copies assemble.py and syncs engine_version to 1.0."""
        if not os.path.exists(INSTALL_ENGINE):
            self.skipTest("install-engine.py not present (PB-T5 has not landed)")
        tmp_lib = self._make_temp_library()
        lib_json = os.path.join(tmp_lib, "library.json")
        with open(lib_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["engine_version"] = "0.9"
        with open(lib_json, "w", encoding="utf-8") as f:
            json.dump(data, f)

        rc, stdout, stderr = self._run_install_engine(["--library", tmp_lib])
        self.assertEqual(rc, 0, f"install-engine failed: {stdout} {stderr}")

        target_assemble = os.path.join(tmp_lib, "assemble.py")
        with open(target_assemble, "rb") as f:
            target_bytes = f.read()
        with open(ENGINE, "rb") as f:
            source_bytes = f.read()
        self.assertEqual(target_bytes, source_bytes, "assemble.py bytes differ")

        with open(lib_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("engine_version"), "1.0")

    def test_install_engine_missing_library_json(self):
        """Missing target library.json → exit 1."""
        if not os.path.exists(INSTALL_ENGINE):
            self.skipTest("install-engine.py not present (PB-T5 has not landed)")
        tmp_dir = tempfile.mkdtemp()
        rc, stdout, stderr = self._run_install_engine(["--library", tmp_dir])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
