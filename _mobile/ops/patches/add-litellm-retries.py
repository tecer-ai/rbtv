#!/usr/bin/env python3
"""Add LiteLLM retry logic to Nanobot's litellm_provider.py.

Injects litellm.num_retries = 3 alongside existing module-level litellm
settings, preventing user-facing errors on transient rate limit responses.

Run on VPS with:
   python3 add-litellm-retries.py /path/to/litellm_provider.py

If no path given, attempts auto-discovery via: pip show nanobot
"""
import subprocess
import sys
from pathlib import Path

ANCHOR = "litellm.drop_params = True"
INJECTION = "litellm.num_retries = 3"


def find_provider_file() -> Path | None:
    """Auto-discover litellm_provider.py from pip installation."""
    try:
        out = subprocess.check_output(
            ["pip", "show", "-f", "nanobot"], text=True, stderr=subprocess.DEVNULL
        )
        location = None
        for line in out.splitlines():
            if line.startswith("Location:"):
                location = line.split(":", 1)[1].strip()
                break
        if location:
            candidate = Path(location) / "nanobot" / "providers" / "litellm_provider.py"
            if candidate.exists():
                return candidate
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = find_provider_file()
        if path is None:
            print("Could not auto-discover litellm_provider.py. Pass path as argument.", file=sys.stderr)
            sys.exit(1)

    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    source = path.read_text()

    if "num_retries" in source:
        print(f"Already patched: {path} (num_retries found)")
        return

    if ANCHOR not in source:
        print(
            f"Patch target not found in {path}.\n"
            f"Expected: {ANCHOR!r}\n"
            f"Nanobot may have been upgraded — review the source and update this patch.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Insert num_retries on the line after drop_params, preserving indentation
    lines = source.split("\n")
    new_lines = []
    for line in lines:
        new_lines.append(line)
        stripped = line.strip()
        if stripped == ANCHOR:
            indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}{INJECTION}")

    patched = "\n".join(new_lines)
    path.write_text(patched)
    print(f"Patched {path} -> added litellm.num_retries = 3")


if __name__ == "__main__":
    main()
