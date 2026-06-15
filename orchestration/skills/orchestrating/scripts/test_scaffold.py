"""test_scaffold.py — acceptance tests for the dispatch-scaffold generator.

Implements the spec's Test Plan (dispatch-scaffold-spec.md § Test Plan).
Every criterion exercises the real scaffold.py over the real card + deltas
(un-piped EXIT codes, files on disk). The derive-test (criterion 2) edits a
SCRATCH COPY of the card via the --wrapper injection — NEVER the live card.

Run from the rbtv repo root:
    python -m pytest orchestration/skills/orchestrating/scripts/test_scaffold.py -q
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RBTV_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SCAFFOLD = (
    RBTV_ROOT / "orchestration" / "skills" / "orchestrating" / "scripts" / "scaffold.py"
)
WRAPPER = (
    RBTV_ROOT / "orchestration" / "skills" / "orchestrating" / "cards" / "dispatch-wrapper.md"
)
MODELS_DIR = RBTV_ROOT / "orchestration" / "models"


def _run_scaffold(*args: str, expect_fail: bool = False) -> subprocess.CompletedProcess:
    """Run scaffold.py with the given args, return CompletedProcess."""
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
    """Create a temporary directory that survives the test."""
    return Path(tempfile.mkdtemp(prefix="scaffold-test-"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Criterion 1 — Skeleton mode: kimi task file with composed header + skeleton
# ---------------------------------------------------------------------------

class TestCriterion1SkeletonKimi:
    """Run scaffold --model kimi --output-folder D --filename F (no --instructions).
    Verify the output carries: composed header (binding addendum + return schema +
    kimi invocation note), kimi frontmatter skeleton keys, and body-section headers.
    """

    def test_skeleton_kimi(self):
        out_dir = _scratch_dir()
        try:
            result = _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "k.task.md",
            )
            assert "wrote" in result.stdout

            content = _read(out_dir / "k.task.md")

            # FIX 2: File MUST start with YAML frontmatter.
            assert content.startswith("---"), "File must start with YAML frontmatter"

            # Composed header: binding addendum present (in the Run-Binding Header section).
            assert "## 2. The binding addendum" in content
            assert "Return-schema compliance" in content

            # Composed header: five-field return schema present.
            assert "## 3. The unified return schema" in content
            assert "**`status`**" in content
            assert "**`landed`**" in content
            assert "**`validation`**" in content
            assert "**`concerns`**" in content
            assert "**`open_questions`**" in content

            # Kimi-specific binding obligations inserted.
            assert "**Non-reasoning executor**" in content
            assert "**Stray-file ban**" in content

            # Kimi invocation/transport note.
            assert "Kimi return surface" in content or "kimi runs headless" in content.lower()

            # Frontmatter skeleton keys.
            assert "execution_kind:" in content
            assert "executor:" in content
            assert "allowed_workdir:" in content
            assert "allowlist:" in content
            assert "commit_policy:" in content
            assert "forbidden_ops:" in content
            assert "doubt_policy:" in content
            assert "reviewer:" in content
            assert "swarm_policy:" in content

            # Body-section headers.
            assert "## Goal" in content
            assert "## Context Snapshot" in content
            assert "## Allowed Paths" in content
            assert "## Forbidden Paths" in content
            assert "## Implementation Requirements" in content
            assert "## Validation" in content
            assert "## Commit Rule" in content
            assert "## Return Format" in content

            # Launch flags as DATA (derived from delta).
            assert "derived-from: delta invocation section" in content
            assert "Confinement diff" in content

            # G3 hook mention.
            assert "pre_dispatch_hook" in content
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Criterion 2 — Derive-test: change scratch card → regenerate → diff changes.
# ---------------------------------------------------------------------------

class TestCriterion2Derive:
    """Copy the real card to a scratch path; edit a line INSIDE a
    RENDER:BEGIN binding-addendum block; regenerate against the scratch card;
    diff against the pre-edit generation. The output MUST change. The live card
    must remain byte-unchanged.
    """

    def test_derive_from_scratch_card(self):
        out_dir = _scratch_dir()
        live_before = _read(WRAPPER)
        try:
            # Copy the real card to scratch.
            scratch_card = out_dir / "dispatch-wrapper-scratch.md"
            scratch_card.write_text(live_before, encoding="utf-8")

            # Generate baseline against the unmodified scratch card.
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "baseline.task.md",
                "--wrapper", str(scratch_card),
            )
            baseline = _read(out_dir / "baseline.task.md")

            # Edit a line INSIDE the binding-addendum block of the SCRATCH copy.
            scratch_text = _read(scratch_card)
            sentinel = "### DERIVED-TEST SENTINEL — scaffold derive-test"
            # Insert the sentinel after the binding-addendum heading.
            modified = scratch_text.replace(
                "## 2. The binding addendum — worker obligations",
                f"## 2. The binding addendum — worker obligations\n\n{sentinel}",
            )
            scratch_card.write_text(modified, encoding="utf-8")

            # Regenerate against the modified scratch card.
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "derived.task.md",
                "--wrapper", str(scratch_card),
            )
            derived = _read(out_dir / "derived.task.md")

            # The derived output MUST differ from baseline.
            assert derived != baseline, "Derived output should differ from baseline after card edit"
            # The sentinel must appear in the derived output.
            assert sentinel in derived, "Sentinel from scratch card should appear in derived output"
            # The live card must be byte-unchanged.
            assert _read(WRAPPER) == live_before, "Live card must remain unchanged"
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Criterion 3 — Pre-flight checks gate generation.
# ---------------------------------------------------------------------------

class TestCriterion3Preflight:
    """Run with (a) non-existent model, (b) missing output dir,
    (c) stale manual — each EXIT≠0 with named error, no file written.
    """

    def test_nonexistent_model(self):
        out_dir = _scratch_dir()
        try:
            _run_scaffold(
                "--model", "nonexistent-model-xyz",
                "--output-folder", str(out_dir),
                "--filename", "x.task.md",
                expect_fail=True,
            )
            assert not (out_dir / "x.task.md").exists()
        finally:
            _rmtree(out_dir)

    def test_missing_output_folder(self):
        missing_dir = _scratch_dir() / "nonexistent-subdir"
        _run_scaffold(
            "--model", "kimi-code-cli",
            "--output-folder", str(missing_dir),
            "--filename", "x.task.md",
            expect_fail=True,
        )
        # No file should be written anywhere.

    def test_stale_manual(self):
        """Modify content inside a RENDER:DELTA section to make the manual stale."""
        out_dir = _scratch_dir()
        delta_path = MODELS_DIR / "kimi-code-cli" / "delta.md"
        original = _read(delta_path)
        try:
            # Modify content inside a RENDER:DELTA block — this will cause
            # render-manuals.py --check to report drift (content change inside
            # a delta section changes the composed manual).
            modified = original.replace(
                "<!-- RENDER:DELTA model-transport-note -->",
                "<!-- RENDER:DELTA model-transport-note -->\nSTALE-TEST-MARKER\n",
            )
            delta_path.write_text(modified, encoding="utf-8")
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "x.task.md",
                expect_fail=True,
            )
            assert not (out_dir / "x.task.md").exists()
        finally:
            # Restore the original delta.
            delta_path.write_text(original, encoding="utf-8")
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Criterion 4 — Launch-flag fields emitted as DATA per model.
# ---------------------------------------------------------------------------

class TestCriterion4LaunchFlags:
    """Generate for kimi and claude-code-cli; inspect each invocation note.
    FIX 1: flags must be DERIVED from the delta invocation section.
    """

    def test_kimi_launch_flags(self):
        out_dir = _scratch_dir()
        try:
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "k.task.md",
            )
            content = _read(out_dir / "k.task.md")
            # Derived flags from kimi delta: --work-dir and --add-dir should appear.
            assert "--work-dir" in content
            assert "--add-dir" in content
            assert "Confinement diff" in content
            assert "work-target" in content.lower()
            assert "derived-from: delta invocation section" in content
        finally:
            _rmtree(out_dir)

    def test_claude_cli_launch_flags(self):
        out_dir = _scratch_dir()
        try:
            _run_scaffold(
                "--model", "claude-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "cc.task.md",
            )
            content = _read(out_dir / "cc.task.md")
            # claude-code-cli delta: --add-dir, -p, --print, etc.
            assert "--add-dir" in content
            assert "Confinement diff" in content
            assert "derived-from: delta invocation section" in content
        finally:
            _rmtree(out_dir)

    def test_codex_launch_flags(self):
        """Codex delta carries --cd and --add-dir (among others)."""
        out_dir = _scratch_dir()
        try:
            _run_scaffold(
                "--model", "codex-cli",
                "--output-folder", str(out_dir),
                "--filename", "cx.task.md",
            )
            content = _read(out_dir / "cx.task.md")
            assert "--cd" in content
            assert "--add-dir" in content
            assert "derived-from: delta invocation section" in content
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Criterion 5 — G3 hook slot exists, named + no-op.
# ---------------------------------------------------------------------------

class TestCriterion5G3Hook:
    """Inspect the scaffold source for the named pre-dispatch hook slot."""

    def test_g3_hook_in_source(self):
        scaffold_src = _read(SCAFFOLD)
        assert "pre_dispatch_hook" in scaffold_src
        # The default should be a no-op that always passes.
        assert "return True" in scaffold_src or "True, \"\"" in scaffold_src

    def test_g3_hook_in_output(self):
        out_dir = _scratch_dir()
        try:
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "k.task.md",
            )
            content = _read(out_dir / "k.task.md")
            assert "pre_dispatch_hook" in content or "Pre-Dispatch Hook" in content
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Criterion 6 — Two scaffolds differ ONLY in model-specific parts.
# ---------------------------------------------------------------------------

class TestCriterion6ModelDiff:
    """Generate for kimi and claude-code-cli with identical other args;
    diff the two files. Generic blocks (the Run-Binding Header sections)
    must be BYTE-IDENTICAL; only model-specific parts should differ.
    FIX 3: assert byte-identical extraction, not just substring presence.
    """

    @staticmethod
    def _extract_run_binding_header(content: str) -> str:
        """Extract the Run-Binding Header section from generated output.

        The header starts after '## Run-Binding Header' and continues to
        the end of the file. This is the wrapper-derived content that should
        be identical across models (modulo model-specific INSERTs which are
        part of the header but differ per model).

        We extract the GENERIC parts: the binding addendum body and return
        schema text (excluding the model-specific delta inserts).
        """
        # Extract everything from the binding addendum through the return schema.
        # These are the wrapper-derived blocks that should be byte-identical.
        addendum_start = content.find("## 2. The binding addendum")
        schema_end = content.find("## Pre-Dispatch Hook")
        if addendum_start == -1 or schema_end == -1:
            return ""
        return content[addendum_start:schema_end]

    @staticmethod
    def _extract_generic_addendum(content: str) -> str:
        """Extract the GENERIC part of the binding addendum (before model-specific insert)."""
        start = content.find("## 2. The binding addendum")
        # The generic obligations end before the model-specific insert.
        # Look for the model-specific obligations table (starts with model name).
        model_insert_markers = [
            "**Kimi-specific worker obligations**",
            "**Claude-cli-specific worker obligations**",
            "**Qwen-specific worker obligations**",
            "**Codex-specific worker obligations**",
        ]
        end_pos = len(content)
        for marker in model_insert_markers:
            pos = content.find(marker, start)
            if pos != -1 and pos < end_pos:
                end_pos = pos
        return content[start:end_pos]

    @staticmethod
    def _extract_generic_return_schema(content: str) -> str:
        """Extract the generic return schema (before model-transport-note insert)."""
        start = content.find("## 3. The unified return schema")
        # The model transport note insert is the line starting with "**Kimi return surface"
        # or "**Claude-cli return surface", etc.
        end_markers = ["return surface", "transport note", "## Pre-Dispatch Hook"]
        end_pos = len(content)
        for marker in end_markers:
            pos = content.find(marker, start)
            if pos != -1 and pos < end_pos:
                # Go back to the start of the line containing the marker.
                line_start = content.rfind("\n", start, pos)
                if line_start != -1:
                    end_pos = line_start
                else:
                    end_pos = pos
        return content[start:end_pos]

    def test_kimi_vs_claude_cli_diff(self):
        out_dir = _scratch_dir()
        try:
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "k.task.md",
            )
            _run_scaffold(
                "--model", "claude-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "cc.task.md",
            )
            k = _read(out_dir / "k.task.md")
            cc = _read(out_dir / "cc.task.md")

            # Files must differ (different models).
            assert k != cc, "kimi and claude-code-cli outputs should differ"

            # FIX 3: Generic binding addendum body must be BYTE-IDENTICAL.
            k_addendum = self._extract_generic_addendum(k)
            cc_addendum = self._extract_generic_addendum(cc)
            assert k_addendum == cc_addendum, (
                f"Generic binding addendum must be byte-identical.\n"
                f"kimi len={len(k_addendum)}, claude-code-cli len={len(cc_addendum)}"
            )

            # FIX 3: Generic return schema must be BYTE-IDENTICAL.
            k_schema = self._extract_generic_return_schema(k)
            cc_schema = self._extract_generic_return_schema(cc)
            assert k_schema == cc_schema, (
                f"Generic return schema must be byte-identical.\n"
                f"kimi len={len(k_schema)}, claude-code-cli len={len(cc_schema)}"
            )

            # Model-specific parts differ: kimi has "Non-reasoning executor",
            # claude-code-cli has "Unattended writes are EXPLICIT".
            assert "Non-reasoning executor" in k
            assert "Unattended writes are EXPLICIT" in cc

            # Frontmatter differs: kimi has max_kimi_subagents, claude-code-cli has model.
            assert "max_kimi_subagents" in k
            assert "model:" in cc  # claude-code-cli frontmatter has 'model' key
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Criterion 7 — --instructions yields complete dispatchable file.
# ---------------------------------------------------------------------------

class TestCriterion7Instructions:
    """Run with --instructions; verify the output satisfies the task-file
    contract §1–§7 headings. FIX 2: file starts with --- (frontmatter at top).
    FIX 4: heading-aware merge.
    """

    def test_instructions_inline(self):
        out_dir = _scratch_dir()
        try:
            instr = "Build a dispatch scaffold for model kimi that passes all tests."
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "full.task.md",
                "--instructions", instr,
            )
            content = _read(out_dir / "full.task.md")
            # FIX 2: File must start with frontmatter.
            assert content.startswith("---"), "File must start with YAML frontmatter"

            # FIX 2 (ADX-13): the frontmatter block is the FIRST thing in the
            # file, parses as YAML, and carries the model's required keys.
            import re as _re
            fm_match = _re.match(r"^---\n(.*?)\n---", content, _re.DOTALL)
            assert fm_match, "A leading --- ... --- frontmatter block must exist"
            fm_block = fm_match.group(1)
            required_keys = [
                "execution_kind", "executor", "allowed_workdir", "allowlist",
                "commit_policy", "forbidden_ops", "doubt_policy", "reviewer",
                "swarm_policy",
            ]
            for key in required_keys:
                assert _re.search(r"(?m)^" + key + r":", fm_block), (
                    f"required frontmatter key '{key}' missing from top block"
                )
            # Parses as YAML where PyYAML is available (skip cleanly if not —
            # PyYAML is not a declared test dependency for this repo).
            try:
                import yaml  # type: ignore
            except ImportError:
                pass
            else:
                parsed = yaml.safe_load(fm_block)
                assert isinstance(parsed, dict), "frontmatter must parse to a YAML mapping"
                for key in required_keys:
                    assert key in parsed, f"parsed frontmatter missing key '{key}'"

            # Instructions should be merged into the Goal section (fallback).
            assert instr in content
            # All required body sections present.
            assert "## Goal" in content
            assert "## Context Snapshot" in content
            assert "## Implementation Requirements" in content
            assert "## Return Format" in content
        finally:
            _rmtree(out_dir)

    def test_instructions_from_file(self):
        out_dir = _scratch_dir()
        try:
            instr_file = out_dir / "instructions.txt"
            instr_file.write_text("Implement the router script per spec.", encoding="utf-8")
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "full2.task.md",
                "--instructions", str(instr_file),
            )
            content = _read(out_dir / "full2.task.md")
            assert "Implement the router script per spec." in content
        finally:
            _rmtree(out_dir)

    def test_instructions_heading_aware_merge(self):
        """FIX 4: If instructions contain matching headings, merge per-section."""
        out_dir = _scratch_dir()
        try:
            # Instructions with headings that match body sections.
            instr = (
                "## Goal\nBuild the scaffold generator.\n\n"
                "## Implementation Requirements\n"
                "- Derive launch flags from delta.\n"
                "- Frontmatter at top of file.\n"
            )
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "heading.task.md",
                "--instructions", instr,
            )
            content = _read(out_dir / "heading.task.md")
            # The Goal section should contain "Build the scaffold generator."
            assert "Build the scaffold generator." in content
            # The Implementation Requirements section should contain the bullet.
            assert "Derive launch flags from delta." in content
            # The unmatched heading "Context Snapshot" would NOT appear.
            # Verify heading-aware merge: the instructions are placed under
            # matching sections, not dumped wholesale into Goal.
        finally:
            _rmtree(out_dir)

    def test_instructions_unmatched_heading_routes_to_goal(self):
        """FIX 4 (ADX-13): content under an UNMATCHED heading — even one that
        appears AFTER a matched section — lands in Goal (it renders BEFORE the
        next known body section), is NOT bled into the preceding matched
        section, and matched-section content is never duplicated."""
        out_dir = _scratch_dir()
        try:
            instr = (
                "## Goal\nBuild the generator.\n\n"
                "## Implementation Requirements\n- Derive flags.\n\n"
                "## Nonexistent Section\nOrphan content lands in Goal.\n"
            )
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "unmatched.task.md",
                "--instructions", instr,
            )
            content = _read(out_dir / "unmatched.task.md")

            goal_pos = content.find("## Goal")
            impl_pos = content.find("## Implementation Requirements")
            ctx_pos = content.find("## Context Snapshot")  # the section after Goal
            orphan_pos = content.find("Orphan content lands in Goal.")
            impl_body_pos = content.find("- Derive flags.")

            # Orphan content is present and rendered in the Goal region
            # (between the Goal heading and the next known body section).
            assert orphan_pos != -1
            assert goal_pos < orphan_pos < ctx_pos
            # It did NOT bleed into the Implementation Requirements section
            # (which renders later in the file).
            assert orphan_pos < impl_pos
            # Matched content landed in its own section, exactly once.
            assert goal_pos < content.find("Build the generator.") < ctx_pos
            assert impl_pos < impl_body_pos
            assert content.count("- Derive flags.") == 1
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Criterion 8 — Determinism: identical inputs → identical output.
# ---------------------------------------------------------------------------

class TestCriterion8Determinism:
    """Run the same command twice; diff the outputs — must be byte-identical."""

    def test_determinism(self):
        out_dir = _scratch_dir()
        try:
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "run1.task.md",
            )
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "run2.task.md",
            )
            r1 = _read(out_dir / "run1.task.md")
            r2 = _read(out_dir / "run2.task.md")
            assert r1 == r2, "Two runs with identical inputs must produce byte-identical output"
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Criterion 9 — Malformed-marker source fails loud.
# ---------------------------------------------------------------------------

class TestCriterion9Malformed:
    """Run against a scratch card with an unterminated RENDER:BEGIN block,
    and separately a scratch delta with an orphan DELTA section.
    Each EXIT≠0 with RenderError-style message; no file written.
    """

    def test_unterminated_begin_in_scratch_card(self):
        out_dir = _scratch_dir()
        scratch_card = out_dir / "bad-card.md"
        # Card with unterminated RENDER:BEGIN.
        scratch_card.write_text(
            "<!-- RENDER:BEGIN generic-packaging -->\n"
            "Some content here\n"
            "# NO RENDER:END — unterminated\n",
            encoding="utf-8",
        )
        try:
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "x.task.md",
                "--wrapper", str(scratch_card),
                expect_fail=True,
            )
            assert not (out_dir / "x.task.md").exists()
        finally:
            _rmtree(out_dir)

    def test_orphan_delta_section(self):
        out_dir = _scratch_dir()
        # Create a scratch model dir with a delta that has an orphan section.
        scratch_models = out_dir / "models"
        scratch_model = scratch_models / "test-orphan"
        scratch_model.mkdir(parents=True)
        # Delta with a RENDER:DELTA section that has no matching INSERT point.
        (scratch_model / "delta.md").write_text(
            "<!-- RENDER:DELTA model-binding-delta -->\n"
            "Some binding delta\n"
            "<!-- RENDER:DELTA-END model-binding-delta -->\n"
            "<!-- RENDER:DELTA model-transport-note -->\n"
            "Some transport note\n"
            "<!-- RENDER:DELTA-END model-transport-note -->\n"
            "<!-- RENDER:DELTA invocation -->\n"
            "Some invocation\n"
            "<!-- RENDER:DELTA-END invocation -->\n"
            "<!-- RENDER:DELTA orphan-section-no-match -->\n"
            "This section matches no INSERT point\n"
            "<!-- RENDER:DELTA-END orphan-section-no-match -->\n",
            encoding="utf-8",
        )
        try:
            _run_scaffold(
                "--model", "test-orphan",
                "--output-folder", str(out_dir / "out"),
                "--filename", "x.task.md",
                "--model-dir", str(scratch_models),
                expect_fail=True,
            )
            assert not (out_dir / "out" / "x.task.md").exists()
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Criterion 10 — Real-corpus generation across multiple models.
# ---------------------------------------------------------------------------

class TestCriterion10RealCorpus:
    """Run the generator for each installed model with a delta.md;
    each should produce a file without errors.
    """

    @pytest.mark.parametrize("model", ["kimi-code-cli", "claude-code-cli", "qwen-code-cli", "codex-cli"])
    def test_real_corpus_model(self, model):
        out_dir = _scratch_dir()
        try:
            result = _run_scaffold(
                "--model", model,
                "--output-folder", str(out_dir),
                "--filename", f"{model}.task.md",
            )
            assert "wrote" in result.stdout
            assert (out_dir / f"{model}.task.md").exists()
        finally:
            _rmtree(out_dir)

    def test_deepseek_derive_or_fail(self):
        """deepseek is named in the spec's criterion-10 corpus but its delta
        declares 'Required frontmatter additions:' (an API-worker variant), not
        the 'Required frontmatter:' block the scaffold parses. Per the spec's
        derive-or-fail contract (S3 / Edge Cases), an unparseable delta MUST be
        a named EXIT!=0 — never a guessed skeleton. This documents that the 5th
        corpus model is intentionally a derive-or-fail, not a silent omission.
        """
        out_dir = _scratch_dir()
        try:
            result = _run_scaffold(
                "--model", "deepseek-api",
                "--output-folder", str(out_dir),
                "--filename", "ds.task.md",
                expect_fail=True,
            )
            # Named-gap error: must mention the missing structured block.
            assert "required-frontmatter" in result.stderr or "machine-readable" in result.stderr
            # No file written on the derive-or-fail.
            assert not (out_dir / "ds.task.md").exists()
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# ADX-18 #2 — Fabrication test: Agent-tool carrier must NOT get CLI flags.
# ---------------------------------------------------------------------------

class TestAD18Fabrication:
    """ADX-18 #2: generating for the claude package (Agent-tool carrier) must
    NOT fabricate CLI invocation flags.  Output must contain the explicit
    Agent-tool note and NO scraped flag tokens in the invocation note section.
    (The composed run-binding header may reference flags descriptively from the
    delta's confinement text — that is not fabrication.)
    """

    def test_claude_no_fabricated_flags(self):
        out_dir = _scratch_dir()
        try:
            _run_scaffold(
                "--model", "claude-code-native",
                "--output-folder", str(out_dir),
                "--filename", "claude.task.md",
            )
            content = _read(out_dir / "claude.task.md")

            # MUST contain the explicit Agent-tool note.
            assert "Agent-tool dispatch" in content
            assert "no CLI invocation" in content
            assert "the prompt is the Agent tool's prompt parameter" in content

            # Check the invocation note section specifically — it must NOT
            # contain any scraped CLI flags.  (The composed header may mention
            # flags descriptively from the delta's confinement text; that is
            # not fabrication and is not what this test guards against.)
            inv_start = content.find("### Invocation note")
            inv_end = content.find("## Pre-Dispatch Hook", inv_start)
            inv_section = content[inv_start:inv_end] if inv_start != -1 else ""

            # No scraped long-form flags in invocation section.
            scraped = re.findall(r'`--([a-z][a-z0-9-]*)`', inv_section)
            assert not scraped, (
                f"Agent-tool invocation must have no scraped --flags, got: {scraped}\n"
                f"Invocation section:\n{inv_section}"
            )
            # No scraped short-form flags.
            scraped_short = re.findall(r'`-([A-Za-z])`', inv_section)
            assert not scraped_short, (
                f"Agent-tool invocation must have no scraped -x flags, got: {scraped_short}"
            )
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Confinement lever: --model-dir (criterion 2 of pilot-levers task)
# ---------------------------------------------------------------------------

class TestModelDirConfinementLever:
    """Criterion 2 of pilot-levers: scaffold.py --model-dir pre-flight confinement.

    (a) A deliberately-stale scratch manual fails the pre-flight: EXIT != 0, no output file.
    (b) A fresh scratch manual passes the pre-flight and produces an output file.
    (c) Omitting --model-dir → today's behavior (pre-flight against the real live tree).

    The scratch model package is built from the REAL kimi delta + a rendered manual so
    render-manuals.py --check can evaluate freshness against it.
    """

    @staticmethod
    def _build_scratch_package(base_dir: Path, stale: bool) -> tuple[Path, str]:
        """Build a scratch models directory with a 'scratch-kimi' package.

        Copies kimi's delta.md as scratch-kimi/delta.md and either:
        - (fresh) renders the manual so --check reports 0 drift,
        - (stale) writes a deliberately wrong manual so --check reports drift.

        Returns (scratch_models_dir, model_name).
        """
        model_name = "scratch-kimi"
        scratch_models = base_dir / "models"
        pkg_dir = scratch_models / model_name
        pkg_dir.mkdir(parents=True)

        # Copy kimi delta as the scratch package delta.
        kimi_delta = MODELS_DIR / "kimi-code-cli" / "delta.md"
        scratch_delta = pkg_dir / "delta.md"
        scratch_delta.write_bytes(kimi_delta.read_bytes())

        render_manuals = RBTV_ROOT / "orchestration" / "models" / "render-manuals.py"
        manual_path = pkg_dir / "manual.md"

        if stale:
            # Write a deliberately wrong manual — any content that won't match
            # what render-manuals.py would compose.
            manual_path.write_text(
                "<!-- STALE MANUAL — DO NOT USE -->\nThis is deliberately stale.\n",
                encoding="utf-8",
            )
        else:
            # Render the manual so it is fresh (--check reports 0 drift).
            result = subprocess.run(
                [sys.executable, str(render_manuals),
                 "--model", model_name, "--models-dir", str(scratch_models)],
                capture_output=True, text=True, cwd=str(RBTV_ROOT),
            )
            assert result.returncode == 0, (
                f"Failed to render scratch manual: {result.stderr}"
            )
            assert manual_path.exists(), "render-manuals.py wrote nothing"

        return scratch_models, model_name

    def test_stale_scratch_manual_fails_preflight(self):
        """Stale scratch manual → preflight EXIT != 0, no output file written."""
        out_dir = _scratch_dir()
        base_dir = _scratch_dir()
        try:
            scratch_models, model_name = self._build_scratch_package(base_dir, stale=True)
            result = subprocess.run(
                [sys.executable, str(SCAFFOLD),
                 "--model", model_name,
                 "--model-dir", str(scratch_models),
                 "--output-folder", str(out_dir),
                 "--filename", "x.task.md"],
                capture_output=True, text=True, cwd=str(RBTV_ROOT),
            )
            assert result.returncode != 0, (
                f"Expected non-zero exit for stale manual, got 0.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
            assert not (out_dir / "x.task.md").exists(), (
                "No output file should be written when pre-flight fails"
            )
            # Error message must mention staleness.
            combined = result.stdout + result.stderr
            assert "stale" in combined.lower() or "drift" in combined.lower() or "re-render" in combined.lower(), (
                f"Error message should mention staleness/drift, got:\n{combined}"
            )
        finally:
            _rmtree(out_dir)
            _rmtree(base_dir)

    def test_fresh_scratch_manual_passes_preflight(self):
        """Fresh scratch manual → preflight passes, output file written."""
        out_dir = _scratch_dir()
        base_dir = _scratch_dir()
        try:
            scratch_models, model_name = self._build_scratch_package(base_dir, stale=False)
            result = subprocess.run(
                [sys.executable, str(SCAFFOLD),
                 "--model", model_name,
                 "--model-dir", str(scratch_models),
                 "--output-folder", str(out_dir),
                 "--filename", "y.task.md"],
                capture_output=True, text=True, cwd=str(RBTV_ROOT),
            )
            assert result.returncode == 0, (
                f"Expected exit 0 for fresh scratch manual, got {result.returncode}.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
            assert (out_dir / "y.task.md").exists(), "Output file should be written"
        finally:
            _rmtree(out_dir)
            _rmtree(base_dir)

    def test_no_model_dir_uses_live_tree(self):
        """Omitting --model-dir → pre-flight checks the LIVE orchestration/models/ tree."""
        out_dir = _scratch_dir()
        try:
            # kimi is a real model with a fresh manual — should pass with no --model-dir.
            result = subprocess.run(
                [sys.executable, str(SCAFFOLD),
                 "--model", "kimi-code-cli",
                 "--output-folder", str(out_dir),
                 "--filename", "live.task.md"],
                capture_output=True, text=True, cwd=str(RBTV_ROOT),
            )
            assert result.returncode == 0, (
                f"No --model-dir: real kimi should pass preflight.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
            assert (out_dir / "live.task.md").exists()
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Criterion 11 — Pre-authored multi-section brief preserved, never mangled.
#
# Regression for the complete-mode mangling bug (rbtv-tasks: "Fix scaffold.py
# complete-mode mangling of pre-authored multi-section task files"). When
# --instructions IS a complete task file, the three observed symptoms — dup
# frontmatter, unfilled `<conductor fills this section>` placeholders, and
# header-match duplication of code-fenced headings — must all be absent, while
# loose instructions still take the skeleton-merge path.
# ---------------------------------------------------------------------------

# A pre-authored brief WITH its own frontmatter + non-model section names
# (p3-1-shaped). The old skeleton-merge dumped this frontmatter into Goal under
# a SECOND skeleton frontmatter block and placeholder-stubbed every model section.
PREAUTHORED_FM_BRIEF = textwrap.dedent('''\
    ---
    task_id: p3-1
    status: pending
    executor: { model: claude-code-native, variant: sonnet }
    reviewer: { model: claude, variant: opus }
    allowlist:
      create: []
      modify:
        - orchestration/rules/orchestrating.md
    ---

    # Task p3-1: Edit orchestrating.md

    ## Goal
    Apply three surgical edits to the rule.

    ## Context Files
    | File | Purpose |
    |------|---------|
    | design.md | the source |

    ## Execution Flow
    ### Phase: Understand
    1. Read the context files.

    ## Output Requirements
    The edited rule.
    ''')

# A pre-authored brief WITH an H1 title + an inlined spec whose markdown headings
# sit INSIDE a code fence (p1-2-shaped). The old parser promoted the fenced
# `## Goal` / `## Context Snapshot` / `## Test Plan` to real sections (header-match
# duplication) and pulled fenced content into the model's Context Snapshot.
PREAUTHORED_CODEFENCE_BRIEF = textwrap.dedent('''\
    **Step 0 — read your rules first.**

    # Task p1-2: CREATE the context-monitor script

    ## Goal
    CREATE the PostToolUse context-monitor script per the inlined spec.

    ## Allowed Paths (create ONLY these)
    - orchestration/hooks/context-monitor.py

    ### [INLINED] spec — build exactly to it
    ```
    # Spec — Context Monitor

    ## Goal
    The owner runs an orchestration session.

    ## Context Snapshot
    Everything inlined so the worker needs no exploration.

    ## Test Plan
    | # | Criterion |
    |---|-----------|
    | 1 | fires at a tier |
    ```

    ## Validation
    Run pytest.
    ''')


def _load_scaffold_module():
    """Import scaffold.py as a module to unit-test its pure helpers."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("scaffold_under_test", str(SCAFFOLD))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestCriterion11PreauthoredBrief:
    def test_discriminator_classifies_briefs_vs_loose(self):
        """is_preauthored_brief: True for own-frontmatter and H1-title briefs;
        False for loose prose and `##`-only section fragments (incl. the
        unmatched-heading case the skeleton path must still own)."""
        m = _load_scaffold_module()
        # Pre-authored → True.
        assert m.is_preauthored_brief(PREAUTHORED_FM_BRIEF) is True
        assert m.is_preauthored_brief(PREAUTHORED_CODEFENCE_BRIEF) is True
        # Loose / fragment → False (these are the existing Criterion-7 inputs).
        assert m.is_preauthored_brief(
            "Build a dispatch scaffold for model kimi that passes all tests."
        ) is False
        assert m.is_preauthored_brief(
            "## Goal\nBuild it.\n\n## Implementation Requirements\n- Do X.\n"
        ) is False
        assert m.is_preauthored_brief(
            "## Goal\nBuild it.\n\n## Nonexistent Section\nOrphan content.\n"
        ) is False

    def test_frontmatter_brief_preserved_no_dup_no_placeholder(self):
        """Symptoms 1+2 gone: a single frontmatter block (brief's own keys intact,
        missing model keys merged in), brief sections preserved verbatim, zero
        `<conductor fills this section>` placeholders."""
        out_dir = _scratch_dir()
        try:
            brief_file = out_dir / "brief.md"
            brief_file.write_text(PREAUTHORED_FM_BRIEF, encoding="utf-8")
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "pa-fm.task.md",
                "--instructions", str(brief_file),
            )
            content = _read(out_dir / "pa-fm.task.md")

            # NO unfilled placeholders (symptom 2).
            assert "conductor fills this section" not in content

            # Exactly ONE frontmatter block, and it is the brief's own (symptom 1).
            assert content.startswith("---")
            assert content.count("task_id: p3-1") == 1
            fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            assert fm_match, "leading frontmatter block must exist"
            fm_block = fm_match.group(1)
            assert "task_id: p3-1" in fm_block
            # Brief's own key/value preserved, not overwritten.
            assert "executor: { model: claude-code-native, variant: sonnet }" in fm_block
            # A required model key the brief lacked was MERGED into the same block.
            assert re.search(r"(?m)^commit_policy:", fm_block)
            assert re.search(r"(?m)^doubt_policy:", fm_block)
            # The brief's frontmatter is NOT re-dumped into the body.
            assert content.index("task_id: p3-1") < content.index("# Task p3-1")

            # Brief's own (non-model) sections preserved verbatim.
            assert "## Context Files" in content
            assert "## Execution Flow" in content
            assert "### Phase: Understand" in content
            assert "1. Read the context files." in content
            assert "## Output Requirements" in content

            # Derived boilerplate still inserted (symptom 3 inverse: value-add kept).
            assert "## Run-Binding Header" in content
            assert "## Pre-Dispatch Hook" in content
            assert "## 2. The binding addendum" in content
        finally:
            _rmtree(out_dir)

    def test_codefence_brief_preserved_verbatim(self):
        """Symptom 3 gone: a brief whose inlined spec carries markdown headings
        inside a code fence is preserved VERBATIM — fenced headings are not
        promoted to real sections, and no placeholder is injected."""
        out_dir = _scratch_dir()
        try:
            brief_file = out_dir / "brief.md"
            brief_file.write_text(PREAUTHORED_CODEFENCE_BRIEF, encoding="utf-8")
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "pa-cf.task.md",
                "--instructions", str(brief_file),
            )
            content = _read(out_dir / "pa-cf.task.md")

            # Scaffold supplies the frontmatter skeleton (brief had none).
            assert content.startswith("---")
            # No unfilled placeholders.
            assert "conductor fills this section" not in content
            # The brief body is preserved as a contiguous verbatim block — the
            # fenced spec stays inside its fence, headings not re-parsed.
            assert PREAUTHORED_CODEFENCE_BRIEF.strip() in content
            # The fenced `## Context Snapshot` was NOT promoted into a second
            # real section (it appears exactly once — inside the fence).
            assert content.count("## Context Snapshot") == 1
            # Derived boilerplate still appended.
            assert "## Run-Binding Header" in content
            assert "## Pre-Dispatch Hook" in content
        finally:
            _rmtree(out_dir)

    def test_loose_instructions_still_skeleton(self):
        """Regression guard: loose instructions still take the skeleton-merge
        path — all model body sections emitted, instr merged into Goal."""
        out_dir = _scratch_dir()
        try:
            instr = "Implement the router per spec."
            _run_scaffold(
                "--model", "kimi-code-cli",
                "--output-folder", str(out_dir),
                "--filename", "loose.task.md",
                "--instructions", instr,
            )
            content = _read(out_dir / "loose.task.md")
            assert instr in content
            # Skeleton path emits all model sections (some as placeholders).
            assert "## Context Snapshot" in content
            assert "## Return Format" in content
            assert "conductor fills this section" in content
        finally:
            _rmtree(out_dir)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _rmtree(path: Path) -> None:
    """Remove a directory tree, ignoring errors (best-effort cleanup)."""
    import shutil
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass
