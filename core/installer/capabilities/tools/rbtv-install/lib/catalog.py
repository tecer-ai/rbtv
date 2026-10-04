"""Reading one discovered component record: its identity and its units.
"""
from __future__ import annotations

from discovery import HUB_DIR, Refuse, pack_rows, unit_rows


def module_id(name: str) -> str:
    """Selector token → catalog module. `-m hub` reaches `_hub`. THE ONE mapping."""
    return HUB_DIR if name == "hub" else name


def _unit_specs(comp: dict) -> list[dict]:
    """Catalog units of one component: [{'id', 'method'}, ...]."""
    if comp.get("kind") == "hub":
        return [{"id": comp["component"],
                 "method": comp.get("method") or "skill"}]
    return [{"id": row["id"], "method": row["method"]}
            for row in (comp["rows"] if "rows" in comp else unit_rows(comp))]


def catalog_units_map(catalog: dict[str, dict]) -> dict[str, list[dict]]:
    """Units of every component. A component whose own files are invalid maps
    to no units here, so it blocks only its own install (planning refuses it),
    never the rest of the catalog."""
    out: dict[str, list[dict]] = {}
    for cid, comp in catalog.items():
        try:
            out[cid] = _unit_specs(comp)
        except Refuse:
            out[cid] = []
    return out


def catalog_packs(catalog: dict[str, dict]) -> dict[str, dict]:
    """Pack declarations keyed by their globally unique names."""
    return {row["name"]: row for row in pack_rows(catalog)}


def check_packs(catalog: dict[str, dict], names: set[str],
                next_cmd: str | None = None) -> None:
    """Refuse, naming every pack in `names` that the catalog does not hold."""
    unknown = sorted(set(names) - set(catalog_packs(catalog)))
    if unknown:
        exc = Refuse("pack-unknown", "unknown pack "
                     + ", ".join(repr(name) for name in unknown)
                     + ". Run `rbtv list --type pack` to see packs.")
        if next_cmd:
            exc.next = next_cmd
        raise exc


def pack_units(catalog: dict[str, dict], names: set[str]) -> set[str]:
    """Expand enabled pack names to their unit ids, refusing unknown names."""
    check_packs(catalog, names)
    packs = catalog_packs(catalog)
    return {unit for name in names for unit in packs[name]["units"]}
