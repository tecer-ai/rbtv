"""Reading the frontmatter of a unit file: the `---` block at the top.

The installer is standard-library only, so this reads the small YAML subset the
unit schemas use: `key: value` scalars (plain or quoted), `key: [a, b]`, and
`key:` followed by `- unit` lines.
"""
from __future__ import annotations

import json
import re

_BLOCK = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)


def split(text: str) -> tuple[dict | None, str]:
    """(frontmatter, body). Frontmatter is None when the file has none."""
    found = _BLOCK.match(text)
    if not found:
        return None, text
    return _parse(found.group(1)), text[found.end():]


def _scalar(raw: str) -> object:
    raw = raw.strip()
    if raw.startswith(("'", '"')) and raw.endswith(raw[0]) and len(raw) >= 2:
        if raw[0] == '"':
            try:
                return json.loads(raw)
            except ValueError:
                pass
        return raw[1:-1]
    return raw


def _flow_list(raw: str) -> list:
    inner = raw.strip()[1:-1].strip()
    return [_scalar(unit) for unit in inner.split(",")] if inner else []


def _parse(block: str) -> dict:
    out: dict = {}
    key: str | None = None
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        unit = re.match(r"\s+-\s+(.*)$", line) or re.match(r"-\s+(.*)$", line)
        if unit and key is not None and isinstance(out.get(key), list):
            out[key].append(_scalar(unit.group(1)))
            continue
        name, sep, value = line.partition(":")
        if not sep:
            continue
        key = name.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            out[key] = _flow_list(value)
        elif value == "":
            out[key] = []
        else:
            out[key] = _scalar(value)
    return out
