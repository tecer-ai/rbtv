"""
Test suite for context-monitor.py — offline fixture tests covering spec rows 1–5.

Rows:
1. Fires at a tier (~32% of 200k window, orchestration signature present)
2. Silent below first tier (~20%, signature present)
3. Silent with no orchestration signature (~50%, no signature)
4. No repeat within a fired tier (same ~32% fixture, note-file persists)
5. Configured window (same fixture with RBTV_CONTEXT_WINDOW=200000 vs default 1M)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Path to the script under test
SCRIPT = Path(__file__).resolve().parent.parent / "context-monitor.py"


def _build_fixture(total_tokens: int, has_signature: bool = True) -> str:
    """Build a JSONL fixture transcript with the given total token usage."""
    lines = []
    # A user turn before the assistant turn
    lines.append(json.dumps({"type": "user", "message": {"content": "hello"}}))

    # An assistant turn with the orchestration signature if requested
    assistant = {
        "type": "assistant",
        "message": {
            "model": "claude-opus-4-8",
            "usage": {
                "input_tokens": total_tokens,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
        },
    }
    if has_signature:
        assistant["attributionSkill"] = "rbtv-orchestrating"
    lines.append(json.dumps(assistant))
    return "\n".join(lines) + "\n"


def _build_fixture_with_sidechain(total_tokens: int) -> str:
    """Build a fixture where the LAST assistant turn is sidechain; main-chain is earlier."""
    lines = []
    lines.append(json.dumps({"type": "user", "message": {"content": "hello"}}))
    # Main-chain assistant turn with real usage
    main = {
        "type": "assistant",
        "attributionSkill": "rbtv-orchestrating",
        "message": {
            "model": "claude-opus-4-8",
            "usage": {
                "input_tokens": total_tokens,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
        },
    }
    lines.append(json.dumps(main))
    # Sidechain assistant turn with different usage (should be ignored)
    side = {
        "type": "assistant",
        "isSidechain": True,
        "message": {
            "model": "claude-opus-4-8",
            "usage": {
                "input_tokens": 999999,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
        },
    }
    lines.append(json.dumps(side))
    return "\n".join(lines) + "\n"


def _run_hook(
    transcript_path: str,
    session_id: str,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run the hook script with the given stdin and optional env overrides."""
    stdin_data = json.dumps({
        "session_id": session_id,
        "transcript_path": transcript_path,
        "cwd": "/tmp",
        "tool_name": "test_tool",
    })
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=stdin_data,
        capture_output=True,
        text=True,
        env=merged_env,
    )
    return result.returncode, result.stdout, result.stderr


def _clear_tier_file(session_id: str) -> None:
    """Remove the tier note-file for a session to ensure clean state."""
    tier_file = Path.home() / ".claude" / "rbtv-runtime" / "context-monitor" / f"{session_id}.tier"
    if tier_file.exists():
        tier_file.unlink()


class TestFiresAtTier:
    """Spec row 1: reads real % and fires at a tier."""

    def test_fires_at_32_percent(self, tmp_path: Path) -> None:
        session_id = "test-session-32"
        _clear_tier_file(session_id)

        # 32% of 200k window = 64,000 tokens
        fixture = _build_fixture(64000, has_signature=True)
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(fixture, encoding="utf-8")

        exit_code, stdout, stderr = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )

        assert exit_code == 0
        assert stdout != ""
        data = json.loads(stdout)
        assert data["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        advisory = data["hookSpecificOutput"]["additionalContext"]
        assert "Context window 32% full (68% free) — recommend refresh" in advisory


class TestSilentBelowTier:
    """Spec row 2: silent below first tier."""

    def test_silent_at_20_percent(self, tmp_path: Path) -> None:
        session_id = "test-session-20"
        _clear_tier_file(session_id)

        # 20% of 200k window = 40,000 tokens
        fixture = _build_fixture(40000, has_signature=True)
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(fixture, encoding="utf-8")

        exit_code, stdout, stderr = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )

        assert exit_code == 0
        assert stdout == ""


class TestSilentNoSignature:
    """Spec row 3: silent with no orchestration signature."""

    def test_silent_no_signature(self, tmp_path: Path) -> None:
        session_id = "test-session-no-sig"
        _clear_tier_file(session_id)

        # 50% of 200k window = 100,000 tokens, but NO signature
        fixture = _build_fixture(100000, has_signature=False)
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(fixture, encoding="utf-8")

        exit_code, stdout, stderr = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )

        assert exit_code == 0
        assert stdout == ""


