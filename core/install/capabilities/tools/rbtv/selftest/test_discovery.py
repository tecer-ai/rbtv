"""What counts as an installable component, and which harnesses exist."""
from __future__ import annotations

import json

from discovery import HUB_DIR, Refuse, scan_all, scan_tree, unit_rows

from lib.constants import (
    RULE_SECTION_HARNESSES,
    GUIDANCE_FILE,
    HARNESSES,
    MATRIX,
    STATE_REL,
)
from lib.catalog import catalog_units_map
from lib.state import read_state, upgrade_book, write_state
from lib.planning import plan_files
from lib.listing import do_scan
from lib.commands import _parse_harnesses
from lib.parser import build_parser
from lib.commands import cmd_add

from .fixture import _component, _reserved_id_refuses, _unit_md, _w


def scan(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("scan")
    data = do_scan(catalog, shadowed)
    check("discovers every component on the tree, and the whole-folder skill",
          sorted(catalog) == ["_hub/skills/vendored",
                              "badmod/badcomp",
                              "deepmod/deepcomp",
                              "fixmod/codexcomp",
                              "fixmod/dupcomp", "fixmod/goodcomp",
                              "fixmod/reservedcomp",
                              "oldmod/oldcomp"],
          str(sorted(catalog)))
    check("a _skills/ folder is discovered as a whole-folder skill (D15)",
          catalog["_hub/skills/vendored"]["kind"] == "hub"
          and catalog["_hub/skills/vendored"]["method"] == "skill"
          and catalog["_hub/skills/vendored"]["module"] == HUB_DIR
          and not catalog["_hub/skills/vendored"]["manifest"],
          str(catalog["_hub/skills/vendored"]))
    check("the scan carries each component's description and its module's",
          catalog["fixmod/goodcomp"]["description"] == "The goodcomp component"
          and catalog["fixmod/goodcomp"]["module_description"]
          == "The fixmod module"
          and catalog["fixmod/goodcomp"]["dependencies"] == [],
          str(catalog["fixmod/goodcomp"]))
    good = {r["id"]: r for r in unit_rows(catalog["fixmod/goodcomp"])}
    check("a component's units are read from its folders, one method each",
          {uid: r["method"] for uid, r in good.items()}
          == {"fixskill": "skill", "fixcmd": "command", "fixrule": "rule",
              "fixagent": "sub-agent", "research": "agent", "fixhook": "hook", "fixmcp": "mcp-server",
              "fixguide": "folder-instructions", "fixtool": "tool"},
          str({u: r["method"] for u, r in good.items()}))
    check("a unit's entry is relative to its component; a tool's is its program",
          good["fixskill"]["entry"] == "skills/fixskill.md"
          and good["fixtool"]["entry"] == "capabilities/tools/fixtool/thing.py"
          and good["fixskill"]["description"]
          == "A fixture skill: with a colon",
          str(good["fixskill"]))
    ctx.keep(locals())


def depth_two_is_the_marker(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nD2 — a component is <module>/<component>/<component>.json")
    check("a component deeper than depth 2 is NOT a component",
          "deepmod/deepcomp/nested" not in catalog
          and not any("nested" in cid for cid in catalog),
          str(sorted(catalog)))
    check("a folder with no record and no unit folders is not a component",
          "fixmod/barecomp" not in catalog,
          str(sorted(catalog)))

    norec = tmp / "no-record"
    _w(norec / "m" / "m.json", json.dumps({"description": "m"}))
    _unit_md(norec / "m" / "c" / "skills" / "x.md", "x", "a skill")
    try:
        scan_tree(norec, "repo")
        check("a component folder without its record refuses by name",
              False, "no refusal")
    except Refuse as exc:
        check("a component folder without its record refuses by name",
              exc.code == "component-record-missing" and "c.json" in exc.message,
              f"{exc.code}: {exc.message}")

    cache = tmp / "cache-leftover"
    _w(cache / "m" / "m.json", json.dumps({"description": "m"}))
    _w(cache / "m" / "former" / "capabilities" / "tools" / "old" /
       "lib" / "__pycache__" / "old.cpython-314.pyc", "bytecode")
    cached = scan_tree(cache, "repo")
    check("a removed component left with only bytecode caches is ignored",
          cached == {}, str(cached))

    nomod = tmp / "no-module-record"
    _w(nomod / "m" / "c" / "c.json",
       json.dumps({"description": "c", "dependencies": []}))
    try:
        scan_tree(nomod, "repo")
        check("a module folder without its record refuses by name",
              False, "no refusal")
    except Refuse as exc:
        check("a module folder without its record refuses by name",
              exc.code == "module-record-missing" and "m.json" in exc.message,
              f"{exc.code}: {exc.message}")

    badrec = tmp / "bad-record"
    _w(badrec / "m" / "m.json", json.dumps({"description": "m"}))
    _w(badrec / "m" / "c" / "c.json", json.dumps({"description": "c"}))
    try:
        scan_tree(badrec, "repo")
        check("a component record that breaks its schema refuses",
              False, "no refusal")
    except Refuse as exc:
        check("a component record that breaks its schema refuses",
              exc.code == "record-invalid" and "dependencies" in exc.message,
              f"{exc.code}: {exc.message}")

    bad_cat = catalog_units_map(catalog)
    check("an invalid unit empties only its own component in the units map",
          bad_cat["badmod/badcomp"] == [] and bad_cat["fixmod/goodcomp"],
          str({k: len(v) for k, v in bad_cat.items()}))
    for cid, code, words in (
            ("badmod/badcomp", "unit-invalid", "not the file name"),
            ("fixmod/dupcomp", "unit-duplicate", "same")):
        try:
            unit_rows(catalog[cid])
            check(f"{cid} refuses by name", False, "no refusal")
        except Refuse as exc:
            check(f"{cid} refuses by name",
                  exc.code == code and words in exc.message,
                  f"{exc.code}: {exc.message}")

    frontless = tmp / "frontless"
    _component(frontless, "m", "c")
    _w(frontless / "m" / "c" / "skills" / "x.md", "# no frontmatter\n")
    try:
        unit_rows(scan_tree(frontless, "repo")["m/c"])
        check("a unit file without frontmatter refuses", False, "no refusal")
    except Refuse as exc:
        check("a unit file without frontmatter refuses",
              exc.code == "unit-invalid" and "no frontmatter" in exc.message,
              f"{exc.code}: {exc.message}")

    extra = tmp / "extra-field"
    _component(extra, "m", "c")
    _unit_md(extra / "m" / "c" / "skills" / "x.md", "x", "a skill",
             extra="color: red\n")
    try:
        unit_rows(scan_tree(extra, "repo")["m/c"])
        check("a frontmatter field the schema does not name refuses",
              False, "no refusal")
    except Refuse as exc:
        check("a frontmatter field the schema does not name refuses",
              exc.code == "unit-invalid" and "color" in exc.message,
              f"{exc.code}: {exc.message}")

    mirror_cat, shadow = scan_all(tmp / "no-mirror", tmp / "no-repo")
    check("an absent tree root scans to nothing", mirror_cat == {} and not shadow)

    ev = tmp / "ws-empty-vanished"
    ev.mkdir()
    write_state(ev, {"components": {
        "gone/empty": {
            "module": "gone", "component": "empty",
            "harnesses": ["claude"], "files": [],
        },
        "fixmod/goodcomp": {
            "module": "fixmod", "component": "goodcomp",
            "harnesses": ["claude"], "files": [],
        },
    }, "shared_claims": []})
    ev_st = upgrade_book(read_state(ev), catalog_units_map(catalog))
    try:
        plan_files(ev_st["components"], catalog)
        ev_refused = None
    except Refuse as exc:
        ev_refused = f"{exc.code}: {exc.message}"
    check("D2-empty-vanished — booked-but-uncatalogued owning zero "
          "files is dropped silently",
          "gone/empty" not in ev_st["components"]
          and "fixmod/goodcomp" in ev_st["components"]
          and ev_refused is None,
          f"comps={sorted(ev_st['components'])} refuse={ev_refused}")

    fv = tmp / "ws-files-vanished"
    fv.mkdir()
    write_state(fv, {"components": {
        "gone/full": {
            "module": "gone", "component": "full",
            "harnesses": ["claude"],
            "files": [".claude/rules/x.md"],
        },
        "fixmod/goodcomp": {
            "module": "fixmod", "component": "goodcomp",
            "harnesses": ["claude"], "files": [],
        },
    }, "shared_claims": []})
    fv_st = upgrade_book(read_state(fv), catalog_units_map(catalog))
    check("D2-files-vanished — owning files is kept in the book",
          "gone/full" in fv_st["components"],
          str(sorted(fv_st["components"])))
    try:
        plan_files(fv_st["components"], catalog)
        check("D2-files-vanished — booked-but-uncatalogued owning "
              "files still refuses component-vanished",
              False, "no refusal")
    except Refuse as exc:
        check("D2-files-vanished — booked-but-uncatalogued owning "
              "files still refuses component-vanished",
              exc.code == "component-vanished"
              and "gone/full" in exc.message,
              f"{exc.code}: {exc.message}")
    ctx.keep(locals())


def three_harnesses(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nD4 — three harnesses (kimi retired 2026-08-14)")
    check("D4-harnesses-are-three",
          HARNESSES == ("claude", "codex", "opencode")
          and len(HARNESSES) == 3
          and "kimi" not in HARNESSES
          and all(name in HARNESSES
                  for name in ("claude", "codex", "opencode"))
          and all("kimi" not in (MATRIX[method] or {})
                  for method in MATRIX)
          and all(h in MATRIX["skill"] for h in HARNESSES)
          and "kimi" not in GUIDANCE_FILE
          and RULE_SECTION_HARNESSES == ("codex", "opencode")
          and all(h in GUIDANCE_FILE for h in HARNESSES),
          f"HARNESSES={HARNESSES} rule_sections={RULE_SECTION_HARNESSES}")
    try:
        _parse_harnesses("kimi")
        check("D4-harness-kimi-refuses", False, "no refusal")
    except Refuse as exc:
        known = [h for h in ("claude", "codex", "opencode")
                 if h in exc.message]
        check("D4-harness-kimi-refuses",
              exc.code == "harness-unknown"
              and "kimi" in exc.message
              and known == ["claude", "codex", "opencode"]
              and "kimi" not in exc.message.split("known:", 1)[-1],
              f"{exc.code}: {exc.message}")
    try:
        _parse_harnesses("kimi,claude")
        check("D4-harness-kimi-mixed-refuses", False, "no refusal")
    except Refuse as exc:
        check("D4-harness-kimi-mixed-refuses",
              exc.code == "harness-unknown" and "kimi" in exc.message,
              f"{exc.code}: {exc.message}")
    kf = tmp / "ws-kimi-flag"
    kf.mkdir()
    try:
        cmd_add(build_parser().parse_args(
            ["add", "-c", "fixmod/goodcomp", "--harness", "kimi",
             "--guidance", "none", "--dry-run"]),
                kf, catalog, [])
        check("D4-cli-harness-kimi-refuses", False, "no refusal")
    except Refuse as exc:
        check("D4-cli-harness-kimi-refuses",
              exc.code == "harness-unknown"
              and "kimi" in exc.message
              and all(h in exc.message
                      for h in ("claude", "codex", "opencode")),
              f"{exc.code}: {exc.message}")

    sk = tmp / "ws-strip-kimi"
    sk.mkdir()
    (sk / STATE_REL).parent.mkdir(parents=True)
    sk_book = {
        "schema": 1, "installer": "install2.py",
        "components": {
            "fixmod/goodcomp": {
                "module": "fixmod", "component": "goodcomp",
                "harnesses": ["kimi", "claude", "opencode", "codex"],
                "files": [],
            },
            "fixmod/codexcomp": {
                "module": "fixmod", "component": "codexcomp",
                "harnesses": ["claude", "kimi"],
                "files": [],
            },
        },
    }
    (sk / STATE_REL).write_text(json.dumps(sk_book), encoding="utf-8")
    sk_before = (sk / STATE_REL).read_text(encoding="utf-8")
    sk_st = read_state(sk)
    sk_good = sk_st["components"]["fixmod/goodcomp"]["harnesses"]
    sk_codex = sk_st["components"]["fixmod/codexcomp"]["harnesses"]
    check("D4-book-strips-kimi-keeps-others",
          sk_good == ["claude", "codex", "opencode"]
          and sk_codex == ["claude"]
          and "kimi" not in sk_good
          and "kimi" not in sk_codex
          and sk_good
          and sk_codex
          and (sk / STATE_REL).read_text(encoding="utf-8") == sk_before,
          f"good={sk_good} codex={sk_codex}")
    write_state(sk, sk_st)
    sk_persisted = json.loads((sk / STATE_REL).read_text(encoding="utf-8"))
    check("D4-book-strip-persists-on-write",
          sk_persisted["components"]["fixmod/goodcomp"]["harnesses"]
          == ["claude", "codex", "opencode"]
          and sk_persisted["components"]["fixmod/codexcomp"]["harnesses"]
          == ["claude"]
          and "kimi" not in json.dumps(sk_persisted["components"]),
          str({cid: rec["harnesses"]
               for cid, rec in sk_persisted["components"].items()}))

    se = tmp / "ws-kimi-only"
    se.mkdir()
    (se / STATE_REL).parent.mkdir(parents=True)
    (se / STATE_REL).write_text(json.dumps({
        "schema": 1, "components": {
            "gone/kimi-only": {
                "module": "gone", "component": "kimi-only",
                "harnesses": ["kimi"], "files": [],
            },
        },
    }), encoding="utf-8")
    try:
        read_state(se)
        check("D4-book-kimi-only-refuses", False, "no refusal")
    except Refuse as exc:
        check("D4-book-kimi-only-refuses",
              exc.code == "harness-list-empty"
              and "gone/kimi-only" in exc.message
              and "kimi" in exc.message,
              f"{exc.code}: {exc.message}")
    ctx.keep(locals())


def predecessor_sweep_cannot_reach(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nD12 — the old installer's sweep cannot reach our names")
    check("a `rbtv-` unit name is REFUSED, never minted",
          _reserved_id_refuses(tmp, catalog))

    # Pre-existing foreign content the run must preserve (D6/D12): an
    # old-installer `rbtv-` sibling in each swept folder, plus foreign keys
    # inside two shared config files.
    for rel, body in (
        (".claude/rules/rbtv-legacy.md", "old installer rule\n"),
        (".claude/commands/rbtv-legacy.md", "old installer command\n"),
        (".claude/agents/rbtv-legacy.md", "old installer agent\n"),
        (".claude/skills/rbtv-legacy/SKILL.md", "old installer skill\n"),
    ):
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        (target / rel).write_text(body, encoding="utf-8")
    (target / ".claude/settings.json").write_text(
        json.dumps({"foreignKey": 1}, indent=2) + "\n", encoding="utf-8")
    (target / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"foreign": {"url": "https://x.invalid"}}},
                   indent=2) + "\n", encoding="utf-8")
    legacy = {rel: (target / rel).read_text(encoding="utf-8") for rel in (
        ".claude/rules/rbtv-legacy.md", ".claude/commands/rbtv-legacy.md",
        ".claude/agents/rbtv-legacy.md",
        ".claude/skills/rbtv-legacy/SKILL.md")}
    ctx.keep(locals())
