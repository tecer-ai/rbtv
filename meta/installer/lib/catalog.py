"""Reading one discovered component record: its identity, its parts, whether it
can be installed.
"""
from __future__ import annotations

from pathlib import Path

from discovery import EXPOSURE_NAME, HUB_DIR, Refuse, exposure_rows


def module_id(name: str) -> str:
    """Selector token → catalog module. `-m hub` reaches `_hub`. THE ONE mapping."""
    return HUB_DIR if name == "hub" else name


def _hub_refuse_message(comp: dict) -> str:
    cid = comp.get("id", "?")
    code = comp.get("hub_refusal")
    if code == "hub-pool-inexpressible":
        return (f"{cid}: pool is not expressible as a hub entry — a pool "
                "part is identified by an exposure.csv row; a bare file "
                "cannot say what it is (R4)")
    if code == "hub-path-directory":
        return (f"{cid}: path is expressible only as a single FILE — a "
                "directory does not say which child to link (R4)")
    return f"{cid}: hub entry refused ({code})"


def _part_specs(comp: dict, *, strict: bool = False) -> list[dict]:
    """Catalog parts of one component: [{'id', 'method'}, ...].

    R1: a duplicate part-id in one exposure.csv refuses when *strict*
    (planning / install / uninstall). Upgrade and list stay silent.
    """
    if comp.get("kind") == "hub":
        return [{"id": comp["component"],
                 "method": comp.get("method") or "skill"}]
    seen: list[str] = []
    dups: set[str] = set()
    out: list[dict] = []
    for row in (comp["rows"] if "rows" in comp else exposure_rows(comp)):
        pid = (row.get("part-id") or "").strip()
        if not pid:
            continue
        if pid in seen:
            dups.add(pid)
        else:
            seen.append(pid)
        out.append({"id": pid, "method": (row.get("method") or "").strip()})
    if dups and strict:
        raise Refuse(
            "part-id-duplicate",
            f"{comp.get('id', '?')}: exposure.csv repeats part-id "
            f"{', '.join(sorted(dups))} — two rows cannot share a bare "
            "part-id (R1). Refusing before any write",
            str(Path(comp["path"]) / EXPOSURE_NAME))
    return out


def catalog_parts_map(catalog: dict[str, dict]) -> dict[str, list[dict]]:
    return {cid: _part_specs(comp) for cid, comp in catalog.items()}


def is_installable(comp: dict) -> bool:
    """A unit this installer can act on: a component with an exposure manifest,
    or a D15 whole-skill folder (which has no manifest by construction)."""
    return bool(comp["manifest"]) or (
        comp.get("kind") == "hub" and not comp.get("hub_refusal"))
