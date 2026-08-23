"""The `ls` and `li` views: what exists, what is installed, and this
workspace's settings.
"""
from __future__ import annotations

import json
from pathlib import Path

from discovery import exposure_rows

from .constants import (ANSI, BASIS_NONE, INDEX_REL, INSTALLER_NAME,
                        MANAGED_MARK, STATE_REL)
from .catalog import (
    _hub_refuse_message,
    _part_specs,
    catalog_parts_map,
    module_id,
)
from .state import _part_in, book_harnesses, read_state, upgrade_book
from .selection import _norm_comp, part_key, scan_fingerprint


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
    want_m = {module_id(m) for m in (modules or [])}
    want_x = set(methods or [])
    want_c = {_norm_comp(c) for c in (components or [])}
    drop_m = {module_id(m) for m in (exclude_modules or [])}
    drop_x = set(exclude_methods or [])
    drop_c = {_norm_comp(c) for c in (exclude_components or [])}
    entries, nmap, n = [], {}, 0
    for cid in sorted(catalog):
        c = catalog[cid]
        hub = c.get("kind") in ("hub", "skill-folder")
        mod = c.get("module") or cid.split("/")[0]
        if want_m and mod not in want_m:
            continue
        if drop_m and mod in drop_m:
            continue
        if want_c and cid not in want_c and not any(
                token == cid or token.endswith("#" + cid.split("/")[-1])
                or (token.startswith(cid + "#"))
                for token in want_c):
            continue
        if drop_c and cid in drop_c:
            continue
        items = []
        for spec in _part_specs(c):
            pid, meth = spec["id"], spec.get("method") or ""
            if want_x and meth not in want_x:
                continue
            if drop_x and meth in drop_x:
                continue
            n += 1
            items.append({"index": n, "part_id": pid, "method": meth,
                          "in": _part_in(state, cid, pid)})
            nmap[str(n)] = {"kind": "part", "id": part_key(cid, pid)}
        refusal = c.get("hub_refusal") or ""
        note = _hub_refuse_message(c) if refusal else ""
        if (want_x or drop_x) and not items:
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
            "hub_refusals": hub_refusals,
            "index": {"fingerprint": scan_fingerprint(catalog), "n": nmap}}


def print_ls(data: dict, *, pretty: bool = False) -> None:
    print(f" {'#':>2}  {'COMPONENT / part':<42} {'TREE':<7} {'METHOD':<10} IN")
    for e in data["components"]:
        extra = f"  ({e['note']})" if e["note"] else ""
        n_in = sum(1 for i in e["items"] if i["in"])
        n = len(e["items"])
        tally = f"{n} part{'' if n == 1 else 's'}, {n_in} in" if n else ""
        print(f"     {e['id']:<42} {e['tree']:<7} {tally}{extra}")
        for i in e["items"]:
            flag = "in" if i["in"] else "-"
            if pretty:
                flag = ((ANSI["ok"] + "in" + ANSI["reset"]) if i["in"]
                        else flag)
            print(f"{i['index']:>3}    {i['part_id']:<39} {'':<7} "
                  f"{i['method']:<10} {flag}")
    for s in data["shadowed"]:
        print(f"\nSHADOWED: {s['id']} exists on both trees — mirror wins "
              f"({s['winner_path']}); repo copy ignored ({s['shadowed_path']})")


def write_visible_index(target: Path, index: dict) -> None:
    path = target / INDEX_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


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


def _print_settings(view: dict) -> None:
    """The workspace settings block at the head of `li` (D16c).

    It is printed where a human is already looking at this workspace, and it
    carries the commands that CHANGE each line — the two verbs that used to
    exist only to show these three values are gone, and a reader who has to
    go find the help to change what they are looking at is why.
    """
    if not view["recorded"]:
        print("settings  : none recorded — nothing installed here yet")
        return
    print("harnesses : " + (", ".join(view["harnesses"]) or "(none)")
          + "   (change: rbtv install add|rm harness <h>)")
    print("artifact  : " + (view["artifact"] or "(unset — no guidance mirror)")
          + "   (change: rbtv install set artifact <name>)")
    print("excluded  : " + (", ".join(view["guidance_excludes"]) or "(none)")
          + "   (change: rbtv install add|rm artifact exclude <dir>)")


def print_li(data: dict, *, pretty: bool = False) -> None:
    print(f"target: {data['target']}  marker: {data['marker']}")
    _print_settings(data["settings"])
    print()
    comps = data["components"]
    if not comps:
        print(f"nothing installed by {INSTALLER_NAME}")
    else:
        print(f"{'#':<3} {'ST':<5} {'IN':<6} {'COMPONENT':<42} {'TREE':<7} "
              f"HARNESSES")
        cids = list(comps)
        part_no: dict[str, dict[str, int]] = {cid: {} for cid in cids}
        k = len(cids) + 1
        for cid, rec in comps.items():
            for pid in sorted(rec.get("parts") or {}):
                part_no[cid][pid] = k
                k += 1
        for i, cid in enumerate(cids, 1):
            rec = comps[cid]
            cat_n = len((set(rec.get("parts") or {})
                         | set(rec.get("missing") or {}))
                        - set(rec.get("orphans") or {}))
            booked = set(rec.get("parts") or {})
            orph = set(rec.get("orphans") or {})
            st = rec["status"]
            if st == "gone":
                inn = f"{len(booked)}/—"
            else:
                inn = f"{len(booked - orph)}/{cat_n}"
            paint = f"{st:<5}"
            if pretty and st in ANSI:
                paint = ANSI[st] + paint + ANSI["reset"]
            hs = ",".join(rec.get("harnesses") or [])
            names = ",".join(sorted(booked))
            if pretty:
                print(f"{i:<3} {paint} {inn:<6} {cid:<42} "
                      f"{rec.get('tree', ''):<7} {hs}")
                for pid, part in sorted((rec.get("parts") or {}).items()):
                    if not isinstance(part, dict):
                        continue
                    print(f"    {part_no[cid][pid]:<3} {pid:<22} "
                          f"{part.get('method', '')}")
            else:
                print(f"{i:<3} {paint} {inn:<6} {cid:<42} "
                      f"{rec.get('tree', ''):<7} {hs}")
            miss = rec.get("missing") or []
            orph_l = rec.get("orphans") or []
            if st == "part" or miss or orph_l:
                extra = []
                if miss:
                    extra.append("out: " + ", ".join(miss))
                if orph_l:
                    extra.append("orphan: " + ", ".join(orph_l))
                if extra:
                    print("        " + " · ".join(extra))
    def _section(label: str, items: list[str]) -> None:
        """Owned outside our own files — the only place a human sees it."""
        if not items:
            print(f"\n{label}: (none)")
            return
        print(f"\n{label}:")
        for it in items:
            print(f"  {it}")

    _section("guidance files written", data["guidance_files"])
    _section("keys held in shared config files", data["shared_claims"])
    _section("commands linked onto PATH",
             [p["name"] for p in data["path_links"]])
