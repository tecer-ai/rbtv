#!/usr/bin/env python3
"""Engine suite — role-token contract v2 + generic no-literal-skin lint (PB v1.2).

Covers:
- §1  Role-token contract v2 presence (pass + fail-with-missing) via --check-themes.
- §2  Mixed-contract library: default 1.0 + a 2.0 theme validate independently.
- §3  Generic no-literal-skin lint — FLAG hex / rgb()-hsl() bare / named colors /
      inline url() / var(--undefinedRole); ALLOW var(--role) / color-mix(...var()) /
      transparent-inherit-currentColor-none / url(var()) / --client-accent; :root
      literals not flagged.
- §4  Structural-leak warning on a 2.0 theme that defines a .class.
- §5  --lint-no-literal CLI mode against a real deck-shaped file.
"""

import importlib.util
import json
import os
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


# A complete contract-2.0 (role-only) theme: every ROLE_CONTRACT_V2 token, no
# structural selectors. Used as the conforming v2 theme in mixed-contract tests.
ROLE_THEME_V2_COMPLETE = """:root {
  --field: #101418;
  --field-2: #161b21;
  --stage: #0b0e12;
  --ink-1: #f4f6f8;
  --ink-2: #c9ced6;
  --ink-3: #9aa1ab;
  --ink-4: #6b7280;
  --accent: #c79a5b;
  --accent-ink: #1a1206;
  --accent-ink-soft: #2a1e10;
  --accent-soft: rgba(199,154,91,0.18);
  --accent-soft-2: rgba(199,154,91,0.08);
  --accent-border: rgba(199,154,91,0.4);
  --highlight: #ffe6a8;
  --surface: #1a2027;
  --surface-2: #20272f;
  --hairline: rgba(255,255,255,0.08);
  --hairline-strong: rgba(255,255,255,0.16);
  --edge-accent: rgba(199,154,91,0.5);
  --shadow-panel: 0 8px 30px rgba(0,0,0,0.4);
  --shadow-card: 0 4px 16px rgba(0,0,0,0.3);
  --texture: url('assets/grain.png');
  --texture-hero: url('assets/grain-hero.png');
  --scrim: rgba(0,0,0,0.45);
  --scrim-hero: rgba(0,0,0,0.6);
  --positive: #4caf6f;
  --positive-glow: rgba(76,175,111,0.3);
  --negative: #d9534f;
  --font-display: "Georgia", serif;
  --font-body: "Inter", sans-serif;
  --font-mono: "Space Mono", monospace;
  --radius: 10px;
  --radius-lg: 18px;
  --hairline-w: 1px;
}
"""


