"""The `ls` and `li` views: what exists, what is installed, and this
workspace's settings.
"""
from __future__ import annotations

from pathlib import Path

from discovery import Refuse, unit_rows

from . import present
from .constants import BASIS_NONE, MANAGED_MARK, STATE_REL
from .catalog import (
    _unit_specs,
    catalog_units_map,
)
from .state import _unit_in, book_harnesses, read_state, upgrade_book
from .selection import (component_keys, iter_booked_units, module_names,
                        unit_key, resolve_name)


def _unit_row(comp: dict, pid: str) -> dict:
    """The catalog row of one unit of a component, or {}."""
    if comp.get("manifest"):
        return next((r for r in unit_rows(comp) if r["id"] == pid), {})
    return {}


def _unit_description(comp: dict, pid: str) -> str:
    row = _unit_row(comp, pid)
    if row:
        return row["description"]
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


def _safe_specs(comp: dict) -> tuple[list[dict], str]:
    """A component's units, or none and why: one component's invalid file must
    not blank the whole listing."""
    try:
        return _unit_specs(comp), ""
    except Refuse as exc:
        return [], exc.message


def _short_description(text: str) -> str:
    sentence = text.split(". ", 1)[0].strip()
    if sentence and not sentence.endswith("."):
        sentence += "."
    if len(sentence) <= 150:
        return sentence
    head = sentence[:147].rsplit(" ", 1)[0] or sentence[:147]
    return head.rstrip(".,;:") + "…"


def unit_detail(catalog: dict, state: dict, part: dict) -> dict:
    cid, pid = part["component"], part["unit_id"]
    comp = catalog.get(cid) or {}
    row = _unit_row(comp, pid)
    entry_point = row.get("entry", "")
    comp_path = Path(comp["path"]) if comp.get("path") else None
    return {**part,
            "description": _unit_description(comp, pid),
            "entry_point": entry_point,
            # The unambiguous path a human can open: entry_point alone
            # (e.g. `prompts/brainstorm.md`) is component-relative and reads
            # like a repo root. This is entry_point resolved under the
            # component's own source directory.
            "source_path": (str(comp_path / entry_point)
                            if comp_path and entry_point else ""),
            "tree": comp.get("tree") or "book",
            "source_available": bool(comp and (comp.get("kind") == "hub" or row)),
            "installed": _unit_in(state, cid, pid)}


def do_scan(catalog: dict[str, dict], shadowed: list[dict]) -> dict:
    entries = []
    for cid in sorted(catalog):
        c = catalog[cid]
        specs, note = _safe_specs(c)
        entries.append({
            "id": cid, "tree": c["tree"], "module": c["module"],
            "kind": c.get("kind", "component"),
            "manifest": c["manifest"],
            "methods": sorted({s["method"] for s in specs}),
            "units": len(specs), "note": note,
        })
    return {"ok": True, "components": entries, "shadowed": shadowed}


def catalog_ids(catalog: dict, cid: str) -> list[str]:
    c = catalog.get(cid) or {}
    return [s["id"] for s in _unit_specs(c) if s.get("id")]


def status_of(cid: str, rec: dict, catalog: dict
              ) -> tuple[str, set[str], set[str], set[str]]:
    cat = set(catalog_ids(catalog, cid))
    booked = set(rec["units"]) if "units" in rec else cat
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
        specs, note = _safe_specs(c)
        for spec in specs:
            pid, meth = spec["id"], spec.get("method") or ""
            key = unit_key(cid, pid)
            if want_c and key not in want_c:
                continue
            if key in drop_c:
                continue
            if want_x and meth not in want_x:
                continue
            if drop_x and meth in drop_x:
                continue
            detail = unit_detail(catalog, state, {
                "key": key, "component": cid, "module": mod,
                "unit_id": pid, "method": meth})
            items.append({"id": key, "unit_id": pid, "method": meth,
                          "description": detail["description"],
                          "in": detail["installed"]})
        if (want_x or drop_x or want_c or drop_c) and not items:
            continue
        entries.append({
            "id": cid, "tree": c.get("tree", ""), "module": mod,
            "kind": "hub" if hub else c.get("kind", "component"),
            "manifest": bool(c.get("manifest")),
            "methods": sorted({i["method"] for i in items}),
            "units": len(items), "items": items, "note": note,
        })
    return {"ok": True, "components": entries, "shadowed": shadowed}


