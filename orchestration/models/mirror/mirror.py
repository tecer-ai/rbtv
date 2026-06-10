#!/usr/bin/env python3
"""mirror.py — generate/refresh a model's per-workspace guidance file.

THE shippable, vault-agnostic mirror engine behind D7's pre-dispatch
guidance-file check (debate-decisions.md D7) and D18's mirror machinery
generalization (D18). A CLI model worker (kimi, codex, claude-code-cli, qwen)
natively loads a per-workspace guidance file — `AGENTS.md` for kimi/codex,
`CLAUDE.md` for claude-code-cli. When a target workspace lacks that file, the routing
card offers to create it via this engine; this engine generates it, stamped with
an auto-generated DO-NOT-EDIT banner, and detects when an existing one has gone
stale relative to its source.

Generalized from the vault-local `.user/runtime/scripts/{kimi,codex}-mirror.py`
+ `sync-check.py`: the validated mechanics (marker/banner bake, idempotent
write-if-changed, staleness `--check`) ship here; everything vault-specific
(hardcoded exclusions, the sb-os/RBTV skill-rendering pipeline, the model-config
sidecars) is NOT this engine's job. WHAT to generate is per-model: each model
package carries a `mirror-config.yaml` that this engine reads (see
`mirror-config.md` for the config convention). The vault's own `.user` mirror
scripts stay untouched — migrating the vault to this shipped engine is the user's
later call, not this engine's concern.

No external dependencies — Python 3.11+ only (a minimal YAML subset is parsed
in-process; see `_parse_config`).

Usage (run from the rbtv repo root, or anywhere with absolute paths):
    # create / refresh the guidance file in a target workspace
    python orchestration/models/mirror/mirror.py --config orchestration/models/<model>/mirror-config.yaml --target <workspace-root>

    # report staleness without writing (exit 1 if the file is missing or stale)
    python orchestration/models/mirror/mirror.py --config <config> --target <workspace-root> --check

    # remove the generated guidance file (only if this engine generated it)
    python orchestration/models/mirror/mirror.py --config <config> --target <workspace-root> --uninstall

----------------------------------------------------------------------------
What it does (the generic, shippable mechanics)
----------------------------------------------------------------------------
- Reads the per-model mirror-config: the guidance filename to emit, the source
  file to mirror from (relative to the target workspace), and the banner label.
- Composes the guidance file = DO-NOT-EDIT banner + the source file's body.
- Idempotent: re-running with no source change rewrites nothing (write-if-changed);
  `--check` reports zero drift and exits 0.
- Staleness: if the guidance file is absent, or its content no longer matches what
  the current source would produce, `--check` reports it and exits 1.
- Deterministic: no timestamps, no machine-specific absolute paths baked into the
  output — the banner names the source by its workspace-relative path, so the same
  source yields a byte-identical guidance file on any machine.

----------------------------------------------------------------------------
Behavior contract
----------------------------------------------------------------------------
- Missing source file (the config's `source` does not exist in the target) FAILS
  LOUDLY, naming the config and the resolved path — the workspace is not mirrorable
  for this model until the source exists.
- Malformed config (missing a required key, unreadable) FAILS LOUDLY, naming the
  config and the offending key.
- `--check` is read-only: it NEVER writes, and returns exit 1 on any
  missing-or-stale guidance file so a pre-dispatch check can gate on it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()

# Required keys every mirror-config MUST declare. See mirror-config.md.
REQUIRED_CONFIG_KEYS = ("model", "guidance_filename", "source", "banner_label")


class MirrorError(Exception):
    """A condition that must fail the mirror loudly (bad config, missing source)."""


# ---------------------------------------------------------------------------
# Minimal config parsing — flat `key: value` YAML subset, no dependency
# ---------------------------------------------------------------------------

def _parse_config(path: Path) -> dict[str, str]:
    """Parse a flat `key: value` mirror-config (the subset every config uses).

    Supports `# comments`, blank lines, and optional single/double quotes around
    values. NOT a general YAML parser — mirror-configs are intentionally flat
    (the schema in mirror-config.md is key/value only) so the engine carries no
    YAML dependency. A nested or list value raises MirrorError naming the line.
    """
    if not path.exists():
        raise MirrorError(f"mirror-config not found: {path}")
    config: dict[str, str] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith((" ", "\t", "-")):
            raise MirrorError(
                f"{path}:{line_no}: mirror-config must be flat key:value — "
                f"nested/list lines are not supported: {raw!r}"
            )
        if ":" not in line:
            raise MirrorError(f"{path}:{line_no}: expected 'key: value', got {raw!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"') and len(value) >= 2) or (
            value.startswith("'") and value.endswith("'") and len(value) >= 2
        ):
            value = value[1:-1]
        config[key] = value
    missing = [k for k in REQUIRED_CONFIG_KEYS if not config.get(k)]
    if missing:
        raise MirrorError(
            f"{path}: mirror-config missing required key(s): {', '.join(missing)} "
            f"(required: {', '.join(REQUIRED_CONFIG_KEYS)})"
        )
    return config


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

def make_banner(config: dict[str, str], source_rel: str, guidance_filename: str) -> str:
    """The DO-NOT-EDIT banner — names the source and the regeneration command.

    Deterministic: no timestamp (a timestamp would break idempotency / the
    re-mirror zero-diff check), no absolute path (source is named workspace-
    relative). The source IS the provenance.
    """
    label = config["banner_label"]
    return (
        f"<!-- AUTO-GENERATED MIRROR — DO NOT EDIT. "
        f"Generated by rbtv mirror.py from {source_rel}. -->\n"
        f"\n"
        f"> [!danger] GENERATED FILE — DO NOT EDIT\n"
        f"> This `{guidance_filename}` is an auto-generated mirror of `{source_rel}`, "
        f"emitted for {label}.\n"
        f"> Hand-edits are overwritten on the next mirror run and are forbidden. To change\n"
        f"> these instructions, edit `{source_rel}` and re-run the mirror:\n"
        f">\n"
        f"> ```\n"
        f"> python {rel_to_repo(SCRIPT_PATH)} --config <this-model>/mirror-config.yaml --target <workspace>\n"
        f"> ```\n"
        f"\n"
        f"---\n"
        f"\n"
    )


def rel_to_repo(path: Path) -> str:
    """Repo-root-relative POSIX path for stable, machine-independent banners.

    The rbtv repo root is three levels up from this script
    (orchestration/models/mirror/mirror.py). Falls back to the bare name if the
    script is run from an unexpected location.
    """
    repo_root = SCRIPT_PATH.parent.parent.parent.parent
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return path.name


def compose_guidance(config: dict[str, str], target_root: Path) -> tuple[str, Path, str]:
    """Compose the guidance file content for one target workspace.

    Returns (content, guidance_path, source_rel). Raises MirrorError if the
    configured source file does not exist in the target workspace.
    """
    guidance_filename = config["guidance_filename"]
    source_rel = config["source"].replace("\\", "/").strip("/")
    source_path = (target_root / source_rel).resolve()
    if not source_path.exists():
        raise MirrorError(
            f"source file '{source_rel}' does not exist in target workspace "
            f"{target_root} (config model '{config['model']}') — workspace is not "
            f"mirrorable for this model until the source exists"
        )
    body = source_path.read_text(encoding="utf-8")
    banner = make_banner(config, source_rel, guidance_filename)
    content = banner + body.lstrip("\n")
    if not content.endswith("\n"):
        content += "\n"
    guidance_path = (target_root / guidance_filename).resolve()
    return content, guidance_path, source_rel


# ---------------------------------------------------------------------------
# Drivers — create/refresh, check, uninstall
# ---------------------------------------------------------------------------

def write_if_changed(path: Path, content: str, *, check: bool) -> str:
    """Return 'created' | 'refreshed' | 'in-sync' | 'stale' (check mode).

    Never writes in check mode. 'created' = the file did not exist; 'refreshed'
    = it existed and differed; 'in-sync' = it existed and matched; 'stale' =
    check mode found it missing or differing.
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