class TestNoRepeat:
    """Spec row 4: no repeat within a fired tier."""

    def test_advisory_first_run_silent_second(self, tmp_path: Path) -> None:
        session_id = "test-session-repeat"
        _clear_tier_file(session_id)

        fixture = _build_fixture(64000, has_signature=True)
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(fixture, encoding="utf-8")

        # First run — should fire
        exit_code, stdout, stderr = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )
        assert exit_code == 0
        assert stdout != ""
        data = json.loads(stdout)
        assert "32%" in data["hookSpecificOutput"]["additionalContext"]

        # Second run — should be silent (tier already recorded)
        exit_code2, stdout2, stderr2 = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )
        assert exit_code2 == 0
        assert stdout2 == ""


class TestConfiguredWindow:
    """Spec row 5: configured window changes the computed percentage."""

    def test_200k_window_vs_default_1m(self, tmp_path: Path) -> None:
        session_id_200k = "test-session-200k"
        session_id_1m = "test-session-1m"
        _clear_tier_file(session_id_200k)
        _clear_tier_file(session_id_1m)

        # Same token count: 64,000
        fixture = _build_fixture(64000, has_signature=True)
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(fixture, encoding="utf-8")

        # With 200k window -> 32% (fires)
        exit_code, stdout, stderr = _run_hook(
            str(transcript), session_id_200k, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )
        assert exit_code == 0
        assert stdout != ""
        data = json.loads(stdout)
        assert "32%" in data["hookSpecificOutput"]["additionalContext"]

        # With default 1M window -> 6.4% (silent, below 30%)
        exit_code2, stdout2, stderr2 = _run_hook(
            str(transcript), session_id_1m, env={}
        )
        assert exit_code2 == 0
        assert stdout2 == ""


class TestSidechainExclusion:
    """Verify sidechain entries are excluded from usage calculation."""

    def test_ignores_sidechain_usage(self, tmp_path: Path) -> None:
        session_id = "test-session-sidechain"
        _clear_tier_file(session_id)

        # Main-chain: 64,000 tokens; sidechain: 999,999 tokens (should be ignored)
        fixture = _build_fixture_with_sidechain(64000)
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(fixture, encoding="utf-8")

        exit_code, stdout, stderr = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )

        assert exit_code == 0
        assert stdout != ""
        data = json.loads(stdout)
        assert "32%" in data["hookSpecificOutput"]["additionalContext"]


class TestMalformedLines:
    """Verify malformed JSONL lines are skipped gracefully."""

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        session_id = "test-session-malformed"
        _clear_tier_file(session_id)

        lines = [
            "this is not json",
            json.dumps({"type": "user", "message": {"content": "hi"}}),
            "{bad json",
            json.dumps({
                "type": "assistant",
                "attributionSkill": "rbtv-orchestrating",
                "message": {
                    "model": "claude-opus-4-8",
                    "usage": {
                        "input_tokens": 64000,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                    },
                },
            }),
        ]
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")

        exit_code, stdout, stderr = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )

        assert exit_code == 0
        assert stdout != ""
        data = json.loads(stdout)
        assert "32%" in data["hookSpecificOutput"]["additionalContext"]


class TestMissingTranscript:
    """Verify missing transcript is silent exit 0."""

    def test_missing_transcript(self, tmp_path: Path) -> None:
        session_id = "test-session-missing"
        _clear_tier_file(session_id)

        nonexistent = tmp_path / "does-not-exist.jsonl"

        exit_code, stdout, stderr = _run_hook(
            str(nonexistent), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )

        assert exit_code == 0
        assert stdout == ""


def _read_tier_file(session_id: str) -> str:
    """Read the recorded tier value from the note-file (empty string if absent)."""
    tier_file = (
        Path.home() / ".claude" / "rbtv-runtime" / "context-monitor" / f"{session_id}.tier"
    )
    if not tier_file.exists():
        return ""
    return tier_file.read_text(encoding="utf-8").strip()


