#!/usr/bin/env python3
"""image-gen capability — source-pluggable image generation.

Entry point: python studio/capabilities/image-gen/generate.py --prompt "..." --out path/img.png [--provider gemini] [--aspect 16:9] [--env-file path]
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add the capability directory to the path for adapter imports
CAP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CAP_DIR))

from adapters import resolve_provider, list_providers  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an image from a text prompt.")
    parser.add_argument("--prompt", required=True, help="Text prompt for image generation.")
    parser.add_argument("--out", required=True, help="Output file path (extension implies format: png/jpg).")
    parser.add_argument("--provider", default="gemini", help="Provider adapter name (default: gemini).")
    parser.add_argument("--aspect", default=None, help="Desired aspect ratio, e.g. 16:9, 1:1.")
    parser.add_argument("--env-file", default=None, help="Path to a KEY=value env file for credentials.")
    return parser.parse_args()


def derive_format(out_path: str) -> str:
    ext = Path(out_path).suffix.lower()
    if ext in (".png",):
        return "png"
    if ext in (".jpg", ".jpeg"):
        return "jpg"
    return "png"


def resolve_gemini_key(env_file: str | None) -> str | None:
    """Resolution order: OS env var GEMINI_API_KEY first, then env-file if supplied."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    if env_file:
        path = Path(env_file)
        if path.exists():
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def ensure_out_writable(out_path: str) -> None:
    """Fail fast if the output path is unwritable."""
    p = Path(out_path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        # Touch a temporary file to verify writability
        tmp = p.parent / f".write-test-{os.getpid()}"
        tmp.write_text("x", encoding="utf-8")
        tmp.unlink()
    except Exception as exc:
        print(f"image-gen: error: cannot write to output path '{out_path}': {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    args = parse_args()

    # Fail fast on unwritable output
    ensure_out_writable(args.out)

    fmt = derive_format(args.out)
    provider_name = args.provider

    # Resolve adapter
    adapter = resolve_provider(provider_name)
    if adapter is None:
        registered = ", ".join(sorted(list_providers()))
        print(f"image-gen: error: unknown provider '{provider_name}'. Registered providers: {registered}", file=sys.stderr)
        return 1

    # Credential resolution (only Gemini needs this currently; interface keeps it explicit)
    api_key = resolve_gemini_key(args.env_file)

    # If the chosen provider is gemini and we have no key, fail cleanly
    if provider_name == "gemini" and not api_key:
        print("image-gen: error: GEMINI_API_KEY is missing. Set the GEMINI_API_KEY environment variable or provide --env-file.", file=sys.stderr)
        return 1

    start = time.perf_counter()
    try:
        adapter.generate(
            prompt=args.prompt,
            out_path=args.out,
            fmt=fmt,
            aspect=args.aspect,
            api_key=api_key,
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        print(f"image-gen: error: generation failed after {elapsed_ms}ms: {exc}", file=sys.stderr)
        # Ensure no partial file is left
        try:
            Path(args.out).unlink(missing_ok=True)
        except Exception:
            pass
        return 1

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    print(f"image-gen: saved {args.out} ({elapsed_ms}ms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
