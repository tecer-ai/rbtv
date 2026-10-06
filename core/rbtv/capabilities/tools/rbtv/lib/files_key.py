"""The keys of the records that list chosen files, read from a record that
names them `units`: `files` in install.json, an agent's agent.json and a pack,
and `selected` under each component of install.json and of an installed
agent.json. Every reader of those records calls the one function here.
"""
from __future__ import annotations


def _renamed(record: dict, key: str) -> None:
    if "units" in record:
        named_units = record.pop("units")
        record.setdefault(key, named_units)


def files_key(record: object) -> object:
    """`record` with its chosen files under `files`, and each component's map
    of what was installed under `selected`. A record whose key is `units` in
    either place is read as if it had the new key; the record is written with
    the new keys the next time the program writes it. A value that is not an
    object is returned as it is, for its reader to refuse."""
    if not isinstance(record, dict):
        return record
    _renamed(record, "files")
    components = record.get("components")
    for component in (components.values() if isinstance(components, dict) else ()):
        if isinstance(component, dict):
            _renamed(component, "selected")
    return record
