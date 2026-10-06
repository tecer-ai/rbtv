"""The key `files` of the three records that list chosen files: install.json,
an agent's agent.json, and a pack. A record that names that key `units` is read
here, in the one place every reader of those records calls.
"""
from __future__ import annotations


def files_key(record: object) -> object:
    """`record` with its chosen files under `files`. A record whose key is
    `units` is read as if it were `files`; the record is written with `files`
    the next time the program writes it. A value that is not an object is
    returned as it is, for its reader to refuse."""
    if isinstance(record, dict) and "units" in record:
        named_units = record.pop("units")
        record.setdefault("files", named_units)
    return record
