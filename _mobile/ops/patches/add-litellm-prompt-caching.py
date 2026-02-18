#!/usr/bin/env python3
"""Add LiteLLM prompt caching to Nanobot's litellm_provider.py.

Injects cache_control_injection_points for system messages into the
acompletion() kwargs, enabling Anthropic prompt caching for the system prompt.

Run on VPS with:
   python3 add-litellm-prompt-caching.py /path/to/litellm_provider.py

If no path given, attempts auto-discovery via: pip show nanobot
"""
import subprocess
import sys
from pathlib import Path

ANCHOR = "response = await acompletion(**kwargs)"
INJECTION = 'kwargs["cache_control_injection_points"] = [{"location": "message", "role": "system"}]'


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

    if "cache_control_injection_points" in source:
        print(f"Already patched: {path} (cache_control_injection_points found)")
        return

    lines = source.split("\n")
    anchor_found = any(line.strip() == ANCHOR for line in lines)
    if not anchor_found:
        print(
            f"Patch target not found in {path}.\n"
            f"Expected: {ANCHOR!r}\n"
            f"Nanobot may have been upgraded — review the source and update this patch.",
            file=sys.stderr,
        )
        sys.exit(1)

    new_lines = []
    for line in lines:
        if line.strip() == ANCHOR:
            indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}{INJECTION}")
        new_lines.append(line)

    patched = "\n".join(new_lines)
    path.write_text(patched)
    print(f"Patched {path} -> added cache_control_injection_points for system messages")


if __name__ == "__main__":
    main()
