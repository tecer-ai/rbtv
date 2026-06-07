#!/usr/bin/env python3
"""Re-vendor tool: copies the engine into a target library and syncs engine_version."""

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Copy the engine into a target library and sync engine_version"
    )
    parser.add_argument("--library", type=str, required=True, help="Path to target library")
    args = parser.parse_args()

    ENGINE_SRC = Path(__file__).resolve().parent / "assemble.py"
    if not ENGINE_SRC.exists():
        print(f"ERROR: engine source not found: {ENGINE_SRC}", file=sys.stderr)
        sys.exit(1)

    library_path = Path(args.library)
    library_json_path = library_path / "library.json"
    if not library_json_path.exists():
        print(f"ERROR: library.json not found in {library_path}", file=sys.stderr)
        sys.exit(1)

    # Read ENGINE_VERSION from engine source via importlib
    spec = importlib.util.spec_from_file_location("engine_assemble", ENGINE_SRC)
    engine_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine_mod)
    engine_version = engine_mod.ENGINE_VERSION

    target_assemble = library_path / "assemble.py"
    shutil.copy2(ENGINE_SRC, target_assemble)
    print(f"copied engine -> {target_assemble}")

    with open(library_json_path, "r", encoding="utf-8") as f:
        library_data = json.load(f)

    old_version = library_data.get("engine_version", "")
    library_data["engine_version"] = engine_version

    with open(library_json_path, "w", encoding="utf-8") as f:
        json.dump(library_data, f, indent=2)
        f.write("\n")

    print(f"engine_version: {old_version} -> {engine_version}")
    sys.exit(0)


if __name__ == "__main__":
    main()
