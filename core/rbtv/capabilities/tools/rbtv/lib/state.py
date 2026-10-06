"""The install book at {target}/.rbtv/config/install.json — read, migrate,
write, query.
"""
from __future__ import annotations

import json
from pathlib import Path

from discovery import HUB_DIR, Refuse, SKILLS_DIR

from .constants import (AGENT_RECORD, HARNESSES, MANAGED_MARK, SCHEMA, STATE_REL, VERSION)
from .claims import _jget, _located
from .content import _is_ours
from .fsio import write_file
from .selection import iter_booked_files


def _state_refuse(path: Path, detail: str) -> None:
    raise Refuse("state-unreadable",
                 f"rbtv state has an invalid structure: {detail} ({path})",
                 str(path))


def _string_list(value: object, label: str, path: Path) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str)
                                              for item in value):
        _state_refuse(path, f"{label} must be a list of strings")


def _validate_state(state: dict, path: Path) -> None:
    """Validate every book shape consumed by migrations and planners."""
    components = state.get("components", {})
    if components is None:
        state["components"] = {}
        components = state["components"]
    if not isinstance(components, dict):
        _state_refuse(path, "components must be an object")
    for cid, rec in components.items():
        if not isinstance(cid, str) or not isinstance(rec, dict):
            _state_refuse(path, "components must map string ids to objects")
        for name in ("files", "claims", "path_links", "harnesses"):
            if name in rec:
                _string_list(rec[name], f"components.{cid}.{name}", path)
        if "units" not in rec:
            continue
        parts = rec["units"]
        if not isinstance(parts, dict):
            _state_refuse(path, f"components.{cid}.units must be an object")
        for pid, part in parts.items():
            if not isinstance(pid, str) or not isinstance(part, dict):
                _state_refuse(path, f"components.{cid}.units must map ids to objects")
            for name in ("files", "claims", "links"):
                if name in part:
                    _string_list(part[name],
                                 f"components.{cid}.units.{pid}.{name}", path)
            values = part.get("sub_agent", {})
            if not isinstance(values, dict) or not all(
                    harness in HARNESSES and isinstance(entry, dict)
                    and all(isinstance(entry.get(key), str)
                            for key in ("model", "model_id", "effort"))
                    for harness, entry in values.items()):
                _state_refuse(path, f"components.{cid}.units.{pid}.sub_agent must map "
                              "a harness to its model, model_id and effort")
    for name in ("harnesses", "guidance_files", "shared_claims", "units", "packs"):
        if name in state:
            _string_list(state[name], name, path)
    if "guidance_basis" in state and state["guidance_basis"] is not None and \
            not isinstance(state["guidance_basis"], str):
        _state_refuse(path, "guidance_basis must be a string or null")


def is_agent_target(target: Path) -> bool:
    """An agent is identified by its two neighbouring authored files."""
    return (target / "agent.md").is_file() and (target / AGENT_RECORD).is_file()


def state_path(target: Path) -> Path:
    """Return the sole record path for a root or an agent folder."""
    return target / (AGENT_RECORD if is_agent_target(target) else STATE_REL)


# How earlier records named what they booked, and the name read today. A
# record up to schema 7 booked an agent's harness-native file as `sub-agent`;
# it is read as an agent, which holds no model and no effort yet.
_LEGACY_METHODS = {"sub-agent": "agent", "config": "mcp-server",
                   "path": "tool", "agents.md": "folder-instructions"}


def migrate_legacy_record(state: dict) -> None:
    """Read a 0.2 book as a 0.2.1 one: a component's `parts` are its `units`,
    its methods carry the new names, and `pool` parts (never installed) go."""
    for rec in (state.get("components") or {}).values():
        if not isinstance(rec, dict):
            continue
        if "parts" in rec and "units" not in rec:
            rec["units"] = rec.pop("parts")
        files = rec.get("units")
        if not isinstance(files, dict):
            continue
        for uid in [u for u, b in files.items()
                    if isinstance(b, dict) and b.get("method") == "pool"]:
            files.pop(uid)
        for file in files.values():
            if isinstance(file, dict) and file.get("method") in _LEGACY_METHODS:
                file["method"] = _LEGACY_METHODS[file["method"]]


def migrate_portable_record(state: dict) -> None:
    """Read schema 3 records as schema 4 records without machine-local data.

    The migration stays in memory until the next state write, like the other
    record migrations in this module.
    """
    for name in ("installed_at", "target", "installer"):
        state.pop(name, None)
    for rec in (state.get("components") or {}).values():
        if isinstance(rec, dict):
            rec.pop("tree_root", None)


