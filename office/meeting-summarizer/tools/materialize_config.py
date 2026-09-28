#!/usr/bin/env python3
"""materialize-config — settings.json -> config/*.json, the ONE source, every cycle.

An agent installing this capability carries its own settings in ONE file,
`settings.json`, in its home (owner ruling 2026-09-28, "Agent settings vs
capabilities"). Every kept tool in this capability still reads its config-module
home as a directory of per-KEY files (`config-root/sources.json`,
`config-root/destination-routing.json`, ...) — that contract is unchanged, so no
kept tool needed editing. This script is the one place that turns the first shape
into the second: split each of `settings.json`'s top-level keys into its own file
under the config root, OVERWRITING whatever was there.

Run it FIRST, every cycle, unconditionally (never "only if the folder is
missing"): `config/` is a DERIVED cache of `settings.json`, rebuilt every time,
never a second copy an owner's edit to `settings.json` could leave stale.
Measured 2026-09-28: gating this to the first cycle only left `config/` holding a
destination-routing.json the owner had already replaced in `settings.json` — the
tools kept reading the stale copy until the orchestrator patched both files by
hand. Running this unconditionally removes the second copy's staleness at the
root: there is exactly one write path into `config/`, and it always starts from
the one settings file.

A key starting with `_` is a comment (this capability's own `settings.json`
convention, e.g. `_this-file`) and is never materialized as a config file.

Run with --help for the command surface.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_REFUSED = 2


def refuse(what: str, fix: str) -> None:
    print(f"materialize-config refused: {what}\n  fix: {fix}", file=sys.stderr)
    raise SystemExit(EXIT_REFUSED)


def materialize(settings: dict, config_root: Path) -> list[str]:
    """Write every non-comment top-level key to `<config_root>/<key>.json`.

    Returns the paths written, in a stable (sorted) order. Nothing is read back
    and nothing is deleted: a key `settings.json` no longer carries leaves its
    old file in place until the OWNER edits `settings.json` to remove it — this
    script mirrors what IS declared, it does not guess what should disappear.
    """
    config_root = Path(config_root)
    config_root.mkdir(parents=True, exist_ok=True)
    written = []
    for key in sorted(settings):
        if key.startswith("_"):
            continue
        path = config_root / f"{key}.json"
        path.write_text(json.dumps(settings[key], ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        written.append(str(path))
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="materialize_config",
        description="Split an agent's settings.json into the per-key config files "
                    "this capability's tools read. Overwrites; run every cycle.")
    parser.add_argument("--settings", required=True, type=Path,
                        help="the agent's settings.json")
    parser.add_argument("--config-root", required=True, type=Path,
                        help="the config-module home to write <key>.json files into")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.settings.is_file():
        refuse(f"no settings file at {args.settings}", "pass --settings pointing at settings.json")
    try:
        settings = json.loads(args.settings.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        refuse(f"{args.settings} is not valid JSON: {exc}", "fix the file, then re-run")
    if not isinstance(settings, dict):
        refuse(f"{args.settings} is not a JSON object", "settings.json must be an object of keys")
    written = materialize(settings, args.config_root)
    json.dump({"written": written}, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