def build_list(catalog: dict, state: dict, *, query: str = "",
               modules: list[str] | None = None,
               components: list[str] | None = None,
               methods: list[str] | None = None,
               installed: bool = False,
               search: bool = False,
               limit: int = 20, offset: int = 0) -> dict:
    """Browse exact hierarchy, or search the same item pool broadly."""
    view = build_ls(catalog, [], state)
    book = state.get("components") or {}
    want_m = module_names(modules or [], catalog, book)
    want_c = component_keys(components or [], catalog, book) if components else set()
    want_x = set(methods or [])
    words = query.casefold().split() if search else []
    rows: list[dict] = []
    for comp in view["components"]:
        source_comp = catalog.get(comp["id"]) or {}
        comp_desc = _short_description(source_comp.get("description", ""))
        mod_desc = _short_description(source_comp.get("module_description", ""))
        for part in comp["items"]:
            rows.append({"id": part["id"], "component": comp["id"],
                         "module": comp["module"], "type": part["method"],
                         "description": _short_description(part["description"]),
                         "component_description": comp_desc,
                         "module_description": mod_desc,
                         "_search": part["description"],
                         "installed": part["in"], "source_available": True,
                         "tree": comp["tree"]})
    seen = {row["id"] for row in rows}
    for part in iter_booked_units(catalog, book):
        if part["key"] in seen:
            continue
        rows.append({"id": part["key"], "component": part["component"],
                     "module": part["module"], "type": part["method"],
                     "description": "Recorded item; source is no longer available.",
                     "component_description": "", "module_description": "",
                     "installed": True, "source_available": False,
                     "tree": "missing"})
    matched = []
    for row in sorted(rows, key=lambda item: item["id"]):
        if want_m and row["module"] not in want_m:
            continue
        if want_c and row["id"] not in want_c:
            continue
        if want_x and row["type"] not in want_x:
            continue
        unit_id = row["id"].split("#", 1)[-1]
        hay = " ".join((row["id"], unit_id,
                        row.get("_search", row["description"]))).casefold()
        if words and not all(word in hay for word in words):
            continue
        matched.append({key: value for key, value in row.items()
                        if key != "_search"})
    scope = "items"
    if not search:
        if query:
            try:
                named_module = module_names([query], catalog, book)
            except Refuse:
                named_module = set()
            if named_module and not want_x:
                scope = "components"
                matched = [r for r in matched if r["module"] in named_module]
                matched = _group_rows(matched, "component")
            elif named_module and want_x:
                matched = [r for r in matched if r["module"] in named_module]
            else:
                chosen = resolve_name(query, catalog, book,
                                      methods=want_x or None)
                ids = {p["key"] for p in chosen["units"]}
                matched = [r for r in matched if r["id"] in ids]
                if chosen["kind"] == "component" and not want_x:
                    scope = "items"
        elif not want_x and not components:
            scope = "modules"
            matched = _group_rows(matched, "module")
        elif components and not want_x:
            scope = "components"
            matched = _group_rows(matched, "component")
    if installed:
        matched = [r for r in matched if (r["installed"] if scope == "items"
                   else r["installed_items"] > 0)]
    total = len(matched)
    page = matched[offset:offset + limit]
    if scope == "items":
        page = [{k: v for k, v in row.items()
                 if k not in ("component_description", "module_description")}
                for row in page]
    return {"ok": True, "query": query, "scope": scope, "total": total,
            "returned": len(page),
            "limit": limit, "offset": offset,
            "items": page}


def _group_rows(rows: list[dict], field: str) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row[field], []).append(row)
    desc_field = "module_description" if field == "module" else "component_description"
    return [{"id": "hub" if name == "_hub" and field == "module" else name,
             "installed_items": sum(r["installed"] for r in parts),
             "source_items": sum(r["source_available"] for r in parts),
             "description": next((r[desc_field] for r in parts if r[desc_field]), "")}
            for name, parts in sorted(grouped.items())]


def _list_scope_noun(data: dict) -> str:
    """The title-line noun: what this table's rows ARE, so list/search/show
    never rely on the reader inferring it from column shape alone."""
    scope, query = data["scope"], data.get("query") or ""
    if data.get("searching"):
        return "search results"
    if scope == "modules":
        return "installed modules" if data.get("installed_only") else "modules"
    if scope == "components":
        return f"{query} components" if query else "components"
    if query and data.get("total") == 1:
        return query
    if query:
        return f"{query} items"
    return "installed items" if data.get("installed_only") else "items"


def _list_context_line(data: dict) -> str | None:
    scope, query = data["scope"], data.get("query") or ""
    if data.get("searching"):
        n = data["total"]
        return (f"Query: {query} (names and descriptions); "
                f"{n} match{'es' if n != 1 else ''}")
    if scope != "items":
        return None
    if query and data["total"] == 1:
        return f"Exact item: {data['items'][0]['id']}"
    start = data["offset"] + 1 if data["returned"] else 0
    end = data["offset"] + data["returned"]
    scope_txt = f"Scope: {query}; " if query else ""
    return f"{scope_txt}showing {start}-{end} of {data['total']}"