def migrate_selected_files(state: dict) -> None:
    """Schema 4 chose every file it had generated; schema 5 says so plainly.

    The old per-component map remains the generated-file ledger.  `units` is
    the independent, portable selection that later updates reconcile against.
    """
    if "units" in state:
        return
    state["units"] = sorted(
        f"{cid}#{pid}"
        for cid, rec in (state.get("components") or {}).items()
        for pid in (rec.get("units") or {})
    )


def migrate_selected_packs(state: dict) -> None:
    """Schema 6 adds pack selection; older records selected no packs."""
    state.setdefault("packs", [])


def migrate_install_component_ids(state: dict) -> None:
    """Move the former installer booking onto the direct rbtv component.

    The old wrapper owned the public shortcut only.  Dropping it here, before
    planning, lets the ordinary reconciliation release its shortcut while the
    renamed component books the replacement.
    """
    components = state.get("components")
    if not isinstance(components, dict):
        return
    old = components.pop("core/installer", None)
    if old is not None:
        if "core/install" in components:
            raise Refuse("component-id-collision", "book has both 'core/installer' and 'core/install'")
        old["component"] = "install"
        files = old.get("units")
        if isinstance(files, dict) and "rbtv-install" in files:
            files["rbtv"] = files.pop("rbtv-install")
        # Keep the old shortcut booking until reconciliation removes it.  If
        # it were renamed here, `reconcile_shared` would no longer know to
        # release rbtv-install from ~/.rbtv/bin or path-owners.json.
        components["core/install"] = old
    components.pop("core/rbtv-cli", None)
    state["components"] = components
    rewrites = {"core/installer#rbtv-install": "core/install#rbtv"}
    if "units" in state:
        state["units"] = [rewrites.get(key, key) for key in state["units"]
                         if not key.startswith("core/rbtv-cli#")]


# The two components that became `core/rbtv`, and what each of their files is
# called there. `None` marks a file with no successor.
_MERGED_INTO_RBTV = ("core/build", "core/install")
_RBTV_FILE_NAMES = {"core/build#build": "framework",
                    "core/install#manage-components": None}


def _merge_component_record(into: dict, rec: dict) -> None:
    """Fold one booked component into another: lists are joined without
    repeats, files are folded name by name, and any other field keeps the
    value it already has."""
    for name, value in rec.items():
        if name == "units":
            files = into.setdefault("units", {})
            for uid, file in value.items():
                if uid in files:
                    _merge_component_record(files[uid], file)
                else:
                    files[uid] = file
        elif isinstance(value, list) and isinstance(into.get(name), list):
            into[name] = into[name] + [item for item in value
                                       if item not in into[name]]
        else:
            into.setdefault(name, value)


def migrate_rbtv_component_ids(state: dict) -> None:
    """Schema 8 booked rbtv's own files under `core/build` and `core/install`;
    schema 9 books them under the one component `core/rbtv`.

    Both records fold into one. The skill `build` is `framework`. The
    skill `manage-components` has no successor: it leaves the selection here
    and keeps its booking, so the next update deletes its files and names it
    as removed. Generated files are not renamed here either; that same update
    replaces them. A record that holds neither old component is left as it is.
    """
    components = state.get("components") or {}
    merged = components.get("core/rbtv")
    for old in _MERGED_INTO_RBTV:
        rec = components.pop(old, None)
        if rec is None:
            continue
        files = rec.get("units") or {}
        for uid in list(files):
            name = _RBTV_FILE_NAMES.get(f"{old}#{uid}")
            if name is not None:
                files[name] = files.pop(uid)
        rec["component"] = "rbtv"
        if merged is None:
            merged = rec
        else:
            _merge_component_record(merged, rec)
    if merged is not None:
        components["core/rbtv"] = merged
    selected: list[str] = []
    for key in state.get("units") or []:
        cid, _, uid = key.partition("#")
        if cid in _MERGED_INTO_RBTV:
            name = _RBTV_FILE_NAMES.get(key, uid)
            if name is None:
                continue
            key = f"core/rbtv#{name}"
        if key not in selected:
            selected.append(key)
    if "units" in state:
        state["units"] = selected


