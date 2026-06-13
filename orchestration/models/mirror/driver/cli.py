"""cli.py — command-line entry for the rbtv mirror driver.

Renders / checks / uninstalls a workspace's worker-mirror artifacts for an
elected set of CLI worker packages (codex-cli / kimi-code-cli / qwen-code-cli).  Flag conventions match
the sibling ``mirror.py`` engine: ``--target`` is the workspace root, ``--check``
is read-only and exits 1 on drift, ``--uninstall`` removes artifacts, and
``--check`` + ``--uninstall`` together are mutually exclusive (exit 2).

Usage
-----
    # render the elected worker set into a workspace
    python -m driver.cli --target <workspace> codex-cli kimi-code-cli qwen-code-cli

    # report drift without writing (exit 1 if anything is stale/missing)
    python -m driver.cli --target <workspace> codex-cli kimi-code-cli qwen-code-cli --check

    # deselect a package; remaining elected workers are read from rbtv.json's
    # model_packages (or pass --remaining to override, e.g. for testing)
    python -m driver.cli --target <workspace> --uninstall codex-cli
    python -m driver.cli --target <workspace> --uninstall codex-cli --remaining kimi-code-cli qwen-code-cli

Exit codes
----------
    0  success (render done / in sync / uninstall done)
    1  --check found drift (missing or stale managed file / state)
    2  usage error (mutually-exclusive flags, bad target, unknown package)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import the driver package's public API whether invoked as a submodule
# (``python -m driver.cli`` → package context present) or as a loose script
# (``python driver/cli.py`` → no package context).
# ---------------------------------------------------------------------------
if __package__ in (None, ""):
    # Loose script — add the parent of driver/ to sys.path and import by name.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from driver import (  # type: ignore[import-not-found]
        PACKAGE_FACTS,
        render as _render_fn,
        state,
        uninstall as _uninstall_fn,
    )
else:
    from . import (
        PACKAGE_FACTS,
        render as _render_fn,
        state,
        uninstall as _uninstall_fn,
    )


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="driver",
        description=(
            "Render/check/uninstall a workspace's CLI-worker mirror artifacts "
            "(guidance files, the shared .agents/ library, per-model config dirs) "
            "for an elected set of worker packages. Source-agnostic; idempotent."
        ),
    )
    parser.add_argument(
        "--target", required=True, metavar="DIR",
        help="Target workspace root the mirror artifacts are rendered into.",
    )
    parser.add_argument(
        "packages", nargs="*", metavar="PACKAGE",
        help="Worker package ids to elect (render mode) or to deselect "
             "(with --uninstall). Known: " + ", ".join(sorted(PACKAGE_FACTS)) + ".",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Read-only drift check: write nothing; exit 1 if any managed file "
             "or the state block is missing or stale.",
    )
    parser.add_argument(
        "--uninstall", action="store_true",
        help="Remove the named packages' artifacts (ref-counted; banner-guarded).",
    )
    parser.add_argument(
        "--remaining", nargs="*", metavar="PACKAGE", default=None,
        help="(uninstall only) Packages that remain elected after the uninstall. "
             "When omitted, the remaining set is read from rbtv.json's "
             "model_packages minus the deselected packages.",
    )
    parser.add_argument(
        "--exclude", nargs="*", metavar="PATH", default=None,
        help="Workspace-relative path prefixes to skip when walking for CLAUDE.md "
             "(render mode). When omitted, exclusions recorded in rbtv.json are reused.",
    )
    return parser


def _validate_packages(packages: list[str]) -> list[str]:
    """Return unknown package ids that are neither mirrorable nor a known native id."""
    known = set(PACKAGE_FACTS) | {"claude-code-cli"}
    return [p for p in packages if p not in known]


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def _run_render(target_root: Path, packages: list[str], *, check: bool,
                exclude: list[str] | None) -> int:
    result = _render_fn(target_root, packages, check=check, excluded_paths=exclude)

    if result.skipped_commands:
        for stem in sorted(result.skipped_commands):
            print(f"skipped command (no name+description frontmatter): {stem}")

    if check:
        if result.stale:
            print(
                f"stale: mirror is out of sync for [{', '.join(sorted(packages))}] "
                f"— {len(result.managed_files)} managed file(s) expected; re-run to refresh"
            )
            return 1
        print(
            f"in sync: mirror is up to date for [{', '.join(sorted(packages))}] "
            f"({len(result.managed_files)} managed file(s) expected)"
        )
        return 0

    if result.state_created:
        verb = "created"
    elif result.state_changed or result.files_written:
        verb = "updated"
    else:
        verb = "unchanged"
    print(
        f"{verb}: rendered mirror for [{', '.join(sorted(packages))}] "
        f"— {len(result.managed_files)} managed file(s) recorded in rbtv.json model_mirror"
    )
    return 0


def _run_uninstall(target_root: Path, deselected: list[str],
                   remaining_override: list[str] | None) -> int:
    if remaining_override is not None:
        remaining = remaining_override
    else:
        # Resolve remaining from rbtv.json's model_packages minus the deselected.
        doc = state.read_document(target_root)
        recorded = doc.get("model_packages", []) if isinstance(doc, dict) else []
        remaining = [p for p in recorded if p not in set(deselected)]

    result = _uninstall_fn(target_root, deselected, remaining)

    print(
        f"uninstalled [{', '.join(sorted(deselected))}]; "
        f"remaining elected [{', '.join(sorted(_remaining_mirrorable(remaining)))}]"
    )
    if result.deleted:
        print(f"  deleted {len(result.deleted)} file(s):")
        for p in result.deleted:
            print(f"    - {p}")
    else:
        print("  deleted 0 file(s)")
    if result.spared:
        print(f"  spared {len(result.spared)} hand-authored guidance file(s) (no banner):")
        for p in result.spared:
            print(f"    ~ {p}")
    if result.leftover_dirs:
        print(
            f"  left {len(result.leftover_dirs)} worker dir(s) in place — they still "
            "hold file(s) rbtv did not create (delete by hand if no longer needed):"
        )
        for entry in result.leftover_dirs:
            print(f"    ~ {entry['dir']}/ ({len(entry['files'])} non-rbtv file(s))")
            for f in entry["files"]:
                print(f"        - {f}")
    print(f"  {len(result.kept_records)} managed file(s) remain recorded in rbtv.json model_mirror")
    return 0


def _remaining_mirrorable(packages: list[str]) -> list[str]:
    return [p for p in packages if p in PACKAGE_FACTS]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Mutually-exclusive flags (matches mirror.py): exit 2.
    if args.check and args.uninstall:
        print("ERROR: --check and --uninstall are mutually exclusive", file=sys.stderr)
        return 2

    target_root = Path(args.target).expanduser().resolve()
    if not target_root.is_dir():
        print(f"ERROR: --target is not a directory: {target_root}", file=sys.stderr)
        return 2

    unknown = _validate_packages(args.packages)
    if unknown:
        print(
            f"ERROR: unknown package(s): {', '.join(unknown)}. "
            f"Known: {', '.join(sorted(set(PACKAGE_FACTS) | {'claude-code-cli'}))}",
            file=sys.stderr,
        )
        return 2

    if args.uninstall:
        if not args.packages:
            print("ERROR: --uninstall requires at least one package to deselect", file=sys.stderr)
            return 2
        if args.remaining is not None:
            bad = _validate_packages(args.remaining)
            if bad:
                print(f"ERROR: unknown --remaining package(s): {', '.join(bad)}", file=sys.stderr)
                return 2
        return _run_uninstall(target_root, args.packages, args.remaining)

    # Render / check mode.
    if not args.packages:
        print("ERROR: at least one package must be elected (or use --uninstall)", file=sys.stderr)
        return 2

    return _run_render(target_root, args.packages, check=args.check, exclude=args.exclude)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
