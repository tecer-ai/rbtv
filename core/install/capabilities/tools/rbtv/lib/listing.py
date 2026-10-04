"""The `ls` and `li` views: what exists, what is installed, and this
installation's settings.
"""
from __future__ import annotations

from pathlib import Path

from discovery import Refuse, unit_rows

from . import present, subagents
from .constants import BASIS_NONE, MANAGED_MARK, STATE_REL
from .catalog import (
    _unit_specs,
    catalog_packs,
    catalog_units_map,
)
from .state import (_unit_in, book_harnesses, read_state, selected_packs,
                    upgrade_book)
from .selection import (component_keys, iter_booked_units, iter_catalog_parts,
                        module_names, unit_key, resolve_name)


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
            "unit_count": len(specs), "note": note,
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
        units = []
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
            units.append({"id": key, "unit_id": pid, "method": meth,
                          "description": detail["description"],
                          "in": detail["installed"]})
        if (want_x or drop_x or want_c or drop_c) and not units:
            continue
        entries.append({
            "id": cid, "tree": c.get("tree", ""), "module": mod,
            "kind": "hub" if hub else c.get("kind", "component"),
            "manifest": bool(c.get("manifest")),
            "methods": sorted({i["method"] for i in units}),
            "unit_count": len(units), "units": units, "note": note,
        })
    return {"ok": True, "components": entries, "shadowed": shadowed}


def build_list(catalog: dict, state: dict, *, query: str = "",
               modules: list[str] | None = None,
               components: list[str] | None = None,
               methods: list[str] | None = None,
               installed: bool = False,
               search: bool = False,
               limit: int = 20, offset: int = 0) -> dict:
    """Browse exact hierarchy, or search the same unit pool broadly."""
    view = build_ls(catalog, [], state)
    book = state.get("components") or {}
    sub_agents = subagents.recorded(state)
    want_m = module_names(modules or [], catalog, book)
    want_c = component_keys(components or [], catalog, book) if components else set()
    want_x = set(methods or [])
    words = query.casefold().split() if search else []
    rows: list[dict] = []
    for comp in view["components"]:
        source_comp = catalog.get(comp["id"]) or {}
        comp_desc = _short_description(source_comp.get("description", ""))
        mod_desc = _short_description(source_comp.get("module_description", ""))
        for part in comp["units"]:
            rows.append({"id": part["id"], "component": comp["id"],
                         "module": comp["module"], "type": part["method"],
                         "description": _short_description(part["description"]),
                         "component_description": comp_desc,
                         "module_description": mod_desc,
                         "_search": part["description"],
                         "installed": part["in"], "source_available": True,
                         "tree": comp["tree"],
                         **({"sub_agent": sub_agents.get(part["id"], {})}
                            if part["method"] == "agent" else {})})
    seen = {row["id"] for row in rows}
    for part in iter_booked_units(catalog, book):
        if part["key"] in seen:
            continue
        rows.append({"id": part["key"], "component": part["component"],
                     "module": part["module"], "type": part["method"],
                     "description": "Recorded unit; source is no longer available.",
                     "component_description": "", "module_description": "",
                     "installed": True, "source_available": False,
                     "tree": "missing"})
    if "pack" in want_x or query or components or search:
        for pack in catalog_packs(catalog).values():
            rows.append({"id": pack["name"], "component": pack["component"],
                         "module": pack["module"], "type": "pack",
                         "description": (f"Declared by {pack['component']}. "
                                         + _short_description(pack["description"])),
                         "component_description": "", "module_description": "",
                         "_search": pack["description"],
                         "installed": pack["name"] in selected_packs(state),
                         "source_available": True, "tree": pack["tree"],
                         "units": list(pack["units"])})
    matched = []
    for row in sorted(rows, key=lambda unit: unit["id"]):
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
    scope = "units"
    if not search:
        if query:
            try:
                named_module = module_names([query], catalog, book)
            except Refuse:
                named_module = set()
            if named_module and not want_x:
                scope = "components"
                matched = [r for r in matched if r["module"] in named_module
                           and r["type"] != "pack"]
                matched = _group_rows(matched, "component")
            elif named_module and want_x:
                matched = [r for r in matched if r["module"] in named_module]
            else:
                chosen = resolve_name(query, catalog, book,
                                      methods=want_x or None)
                ids = {p["key"] for p in chosen["units"]}
                owner = chosen["id"] if chosen["kind"] == "component" else None
                matched = [r for r in matched if r["id"] in ids
                           or (r["type"] == "pack" and r["component"] == owner)]
                if chosen["kind"] == "component" and not want_x:
                    scope = "units"
        elif not want_x and not components:
            scope = "modules"
            matched = _group_rows(matched, "module")
        elif components and not want_x:
            scope = "components"
            matched = _group_rows([r for r in matched if r["type"] != "pack"],
                                  "component")
    if installed:
        matched = [r for r in matched if (r["installed"] if scope == "units"
                   else r["installed_units"] > 0)]
    total = len(matched)
    page = matched[offset:offset + limit]
    if scope == "units":
        page = [{k: v for k, v in row.items()
                 if k not in ("component_description", "module_description")}
                for row in page]
    return {"ok": True, "query": query, "scope": scope, "total": total,
            "returned": len(page),
            "limit": limit, "offset": offset,
            "units": page}


