"""Resolve stable component and part names for every installer command."""
from __future__ import annotations

import argparse
import difflib
import re

from discovery import Refuse

from .catalog import _file_specs, module_id


def file_key(cid: str, pid: str) -> str:
    return f"{cid}#{pid}"


def iter_catalog_parts(catalog: dict[str, dict]) -> list[dict]:
    out: list[dict] = []
    for cid, comp in catalog.items():
        try:
            specs = _file_specs(comp)
        except Refuse:
            continue        # its own install refuses it; it never blocks the rest
        for spec in specs:
            if spec["id"]:
                out.append({"key": file_key(cid, spec["id"]),
                            "component": cid,
                            "module": comp.get("module") or cid.split("/")[0],
                            "file_id": spec["id"],
                            "method": spec.get("method") or ""})
    return out


def iter_booked_files(catalog: dict[str, dict],
                      book: dict[str, dict] | None) -> list[dict]:
    by_cid: dict[str, list[dict]] = {}
    for part in iter_catalog_parts(catalog):
        by_cid.setdefault(part["component"], []).append(part)
    booked: list[dict] = []
    for cid, rec in (book or {}).items():
        declared = rec.get("selected")
        if isinstance(declared, dict) and declared:
            for pid, part in declared.items():
                booked.append({"key": file_key(cid, pid), "component": cid,
                               "module": rec.get("module") or cid.split("/")[0],
                               "file_id": pid, "method": (part or {}).get("method") or ""})
        elif cid in by_cid:
            booked.extend(by_cid[cid])
        else:
            pid = rec.get("component") or cid.split("/")[-1]
            booked.append({"key": file_key(cid, pid), "component": cid,
                           "module": rec.get("module") or cid.split("/")[0],
                           "file_id": pid, "method": "component"})
    return booked


def _norm_comp(name: str) -> str:
    if name == "hub" or name.startswith("hub/"):
        return "_" + name
    return name


def _retire_number(token: str) -> None:
    if re.fullmatch(r"\d+(?:-\d+)?", token):
        raise Refuse("index-retired",
                     f"numeric selector {token!r} is retired because list order can change. "
                     "Run `rbtv list` and copy its stable identifier")


# How alike a name must be to the one typed before a refusal suggests it.
CLOSE_NAME = 0.75


def close_names(token: str, choices: list[str]) -> list[str]:
    """Up to three of `choices` close enough to `token` to be what was meant."""
    return difflib.get_close_matches(token, sorted(set(choices)), n=3, cutoff=CLOSE_NAME)


def close_names_sentence(close: list[str]) -> str:
    return f"Did you mean: {', '.join(close)}?" if close else "No close name exists."


def _unknown(code: str, label: str, token: str, choices: list[str]) -> Refuse:
    close = close_names(token, choices)
    exc = Refuse(code, f"unknown {label} {token!r}. {close_names_sentence(close)} "
                 "Run `rbtv list` to see stable identifiers")
    exc.candidates = close
    return exc


def _ambiguous(token: str, choices: list[str]) -> Refuse:
    keys = sorted(set(choices))
    exc = Refuse("name-ambiguous",
                 f"{token!r} names multiple files or components: "
                 + ", ".join(keys) + ". Use a full identifier")
    exc.candidates = keys
    return exc


def _pool(catalog: dict, book: dict | None = None) -> list[dict]:
    by_key = {p["key"]: p for p in iter_catalog_parts(catalog)}
    for part in iter_booked_files(catalog, book):
        by_key[part["key"]] = part
    return list(by_key.values())


def resolve_name(token: str, catalog: dict, book: dict | None = None,
                 *, methods: set[str] | None = None,
                 component_only: bool = False,
                 suggest_installed: bool = False,
                 empty_ok: bool = False) -> dict:
    """One name -> one exposed part or one component with its parts. A name
    that is unknown is refused with the close names: of the whole catalog, or,
    with `suggest_installed`, of what `book` records as installed. A component
    that holds no installable file is refused unless `empty_ok`, which a
    reader of the catalog passes."""
    _retire_number(token)
    token = _norm_comp(token)
    pool = _pool(catalog, book)
    by_key = {p["key"]: p for p in pool}
    components = set(catalog) | set(book or {})
    allowed = [p for p in pool if not methods or p["method"] in methods]
    suggested, suggested_components = allowed, components
    if suggest_installed:
        suggested = [p for p in iter_booked_files(catalog, book)
                     if not methods or p["method"] in methods]
        suggested_components = set(book or {})
    if "#" in token:
        part = by_key.get(token)
        if part and (not methods or part["method"] in methods):
            return {"kind": "part", "id": token, "files": [part]}
        raise _unknown("file-unknown", "file", token,
                       [p["key"] for p in suggested])
    if token in components:
        parts = [p for p in allowed if p["component"] == token]
        if parts:
            return {"kind": "component", "id": token, "files": parts}
        if token in catalog:
            _file_specs(catalog[token])     # an invalid component says why
            if empty_ok and not methods:
                return {"kind": "component", "id": token, "files": []}
        raise Refuse("kind-mismatch", f"{token!r} has no file of the requested type")
    if not component_only:
        hits = [p for p in allowed if p["file_id"] == token]
        if len(hits) == 1:
            return {"kind": "part", "id": hits[0]["key"], "files": hits}
        if len(hits) > 1:
            raise _ambiguous(token, [p["key"] for p in hits])
    if component_only:
        hits_c = sorted(cid for cid in components if cid.split("/")[-1] == token)
        if len(hits_c) == 1:
            return resolve_name(hits_c[0], catalog, book, methods=methods,
                                component_only=True,
                                suggest_installed=suggest_installed,
                                empty_ok=empty_ok)
        if len(hits_c) > 1:
            raise _ambiguous(token, hits_c)
    choices = ([p["key"] for p in suggested] + [p["file_id"] for p in suggested]
               + sorted(suggested_components))
    raise _unknown("component-unknown" if component_only else "name-unknown",
                   "component" if component_only else "name", token, choices)