def run_mirror(config: dict[str, str], target_root: Path, *, check: bool) -> int:
    content, guidance_path, source_rel = compose_guidance(config, target_root)
    status = write_if_changed(guidance_path, content, check=check)
    rel_guidance = _display_rel(guidance_path, target_root)

    if check:
        if status == "in-sync":
            print(f"in sync: {rel_guidance} is up to date with {source_rel}")
            return 0
        if not guidance_path.exists():
            print(f"stale: {rel_guidance} is MISSING (would be created from {source_rel})")
        else:
            print(f"stale: {rel_guidance} differs from {source_rel} — re-run the mirror to refresh")
        return 1

    if status == "created":
        print(f"created {rel_guidance} from {source_rel}")
    elif status == "refreshed":
        print(f"refreshed {rel_guidance} from {source_rel}")
    else:
        print(f"unchanged {rel_guidance} (already in sync with {source_rel})")
    return 0


def run_uninstall(config: dict[str, str], target_root: Path) -> int:
    """Delete the generated guidance file — but only if it carries this engine's
    banner, so a hand-authored guidance file is never destroyed."""
    guidance_filename = config["guidance_filename"]
    guidance_path = (target_root / guidance_filename).resolve()
    rel_guidance = _display_rel(guidance_path, target_root)
    if not guidance_path.exists():
        print(f"nothing to remove: {rel_guidance} does not exist")
        return 0
    head = guidance_path.read_text(encoding="utf-8")[:200]
    if "AUTO-GENERATED MIRROR — DO NOT EDIT" not in head:
        print(
            f"refused: {rel_guidance} is not an auto-generated mirror "
            f"(no DO-NOT-EDIT banner) — leaving it untouched"
        )
        return 1
    guidance_path.unlink()
    print(f"removed {rel_guidance}")
    return 0


def _display_rel(path: Path, target_root: Path) -> str:
    try:
        return path.relative_to(target_root).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Generate/refresh a model's per-workspace guidance file from a "
                    "per-model mirror-config. Vault-agnostic; deterministic; idempotent."
    )
    parser.add_argument(
        "--config", required=True, metavar="PATH",
        help="Path to the model package's mirror-config.yaml.",
    )
    parser.add_argument(
        "--target", required=True, metavar="DIR",
        help="Target workspace root the guidance file is generated into.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Report staleness and exit 1 if the guidance file is missing or stale; write nothing.",
    )
    parser.add_argument(
        "--uninstall", action="store_true",
        help="Remove the generated guidance file (only if it carries the DO-NOT-EDIT banner).",
    )
    args = parser.parse_args(argv)

    if args.check and args.uninstall:
        print("ERROR: --check and --uninstall are mutually exclusive", file=sys.stderr)
        return 2

    config_path = Path(args.config).expanduser().resolve()
    target_root = Path(args.target).expanduser().resolve()

    try:
        if not target_root.is_dir():
            raise MirrorError(f"--target is not a directory: {target_root}")
        config = _parse_config(config_path)
        if args.uninstall:
            return run_uninstall(config, target_root)
        return run_mirror(config, target_root, check=args.check)
    except MirrorError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
