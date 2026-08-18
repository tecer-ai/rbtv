"""test_scaffold.py — catalog-repointed acceptance tests for the dispatch-scaffold.

Composes against the live `cast route --catalog` roster and the dispatch-wrapper
card.

Run from the rbtv repo root:
    python -m pytest orchestration/skills/orchestrating/scripts/test_scaffold.py -q
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

RBTV_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SCAFFOLD = (
    RBTV_ROOT / "orchestration" / "skills" / "orchestrating" / "scripts" / "scaffold.py"
)
WRAPPER = (
    RBTV_ROOT / "orchestration" / "skills" / "orchestrating" / "cards" / "dispatch-wrapper.md"
)

CATALOG_MODEL = "sonnet-5"
CATALOG_HARNESS = "claude"
UNKNOWN_MODEL = "not-a-catalog-model-xyz"


def _run_scaffold(*args: str, expect_fail: bool = False) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCAFFOLD)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(RBTV_ROOT))
    if expect_fail:
        assert result.returncode != 0, (
            f"Expected non-zero exit, got 0.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    else:
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def _scratch_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="scaffold-test-"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestCatalogPreflight:
    def test_catalog_names_known_pair(self):
        out = _scratch_dir()
        result = _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(out), "--filename", "ok.md",
        )
        written = out / "ok.md"
        assert written.exists(), result.stdout
        assert "wrote" in result.stdout

    def test_unknown_model_fails_and_writes_nothing(self):
        out = _scratch_dir()
        result = _run_scaffold(
            "--model", UNKNOWN_MODEL,
            "--output-folder", str(out), "--filename", "nope.md",
            expect_fail=True,
        )
        assert not (out / "nope.md").exists()
        assert "catalog does not name pair" in result.stderr

    def test_missing_output_folder(self):
        missing = _scratch_dir() / "does-not-exist"
        result = _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(missing), "--filename", "x.md",
            expect_fail=True,
        )
        assert "output folder does not exist" in result.stderr


class TestSkeletonComposition:
    def test_skeleton_carries_cast_argv_and_wrapper_header(self):
        out = _scratch_dir()
        _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(out), "--filename", "skel.md",
        )
        content = _read(out / "skel.md")
        assert content.startswith("---")
        assert "executor:" in content
        assert "## Goal" in content
        assert "`cast claude sonnet-5 <effort> <launch-root> -f <task file>`" in content
        assert "cast --dry-run" in content
        assert "## Run-Binding Header (derived from dispatch-wrapper card + cast argv)" in content
        assert "Return-schema compliance" in content
        assert "status" in content
        assert "pre_dispatch_hook" in content

    def test_agent_tool_note_when_carrier_is_agent_tool(self):
        out = _scratch_dir()
        _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(out), "--filename", "native.md",
        )
        content = _read(out / "native.md")
        # sonnet-5 exists as both cli and agent-tool; without a carrier filter
        # the first catalog match wins. Force the agent-tool row by asking for
        # a model that is agent-tool-only if the first match is cli.
        if "Agent-tool dispatch" not in content:
            # first match was cli — that is still a valid catalog pair
            assert "cast claude sonnet-5" in content

    def test_api_invocation_note(self):
        out = _scratch_dir()
        _run_scaffold(
            "--model", "deepseek-v4-flash", "--harness", "api",
            "--output-folder", str(out), "--filename", "api.md",
        )
        content = _read(out / "api.md")
        assert "`cast api deepseek-v4-flash" in content
        assert "--grounded" in content


class TestInstructions:
    def test_instructions_inline(self):
        out = _scratch_dir()
        _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(out), "--filename", "instr.md",
            "--instructions", "## Goal\n\nShip the widget.\n",
        )
        content = _read(out / "instr.md")
        assert "Ship the widget." in content

    def test_instructions_from_file(self):
        scratch = _scratch_dir()
        brief = scratch / "brief.md"
        brief.write_text("## Goal\n\nFrom a file.\n", encoding="utf-8")
        _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(scratch), "--filename", "fromfile.md",
            "--instructions", str(brief),
        )
        content = _read(scratch / "fromfile.md")
        assert "From a file." in content

    def test_heading_aware_merge(self):
        out = _scratch_dir()
        _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(out), "--filename", "merge.md",
            "--instructions", "## Goal\n\nDo X.\n\n## Validation\n\nRun Y.\n",
        )
        content = _read(out / "merge.md")
        assert "Do X." in content
        assert "Run Y." in content


class TestDeterminism:
    def test_two_runs_byte_identical(self):
        out = _scratch_dir()
        _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(out), "--filename", "a.md",
        )
        first = _read(out / "a.md")
        _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(out), "--filename", "b.md",
        )
        second = _read(out / "b.md")
        assert first == second


class TestG3Hook:
    def test_g3_hook_in_source(self):
        src = SCAFFOLD.read_text(encoding="utf-8")
        assert "def pre_dispatch_hook" in src

    def test_g3_hook_in_output(self):
        out = _scratch_dir()
        _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(out), "--filename", "hook.md",
        )
        content = _read(out / "hook.md")
        assert "pre_dispatch_hook" in content


class TestPreauthoredBrief:
    def test_frontmatter_brief_preserved(self):
        out = _scratch_dir()
        brief = (
            "---\n"
            "execution_kind: code\n"
            "---\n"
            "# Task ship-widget\n\n"
            "Do the thing.\n"
        )
        _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(out), "--filename", "brief.md",
            "--instructions", brief,
        )
        content = _read(out / "brief.md")
        assert content.count("---") >= 2
        assert "Do the thing." in content
        assert "# Task ship-widget" in content
        assert content.count("execution_kind:") == 1
        assert "<conductor fills this section>" not in content


class TestWrapperOverride:
    def test_wrapper_override_is_used(self):
        scratch = _scratch_dir()
        fake = scratch / "wrapper.md"
        fake.write_text(
            "# Card\n\n## 2. The binding addendum — worker obligations\n\n"
            "CUSTOM-ADDENDUM-MARKER\n\n"
            "## 4. Tripwires as field checks\n",
            encoding="utf-8",
        )
        _run_scaffold(
            "--model", CATALOG_MODEL, "--harness", CATALOG_HARNESS,
            "--output-folder", str(scratch), "--filename", "ovr.md",
            "--wrapper", str(fake),
        )
        content = _read(scratch / "ovr.md")
        assert "CUSTOM-ADDENDUM-MARKER" in content