def component_keys(tokens: list[str], catalog: dict,
                   book: dict | None = None,
                   *, methods: set[str] | None = None,
                   suggest_installed: bool = False) -> set[str]:
    """Explicit -c/--component tokens keep component semantics."""
    keys: set[str] = set()
    for token in tokens:
        resolved = resolve_name(token, catalog, book, methods=methods,
                                component_only=True,
                                suggest_installed=suggest_installed)
        keys.update(p["key"] for p in resolved["files"])
    return keys


def module_names(tokens: list[str], catalog: dict,
                 book: dict | None = None) -> set[str]:
    known = {p["module"] for p in _pool(catalog, book)} | {
        c.get("module") or cid.split("/")[0] for cid, c in catalog.items()}
    resolved = {module_id(token) for token in tokens}
    for token in tokens:
        _retire_number(token)
    for mod in resolved:
        if mod not in known:
            raise _unknown("module-unknown", "module", mod, sorted(known))
    return resolved


def resolve_selection(args, catalog: dict[str, dict],
                      book: dict[str, dict] | None = None) -> set[str]:
    """AND across selector kinds, OR within one kind, exclusions last."""
    verb = getattr(args, "verb", None)
    names = list(getattr(args, "names", None) or [])
    pos_c = list(getattr(args, "component", None) or [])
    neg_c = list(getattr(args, "exclude_component", None) or [])
    pos_m = module_names(list(getattr(args, "module", None) or []), catalog, book)
    neg_m = module_names(list(getattr(args, "exclude_module", None) or []), catalog, book)
    pos_x = set(getattr(args, "method", None) or [])
    neg_x = set(getattr(args, "exclude_method", None) or [])
    all_flag = bool(getattr(args, "all", False))
    for token in (*names, *pos_c, *neg_c, *pos_m, *neg_m):
        _retire_number(token)
    if not (all_flag or names or pos_c or pos_m or pos_x):
        raise Refuse("selection-empty", "name a file or component, or use --all, "
                     "--module, --component or --type")

    removing = verb in ("rm", "remove")
    universe = (iter_booked_files(catalog, book) if removing
                else iter_catalog_parts(catalog))
    by_key = {p["key"]: p for p in universe}
    selected = set(by_key)
    if names or pos_c:
        requested: set[str] = set()
        for name in names:
            resolved = resolve_name(name, catalog, book, methods=pos_x or None,
                                    suggest_installed=removing)
            requested.update(p["key"] for p in resolved["files"])
        requested |= component_keys(pos_c, catalog, book, suggest_installed=removing)
        selected &= requested
    if pos_m:
        selected &= {p["key"] for p in universe if p["module"] in pos_m}
    if pos_x:
        selected &= {p["key"] for p in universe if p["method"] in pos_x}
    if neg_m:
        selected -= {p["key"] for p in universe if p["module"] in neg_m}
    if neg_c:
        selected -= component_keys(neg_c, catalog, book)
    if neg_x:
        selected -= {p["key"] for p in universe if p["method"] in neg_x}
    if removing:
        return selected
    if not selected:
        raise Refuse("selection-empty", "selectors matched no installable file")
    return selected


def _sel(verb: str = "add", **kw):
    base = dict(all=False, names=[], module=[], component=[], method=[],
                exclude_module=[], exclude_component=[], exclude_method=[])
    base.update(kw)
    return argparse.Namespace(verb=verb, **base)


def _has_negative(args) -> bool:
    return bool(getattr(args, "exclude_module", None)
                or getattr(args, "exclude_component", None)
                or getattr(args, "exclude_method", None))


def _split_part_keys(keys) -> tuple[list[str], list[str]]:
    return sorted({k.split("#", 1)[0] for k in keys}), sorted(keys)