def _group_rows(rows: list[dict], field: str) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row[field], []).append(row)
    desc_field = "module_description" if field == "module" else "component_description"
    return [{"id": "hub" if name == "_hub" and field == "module" else name,
             "installed_units": sum(r["installed"] for r in parts),
             "source_units": sum(r["source_available"] for r in parts),
             "description": next((r[desc_field] for r in parts if r[desc_field]), "")}
            for name, parts in sorted(grouped.items())]


def _list_scope_noun(data: dict) -> str:
    """The title-line noun: what this table's rows ARE, so list/search/show
    never rely on the reader inferring it from column shape alone."""
    scope, query = data["scope"], data.get("query") or ""
    methods = data.get("methods") or []
    if data.get("searching"):
        return "search results"
    if scope == "modules":
        return "installed modules" if data.get("installed_only") else "modules"
    if scope == "components":
        return f"{query} components" if query else "components"
    if query and data.get("total") == 1:
        return query
    if query:
        packs = any(row["type"] == "pack" for row in data["units"])
        return f"{query} units and packs" if packs else f"{query} units"
    if len(methods) == 1:
        return f"{methods[0]}s"
    return "installed units" if data.get("installed_only") else "units"


def _list_context_line(data: dict) -> str | None:
    scope, query = data["scope"], data.get("query") or ""
    methods = data.get("methods") or []
    if data.get("searching"):
        n = data["total"]
        return (f"Query: {query} (names and descriptions); "
                f"{n} match{'es' if n != 1 else ''}")
    start = data["offset"] + 1 if data["returned"] else 0
    end = data["offset"] + data["returned"]
    if scope == "modules":
        paged = data.get("has_more") or data["offset"]
        return f"Showing {start}-{end} of {data['total']}" if paged else None
    if scope != "units":
        return None
    if query and data["total"] == 1:
        return f"Exact unit: {data['units'][0]['id']}"
    parts = ([query] if query else []) + (
        [f"type {', '.join(methods)}"] if methods else [])
    scope_txt = f"Scope: {'; '.join(parts)}; " if parts else ""
    return f"{scope_txt}showing {start}-{end} of {data['total']}"


_PACK_MEANING = "A named list of units a component declares."


def print_list(data: dict) -> None:
    """Human-readable rendering of `build_list`'s JSON envelope — the JSON
    field names are the stable contract; this only decides how they look on
    a terminal. Module/component rows use ID/Installed units/Description;
    unit rows use ID/Type/State/Description (D9)."""
    print(present.title(_list_scope_noun(data)))
    print()
    print(f"Target: {data['target']} "
          f"({present.target_source_label(data.get('source'))})")
    context = _list_context_line(data)
    if context:
        print(context)
    print()
    units = data["units"]
    if data["scope"] == "units":
        headers = ["ID", "Type", "State", "Description"]
        rows = [[row["id"], row["type"], _unit_state(row),
                 row["description"] + ("" if row["source_available"]
                                        else " (source missing)")]
                for row in units]
    else:
        headers = ["ID", "Installed units", "Description"]
        rows = [[row["id"], f"{row['installed_units']}/{row['source_units']}",
                 row["description"]] for row in units]
    lines = present.render_table(headers, rows)
    for line in lines:
        print(line)
    if not units and not data.get("searching"):  # search says "0 matches"
        print("No installed units in this target." if data.get("installed_only")
              else "No matching units.")
    if units:
        print()
        if data["scope"] != "units":
            text = "Installed units is the saved selection; run doctor to check files."
        elif any(row["type"] == "pack" for row in units):
            if all(row["type"] == "pack" for row in units):
                text = ("State is on or off for this target. Saved selection; "
                        "run doctor to check files.")
            else:
                text = ("State is installed or not installed for a unit, and on or "
                        "off for a pack.\nSaved selection; run doctor to check files.")
        else:
            text = ("State is the saved selection for this target; "
                    "run doctor to check files.")
        print("\n".join(present.wrap(text)))
        for line in subagents.installed_lines(
                {row["id"]: row["sub_agent"] for row in units if row.get("sub_agent")}):
            print("\n".join(present.wrap(line, hang="  ")))
    print()
    label = "More" if data.get("has_more") else "Next"
    print(f"{label}: {data['next']}")