class TestTierProgression:
    """
    Spec behavior row 3 + "first at 30%, then once each at every additional +5%".
    Pins that _compute_tier returns the HIGHEST tier crossed (regression guard for
    the ascending-range bug where any usage >=30 returned tier 30 and stuck).
    """

    def test_jump_to_50_fires_tier_50(self, tmp_path: Path) -> None:
        """A first observation at ~50% fires and the note-file records 50, not 30."""
        session_id = "test-session-jump-50"
        _clear_tier_file(session_id)

        # 50% of 200k = 100,000 tokens
        fixture = _build_fixture(100000, has_signature=True)
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(fixture, encoding="utf-8")

        exit_code, stdout, stderr = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )

        assert exit_code == 0
        assert stdout != ""
        data = json.loads(stdout)
        # Advisory reports the REAL percentage (50), not the tier number
        assert "Context window 50% full (50% free) — recommend refresh" in data["hookSpecificOutput"]["additionalContext"]
        # Note-file records tier 50 (the highest crossed), not 30
        assert _read_tier_file(session_id) == "50"

    def test_after_30_a_later_50_fires_once(self, tmp_path: Path) -> None:
        """After firing at 30%, a later jump to ~50% fires once (not stuck at 30)."""
        session_id = "test-session-30-then-50"
        _clear_tier_file(session_id)

        # First: ~32% (64,000 of 200k) fires tier 30
        fixture_32 = _build_fixture(64000, has_signature=True)
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(fixture_32, encoding="utf-8")
        exit_code, stdout, _ = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )
        assert exit_code == 0
        assert "Context window 32% full" in stdout
        assert _read_tier_file(session_id) == "30"

        # Then: usage climbs to ~50% (100,000) — must fire again, record 50
        fixture_50 = _build_fixture(100000, has_signature=True)
        transcript.write_text(fixture_50, encoding="utf-8")
        exit_code2, stdout2, _ = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )
        assert exit_code2 == 0
        assert stdout2 != ""
        data = json.loads(stdout2)
        assert "Context window 50% full" in data["hookSpecificOutput"]["additionalContext"]
        assert _read_tier_file(session_id) == "50"

        # Re-run at the same 50% — silent (tier 50 already recorded)
        exit_code3, stdout3, _ = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )
        assert exit_code3 == 0
        assert stdout3 == ""

    def test_consecutive_plus5_tiers_each_fire_once(self, tmp_path: Path) -> None:
        """Stepping 30 -> 35 -> 40 each fires exactly once, recording each tier."""
        session_id = "test-session-steps"
        _clear_tier_file(session_id)
        transcript = tmp_path / "transcript.jsonl"

        # token counts for 30%, 35%, 40% of a 200k window
        for pct, tokens in ((30, 60000), (35, 70000), (40, 80000)):
            fixture = _build_fixture(tokens, has_signature=True)
            transcript.write_text(fixture, encoding="utf-8")

            # First run at this tier fires
            exit_code, stdout, _ = _run_hook(
                str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
            )
            assert exit_code == 0, f"tier {pct}: expected exit 0"
            assert stdout != "", f"tier {pct}: expected an advisory on first crossing"
            assert f"Context window {pct}% full" in stdout, f"tier {pct}: wrong percentage in advisory"
            assert _read_tier_file(session_id) == str(pct), f"tier {pct}: note-file not recorded"

            # Immediate re-run at same tier is silent (no repeat)
            exit_code2, stdout2, _ = _run_hook(
                str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
            )
            assert exit_code2 == 0
            assert stdout2 == "", f"tier {pct}: expected silence on repeat"

    def test_95_cap(self, tmp_path: Path) -> None:
        """Usage at/above 95% caps the recorded tier at 95 (no 100 tier)."""
        session_id = "test-session-95-cap"
        _clear_tier_file(session_id)

        # 99% of 200k = 198,000 tokens
        fixture = _build_fixture(198000, has_signature=True)
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(fixture, encoding="utf-8")

        exit_code, stdout, _ = _run_hook(
            str(transcript), session_id, env={"RBTV_CONTEXT_WINDOW": "200000"}
        )

        assert exit_code == 0
        assert stdout != ""
        data = json.loads(stdout)
        # Advisory still reports the real 99%
        assert "Context window 99% full" in data["hookSpecificOutput"]["additionalContext"]
        # But the recorded tier is capped at 95
        assert _read_tier_file(session_id) == "95"
