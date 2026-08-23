"""The install book at {target}/.rbtv/config/install.json — read, migrate,
write, query.
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from discovery import HUB_DIR, HUB_ID_FOLDER, Refuse, SKILLS_DIR

from .constants import (HARNESSES, INSTALLER_NAME, MANAGED_MARK, SCHEMA,
                        STATE_REL, VERSION)
from .claims import _fence, _jget


def read_state(target: Path) -> dict:
    path = target / STATE_REL
    if not path.is_file():
        return {"schema": SCHEMA, "installer": INSTALLER_NAME, "components": {},
                "shared_claims": []}
    state = json.loads(path.read_text(encoding="utf-8"))
    rewrite_legacy_skill_ids(state)
    strip_retired_harnesses(state)
    migrate_workspace_harnesses(state)
    return state


def write_state(target: Path, state: dict) -> None:
    path = target / STATE_REL
    state["schema"] = SCHEMA
    state["installer"] = INSTALLER_NAME
    state["version"] = VERSION
    state["marker"] = MANAGED_MARK
    state["installed_at"] = _dt.datetime.now().isoformat(timespec="seconds")
    state["target"] = str(target.resolve())
    state.pop("prefix", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def rewrite_legacy_skill_ids(state: dict) -> list[tuple[str, str]]:
    """R6 — `_skills/<name>` → `_hub/skills/<name>` on load; persist on write."""
    moved: list[tuple[str, str]] = []
    comps = state.get("components") or {}
    for old in list(comps):
        if not old.startswith(f"{SKILLS_DIR}/"):
            continue
        new = f"{HUB_DIR}/{HUB_ID_FOLDER['skill']}/{old.split('/', 1)[1]}"
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
    """D16 — the WORKSPACE harness set. `None` means never recorded, which is
    what makes `--harness` mandatory on the first `add` and refused after it.
    A recorded set is normalised to canonical order and filtered to D4's
    harnesses (a hand-edited book cannot smuggle one back in)."""
    raw = state.get("harnesses")
    if raw is None:
        return None
    return [h for h in HARNESSES if h in raw]


def migrate_workspace_harnesses(state: dict) -> None:
    """D16 — a pre-D16 book records harnesses only per component. Lift them to
    the workspace level by UNION: the widest set any component held. Narrower
    would delete files on the very next run, before the human asked for it.
    A book with no components stays unrecorded — nothing was ever installed,
    so the first `add` is still the first `add`."""
    comps = state.get("components") or {}
    if state.get("harnesses") is not None or not comps:
        return
    lifted = installed_harnesses(comps)
    if lifted:
        state["harnesses"] = lifted


def _wanted_parts(rec: dict) -> set[str] | None:
    raw = rec.get("parts")
    return None if raw is None else set(raw)


def rec_files(rec: dict) -> set[str]:
    out = set(rec.get("files") or [])
    for part in (rec.get("parts") or {}).values():
        out |= set(part.get("files") or [])
    return out


def rec_owns_nothing(rec: dict) -> bool:
    """True when a booked record holds no files, claims, or PATH links."""
    if rec_files(rec) or rec.get("path_links") or rec.get("claims"):
        return False
    for part in (rec.get("parts") or {}).values():
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


def _part_in(state: dict, cid: str, pid: str) -> bool:
    rec = (state.get("components") or {}).get(cid)
    if rec is None and cid.startswith(f"{HUB_DIR}/skills/"):
        rec = (state.get("components") or {}).get(
            f"{SKILLS_DIR}/{cid.rsplit('/', 1)[-1]}")
    if rec is None:
        return False
    parts = rec.get("parts")
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
    migrate_workspace_harnesses(state)
    out = dict(state)
    out["schema"] = SCHEMA
    comps = {k: dict(v) for k, v in (state.get("components") or {}).items()}
    for cid in list(comps):
        rec = comps[cid]
        if cid not in catalog_parts and rec_owns_nothing(rec):
            comps.pop(cid)
            continue
        if "parts" in rec:
            rec["parts"] = {p: dict(b) for p, b in rec["parts"].items()}
            continue
        if cid not in catalog_parts:
            continue
        rec["parts"] = {r["id"]: {"method": r["method"], "files": []}
                        for r in catalog_parts[cid]}
    out["components"] = comps
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
    if keypart == "#block":
        text = path.read_text(encoding="utf-8")
        start, end = _fence("#")
        if start not in text or end not in text:
            return None
        body = text.split(start, 1)[1].split(end, 1)[0].strip("\n")
        return {"path": rel, "fmt": "text", "comment": "#", "key": None,
                "value": body, "owner": owner}
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
