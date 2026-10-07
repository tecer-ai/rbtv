"""The `ls` and `li` views: what exists, what is installed, and this
installation's settings.
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from discovery import Refuse, file_rows

from . import frontmatter, present, subagents
from .constants import BASIS_NONE, GROUP_TYPES, MANAGED_MARK, STATE_REL
from .catalog import (
    _file_specs,
    catalog_packs,
    catalog_files_map,
    module_id,
)
from .state import (_file_in, book_harnesses, read_state, selected_packs,
                    upgrade_book)
from .selection import (CLOSE_NAME, component_keys, iter_booked_files, iter_catalog_parts,
                        module_names, file_key, resolve_name)


def _file_row(comp: dict, pid: str) -> dict:
    """The catalog row of one file of a component, or {}."""
    if comp.get("manifest"):
        return next((r for r in file_rows(comp) if r["id"] == pid), {})
    return {}


def _file_description(comp: dict, pid: str) -> str:
    row = _file_row(comp, pid)
    if row:
        return row["description"]
    if comp.get("kind") == "hub":
        source = Path(comp["path"])
        if source.is_dir():
            source /= "SKILL.md"
        if source.is_file() and source.suffix == ".md":
            try:
                front, _body = frontmatter.split(source.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                return ""
            description = (front or {}).get("description")
            return description.strip() if isinstance(description, str) else ""
    return ""


def _safe_specs(comp: dict) -> tuple[list[dict], str]:
    """A component's files, or none and why: one component's invalid file must
    not blank the whole listing."""
    try:
        return _file_specs(comp), ""
    except Refuse as exc:
        return [], exc.message


def _description(text: str, full: bool) -> str:
    """A description as a list shows it: its first sentence, cut at 150
    characters; with --full, the whole text on one line."""
    return " ".join(text.split()) if full else _short_description(text)


def _short_description(text: str) -> str:
    sentence = text.split(". ", 1)[0].strip()
    if sentence and not sentence.endswith("."):
        sentence += "."
    if len(sentence) <= 150:
        return sentence
    head = sentence[:147].rsplit(" ", 1)[0] or sentence[:147]
    return head.rstrip(".,;:") + "…"


def file_detail(catalog: dict, state: dict, part: dict) -> dict:
    cid, pid = part["component"], part["file_id"]
    comp = catalog.get(cid) or {}
    row = _file_row(comp, pid)
    entry_point = row.get("entry", "")
    comp_path = Path(comp["path"]) if comp.get("path") else None
    return {**part,
            "description": _file_description(comp, pid),
            "entry_point": entry_point,
            # The unambiguous path a human can open: entry_point alone
            # (e.g. `prompts/brainstorm.md`) is component-relative and reads
            # like a repo root. This is entry_point resolved under the
            # component's own source directory.
            "source_path": (str(comp_path / entry_point)
                            if comp_path and entry_point else ""),
            "tree": comp.get("tree") or "book",
            "source_available": bool(comp and (comp.get("kind") == "hub" or row)),
            "installed": _file_in(state, cid, pid)}


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
            "file_count": len(specs), "note": note,
        })
    return {"ok": True, "components": entries, "shadowed": shadowed}


def catalog_ids(catalog: dict, cid: str) -> list[str]:
    c = catalog.get(cid) or {}
    return [s["id"] for s in _file_specs(c) if s.get("id")]


def status_of(cid: str, rec: dict, catalog: dict
              ) -> tuple[str, set[str], set[str], set[str]]:
    cat = set(catalog_ids(catalog, cid))
    booked = set(rec["selected"]) if "selected" in rec else cat
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
        files = []
        specs, note = _safe_specs(c)
        for spec in specs:
            pid, meth = spec["id"], spec.get("method") or ""
            key = file_key(cid, pid)
            if want_c and key not in want_c:
                continue
            if key in drop_c:
                continue
            if want_x and meth not in want_x:
                continue
            if drop_x and meth in drop_x:
                continue
            detail = file_detail(catalog, state, {
                "key": key, "component": cid, "module": mod,
                "file_id": pid, "method": meth})
            files.append({"id": key, "file_id": pid, "method": meth,
                          "description": detail["description"],
                          "in": detail["installed"]})
        if (want_x or drop_x or want_c or drop_c) and not files:
            continue
        entries.append({
            "id": cid, "tree": c.get("tree", ""), "module": mod,
            "kind": "hub" if hub else c.get("kind", "component"),
            "manifest": bool(c.get("manifest")),
            "methods": sorted({i["method"] for i in files}),
            "file_count": len(files), "files": files, "note": note,
        })
    return {"ok": True, "components": entries, "shadowed": shadowed}


def build_list(catalog: dict, state: dict, *, query: str = "",
               modules: list[str] | None = None,
               components: list[str] | None = None,
               methods: list[str] | None = None,
               installed: bool = False,
               search: bool = False, full: bool = False,
               limit: int = 20, offset: int = 0) -> dict:
    """Browse exact hierarchy, or search the same file pool broadly. The type
    `module` or `component` asks for that table of groups, alone: a list of
    them, or the search rows of that kind."""
    view = build_ls(catalog, [], state)
    book = state.get("components") or {}
    sub_agents = subagents.recorded(state)
    want_m = module_names(modules or [], catalog, book)
    want_c = component_keys(components or [], catalog, book) if components else set()
    want_x = set(methods or [])
    group = single_group_type(want_x)
    if group and not search:
        want_x = set()
    words = query.casefold().split() if search else []
    rows: list[dict] = []
    # Every module and component of the source, with or without installable files.
    groups: dict[str, dict[str, dict]] = {"module": {}, "component": {}}
    for comp in view["components"]:
        source_comp = catalog.get(comp["id"]) or {}
        comp_desc = _description(source_comp.get("description", ""), full)
        mod_desc = _description(source_comp.get("module_description", ""), full)
        groups["component"][comp["id"]] = {
            "module": comp["module"], "description": comp_desc,
            "whole": source_comp.get("description", "")}
        groups["module"].setdefault(comp["module"], {
            "module": comp["module"], "description": mod_desc,
            "whole": source_comp.get("module_description", "")})
        for part in comp["files"]:
            rows.append({"id": part["id"], "component": comp["id"],
                         "module": comp["module"], "type": part["method"],
                         "description": _description(part["description"], full),
                         "component_description": comp_desc,
                         "module_description": mod_desc,
                         "_search": part["description"],
                         "installed": part["in"], "source_available": True,
                         "tree": comp["tree"],
                         **({"sub_agent": sub_agents.get(part["id"], {})}
                            if part["method"] == "agent" else {})})
    seen = {row["id"] for row in rows}
    for part in iter_booked_files(catalog, book):
        if part["key"] in seen:
            continue
        rows.append({"id": part["key"], "component": part["component"],
                     "module": part["module"], "type": part["method"],
                     "description": "Recorded file; source is no longer available.",
                     "component_description": "", "module_description": "",
                     "installed": True, "source_available": False,
                     "tree": "missing"})
    if "pack" in want_x or query or components or search:
        rows += [_pack_row(pack, state, full) for pack in catalog_packs(catalog).values()]
    if search:
        rows += [row for field in GROUP_TYPES
                 for row in _group_search_rows(rows, field, groups[field])]
    matched = []
    for row in sorted(rows, key=lambda file: file["id"]):
        if want_m and row["module"] not in want_m:
            continue
        if want_c and row["id"] not in want_c:
            continue
        if want_x and row["type"] not in want_x:
            continue
        if words and not all(word in _search_text(row) for word in words):
            continue
        matched.append({key: value for key, value in row.items()
                        if key != "_search"})
    scope = "files"
    if group and not search:
        scope = group + "s"
        files = [r for r in matched if r["type"] != "pack"]
        named = {name for name, known in groups[group].items()
                 if not want_m or known["module"] in want_m}
        if query and (group == "module" or module_id(query) in groups["module"]):
            modules_named = module_names([query], catalog, book)
            files = [r for r in files if r["module"] in modules_named]
            named = {name for name in named
                     if groups[group][name]["module"] in modules_named}
        elif query:
            chosen = resolve_name(query, catalog, book, component_only=True,
                                  empty_ok=True)["id"]
            files = [r for r in files if r["component"] == chosen]
            named &= {chosen}
        matched = _group_rows(files, group, {name: groups[group][name] for name in named})
    elif not search:
        if query:
            try:
                named_module = module_names([query], catalog, book)
            except Refuse:
                named_module = set()
            if named_module and not want_x:
                scope = "components"
                matched = [r for r in matched if r["module"] in named_module
                           and r["type"] != "pack"]
                matched = _group_rows(matched, "component", {
                    name: known for name, known in groups["component"].items()
                    if known["module"] in named_module})
            elif named_module and want_x:
                matched = [r for r in matched if r["module"] in named_module]
            else:
                chosen = resolve_name(query, catalog, book,
                                      methods=want_x or None)
                ids = {p["key"] for p in chosen["files"]}
                owner = chosen["id"] if chosen["kind"] == "component" else None
                matched = [r for r in matched if r["id"] in ids
                           or (r["type"] == "pack" and r["component"] == owner)]
                if chosen["kind"] == "component" and not want_x:
                    scope = "files"
        elif installed and not want_x and not components:
            # Every installed file across modules, then the packs that are on.
            on = [_pack_row(pack, state, full) for pack in catalog_packs(catalog).values()
                  if not want_m or pack["module"] in want_m]
            matched += [{key: value for key, value in row.items() if key != "_search"}
                        for row in sorted(on, key=lambda pack: pack["id"])]
        elif not want_x and not components:
            scope = "modules"
            matched = _group_rows(matched, "module")
        elif components and not want_x:
            scope = "components"
            matched = _group_rows([r for r in matched if r["type"] != "pack"],
                                  "component")
    if installed:
        matched = [r for r in matched if (r["installed"] if scope == "files"
                   else r["installed_files"] > 0)]
    total = len(matched)
    page = matched[offset:offset + limit]
    if scope == "files":
        page = [{k: v for k, v in row.items()
                 if k not in ("component_description", "module_description")}
                for row in page]
    out = {"ok": True, "query": query, "scope": scope, "total": total,
           "returned": len(page),
           "limit": limit, "offset": offset,
           "files": page}
    if search and not total:
        out["did_you_mean"] = nearest_words(words, rows)
    return out


def _pack_row(pack: dict, state: dict, full: bool) -> dict:
    """One pack as a row of the file listing; it is installed when it is on."""
    return {"id": pack["name"], "component": pack["component"],
            "module": pack["module"], "type": "pack",
            "description": (f"Declared by {pack['component']}. "
                            + _description(pack["description"], full)),
            "component_description": "", "module_description": "",
            "_search": pack["description"],
            "installed": pack["name"] in selected_packs(state),
            "source_available": True, "tree": pack["tree"],
            "files": list(pack["files"])}


def single_group_type(types: set[str]) -> str | None:
    """`module` or `component` when --type names one, which it does alone: each
    is its own table, so a second type beside it is refused."""
    named = [kind for kind in GROUP_TYPES if kind in types]
    if not named:
        return None
    if len(types) > 1:
        raise Refuse("usage", f"--type {named[0]} stands alone: its rows are "
                     f"{named[0]}s, a table of their own. Name it without another type.")
    return named[0]


def _group_search_rows(rows: list[dict], field: str, known: dict[str, dict]) -> list[dict]:
    """The modules or the components as search rows: matched on the name and
    the whole description, shown with their count of installed files."""
    out = []
    for entry in _group_rows([row for row in rows if row["type"] != "pack"], field, known):
        name = module_id(entry["id"]) if field == "module" else entry["id"]
        source = known.get(name) or {}
        out.append({**entry, "type": field, "component": name,
                    "module": source.get("module", name.split("/")[0]),
                    "_search": source.get("whole", ""),
                    "installed": entry["installed_files"] > 0,
                    "source_available": name in known, "tree": ""})
    return out


def _search_text(row: dict) -> str:
    """What a search word is matched against: the id, the name, the description."""
    return " ".join((row["id"], row["id"].split("#", 1)[-1],
                     row.get("_search", row["description"]))).casefold()


# How many words a search with no hit suggests, and how short a word may be.
NEAREST_WORDS = 5
SHORTEST_WORD = 4


def nearest_words(words: list[str], rows: list[dict]) -> list[str]:
    """For a search that returned nothing: the words of the searched ids and
    descriptions as close to a searched word that no row holds as a name must
    be to be suggested in a refusal."""
    texts = [_search_text(row) for row in rows]
    vocabulary = sorted({word for text in texts
                         for word in re.findall(r"[^\W_]+", text)
                         if len(word) >= SHORTEST_WORD})
    near: list[str] = []
    for word in words:
        if not any(word in text for text in texts):
            near += [w for w in difflib.get_close_matches(word, vocabulary, n=NEAREST_WORDS,
                                                      cutoff=CLOSE_NAME)
                     if w not in near]
    return near[:NEAREST_WORDS]


def _group_rows(rows: list[dict], field: str,
                known: dict[str, dict] | None = None) -> list[dict]:
    """One row per module or component of `rows`, and one per name of `known`
    that holds none of them: a component of capabilities only has no
    installable file and is still a component."""
    grouped: dict[str, list[dict]] = {name: [] for name in known or {}}
    for row in rows:
        grouped.setdefault(row[field], []).append(row)
    desc_field = "module_description" if field == "module" else "component_description"
    return [{"id": "hub" if name == "_hub" and field == "module" else name,
             "installed_files": sum(r["installed"] for r in parts),
             "source_files": sum(r["source_available"] for r in parts),
             "description": next((r[desc_field] for r in parts if r[desc_field]),
                                 ((known or {}).get(name) or {}).get("description", ""))}
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
        packs = any(row["type"] == "pack" for row in data["files"])
        return f"{query} files and packs" if packs else f"{query} files"
    if len(methods) == 1:
        return f"{methods[0]}s"
    return "installed files" if data.get("installed_only") else "files"


def _list_context_line(data: dict) -> str | None:
    scope, query = data["scope"], data.get("query") or ""
    methods = data.get("methods") or []
    if data.get("searching"):
        n = data["total"]
        return (f"Query: {query} (names and descriptions); "
                f"{n} match{'es' if n != 1 else ''}")
    start = data["offset"] + 1 if data["returned"] else 0
    end = data["offset"] + data["returned"]
    if scope != "files":
        paged = data.get("has_more") or data["offset"]
        return f"Showing {start}-{end} of {data['total']}" if paged else None
    if query and data["total"] == 1:
        return f"Exact file: {data['files'][0]['id']}"
    parts = ([query] if query else []) + (
        [f"type {', '.join(methods)}"] if methods else [])
    scope_txt = f"Scope: {'; '.join(parts)}; " if parts else ""
    return f"{scope_txt}showing {start}-{end} of {data['total']}"


def print_list(data: dict) -> None:
    """Human-readable rendering of `build_list`'s JSON envelope — the JSON
    field names are the stable contract; this only decides how they look on
    a terminal. Module/component rows use ID/Installed files/Description;
    file rows use ID/Type/State/Description (D9)."""
    print(present.title(_list_scope_noun(data)))
    print()
    print(f"Target: {data['target']} "
          f"({present.target_source_label(data.get('source'))})")
    context = _list_context_line(data)
    if context:
        print(context)
    print()
    files = data["files"]
    if data["scope"] == "files":
        headers = ["ID", "Type", "State", "Description"]
        rows = [[row["id"], row["type"], _file_state(row),
                 row["description"] + ("" if row["source_available"]
                                        else " (source missing)")]
                for row in files]
    else:
        headers = ["ID", "Installed files", "Description"]
        rows = [[row["id"], f"{row['installed_files']}/{row['source_files']}",
                 row["description"]] for row in files]
    # --full: one labeled block per row, the description whole and wrapped;
    # a table would cut its last column to the width again.
    lines = (present.render_blocks(headers, rows) if data.get("full")
             else present.render_table(headers, rows))
    for line in lines:
        print(line)
    if not files and data.get("searching"):
        near = data["did_you_mean"]
        print("No module, component, file or pack matches."
              + (f" Did you mean: {', '.join(near)}?" if near else ""))
    elif not files:
        print("No installed files in this target." if data.get("installed_only")
              else "No matching files.")
    if files:
        print()
        if data["scope"] != "files":
            text = "Installed files is the saved selection; run doctor to check harness files."
        elif any(row["type"] in GROUP_TYPES for row in files):
            text = ("State is installed or not installed for a file, on or off for a "
                    "pack, and installed files out of source files for a module or "
                    "component.\nSaved selection; run doctor to check files.")
        elif any(row["type"] == "pack" for row in files):
            if all(row["type"] == "pack" for row in files):
                text = ("State is on or off for this target. Saved selection; "
                        "run doctor to check files.")
            else:
                text = ("State is installed or not installed for a file, and on or "
                        "off for a pack.\nSaved selection; run doctor to check files.")
        else:
            text = ("State is the saved selection for this target; "
                    "run doctor to check files.")
        print("\n".join(present.wrap(text)))
        for line in subagents.installed_lines(
                {row["id"]: row["sub_agent"] for row in files if row.get("sub_agent")}):
            print("\n".join(present.wrap(line, hang="  ")))
        # A cut description ends with an ellipsis; say how to read it whole.
        if any(line.endswith("…") for line in lines):
            print("Whole descriptions: add --full.")
    print()
    label = "More" if data.get("has_more") else "Next"
    print(f"{label}: {data['next']}")


def _file_state(row: dict) -> str:
    if row["type"] in GROUP_TYPES:
        return f"{row['installed_files']}/{row['source_files']} files"
    if row["type"] == "pack":
        return "on" if row["installed"] else "off"
    return "installed" if row["installed"] else "not installed"


def json_view(data: dict, *, searching: bool) -> dict:
    """The list/search envelope with the per-row JSON shape the approved
    screens show: list and search carry different keys for a file row and for
    a pack row. A table of modules or of components is returned unchanged; a
    module or a component among search results carries its counts of files."""
    if data["scope"] != "files":
        return data
    shaped = []
    for row in data["files"]:
        if row["type"] in GROUP_TYPES:
            shape = {"id": row["id"], "type": row["type"], "description": row["description"],
                     "installed_files": row["installed_files"],
                     "source_files": row["source_files"]}
        elif row["type"] == "pack" and searching:
            shape = {"id": row["id"], "type": "pack", "description": row["description"],
                     "tree": row["tree"], "source_available": row["source_available"],
                     "on": row["installed"], "declared_by": row["component"]}
        elif row["type"] == "pack":
            shape = {"id": row["id"], "component": row["component"],
                     "module": row["module"], "type": "pack", "on": row["installed"],
                     "declared_by": row["component"], "description": row["description"],
                     "files": row["files"]}
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
    return {**data, "files": shaped}


def pack_members(catalog: dict, state: dict, pack: dict) -> list[dict]:
    """The files a pack includes, each with its type and whether it is installed here."""
    types = {part["key"]: part["method"] for part in iter_catalog_parts(catalog)}
    members = []
    for key in pack["files"]:
        cid, _, pid = key.partition("#")
        members.append({"key": key, "type": types.get(key, ""),
                        "installed": _file_in(state, cid, pid)})
    return members


def build_show(selection: dict, catalog: dict, state: dict, full: bool = False) -> dict:
    parts = [file_detail(catalog, state, part) for part in selection["files"]]
    parts = [{**p, "type": p["method"]} for p in parts]
    for part in parts:
        part.pop("method", None)
    out = {"scope": "file" if selection["kind"] == "part" else selection["kind"],
           "id": selection["id"],
           "files": parts,
           "harnesses": book_harnesses(state) or []}
    if selection["kind"] == "part":
        out.update(type=parts[0]["type"], component=parts[0]["component"],
                   file_id=parts[0]["file_id"])
        if parts[0]["type"] == "agent":
            row = _file_row(catalog[parts[0]["component"]], parts[0]["file_id"])
            home = Path(state.get("_target", "")) / ".rbtv" / "agents" / parts[0]["file_id"]
            name = parts[0]["file_id"]
            out["agent"] = {"packs": row["data"].get("packs", []),
                            "files": row["data"].get("files", []),
                            "placed": home.is_dir(), "home": str(home),
                            "sub_agent": subagents.recorded(state).get(selection["id"], {}),
                            "add": {"rbtv_agent": f"rbtv agent add {name} --harness HARNESS "
                                                  "--model MODEL --effort EFFORT",
                                    "sub_agent": f"rbtv add {name} --on {subagents.ON_FORM}"}}
    elif selection["kind"] == "component":
        source_comp = catalog.get(selection["id"]) or {}
        source_path = Path(source_comp["path"]) if source_comp.get("path") else None
        description = _description(source_comp.get("description", ""), full)
        out.update(description=description,
                   dependencies=list(source_comp.get("dependencies") or []),
                   source_entry=(str(source_path) if source_path else ""))
    return out


def _say(text: str) -> None:
    """One `Label: prose` line, wrapped under a two-space hang."""
    print("\n".join(present.wrap(text, hang="  ")))


def print_show(data: dict) -> None:
    """Human-readable rendering of `build_show`'s envelope: description,
    included files or installation details, source entry path (D9 §4)."""
    sel = data["selection"]
    print(present.title(f"pack {sel['id']}" if sel["scope"] == "pack" else sel["id"]))
    print()
    print(f"Target: {data['target']} "
          f"({present.target_source_label(data.get('source'))})")
    if sel["scope"] == "pack":
        print(f"Type: pack ({present.TYPE_MEANING['pack']})")
        print("Name: " + sel["id"])
        print("Declared by: " + sel["component"])
        print("Declaration: " + sel["path"])
        _say(f"Description: {sel['description']}")
        print(f"Files: {len(sel['files'])}")
        print("Pack: " + ("on" if sel["enabled"] else "off") + " for this target")
        print()
        rows = [[file["key"], file["type"],
                 "installed" if file["installed"] else "not installed"]
                for file in sel["files"]]
        for line in present.render_table(["ID", "Type", "State"], rows):
            print(line)
        print()
        print("State is the saved selection for this target; run doctor to check files.")
        print()
        print("Next: " + data["next"])
        return
    if sel["scope"] == "module":
        _say(f"Description: {sel['description'] or '(no description in the source catalog)'}")
        _say(f"Local source: {sel['source_files']} files; "
              f"installed here: {sel['installed_files']} saved selections. "
              "Harness files not checked.")
        print()
        headers = ["ID", "Installed files", "Description"]
        rows = [[c["id"], f"{c['installed_files']}/{c['source_files']}",
                 c["description"]] for c in sel["components"]]
        for line in present.render_table(headers, rows):
            print(line)
        print()
        print("Next: " + data["next"])
        return
    if sel["scope"] == "component":
        _say(f"Description: {sel.get('description') or '(no description in the source catalog)'}")
        _say("Dependencies: " + (", ".join(sel.get("dependencies") or []) or "none"))
        if sel.get("source_entry"):
            print("Source entry (local RBTV source): " + sel['source_entry'])
        _say(f"Local source: {len(sel['files'])} file(s) in this component.")
        headers = ["ID", "Type", "State", "Description"]
        rows = [[p["key"], p["type"],
                 "installed" if p["installed"] else "not installed",
                 p["description"]] for p in sel["files"]]
        if rows:
            print()
        for line in present.render_table(headers, rows):
            print(line)
        print()
        print("Next: " + data["next"])
        return
    part = sel["files"][0]
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
        print("  Other files: " + (", ".join(agent["files"]) or "none"))
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
        print("  Source: no longer present in the local source catalog")
    if part["type"] == "agent":
        print()
        print("Add it in either form, or both")
        print("  As a harness-native sub-agent: " + sel["agent"]["add"]["sub_agent"])
        print("  As an rbtv agent: " + sel["agent"]["add"]["rbtv_agent"])
        print("  Harnesses, models and efforts: cast models list")
    print()
    print("Next: " + data["next"])


def do_list(target: Path, catalog: dict | None = None) -> dict:
    raw = read_state(target)
    catalog = catalog or {}
    state = upgrade_book(raw, catalog_files_map(catalog)) if catalog else raw
    comps: dict = {}
    links: list[dict] = []
    for cid, rec in sorted((state.get("components") or {}).items()):
        rec = dict(rec)
        st, booked, miss, orph = status_of(cid, rec, catalog)
        rec["status"], rec["missing"], rec["orphans"] = (
            st, sorted(miss), sorted(orph))
        rec.setdefault("selected", {})
        comps[cid] = rec
        for pid, part in (rec.get("selected") or {}).items():
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
