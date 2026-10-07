"""Reading the frontmatter of a source file: the `---` block at the top.

The installer is standard-library only, so this reads the small YAML subset the
schemas use, and the block scalars a shareable `SKILL.md` writes its description
in: `key: value` scalars (plain or quoted), `key: [a, b]`, `key:` followed by
`- item` lines, and `key: >` (folded) or `key: |` (literal) followed by indented
lines, each with an optional chomping mark `-` or `+`.
"""
from __future__ import annotations

import json
import re
from itertools import groupby

_BLOCK = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
# What follows the colon when the value is a block: the style, then the chomping mark.
_BLOCK_SCALAR = re.compile(r"([>|])([+-]?)")


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
    return [_scalar(item) for item in inner.split(",")] if inner else []


def _block_scalar(lines: list[str], style: str, chomp: str) -> str:
    """The value of a `>` or `|` block: its lines without their shared indent.
    Folded joins the lines of a paragraph with one space and keeps one line
    break per blank line; literal keeps every line break. The value ends with
    one line break, none with `-`, every trailing one with `+`."""
    indent = min((len(line) - len(line.lstrip()) for line in lines if line.strip()),
                 default=0)
    rows = [line[indent:] if line.strip() else "" for line in lines]
    content = rows[:max((n + 1 for n, row in enumerate(rows) if row), default=0)]
    if not content:
        return ""
    if style == "|":
        text = "\n".join(content)
    else:
        text = "".join(" ".join(group) if filled else "\n" * len(list(group))
                       for filled, group in groupby(content, key=bool))
    if chomp == "-":
        return text
    return text + "\n" * (len(rows) - len(content) + 1 if chomp == "+" else 1)


def _parse(block: str) -> dict:
    out: dict = {}
    key: str | None = None
    lines = block.splitlines()
    at = 0
    while at < len(lines):
        line = lines[at]
        at += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"\s+-\s+(.*)$", line) or re.match(r"-\s+(.*)$", line)
        if item and key is not None and isinstance(out.get(key), list):
            out[key].append(_scalar(item.group(1)))
            continue
        name, sep, value = line.partition(":")
        if not sep:
            continue
        key = name.strip()
        value = value.strip()
        scalar = _BLOCK_SCALAR.fullmatch(value)
        if scalar:
            end = at
            while end < len(lines) and (not lines[end].strip() or lines[end][0] in " \t"):
                end += 1
            out[key] = _block_scalar(lines[at:end], *scalar.groups())
            at = end
        elif value.startswith("[") and value.endswith("]"):
            out[key] = _flow_list(value)
        elif value == "":
            out[key] = []
        else:
            out[key] = _scalar(value)
    return out
