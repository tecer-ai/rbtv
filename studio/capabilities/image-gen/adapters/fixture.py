"""Deterministic fixture/echo adapter for pluggability testing.

Generates a solid-color image via Pillow. Completely offline and deterministic.
"""

from pathlib import Path

from PIL import Image

# Deterministic dimensions by aspect ratio
_ASPECT_MAP = {
    "1:1": (512, 512),
    "16:9": (1024, 576),
    "9:16": (576, 1024),
    "4:3": (1024, 768),
    "3:2": (1024, 683),
    "21:9": (1344, 576),
}

_DEFAULT_SIZE = (512, 512)

# A distinct fixture color (RGB)
_FIXTURE_COLOR = (0x42, 0x8A, 0xF5)  # cornflower blue


def generate(prompt: str, out_path: str, fmt: str, aspect: str | None = None, api_key: str | None = None) -> None:
    size = _ASPECT_MAP.get(aspect, _DEFAULT_SIZE)
    img = Image.new("RGB", size, _FIXTURE_COLOR)

    out = Path(out_path)
    if fmt == "jpg":
        img.save(out, format="JPEG", quality=85)
    else:
        img.save(out, format="PNG")
