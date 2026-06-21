"""
Context Monitor — PostToolUse hook script for rbtv orchestration.

Reads a session transcript (JSONL), self-detects an orchestration run by scanning
for the attributionSkill == "rbtv-orchestrating" signature, computes the latest
main-chain assistant turn's context usage, and emits a tiered refresh advisory
when a new threshold is crossed.

Behavior (exact per spec):
- Silent exit 0 if no orchestration signature, below first tier, already-fired tier,
  or any read/parse failure.
- First advisory at 30%, then every +5% (35, 40, … 95).
- Output on new tier: JSON with hookSpecificOutput.additionalContext carrying the
  real N% and advisory text.
- Tier note-file lives outside the vault at ~/.claude/rbtv-runtime/context-monitor/<session_id>.tier
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _get_window_size() -> int:
    """Return context window size from env or default 1_000_000."""
    raw = os.environ.get("RBTV_CONTEXT_WINDOW", "")
    try:
        value = int(raw)
        if value > 0:
            return value
    except ValueError:
        pass
    return 1_000_000


def _resolve_tier_dir() -> Path:
    """Resolve the runtime tier directory outside the vault, cross-platform."""
    home = Path.home()
    tier_dir = home / ".claude" / "rbtv-runtime" / "context-monitor"
    return tier_dir


def _read_tier_record(tier_dir: Path, session_id: str) -> int:
    """Return the highest tier already fired (0 if none)."""
    tier_file = tier_dir / f"{session_id}.tier"
    if not tier_file.exists():
        return 0
    try:
        content = tier_file.read_text(encoding="utf-8").strip()
        return int(content)
    except (ValueError, OSError):
        return 0


def _write_tier_record(tier_dir: Path, session_id: str, tier: int) -> None:
    """Write the highest tier fired to the note-file."""
    try:
        tier_dir.mkdir(parents=True, exist_ok=True)
        tier_file = tier_dir / f"{session_id}.tier"
        tier_file.write_text(str(tier), encoding="utf-8")
    except OSError:
        pass  # never crash on write failure


def _compute_tier(usage_pct: float) -> int:
    """
    Return the HIGHEST tier threshold (30, 35, ..., 95) that usage_pct has
    crossed, or 0 if below the first tier (30). Caps at 95.

    Examples: 32 -> 30, 50 -> 50, 67 -> 65, 99 -> 95, 29.9 -> 0.
    """
    if usage_pct < 30.0:
        return 0
    # Highest +5 step at or below usage_pct, capped at 95.
    tier = 30 + (int(usage_pct) - 30) // 5 * 5
    return min(tier, 95)


def _build_advisory(usage_pct: float) -> str:
    """Build the advisory text for the conductor."""
    n = int(usage_pct)
    return (
        f"Context window {n}% full ({100 - n}% free) — recommend refresh. "
        "Do NOT overthink or deliberate over whether to halt. "
        "Keep working to the NEXT natural checkpoint (a finished worker return or a completed step) — do not stop mid-step. "
        "At that checkpoint bring the spine (state-capsule + run-log) and any state docs current so a fresh agent can resume from them alone. "
        "If this is a full-auto / AFK orchestrated run, just continue — do NOT interrupt the owner. "
        "Otherwise surface a one-line refresh proposal to the owner ONCE and keep working until they respond; "
        "do not re-propose at later tiers. Propose, never agonize over halting."
    )


def _build_output(usage_pct: float) -> str:
    """Build the JSON stdout payload for a new tier trigger."""
    advisory = _build_advisory(usage_pct)
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": advisory,
        }
    }
    return json.dumps(payload)


def _scan_transcript(transcript_path: str) -> tuple[bool, int]:
    """
    Scan the transcript JSONL for orchestration signature and latest main-chain usage.

    Returns:
        (has_orchestration_signature, total_tokens)
        has_orchestration_signature: True if ANY assistant entry has attributionSkill == "rbtv-orchestrating"
        total_tokens: sum of input_tokens + cache_read_input_tokens + cache_creation_input_tokens
                      from the LAST non-sidechain assistant turn; 0 if none found.
    """
    has_signature = False
    last_usage = 0

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue  # skip malformed lines

                if not isinstance(entry, dict):
                    continue

                entry_type = entry.get("type")
                if entry_type != "assistant":
                    continue

                # Check for orchestration signature
                if entry.get("attributionSkill") == "rbtv-orchestrating":
                    has_signature = True

                # Skip sidechain entries
                if entry.get("isSidechain") is True:
                    continue

                message = entry.get("message", {})
                if not isinstance(message, dict):
                    continue

                usage = message.get("usage", {})
                if not isinstance(usage, dict):
                    continue

                try:
                    input_tokens = int(usage.get("input_tokens", 0) or 0)
                    cache_read = int(usage.get("cache_read_input_tokens", 0) or 0)
                    cache_creation = int(usage.get("cache_creation_input_tokens", 0) or 0)
                    last_usage = input_tokens + cache_read + cache_creation
                except (ValueError, TypeError):
                    continue
    except (OSError, FileNotFoundError):
        return False, 0

    return has_signature, last_usage


def main() -> None:
    """Entry point: read stdin JSON, scan transcript, emit advisory if needed."""
    # Read stdin JSON
    try:
        raw_stdin = sys.stdin.read()
        if not raw_stdin.strip():
            sys.exit(0)
        stdin_data = json.loads(raw_stdin)
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    if not isinstance(stdin_data, dict):
        sys.exit(0)

    transcript_path = stdin_data.get("transcript_path")
    session_id = stdin_data.get("session_id")
    if not transcript_path or not session_id:
        sys.exit(0)

    # Scan transcript
    has_signature, total_tokens = _scan_transcript(transcript_path)

    # D9: silent if not an orchestration run
    if not has_signature:
        sys.exit(0)

    # No main-chain assistant turn yet
    if total_tokens <= 0:
        sys.exit(0)

    # Compute usage %
    window = _get_window_size()
    usage_pct = (total_tokens / window) * 100.0

    # Determine current tier
    current_tier = _compute_tier(usage_pct)
    if current_tier == 0:
        sys.exit(0)

    # Check note-file for already-fired tier
    tier_dir = _resolve_tier_dir()
    highest_fired = _read_tier_record(tier_dir, session_id)

    if current_tier <= highest_fired:
        sys.exit(0)

    # New tier — emit advisory and record it
    print(_build_output(usage_pct))
    _write_tier_record(tier_dir, session_id, current_tier)
    sys.exit(0)


if __name__ == "__main__":
    main()