def _unit_state(row: dict) -> str:
    if row["type"] == "pack":
        return "on" if row["installed"] else "off"
    return "installed" if row["installed"] else "not installed"


def json_view(data: dict, *, searching: bool) -> dict:
    """The list/search envelope with the per-row JSON shape the approved
    screens show: list and search carry different keys for a unit row and for
    a pack row. Module and component rows are returned unchanged."""
    if data["scope"] != "units":
        return data
    shaped = []
    for row in data["units"]:
        if row["type"] == "pack" and searching:
            shape = {"id": row["id"], "type": "pack", "description": row["description"],
                     "tree": row["tree"], "source_available": row["source_available"],
                     "on": row["installed"], "declared_by": row["component"]}
        elif row["type"] == "pack":
            shape = {"id": row["id"], "component": row["component"],
                     "module": row["module"], "type": "pack", "on": row["installed"],
                     "declared_by": row["component"], "description": row["description"],
                     "units": row["units"]}
        elif searching:
            shape = {"id": row["id"], "type": row["type"], "description": row["description"],
                     "tree": row["tree"], "source_available": row["source_available"],
                     "installed": row["installed"]}
        else:
            shape = {"id": row["id"], "component": row["component"],
                     "module": row["module"], "type": row["type"],
                     "installed": row["installed"], "description": row["description"],
                     "tree": row["tree"], "source_available": row["source_available"]}
        if "sub_agent" in row:
            shape["sub_agent"] = row["sub_agent"]
        shaped.append(shape)
    return {**data, "units": shaped}


def pack_members(catalog: dict, state: dict, pack: dict) -> list[dict]:
    """The units a pack includes, each with its type and whether it is installed here."""
    types = {part["key"]: part["method"] for part in iter_catalog_parts(catalog)}
    members = []
    for key in pack["units"]:
        cid, _, pid = key.partition("#")
        members.append({"key": key, "type": types.get(key, ""),
                        "installed": _unit_in(state, cid, pid)})
    return members


def build_show(selection: dict, catalog: dict, state: dict) -> dict:
    parts = [unit_detail(catalog, state, part) for part in selection["units"]]
    parts = [{**p, "type": p["method"]} for p in parts]
    for part in parts:
        part.pop("method", None)
    out = {"scope": "unit" if selection["kind"] == "part" else selection["kind"],
           "id": selection["id"],
           "units": parts,
           "harnesses": book_harnesses(state) or []}
    if selection["kind"] == "part":
        out.update(type=parts[0]["type"], component=parts[0]["component"],
                   unit_id=parts[0]["unit_id"])
        if parts[0]["type"] == "agent":
            row = _unit_row(catalog[parts[0]["component"]], parts[0]["unit_id"])
            home = Path(state.get("_target", "")) / ".rbtv" / "agents" / parts[0]["unit_id"]
            name = parts[0]["unit_id"]
            out["agent"] = {"packs": row["data"].get("packs", []),
                            "units": row["data"].get("units", []),
                            "placed": home.is_dir(), "home": str(home),
                            "sub_agent": subagents.recorded(state).get(selection["id"], {}),
                            "add": {"rbtv_agent": f"rbtv agent add {name} --harness HARNESS "
                                                  "--model MODEL --effort EFFORT",
                                    "sub_agent": f"rbtv add {name} --on {subagents.ON_FORM}"}}
    elif selection["kind"] == "component":
        source_comp = catalog.get(selection["id"]) or {}
        source_path = Path(source_comp["path"]) if source_comp.get("path") else None
        description = _short_description(source_comp.get("description", ""))
        out.update(description=description,
                   dependencies=list(source_comp.get("dependencies") or []),
                   source_entry=(str(source_path) if source_path else ""))
    return out


