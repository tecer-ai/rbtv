"""Checking a value against one of the JSON Schemas in `core/build/capabilities/
templates/`. The installer is standard-library only, so this covers exactly the
keywords those schemas use: type, required, properties, additionalProperties,
items, enum, const, pattern, minLength, minimum, minItems, uniqueItems, oneOf,
not. `format`, `title` and `description` are ignored.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .constants import REPO_ROOT

SCHEMA_DIR = REPO_ROOT / "core" / "build" / "capabilities" / "templates"

_TYPES = {
    "object": dict, "array": list, "string": str,
    "integer": int, "number": (int, float), "boolean": bool,
}


def load(name: str) -> dict:
    """The schema `<name>.schema.json`, by its template name."""
    path = SCHEMA_DIR / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def errors(value: object, schema: dict, at: str = "") -> list[str]:
    """Every way *value* breaks *schema*, each naming where. Empty = valid."""
    out: list[str] = []
    where = at or "(top level)"
    want = schema.get("type")
    if want:
        expected = _TYPES[want]
        ok = isinstance(value, expected) and not (
            want in ("integer", "number") and isinstance(value, bool))
        if not ok:
            return [f"{where}: must be {want}"]
    if "const" in schema and value != schema["const"]:
        out.append(f"{where}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{where}: must be one of {', '.join(map(str, schema['enum']))}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            out.append(f"{where}: must not be empty")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{where}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and "minimum" in schema \
            and value < schema["minimum"]:
        out.append(f"{where}: must be at least {schema['minimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            out.append(f"{where}: needs at least {schema['minItems']} item(s)")
        if schema.get("uniqueItems") and len(set(map(json.dumps, value))) != len(value):
            out.append(f"{where}: items must be unique")
        if "items" in schema:
            for i, item in enumerate(value):
                out += errors(item, schema["items"], f"{at}[{i}]")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                out.append(f"{where}: missing {key!r}")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            sub = f"{at}.{key}" if at else key
            if key in props:
                out += errors(item, props[key], sub)
            elif extra is False:
                out.append(f"{sub}: not a field of this file")
            elif isinstance(extra, dict):
                out += errors(item, extra, sub)
    if "oneOf" in schema:
        hits = sum(not errors(value, sub, at) for sub in schema["oneOf"])
        if hits != 1:
            out.append(f"{where}: must match exactly one of the allowed shapes")
    if "not" in schema and not errors(value, schema["not"], at):
        out.append(f"{where}: is not allowed here")
    return out
