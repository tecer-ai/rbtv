"""What counts as an installable component, and which harnesses exist."""
from __future__ import annotations

import json

from discovery import (EXPOSURE_COLS, EXPOSURE_NAME, HUB_DIR, Refuse,
                       exposure_rows, scan_all)

from lib.constants import (
    FORCED_READ_HARNESSES,
    GUIDANCE_FILE,
    HARNESSES,
    MATRIX,
    STATE_REL,
)
from lib.catalog import catalog_parts_map, is_installable
from lib.state import read_state, upgrade_book, write_state
from lib.planning import plan_files
from lib.listing import do_scan
from lib.commands import _parse_harnesses
from lib.parser import build_parser
from lib.commands import cmd_add

from .fixture import _reserved_id_refuses


def scan(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("scan")
    data = do_scan(catalog, shadowed)
    check("discovers every NEW-STANDARD component on the tree",
          sorted(catalog) == ["_hub/agents.md/hubguide",
                              "_hub/command/hubcmd",
                              "_hub/config/hubmcp",
                              "_hub/hook/hubhook",
                              "_hub/path/hubbin.py",
                              "_hub/path/hubbindir",
                              "_hub/pool/hubpool",
                              "_hub/rules/hubrule",
                              "_hub/skills/hubskill",
                              "_hub/skills/vendored",
                              "_hub/sub-agent/hubagent",
                              "badmod/badcomp",
                              "fixmod/codexcomp",
                              "fixmod/dupcomp", "fixmod/goodcomp",
                              "fixmod/reservedcomp",
                              "oldmod/oldcomp"],
          str(sorted(catalog)))
    check("a _skills/ folder is discovered as a hub skill unit (D15)",
          catalog["_hub/skills/vendored"]["kind"] == "hub"
          and catalog["_hub/skills/vendored"]["method"] == "skill"
          and catalog["_hub/skills/vendored"]["module"] == HUB_DIR
          and catalog["_hub/skills/vendored"]["legacy_skills_dir"]
          and not catalog["_hub/skills/vendored"]["manifest"],
          str(catalog["_hub/skills/vendored"]))
    check("it is INSTALLABLE despite having no manifest, and says so",
          is_installable(catalog["_hub/skills/vendored"])
          and [e for e in data["components"]
               if e["id"] == "_hub/skills/vendored"][0]["methods"]
          == ["skill"], str(catalog["_hub/skills/vendored"]))
    ctx.keep(locals())


def depth_two_is_the_marker(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nD2 — depth-2 + exposure.csv is the marker")
    check("a module-root exposure.csv is NOT a component (depth 1)",
          "oldmod" not in catalog,
          str(sorted(catalog)))
    check("a depth-2 exposure.csv IS a component even without component.md",
          "oldmod/oldcomp" in catalog
          and catalog["oldmod/oldcomp"]["manifest"],
          str(sorted(catalog)))
    check("a component.md with no exposure.csv is not a component",
          "fixmod/barecomp" not in catalog,
          str(sorted(catalog)))

    d1 = tmp / "d1-only"
    (d1 / "onlymod").mkdir(parents=True)
    (d1 / "onlymod" / EXPOSURE_NAME).write_text(
        ",".join(EXPOSURE_COLS) + "\n", encoding="utf-8")
    d1_cat, _ = scan_all(tmp / "no-mirror-d1", d1)
    check("D2-depth1 — a depth-1 manifest stays invisible",
          "onlymod" not in d1_cat
          and not any(cid == "onlymod" or cid.startswith("onlymod/")
                      for cid in d1_cat),
          str(sorted(d1_cat)))

    d2 = tmp / "d2-only"
    (d2 / "m" / "c").mkdir(parents=True)
    (d2 / "m" / "c" / EXPOSURE_NAME).write_text(
        ",".join(EXPOSURE_COLS) + "\n", encoding="utf-8")
    md_hits = list(d2.rglob("component.md"))
    d2_cat, _ = scan_all(tmp / "no-mirror-d2", d2)
    check("D2-depth2 — a depth-2 manifest is a component with no "
          "component.md present anywhere",
          not md_hits and "m/c" in d2_cat
          and d2_cat["m/c"]["manifest"],
          f"md={md_hits} cat={sorted(d2_cat)}")

    d3 = tmp / "d3-only"
    (d3 / "m" / "c" / "nested").mkdir(parents=True)
    (d3 / "m" / "c" / "nested" / EXPOSURE_NAME).write_text(
        ",".join(EXPOSURE_COLS) + "\n", encoding="utf-8")
    d3_cat, _ = scan_all(tmp / "no-mirror-d3", d3)
    check("D2-depth3 — a depth-3 manifest is not a component",
          "m/c" not in d3_cat and "m/c/nested" not in d3_cat
          and not any("nested" in cid for cid in d3_cat),
          str(sorted(d3_cat)))

    badm = tmp / "bad-manifest"
    (badm / "m" / "c").mkdir(parents=True)
    (badm / "m" / "c" / EXPOSURE_NAME).write_text(
        "part-id,method,entry-point\nfoo,skill,x.md\n", encoding="utf-8")
    bad_cat, _ = scan_all(tmp / "no-mirror-bad", badm)
    try:
        exposure_rows(bad_cat["m/c"])
        check("D2-malformed — a malformed manifest refuses by name",
              False, "no refusal")
    except Refuse as exc:
        check("D2-malformed — a malformed manifest refuses by name",
              exc.code == "manifest-malformed"
              and "exposure.csv" in (exc.path or exc.message)
              and "part-kind" in exc.message,
              f"{exc.code}: {exc.message}")
    check("D2-malformed — the component is still catalogued "
          "(refuses, does not vanish)",
          "m/c" in bad_cat, str(sorted(bad_cat)))

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
    ev_st = upgrade_book(read_state(ev), catalog_parts_map(catalog))
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
    fv_st = upgrade_book(read_state(fv), catalog_parts_map(catalog))
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
          and "kimi" not in FORCED_READ_HARNESSES
          and FORCED_READ_HARNESSES == ("codex",)
          and all(h in GUIDANCE_FILE for h in HARNESSES),
          f"HARNESSES={HARNESSES} forced={FORCED_READ_HARNESSES}")
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
             "--dry-run"]),
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
    check("a `rbtv-` part id is REFUSED, never minted",
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