def _say(text: str) -> None:
    """One `Label: prose` line, wrapped under a two-space hang."""
    print("\n".join(present.wrap(text, hang="  ")))


def print_show(data: dict) -> None:
    """Human-readable rendering of `build_show`'s envelope: description,
    included units or installation details, source entry path (D9 §4)."""
    sel = data["selection"]
    print(present.title(f"pack {sel['id']}" if sel["scope"] == "pack" else sel["id"]))
    print()
    print(f"Target: {data['target']} "
          f"({present.target_source_label(data.get('source'))})")
    if sel["scope"] == "pack":
        print(f"Type: pack ({_PACK_MEANING})")
        print("Name: " + sel["id"])
        print("Declared by: " + sel["component"])
        print("Declaration: " + sel["path"])
        _say(f"Description: {sel['description']}")
        print(f"Units: {len(sel['units'])}")
        print("Pack: " + ("on" if sel["enabled"] else "off") + " for this target")
        print()
        rows = [[unit["key"], unit["type"],
                 "installed" if unit["installed"] else "not installed"]
                for unit in sel["units"]]
        for line in present.render_table(["ID", "Type", "State"], rows):
            print(line)
        print()
        print("State is the saved selection for this target; run doctor to check files.")
        print()
        print("Next: " + data["next"])
        return
    if sel["scope"] == "module":
        _say(f"Description: {sel['description'] or '(no catalog description)'}")
        _say(f"Local source: {sel['source_units']} units; "
              f"installed here: {sel['installed_units']} saved selections. "
              "Files not checked.")
        print()
        headers = ["ID", "Installed units", "Description"]
        rows = [[c["id"], f"{c['installed_units']}/{c['source_units']}",
                 c["description"]] for c in sel["components"]]
        for line in present.render_table(headers, rows):
            print(line)
        print()
        print("Next: " + data["next"])
        return
    if sel["scope"] == "component":
        _say(f"Description: {sel.get('description') or '(no catalog description)'}")
        _say("Dependencies: " + (", ".join(sel.get("dependencies") or []) or "none"))
        if sel.get("source_entry"):
            print("Source entry (local RBTV source): " + sel['source_entry'])
        _say(f"Local source: {len(sel['units'])} unit(s) in this component.")
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
        _say(f"Description: {part['description']}")
    if part.get("source_path"):
        print("Source entry (local RBTV source): " + part['source_path'])
    elif part["entry_point"]:
        print("Source entry (local RBTV source): " + part['entry_point'])
    if part["type"] == "agent":
        agent = sel["agent"]
        print()
        print("Declared in its agent.json")
        print("  Packs: " + (", ".join(agent["packs"]) or "none"))
        print("  Other units: " + (", ".join(agent["units"]) or "none"))
    print()
    print("Installation in this target")
    print(f"  Selection: {'installed' if part['installed'] else 'not installed'} "
          "(saved; files not checked here)")
    if part["installed"] and sel.get("harnesses"):
        print("  Receiving tools: " + ", ".join(
            f"{h} ({present.HARNESS_MEANING.get(h, h)})" for h in sel["harnesses"]))
    if part["type"] == "agent":
        agent = sel["agent"]
        written = "; ".join(f"{h} ({subagents.text(v)})"
                            for h, v in agent["sub_agent"].items())
        print("  Harness-native sub-agent: " + (written or "not written for any harness"))
        print("  rbtv agent: " + ("placed at " if agent["placed"] else "no folder at ")
              + agent["home"])
    if not part["source_available"]:
        print("  Source: no longer present in the local catalog")
    if part["type"] == "agent":
        print()
        print("Add it in either form, or both")
        print("  As a harness-native sub-agent: " + sel["agent"]["add"]["sub_agent"])
        print("  As an rbtv agent: " + sel["agent"]["add"]["rbtv_agent"])
        print("  Harnesses, models and efforts: cast list")
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
            # this installation, so they belong with what is installed in it,
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
            "guidance_excludes": list(state.get("guidance_excludes") or []),
            "packs": sorted(selected_packs(state))}
