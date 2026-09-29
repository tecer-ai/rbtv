"""The `ls` and `li` views: what exists, what is installed, and this
workspace's settings.
"""
from __future__ import annotations

from pathlib import Path

from discovery import exposure_rows

from .constants import BASIS_NONE, MANAGED_MARK, STATE_REL
from .catalog import (
    _hub_refuse_message,
    _part_specs,
    catalog_parts_map,
)
from .state import _part_in, book_harnesses, read_state, upgrade_book
from .selection import component_keys, iter_booked_parts, module_names, part_key


def _part_description(comp: dict, pid: str) -> str:
    if comp.get("manifest"):
        for row in exposure_rows(comp):
            if (row.get("part-id") or "").strip() == pid:
                return (row.get("description") or "").strip()
    if comp.get("kind") == "hub":
        source = Path(comp["path"])
        if source.is_dir():
            source /= "SKILL.md"
        if source.is_file() and source.suffix == ".md":
            try:
                lines = source.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                return ""
            for line in lines[:20]:
                if line.startswith("description:"):
                    return line.partition(":")[2].strip().strip('"')
    return ""


def _short_description(text: str) -> str:
    sentence = text.split(". ", 1)[0].strip()
    if sentence and not sentence.endswith("."):
        sentence += "."
    return sentence if len(sentence) <= 150 else sentence[:147].rstrip() + "…"


def part_detail(catalog: dict, state: dict, part: dict) -> dict:
    cid, pid = part["component"], part["part_id"]
    comp = catalog.get(cid) or {}
    row = next((r for r in exposure_rows(comp)
                if (r.get("part-id") or "").strip() == pid), {}) if comp.get("manifest") else {}
    return {**part,
            "description": _part_description(comp, pid),
            "entry_point": (row.get("entry-point") or "").strip(),
            "tree": comp.get("tree") or "book",
            "source_available": bool(comp and (comp.get("kind") == "hub" or row)),
            "installed": _part_in(state, cid, pid)}


def do_scan(catalog: dict[str, dict], shadowed: list[dict]) -> dict:
    entries = []
    for cid in sorted(catalog):
        c = catalog[cid]
        hub = c.get("kind") == "hub"
        rows = exposure_rows(c) if c["manifest"] else []
        refusal = c.get("hub_refusal") or ""
        specs = _part_specs(c)
        entries.append({
            "id": cid, "tree": c["tree"], "module": c["module"],
            "kind": c.get("kind", "component"),
            "manifest": c["manifest"],
            "methods": ([c["method"]] if hub else
                        sorted({(r.get("method") or "").strip() for r in rows
                                if (r.get("part-id") or "").strip()})),
            "parts": len(specs),
            "note": (_hub_refuse_message(c) if refusal else ""),
            "refusal": refusal,
        })
    return {"ok": True, "components": entries, "shadowed": shadowed,
            "hub_refusals": [e["id"] for e in entries if e.get("refusal")]}


def catalog_ids(catalog: dict, cid: str) -> list[str]:
    c = catalog.get(cid) or {}
    return [s["id"] for s in _part_specs(c) if s.get("id")]


def status_of(cid: str, rec: dict, catalog: dict
              ) -> tuple[str, set[str], set[str], set[str]]:
    cat = set(catalog_ids(catalog, cid))
    booked = set(rec["parts"]) if "parts" in rec else cat
    if cid not in catalog:
        return "gone", booked, set(), booked
    if not cat:
        return "ok", booked, set(), booked - cat
    miss, orph = cat - booked, booked - cat
    st = "part" if booked and booked < cat else "full"
    return st, booked, miss, orph


def build_ls(catalog: dict, shadowed: list, state: dict, *,
             modules: list[str] | None = None,
             methods: list[str] | None = None,
             components: list[str] | None = None,
             exclude_modules: list[str] | None = None,
             exclude_methods: list[str] | None = None,
             exclude_components: list[str] | None = None) -> dict:
    want_m = module_names(modules or [], catalog)
    want_x = set(methods or [])
    want_c = component_keys(components or [], catalog) if components else set()
    drop_m = module_names(exclude_modules or [], catalog)
    drop_x = set(exclude_methods or [])
    drop_c = component_keys(exclude_components or [], catalog) if exclude_components else set()
    entries = []
    for cid in sorted(catalog):
        c = catalog[cid]
        hub = c.get("kind") in ("hub", "skill-folder")
        mod = c.get("module") or cid.split("/")[0]
        if want_m and mod not in want_m:
            continue
        if drop_m and mod in drop_m:
            continue
        items = []
        for spec in _part_specs(c):
            pid, meth = spec["id"], spec.get("method") or ""
            key = part_key(cid, pid)
            if want_c and key not in want_c:
                continue
            if key in drop_c:
                continue
            if want_x and meth not in want_x:
                continue
            if drop_x and meth in drop_x:
                continue
            detail = part_detail(catalog, state, {
                "key": key, "component": cid, "module": mod,
                "part_id": pid, "method": meth})
            items.append({"id": key, "part_id": pid, "method": meth,
                          "description": detail["description"],
                          "in": detail["installed"]})
        refusal = c.get("hub_refusal") or ""
        note = _hub_refuse_message(c) if refusal else ""
        if (want_x or drop_x or want_c or drop_c) and not items:
            continue
        entries.append({
            "id": cid, "tree": c.get("tree", ""), "module": mod,
            "kind": "hub" if hub else c.get("kind", "component"),
            "manifest": bool(c.get("manifest")),
            "methods": sorted({i["method"] for i in items}),
            "parts": len(items), "note": note, "items": items,
            "refusal": refusal,
        })
    hub_refusals = [cid for cid, c in sorted(catalog.items())
                    if c.get("hub_refusal")]
    return {"ok": True, "components": entries, "shadowed": shadowed,
            "hub_refusals": hub_refusals}