class TestEngineRoleContract(unittest.TestCase):
    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_temp_library(self):
        tmp_parent = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_parent, ignore_errors=True)
        dst_fixture = os.path.join(tmp_parent, "fixture-library")
        dst_shared = os.path.join(tmp_parent, "shared-brand")
        shutil.copytree(FIXTURE_LIBRARY, dst_fixture)
        shutil.copytree(FIXTURE_SHARED_BRAND, dst_shared)
        shutil.copy2(ENGINE, os.path.join(dst_fixture, "assemble.py"))
        return dst_fixture

    def _run_engine(self, tmp_lib, args):
        cmd = [sys.executable, os.path.join(tmp_lib, "assemble.py")] + args
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8"
        )
        return result.returncode, result.stdout, result.stderr

    def _read_json_lib(self, tmp_lib):
        with open(os.path.join(tmp_lib, "library.json"), "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json_lib(self, tmp_lib, data):
        with open(os.path.join(tmp_lib, "library.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def _write(self, path, content):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _import_engine(self):
        spec = importlib.util.spec_from_file_location("assemble", ENGINE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _add_v2_theme(self, tmp_lib, name, css):
        """Drop a themes/{name}.css and register it as a contract_version 2.0
        theme in library.json. Returns the css file path."""
        css_path = os.path.join(tmp_lib, "themes", f"{name}.css")
        self._write(css_path, css)
        data = self._read_json_lib(tmp_lib)
        data.setdefault("themes", []).append({
            "name": name,
            "file": f"themes/{name}.css",
            "label": name.title(),
            "contract_version": "2.0",
        })
        self._write_json_lib(tmp_lib, data)
        return css_path

    # ═══════════════════════════════════════════════════════════════════════════
    # §1  Role-token contract v2 presence
    # ═══════════════════════════════════════════════════════════════════════════

    def test_v2_role_theme_complete_passes(self):
        """A complete v2 role theme passes --check-themes (default 1.0 unchanged)."""
        tmp_lib = self._make_temp_library()
        self._add_v2_theme(tmp_lib, "role-pass", ROLE_THEME_V2_COMPLETE)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--check-themes", "--json"])
        self.assertEqual(rc, 0, f"Expected exit 0. stdout={stdout} stderr={stderr}")
        self.assertTrue(json.loads(stdout)["ok"])

    def test_v2_role_theme_missing_token_fails_naming_it(self):
        """A v2 theme missing a role token FAILS, naming the missing token."""
        tmp_lib = self._make_temp_library()
        # Drop the --accent token entirely.
        broken = ROLE_THEME_V2_COMPLETE.replace(
            "  --accent: #c79a5b;\n", ""
        )
        self._add_v2_theme(tmp_lib, "role-broken", broken)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--check-themes", "--json"])
        self.assertNotEqual(rc, 0, f"Expected non-zero. stdout={stdout} stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(
            any("--accent" in e and "role-token contract v2" in e
                for e in envelope["errors"]),
            f"Expected missing --accent named for v2 contract: {envelope['errors']}",
        )

    def test_unknown_contract_version_fails(self):
        """A theme declaring an unknown contract_version is a loud error."""
        tmp_lib = self._make_temp_library()
        data = self._read_json_lib(tmp_lib)
        # graphite already exists at contract 1.0 — flip it to bogus.
        for t in data["themes"]:
            if t["name"] == "graphite":
                t["contract_version"] = "9.9"
        self._write_json_lib(tmp_lib, data)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--check-themes", "--json"])
        self.assertNotEqual(rc, 0)
        envelope = json.loads(stdout)
        self.assertTrue(
            any("unknown contract_version" in e and "9.9" in e
                for e in envelope["errors"]),
            f"Expected unknown-contract error: {envelope['errors']}",
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # §2  Mixed-contract library — each theme validated against its own contract
    # ═══════════════════════════════════════════════════════════════════════════

    def test_mixed_contract_validate_independently(self):
        """Default theme.css (1.0) + a complete 2.0 role theme both pass; the v1
        graphite theme is NOT held to the v2 role set and vice versa."""
        tmp_lib = self._make_temp_library()
        # graphite stays contract 1.0 (the class contract); add a complete v2.
        self._add_v2_theme(tmp_lib, "atlas", ROLE_THEME_V2_COMPLETE)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--check-themes", "--json"])
        self.assertEqual(rc, 0, f"Expected exit 0. stdout={stdout} stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"], f"errors={envelope['errors']}")

    def test_mixed_contract_v1_theme_not_held_to_v2(self):
        """A class-contract 1.0 theme (graphite) does NOT fail for lacking v2 role
        tokens — contracts are scoped per-theme."""
        tmp_lib = self._make_temp_library()
        # graphite has no --field/--accent role tokens; it must still pass at 1.0.
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--check-themes", "--json"])
        self.assertEqual(rc, 0, f"v1 graphite should pass. stderr={stderr}")
        self.assertTrue(json.loads(stdout)["ok"])

    # ═══════════════════════════════════════════════════════════════════════════
    # §3  Generic no-literal-skin lint (pure-function unit tests)
    # ═══════════════════════════════════════════════════════════════════════════

    def setUp(self):
        self.mod = self._import_engine()
        # Active role set = v2 roles ∪ injected tokens (--client-accent).
        self.allowed = set(self.mod.ROLE_CONTRACT_V2) | set(self.mod.INJECTED_TOKENS)

    def _lint_css(self, css):
        return self.mod.lint_no_literal_skin(css, False, allowed_tokens=self.allowed)

    def _lint_html(self, html):
        return self.mod.lint_no_literal_skin(html, True, allowed_tokens=self.allowed)

    # ── FLAG cases ──
    def test_flag_bare_hex(self):
        errs = self._lint_css(".card { color: #ff0044; }")
        self.assertTrue(any("hex" in e for e in errs), errs)

    def test_flag_rgb_bare_numbers(self):
        errs = self._lint_css(".card { background: rgb(12, 34, 56); }")
        self.assertTrue(any("color function" in e for e in errs), errs)

    def test_flag_hsl_bare_numbers(self):
        errs = self._lint_css(".card { color: hsl(200, 50%, 40%); }")
        self.assertTrue(any("color function" in e for e in errs), errs)

    def test_flag_named_color_in_skin_prop(self):
        errs = self._lint_css(".card { color: white; }")
        self.assertTrue(any("named color" in e for e in errs), errs)

    def test_flag_inline_url_background_image(self):
        html = '<section style="background-image:url(\'bg.jpg\')"></section>'
        errs = self._lint_html(html)
        self.assertTrue(
            any("inline background image" in e for e in errs), errs
        )

    def test_flag_undefined_role_token(self):
        """var(--navy) in a skin prop flags ONLY because --navy is not a known
        role — proving GENERIC derivation, not a hardcoded palette blocklist."""
        errs = self._lint_css(".card { color: var(--navy); }")
        self.assertTrue(
            any("undefined role token --navy" in e for e in errs), errs
        )

    def test_flag_undefined_token_generic_not_palette(self):
        """An arbitrary undefined token (not in tecer's old palette) also flags —
        the check is set-membership, not a fixed name list."""
        errs = self._lint_css(".card { color: var(--totally-made-up); }")
        self.assertTrue(
            any("undefined role token --totally-made-up" in e for e in errs), errs
        )

    # ── ALLOW cases ──
    def test_allow_defined_role_var(self):
        # --accent is a v2 role → legitimate.
        self.assertEqual(self._lint_css(".card { color: var(--accent); }"), [])

    def test_allow_color_mix_with_var(self):
        css = ".card { background: color-mix(in srgb, var(--accent) 40%, var(--surface)); }"
        self.assertEqual(self._lint_css(css), [])

    def test_allow_css_wide_keywords(self):
        for kw in ("transparent", "inherit", "currentColor", "none"):
            self.assertEqual(
                self._lint_css(f".card {{ background: {kw}; }}"), [],
                f"{kw} should be allowed",
            )

    def test_allow_url_var_texture(self):
        self.assertEqual(
            self._lint_css(".card { background-image: url(var(--texture)); }"), []
        )

    def test_allow_client_accent_injected_token(self):
        # --client-accent is injected per-deck → always legitimate.
        self.assertEqual(self._lint_css(".kicker { color: var(--client-accent); }"), [])

    def test_root_literals_not_flagged(self):
        """Literal values inside :root are token DEFINITIONS, never flagged."""
        css = (
            ":root { --accent: #c79a5b; --surface: rgb(20,30,40); }\n"
            ".card { color: var(--accent); }"
        )
        self.assertEqual(self._lint_css(css), [])

    def test_non_skin_property_literal_not_flagged(self):
        """A literal in a non-skin property (e.g. font-size) is never flagged."""
        self.assertEqual(self._lint_css(".card { font-size: 18px; }"), [])

    # ═══════════════════════════════════════════════════════════════════════════
    # §4  Structural-leak warning on a 2.0 role-only theme
    # ═══════════════════════════════════════════════════════════════════════════

    def test_v2_structural_leak_warns(self):
        """A 2.0 theme that defines a structural selector draws a WARNING (not an
        error) while still passing the role-presence check."""
        tmp_lib = self._make_temp_library()
        leaky = ROLE_THEME_V2_COMPLETE + "\n.card { padding: 24px; }\n"
        self._add_v2_theme(tmp_lib, "leaky", leaky)
        rc, stdout, stderr = self._run_engine(tmp_lib, ["--check-themes", "--json"])
        self.assertEqual(rc, 0, f"Leak is a warning, not an error. stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertTrue(envelope["ok"])
        self.assertTrue(
            any("contract 2.0" in w and ".card" in w for w in envelope["warnings"]),
            f"Expected structural-leak warning naming .card: {envelope['warnings']}",
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # §5  --lint-no-literal CLI mode against a deck-shaped file
    # ═══════════════════════════════════════════════════════════════════════════

    def test_cli_lint_no_literal_flags_and_passes(self):
        """The --lint-no-literal CLI mode flags a deck with a literal skin value
        and passes a clean one; the allowlist is derived from the library."""
        tmp_lib = self._make_temp_library()
        # Register a v2 contract so --field etc. are legitimate roles.
        self._add_v2_theme(tmp_lib, "atlas", ROLE_THEME_V2_COMPLETE)

        dirty = os.path.join(tmp_lib, "dirty.html")
        self._write(dirty, (
            "<html><head><style>\n"
            ".slide { background: #112233; }\n"
            ".kicker { color: var(--client-accent); }\n"
            "</style></head><body></body></html>"
        ))
        rc, stdout, stderr = self._run_engine(
            tmp_lib, ["--lint-no-literal", dirty, "--json"]
        )
        self.assertNotEqual(rc, 0, f"Expected flag. stdout={stdout} stderr={stderr}")
        envelope = json.loads(stdout)
        self.assertFalse(envelope["ok"])
        self.assertTrue(any("hex" in e for e in envelope["errors"]), envelope["errors"])

        clean = os.path.join(tmp_lib, "clean.html")
        self._write(clean, (
            "<html><head><style>\n"
            ".slide { background: var(--field); color: var(--ink-1); }\n"
            ".kicker { color: var(--client-accent); }\n"
            ".card { background: color-mix(in srgb, var(--accent) 30%, var(--surface)); }\n"
            "</style></head><body></body></html>"
        ))
        rc, stdout, stderr = self._run_engine(
            tmp_lib, ["--lint-no-literal", clean, "--json"]
        )
        self.assertEqual(rc, 0, f"Clean deck should pass. stdout={stdout} stderr={stderr}")
        self.assertTrue(json.loads(stdout)["ok"])

    def test_cli_lint_no_literal_undefined_token_flagged(self):
        """A var(--undefinedRole) in a skin prop is flagged by the CLI, derived
        generically from the library's contracts."""
        tmp_lib = self._make_temp_library()
        self._add_v2_theme(tmp_lib, "atlas", ROLE_THEME_V2_COMPLETE)
        deck = os.path.join(tmp_lib, "undef.html")
        self._write(deck, (
            "<html><head><style>\n"
            ".slide { color: var(--made-up-role); }\n"
            "</style></head><body></body></html>"
        ))
        rc, stdout, stderr = self._run_engine(
            tmp_lib, ["--lint-no-literal", deck, "--json"]
        )
        self.assertNotEqual(rc, 0)
        envelope = json.loads(stdout)
        self.assertTrue(
            any("undefined role token --made-up-role" in e
                for e in envelope["errors"]),
            envelope["errors"],
        )


if __name__ == "__main__":
    unittest.main()
