"""Turning what the human typed into the set of component and part keys it
names.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from discovery import Refuse

from .constants import INDEX_REL
from .catalog import _part_specs, is_installable, module_id


def part_key(cid: str, pid: str) -> str:
    """Global selector key. R1: `{cid}#{part-id}` — no method in the key."""
    return f"{cid}#{pid}"


def iter_catalog_parts(catalog: dict[str, dict]) -> list[dict]:
    out: list[dict] = []
    for cid, c in catalog.items():
        if not is_installable(c):
            continue
        for spec in _part_specs(c):
            pid = spec["id"]
            if not pid:
                continue
            out.append({
                "key": part_key(cid, pid),
                "component": cid,
                "module": c.get("module") or cid.split("/")[0],
                "part_id": pid,
                "method": spec.get("method") or "",
            })
    return out


def iter_booked_parts(catalog: dict[str, dict],
                      book: dict[str, dict] | None) -> list[dict]:
    by_cid: dict[str, list[dict]] = {}
    for p in iter_catalog_parts(catalog):
        by_cid.setdefault(p["component"], []).append(p)
    booked: list[dict] = []
    for cid, rec in (book or {}).items():
        declared = rec.get("parts")
        if isinstance(declared, dict) and declared:
            for pid, part in declared.items():
                booked.append({
                    "key": part_key(cid, pid),
                    "component": cid,
                    "module": rec.get("module") or cid.split("/")[0],
                    "part_id": pid,
                    "method": (part or {}).get("method") or "",
                })
        elif isinstance(declared, list) and declared:
            for d in declared:
                pid = (d.get("part-id") or d.get("part_id") or "").strip()
                booked.append({
                    "key": part_key(cid, pid),
                    "component": cid,
                    "module": rec.get("module") or cid.split("/")[0],
                    "part_id": pid,
                    "method": (d.get("method") or "").strip(),
                })
        elif cid in by_cid:
            booked.extend(by_cid[cid])
        else:
            name = rec.get("component") or cid.split("/")[-1]
            booked.append({
                "key": part_key(cid, name),
                "component": cid,
                "module": rec.get("module") or cid.split("/")[0],
                "part_id": name,
                "method": "component",
            })
    return booked


def scan_fingerprint(catalog: dict[str, dict]) -> str:
    """sha256 of sorted JSON of catalog part keys ∪ catalog ids."""
    keys = sorted({p["key"] for p in iter_catalog_parts(catalog)} | set(catalog))
    return hashlib.sha256(
        json.dumps(keys, separators=(",", ":")).encode()).hexdigest()


def write_index(target: Path, catalog: dict[str, dict],
                book: dict[str, dict] | None = None) -> dict:
    parts = iter_catalog_parts(catalog)
    booked = iter_booked_parts(catalog, book) if book is not None else []
    modules = sorted({p["module"] for p in parts}
                     | {c.get("module") or cid.split("/")[0]
                        for cid, c in catalog.items()})
    components = sorted(set(catalog) | {p["component"] for p in booked})
    part_ids = sorted({p["key"] for p in parts} | {p["key"] for p in booked})
    n: dict[str, dict] = {}
    i = 1
    for mid in modules:
        n[str(i)] = {"kind": "module", "id": mid}
        i += 1
    for cid in components:
        n[str(i)] = {"kind": "component", "id": cid}
        i += 1
    for key in part_ids:
        n[str(i)] = {"kind": "part", "id": key}
        i += 1
    payload = {"fingerprint": scan_fingerprint(catalog), "n": n}
    path = target / INDEX_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def read_index(target: Path) -> dict | None:
    path = target / INDEX_REL
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _norm_comp(name: str) -> str:
    if name == "hub" or name.startswith("hub/"):
        return "_" + name
    return name


# A range may not span more than this many ls/li slots. The bound is not a
# policy about how much anyone may select — it is what stops a fat-fingered
# `-c 1-99999999999` from materializing eleven billion strings before the
# first slot lookup gets a chance to refuse. No real listing approaches it.
RANGE_SPAN_MAX = 1000


def _index_nums(t: str) -> list[str] | None:
    """The ls/li numbers a selector token names, or None if it names none.

    `7` names one. `3-7` names five, inclusive and ascending. A range is
    digits on BOTH sides of the hyphen and nothing else — component ids carry
    hyphens of their own (`ponytail-audit`, `web/browse`), so every other
    shape is a NAME and is handed back untouched rather than guessed at.
    """
    if t.isdigit():
        return [t]
    lo, sep, hi = t.partition("-")
    if not sep or not lo.isdigit() or not hi.isdigit():
        return None
    a, b = int(lo), int(hi)
    if b < a:
        raise Refuse("index-range-inverted",
                     f"range {t!r} counts down; write {b}-{a}")
    if b - a + 1 > RANGE_SPAN_MAX:
        raise Refuse("index-range-too-wide",
                     f"range {t!r} spans {b - a + 1} slots (max "
                     f"{RANGE_SPAN_MAX}) — no ls/li listing is this long, "
                     "so this is a typo, not a selection")
    return [str(n) for n in range(a, b + 1)]


def _expand_nums(tokens: list[str], want: str, index: dict | None,
                 fp: str) -> list[str]:
    out: list[str] = []
    for t in tokens:
        nums = _index_nums(t)
        if nums is None:
            out.append(t)
            continue
        if not index:
            raise Refuse("index-missing",
                         f"numeric selector {t!r} but no ls/li index")
        if index.get("fingerprint") != fp:
            raise Refuse("index-stale",
                         "scanned set changed since last ls/li")
        for n in nums:
            slot = (index.get("n") or {}).get(n)
            if not slot:
                raise Refuse("index-unknown", f"no index slot {n}")
            sk = slot["kind"]
            if sk != want and not (want == "component" and sk == "part"):
                raise Refuse("index-kind-mismatch",
                             f"index {n} is {sk}, not {want}")
            out.append(slot["id"])
    return out


def _comp_hits(name: str, names_c: set[str], pool: list[dict]) -> bool:
    if name in names_c:
        return True
    if any(p["key"] == name for p in pool):
        return True
    if any(cid == name or cid.endswith("/" + name)
           or cid.split("/")[-1] == name for cid in names_c):
        return True
    return False


def _match_c(p: dict, toks: list[str]) -> bool:
    if p["component"] in toks or p["key"] in toks:
        return True
    short = p["component"].split("/")[-1]
    return short in toks or p["component"].endswith("/" + short) and short in toks


def resolve_selection(args, catalog: dict[str, dict],
                      book: dict[str, dict] | None = None) -> set[str]:
    """AND across selector kinds, OR within a kind, exclusions last.

    Returns a set of `{cid}#{part-id}` keys (R1). `add` universe = installable
    catalog parts. `rm` universe = catalog ∪ booked (incl. vanished); output
    is the booked intersection.
    """
    verb = getattr(args, "verb", None)
    index = getattr(args, "index", None)
    fp = scan_fingerprint(catalog)
    pos_m = [module_id(x) for x in _expand_nums(
        list(getattr(args, "module", None) or []), "module", index, fp)]
    neg_m = [module_id(x) for x in _expand_nums(
        list(getattr(args, "exclude_module", None) or []), "module", index, fp)]
    pos_c = [_norm_comp(x) for x in _expand_nums(
        list(getattr(args, "component", None) or []), "component", index, fp)]
    neg_c = [_norm_comp(x) for x in _expand_nums(
        list(getattr(args, "exclude_component", None) or []),
        "component", index, fp)]
    pos_x = list(getattr(args, "method", None) or [])
    neg_x = list(getattr(args, "exclude_method", None) or [])
    flag_a = bool(getattr(args, "all", False))
    if not (flag_a or pos_m or pos_c or pos_x):
        raise Refuse("selection-empty",
                     "need -A or a non-exclusion -m/-c/-x")

    cat_parts = iter_catalog_parts(catalog)
    booked = iter_booked_parts(catalog, book)
    names_c = set(catalog) | {p["component"] for p in booked}
    names_m = ({c.get("module") or cid.split("/")[0]
                for cid, c in catalog.items()}
               | {p["module"] for p in booked})
    pool = cat_parts + booked
    for label, bucket, names, code in (
        ("module", pos_m + neg_m, names_m, "module-unknown"),
        ("component", pos_c + neg_c, names_c, "component-unknown"),
    ):
        for n in bucket:
            if label == "component":
                if not _comp_hits(n, names, pool):
                    raise Refuse(code, f"no {label} {n!r} on either tree")
            elif n not in names:
                raise Refuse(code, f"no {label} {n!r} on either tree")
    for n in pos_c + neg_c:
        if n in catalog and not is_installable(catalog[n]) and n not in (book or {}):
            raise Refuse("component-not-installable",
                         f"{n!r} has no exposure manifest")

    by_key = {p["key"]: p for p in (cat_parts if verb != "rm" else pool)}
    universe = list(by_key.values())
    selected = set(by_key)
    if pos_m:
        selected &= {p["key"] for p in universe if p["module"] in pos_m}
    if pos_c:
        selected &= {p["key"] for p in universe if _match_c(p, pos_c)}
    if pos_x:
        selected &= {p["key"] for p in universe if p["method"] in pos_x}
    if neg_m:
        selected -= {p["key"] for p in universe if p["module"] in neg_m}
    if neg_c:
        selected -= {p["key"] for p in universe if _match_c(p, neg_c)}
    if neg_x:
        selected -= {p["key"] for p in universe if p["method"] in neg_x}

    if verb == "rm":
        booked_keys = {p["key"] for p in booked}
        hit = selected & booked_keys
        if not hit:
            raise Refuse(
                "not-installed",
                "not installed at this target: "
                + ", ".join(sorted(selected) or pos_c or pos_m or pos_x
                            or ["-A"]))
        return hit
    if not selected:
        raise Refuse("selection-empty",
                     "selectors matched no installable part")
    return selected


def _sel(verb: str = "add", **kw):
    base = dict(all=False, module=[], component=[], method=[],
                exclude_module=[], exclude_component=[], exclude_method=[],
                index=None, verb=verb)
    base.update(kw)
    return argparse.Namespace(**base)


def _has_negative(args) -> bool:
    return bool(getattr(args, "exclude_module", None)
                or getattr(args, "exclude_component", None)
                or getattr(args, "exclude_method", None))


def _split_part_keys(keys) -> tuple[list[str], list[str]]:
    return sorted({k.split("#", 1)[0] for k in keys}), sorted(keys)