def build_list(catalog: dict, state: dict, *, query: str = "",
               modules: list[str] | None = None,
               components: list[str] | None = None,
               methods: list[str] | None = None,
               installed: bool = False,
               limit: int = 20, offset: int = 0) -> dict:
    """Bounded search over the same stable keys that mutation resolves."""
    view = build_ls(catalog, [], state)
    book = state.get("components") or {}
    want_m = module_names(modules or [], catalog, book)
    want_c = component_keys(components or [], catalog, book) if components else set()
    want_x = set(methods or [])
    words = query.casefold().split()
    rows: list[dict] = []
    for comp in view["components"]:
        for part in comp["items"]:
            rows.append({"id": part["id"], "component": comp["id"],
                         "module": comp["module"], "method": part["method"],
                         "description": _short_description(part["description"]),
                         "_search": part["description"],
                         "installed": part["in"], "source_available": True,
                         "tree": comp["tree"]})
    seen = {row["id"] for row in rows}
    for part in iter_booked_parts(catalog, book):
        if part["key"] in seen:
            continue
        rows.append({"id": part["key"], "component": part["component"],
                     "module": part["module"], "method": part["method"],
                     "description": "Recorded item; source is no longer available.",
                     "installed": True, "source_available": False,
                     "tree": "missing"})
    matched = []
    for row in sorted(rows, key=lambda item: item["id"]):
        if want_m and row["module"] not in want_m:
            continue
        if want_c and row["id"] not in want_c:
            continue
        if want_x and row["method"] not in want_x:
            continue
        if installed and not row["installed"]:
            continue
        part_id = row["id"].split("#", 1)[-1]
        hay = " ".join((row["id"], part_id,
                        row.get("_search", row["description"]))).casefold()
        if words and not all(word in hay for word in words):
            continue
        matched.append({key: value for key, value in row.items()
                        if key != "_search"})
    total = len(matched)
    return {"ok": True, "query": query, "total": total,
            "returned": len(matched[offset:offset + limit]),
            "limit": limit, "offset": offset,
            "items": matched[offset:offset + limit]}


def print_list(data: dict) -> None:
    start = data["offset"] + 1 if data["returned"] else 0
    end = data["offset"] + data["returned"]
    print(f"Found {data['total']} item(s); showing {start}-{end}.")
    for row in data["items"]:
        state = ("recorded installed" if row["installed"] else "available")
        if not row["source_available"]:
            state += "; source unavailable"
        description = f" — {row['description']}" if row["description"] else ""
        print(f"{row['id']} ({row['method']}, {state}){description}")
    print("next: " + data["next"])


def build_show(selection: dict, catalog: dict, state: dict) -> dict:
    parts = [part_detail(catalog, state, part) for part in selection["parts"]]
    out = {"kind": selection["kind"], "id": selection["id"],
           "parts": parts}
    if selection["kind"] == "part":
        out.update(method=parts[0]["method"], component=parts[0]["component"],
                   part_id=parts[0]["part_id"])
    return out


def print_show(data: dict) -> None:
    selected = data["selection"]
    print(f"{selected['kind']}: {selected['id']}")
    for part in selected["parts"]:
        print(f"  {part['key']} — {part['method']}, "
              f"{'recorded installed' if part['installed'] else 'available'}")
        if part["description"]:
            print(f"  {part['description']}")
        if part["entry_point"]:
            print(f"  Source: {part['entry_point']}")
    print("next: " + data["next"])


def do_list(target: Path, catalog: dict | None = None) -> dict:
    raw = read_state(target)
    catalog = catalog or {}
    state = upgrade_book(raw, catalog_parts_map(catalog)) if catalog else raw
    comps: dict = {}
    links: list[dict] = []
    for cid, rec in sorted((state.get("components") or {}).items()):
        rec = dict(rec)
        st, booked, miss, orph = status_of(cid, rec, catalog)
        rec["status"], rec["missing"], rec["orphans"] = (
            st, sorted(miss), sorted(orph))
        rec.setdefault("parts", {})
        comps[cid] = rec
        for pid, part in (rec.get("parts") or {}).items():
            if not isinstance(part, dict):
                continue
            for name in part.get("links") or []:
                links.append({"name": name, "component": cid, "part": pid})
    return {"ok": True, "target": str(target.resolve()),
            "schema": state.get("schema"),
            "state_file": str(target / STATE_REL),
            "marker": MANAGED_MARK,
            "guidance_basis": state.get("guidance_basis"),
            # D16c — the settings ride the INSTALLED listing. They describe
            # this workspace, so they belong with what is installed in it,
            # not behind two verbs of their own.
            "settings": _settings_view(state),
            "components": comps,
            "guidance_files": state.get("guidance_files") or [],
            "shared_claims": state.get("shared_claims") or [],
            "path_links": links}


def _settings_view(state: dict) -> dict:
    harnesses = book_harnesses(state)
    return {"ok": True,
            "recorded": harnesses is not None,
            "harnesses": harnesses,
            "artifact": (state.get("guidance_basis") or BASIS_NONE
                         if "guidance_basis" in state else None),
            "guidance_excludes": list(state.get("guidance_excludes") or [])}
