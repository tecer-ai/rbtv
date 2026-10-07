"""The keys of the records that list chosen files, read from a record that
names them `units`: `files` in install.json, an agent's agent.json and a pack,
and `selected` under each component of install.json and of an installed
agent.json. Every reader of those records calls `current_keys`.
"""
from __future__ import annotations


def _renamed(record: dict, key: str) -> None:
    if "units" in record:
        named_units = record.pop("units")
        record.setdefault(key, named_units)


def both_spellings(record: object) -> list[str]:
    """Where `record`, as it is on disk, carries a key under both of its
    names. `current_keys` keeps the new key there and drops `units`."""
    if not isinstance(record, dict):
        return []
    found = []
    if "units" in record and "files" in record:
        found.append("`files` and `units` at the top of the record")
    components = record.get("components")
    for cid, component in sorted(components.items()
                                 if isinstance(components, dict) else ()):
        if isinstance(component, dict) and {"units", "selected"} <= set(component):
            found.append(f"`selected` and `units` under {cid}")
    return found


def current_keys(record: object) -> object:
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