def read_state(target: Path) -> dict:
    path = state_path(target)
    if not path.is_file():
        # A fresh target has made no explicit choice.  Without these fields,
        # the next read mistakes files generated for a newly enabled pack as
        # the schema-4 migration input and records them as explicit choices.
        return {"schema": SCHEMA, "components": {}, "shared_claims": [],
                "units": [], "packs": []}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refuse("state-unreadable",
                     f"cannot read rbtv state; repair or restore {path} before changing this installation ({exc})",
                     str(path)) from exc
    if not isinstance(state, dict):
        raise Refuse("state-unreadable",
                     f"rbtv state must be a JSON object: {path}", str(path))
    migrate_legacy_record(state)
    migrate_portable_record(state)
    migrate_install_component_ids(state)
    migrate_selected_files(state)
    migrate_selected_packs(state)
    _validate_state(state, path)
    migrate_rbtv_component_ids(state)
    rewrite_legacy_skill_ids(state)
    strip_retired_harnesses(state)
    migrate_installation_harnesses(state)
    return state


def write_state(target: Path, state: dict) -> None:
    path = state_path(target)
    state["schema"] = SCHEMA
    state["version"] = VERSION
    state["marker"] = MANAGED_MARK
    for name in ("prefix", "installed_at", "target", "installer"):
        state.pop(name, None)
    if is_agent_target(target):
        state.pop("harnesses", None)
    for rec in (state.get("components") or {}).values():
        if isinstance(rec, dict):
            rec.pop("tree_root", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_file(path, json.dumps(state, indent=2, sort_keys=True) + "\n")


def rewrite_legacy_skill_ids(state: dict) -> list[tuple[str, str]]:
    """R6 — `_skills/<name>` → `_hub/skills/<name>` on load; persist on write."""
    moved: list[tuple[str, str]] = []
    comps = state.get("components") or {}
    for old in list(comps):
        if not old.startswith(f"{SKILLS_DIR}/"):
            continue
        new = f"{HUB_DIR}/skills/{old.split('/', 1)[1]}"
        rec = comps.pop(old)
        rec["module"] = HUB_DIR
        if new in comps:
            raise Refuse("hub-id-collision",
                         f"book has both {old!r} and {new!r}", old)
        comps[new] = rec
        moved.append((old, new))
    return moved


def strip_retired_harnesses(state: dict) -> None:
    """D4 — drop `kimi` (and any other name not in HARNESSES) from every
    booked record. Persist happens on the next write. A strip that would
    leave a record with no harness refuses — never write an empty list."""
    for cid, rec in (state.get("components") or {}).items():
        raw = rec.get("harnesses")
        if raw is None:
            continue
        kept = [h for h in HARNESSES if h in raw]
        if not kept:
            raise Refuse(
                "harness-list-empty",
                f"{cid}: dropping retired harnesses would leave none "
                f"(had: {', '.join(raw) or '(empty)'})",
                cid)
        rec["harnesses"] = kept


def installed_harnesses(records: dict[str, dict]) -> list[str]:
    """The harness set the whole installed set targets — the union across the
    book's records, in canonical order. This is what keys the guidance mirror
    (D13): a component installed for codex is what puts AGENTS.md on the tree."""
    return [h for h in HARNESSES
            if any(h in (rec.get("harnesses") or []) for rec in records.values())]


def book_harnesses(state: dict) -> list[str] | None:
    """D16 — the INSTALLATION harness set. `None` means never recorded, which is
    what makes `--harness` mandatory on the first `add` and refused after it.
    A recorded set is normalised to canonical order and filtered to D4's
    harnesses (a hand-edited book cannot smuggle one back in)."""
    raw = state.get("harnesses")
    if raw is None:
        return None
    return [h for h in HARNESSES if h in raw]


def migrate_installation_harnesses(state: dict) -> None:
    """D16 — a pre-D16 book records harnesses only per component. Lift them to
    the installation level by UNION: the widest set any component held. Narrower
    would delete files on the very next run, before the human asked for it.
    A book with no components stays unrecorded — nothing was ever installed,
    so the first `add` is still the first `add`."""
    comps = state.get("components") or {}
    if state.get("harnesses") is not None or not comps:
        return
    lifted = installed_harnesses(comps)
    if lifted:
        state["harnesses"] = lifted


def _wanted_files(rec: dict) -> set[str] | None:
    raw = rec.get("units")
    return None if raw is None else set(raw)


def rec_files(rec: dict) -> set[str]:
    out = set(rec.get("files") or [])
    for part in (rec.get("units") or {}).values():
        out |= set(part.get("files") or [])
    return out


def rec_owns_nothing(rec: dict) -> bool:
    """True when a booked record holds no files, claims, or PATH links."""
    if rec_files(rec) or rec.get("path_links") or rec.get("claims"):
        return False
    for part in (rec.get("units") or {}).values():
        if not isinstance(part, dict):
            continue
        if part.get("claims") or part.get("links"):
            return False
    return True


def known_files(state: dict) -> set[str]:
    out = set(state.get("guidance_files") or [])
    for rec in (state.get("components") or {}).values():
        out |= rec_files(rec)
    return out


def known_claims(state: dict) -> set[str]:
    return set(state.get("shared_claims") or [])


def selected_files(state: dict) -> set[str]:
    """The root's explicit file selection, as full catalog ids."""
    return set(state.get("units") or [])


def selected_packs(state: dict) -> set[str]:
    """The root's enabled pack names."""
    return set(state.get("packs") or [])


def _file_in(state: dict, cid: str, pid: str) -> bool:
    rec = (state.get("components") or {}).get(cid)
    if rec is None and cid.startswith(f"{HUB_DIR}/skills/"):
        rec = (state.get("components") or {}).get(
            f"{SKILLS_DIR}/{cid.rsplit('/', 1)[-1]}")
    if rec is None:
        return False
    parts = rec.get("units")
    if parts is None:
        return True
    return pid in parts


def upgrade_book(state: dict, catalog_parts: dict[str, list[dict]]) -> dict:
    """In-memory schema-2 view. Does not strip rec['files'] (apply still needs them).

    A booked id that is no longer catalogued and owns nothing (no files, no
    claims, no PATH links) is dropped: it never installed anything, so there
    is nothing to protect. A vanished id that DOES own files stays and later
    refuses component-vanished.
    """
    strip_retired_harnesses(state)
    migrate_installation_harnesses(state)
    out = dict(state)
    out["schema"] = SCHEMA
    comps = {k: dict(v) for k, v in (state.get("components") or {}).items()}
    for cid in list(comps):
        rec = comps[cid]
        if cid not in catalog_parts and rec_owns_nothing(rec):
            comps.pop(cid)
            continue
        if "units" in rec:
            rec["units"] = {p: dict(b) for p, b in rec["units"].items()}
            continue
        if cid not in catalog_parts:
            continue
        rec["units"] = {r["id"]: {"method": r["method"], "files": []}
                        for r in catalog_parts[cid]}
    out["components"] = comps
    migrate_portable_record(out)
    out.pop("prefix", None)
    return out


def _rebuild_claim(target: Path, claim_id: str, owner: tuple) -> dict | None:
    """Reconstruct a planned claim from a booked id + on-disk value.

    Used when a vanished component's remaining parts cannot remint from a
    catalog: D7 still needs the claim in the planned set so apply does not
    release a sibling part's key.
    """
    rel, _, keypart = claim_id.partition("::")
    path = target / rel
    if not path.is_file():
        return None
    if keypart.startswith("#block"):
        label = keypart[len("#block:"):] or None
        comment = "<!--" if rel.endswith(".md") else "#"
        text = path.read_text(encoding="utf-8")
        found = _located(text, comment, label)
        if not found:
            return None
        body = text.split(found[0], 1)[1].split(found[1], 1)[0].strip("\n")
        claim = {"path": rel, "fmt": "text", "comment": comment, "key": None,
                 "value": body, "owner": owner}
        if label:
            claim["label"] = label
        return claim
    key = json.loads(keypart)
    try:
        doc = json.loads(path.read_text(encoding="utf-8") or "{}")
    except ValueError:
        return None
    value, found = _jget(doc, key)
    if not found:
        return None
    return {"path": rel, "fmt": "json", "key": key, "value": value,
            "owner": owner}


def _files_missing_generated(target: Path, state: dict) -> set[str]:
    """Recorded files whose generated files are absent or released."""
    missing: set[str] = set()
    for cid, rec in (state.get("components") or {}).items():
        for pid, booked in (rec.get("units") or {}).items():
            generated = booked.get("files") or []
            if any(not (target / rel).is_file() or not _is_ours(target, rel)
                   for rel in generated):
                missing.add(f"{cid}#{pid}")
    return missing


def file_membership(target: Path, catalog: dict, state: dict, chosen: set[str]) -> dict:
    """An update's reconciliation: the files the record lists (`chosen`) against
    the files booked on disk. Read it before the update writes anything. A
    listed file whose generated files are gone counts as added."""
    booked = {row["key"] for row in iter_booked_files(catalog, state.get("components") or {})}
    missing = _files_missing_generated(target, state)
    return {"booked": booked, "listed_missing": chosen - booked,
            "on_disk_unlisted": booked - chosen,
            "added": (chosen - booked) | (chosen & missing),
            "removed": booked - chosen}
