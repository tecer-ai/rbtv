#!/usr/bin/env python3
"""mirror.py — RETIRED guidance engine; now the shared write primitive + a refusal.

RETIREMENT (owner ruling ``d-hard-guard-retire-model-mirror``, 2026-08-10, in
``1-projects/rbtv-sb-merge-refactor-core-build/decisions.md`` — extended to this
script by the owner the same day, after the driver retirement landed at rbtv
``1336133``): this engine generated a model's per-workspace guidance file
(``AGENTS.md``/``QWEN.md``) from a ``CLAUDE.md`` basis. Run by hand against a
workspace it would OVERWRITE the guidance files the modern installer owns
(``d-s17`` / ``d-s17bis``) with its own banner — the last open door after the
driver's guidance leg was removed. It is now shut in code: the render, ``--check``
and ``--uninstall`` verbs all REFUSE, and the composition machinery is DELETED
(not gated — there is nothing left to re-enable). Read it at ``1336133^`` if the
history is needed.

WHAT REPLACES IT — the modern installer renders the guidance mirror for any
target, a fresh worktree included::

    python install2.py install --target <workspace-or-worktree> --guidance-basis CLAUDE.md

…or inline the load-bearing rules in the worker's prompt. The per-model manuals'
pre-dispatch rows say the same.

STILL LIVE — do NOT delete this file: ``write_if_changed`` below is imported by
the mirror driver's ``library.py`` and ``config_assets.py``, which render the
``.agents/`` skill+rule library and the ``.codex``/``.kimi`` config dirs. Those
are the live artifacts the non-claude harnesses read; they are not guidance files
and this retirement does not touch them.

No external dependencies — Python 3.11+ only.

Exit codes
----------
    2  every guidance verb — refused, nothing written or deleted
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()

#: Every guidance operation refuses with this, citing the ruling that retired it.
RETIRED_MESSAGE = (
    "refused: this engine's guidance rendering is RETIRED (owner ruling "
    "d-hard-guard-retire-model-mirror, 2026-08-10) — it would overwrite the "
    "guidance files the modern installer owns. Nothing was written or deleted.\n"
    "  Render guidance with: python install2.py install --target <workspace> "
    "--guidance-basis CLAUDE.md\n"
    "  (or inline the load-bearing rules in the worker's prompt)."
)


def write_if_changed(path: Path, content: str, *, check: bool) -> str:
    """Return 'created' | 'refreshed' | 'in-sync' | 'stale' (check mode).

    The one primitive that outlives the retirement: the mirror driver's
    ``library.py`` / ``config_assets.py`` write the live ``.agents/`` and
    per-model config artifacts through it. Never writes in check mode.
    'created' = the file did not exist; 'refreshed' = it existed and differed;
    'in-sync' = it existed and matched; 'stale' = check mode found it missing or
    differing.
    """
    existed = path.exists()
    current = path.read_text(encoding="utf-8") if existed else None
    if current == content:
        return "in-sync"
    if check:
        return "stale"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return "refreshed" if existed else "created"


def main(argv: list[str]) -> int:
    """Parse the historical flags, then refuse — whatever was asked.

    The CLI surface is kept so a stale documented command (a manual, a
    ``mirror-config.yaml`` header, an operator's shell history) gets the ruling
    and its replacement instead of an argparse error. Refusing --check too is
    deliberate: it writes nothing, but its answer ("your AGENTS.md is stale,
    re-run the mirror") would send the operator straight back into the overwrite
    this ruling exists to prevent.
    """
    parser = argparse.ArgumentParser(
        description="RETIRED (d-hard-guard-retire-model-mirror, 2026-08-10): every "
                    "guidance operation refuses and writes nothing. Render guidance "
                    "with: install2.py install --target <ws> --guidance-basis CLAUDE.md."
    )
    parser.add_argument("--config", metavar="PATH", help="(retired) model mirror-config.")
    parser.add_argument("--target", metavar="DIR", help="(retired) target workspace root.")
    parser.add_argument("--check", action="store_true", help="(retired) staleness probe.")
    parser.add_argument("--uninstall", action="store_true", help="(retired) remove the guidance file.")
    parser.parse_args(argv)

    print(RETIRED_MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