def print_list(data: dict) -> None:
    """Human-readable rendering of `build_list`'s JSON envelope — the JSON
    field names are the stable contract; this only decides how they look on
    a terminal. Module/component rows use ID/Installed items/Description;
    item rows use ID/Type/State/Description (D9)."""
    print(present.title(_list_scope_noun(data)))
    print()
    print(f"Target: {data['target']} "
          f"({present.target_source_label(data.get('source'))})")
    context = _list_context_line(data)
    if context:
        print(context)
    print()
    items = data["items"]
    if data["scope"] == "items":
        headers = ["ID", "Type", "State", "Description"]
        rows = [[row["id"], row["type"],
                 "installed" if row["installed"] else "not installed",
                 row["description"] + ("" if row["source_available"]
                                        else " (source missing)")]
                for row in items]
    else:
        headers = ["ID", "Installed items", "Description"]
        rows = [[row["id"], f"{row['installed_items']}/{row['source_items']}",
                 row["description"]] for row in items]
    lines = present.render_table(headers, rows)
    for line in lines:
        print(line)
    if items:
        print()
        if data["scope"] == "items":
            print("State is the saved selection for this target; "
                  "run doctor to check files.")
        else:
            print("Installed items is the saved selection; "
                  "run doctor to check files.")
    print()
    label = "More" if data.get("has_more") else "Next"
    print(f"{label}: {data['next']}")


def build_show(selection: dict, catalog: dict, state: dict) -> dict:
    parts = [unit_detail(catalog, state, part) for part in selection["units"]]
    parts = [{**p, "type": p["method"]} for p in parts]
    for part in parts:
        part.pop("method", None)
    out = {"scope": "item" if selection["kind"] == "part" else selection["kind"],
           "id": selection["id"],
           "units": parts,
           "harnesses": book_harnesses(state) or []}
    if selection["kind"] == "part":
        out.update(type=parts[0]["type"], component=parts[0]["component"],
                   unit_id=parts[0]["unit_id"])
    elif selection["kind"] == "component":
        source_comp = catalog.get(selection["id"]) or {}
        source_path = Path(source_comp["path"]) if source_comp.get("path") else None
        description = _short_description(source_comp.get("description", ""))
        out.update(description=description,
                   source_entry=(str(source_path) if source_path else ""))
    return out


def print_show(data: dict) -> None:
    """Human-readable rendering of `build_show`'s envelope: description,
    included items or installation details, source entry path (D9 §4)."""
    sel = data["selection"]
    print(present.title(sel["id"]))
    print()
    print(f"Target: {data['target']} "
          f"({present.target_source_label(data.get('source'))})")
    if sel["scope"] == "module":
        print(f"Description: {sel['description'] or '(no catalog description)'}")
        print(f"Local source: {sel['source_items']} items; "
              f"installed here: {sel['installed_items']} saved selections. "
              "Files not checked.")
        print()
        headers = ["ID", "Installed items", "Description"]
        rows = [[c["id"], f"{c['installed_items']}/{c['source_items']}",
                 c["description"]] for c in sel["components"]]
        for line in present.render_table(headers, rows):
            print(line)
        print()
        print("Next: " + data["next"])
        return
    if sel["scope"] == "component":
        print(f"Description: {sel.get('description') or '(no catalog description)'}")
        if sel.get("source_entry"):
            print(f"Source entry: {sel['source_entry']} (local RBTV source)")
        print(f"Local source: {len(sel['units'])} item(s) in this component.")
        print()
        headers = ["ID", "Type", "State", "Description"]
        rows = [[p["key"], p["type"],
                 "installed" if p["installed"] else "not installed",
                 p["description"]] for p in sel["units"]]
        for line in present.render_table(headers, rows):
            print(line)
        print()
        print("Next: " + data["next"])
        return
    part = sel["units"][0]
    meaning = present.TYPE_MEANING.get(part["type"], "")
    print(f"Type: {part['type']}" + (f" ({meaning})" if meaning else ""))
    if part["description"]:
        print(f"Description: {part['description']}")
    if part.get("source_path"):
        print(f"Source entry: {part['source_path']} (local RBTV source)")
    elif part["entry_point"]:
        print(f"Source entry: {part['entry_point']} (local RBTV source)")
    print()
    print("Installation in this target")
    print(f"  Selection: {'installed' if part['installed'] else 'not installed'} "
          "(saved; files not checked here)")
    if part["installed"] and sel.get("harnesses"):
        print("  Receiving tools: " + ", ".join(
            f"{h} ({present.HARNESS_MEANING.get(h, h)})" for h in sel["harnesses"]))
    if not part["source_available"]:
        print("  Source: no longer present in the local catalog")
    print()
    print("Next: " + data["next"])


def do_list(target: Path, catalog: dict | None = None) -> dict:
    raw = read_state(target)
    catalog = catalog or {}
    state = upgrade_book(raw, catalog_units_map(catalog)) if catalog else raw
    comps: dict = {}
    links: list[dict] = []
    for cid, rec in sorted((state.get("components") or {}).items()):
        rec = dict(rec)
        st, booked, miss, orph = status_of(cid, rec, catalog)
        rec["status"], rec["missing"], rec["orphans"] = (
            st, sorted(miss), sorted(orph))
        rec.setdefault("units", {})
        comps[cid] = rec
        for pid, part in (rec.get("units") or {}).items():
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
