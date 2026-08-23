"""Installing and removing single parts, and the v1 to v2 book upgrade."""
from __future__ import annotations

import json
from pathlib import Path

from discovery import HUB_DIR, HUB_ID_FOLDER, Refuse, scan_all

from lib.constants import (
    HARNESSES,
    MANAGED_BANNER,
    REPO_ROOT,
    SCHEMA,
    STATE_REL,
)
from lib.catalog import catalog_parts_map
from lib.claims import _claim_id
from lib.target import discover_target
from lib.state import (
    known_files,
    read_state,
    rec_files,
    rewrite_legacy_skill_ids,
    upgrade_book,
    write_state,
)
from lib.planning import plan_files
from lib.selection import _sel, resolve_selection
from lib.operations import _select_parts, do_install, do_uninstall


def vanished_component_removable(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nV — a VANISHED booked component is removable without the tree")
    vn = tmp / "ws-vanished"
    vn.mkdir()
    do_install(vn, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
    gone_rel = ".claude/rules/goner.md"
    (vn / gone_rel).write_text(MANAGED_BANNER + "# from a folder now gone\n",
                               encoding="utf-8")
    stv = read_state(vn)
    stv["components"]["gonemod/gonecomp"] = {
        "tree": "mirror", "tree_root": str(vn / ".rbtv/mirror"),
        "module": "gonemod", "component": "gonecomp",
        "harnesses": ["claude"], "files": [gone_rel]}
    write_state(vn, stv)
    try:
        do_install(vn, catalog, ["fixmod/goodcomp"], ["claude"],
                   dry_run=False)
        check("V1 — a vanished component blocks the run", False,
              "no refusal raised")
    except Refuse as exc:
        check("V1 — a vanished component blocks the run",
              exc.code == "component-vanished", exc.code)
        check("V1 — and the refusal names a door that actually opens",
              "uninstall --component gonemod/gonecomp" in exc.message,
              exc.message)
    try:
        resolve_selection(_sel(verb="add", component=["gonemod/gonecomp"]),
                          catalog, None)
        catalog_only = "no refusal"
    except Refuse as exc:
        catalog_only = exc.code
    check("V2 — the trees alone cannot name it (that was the trap)",
          catalog_only == "component-unknown", catalog_only)
    check("V2 — the BOOK can",
          resolve_selection(
              _sel(verb="rm", component=["gonemod/gonecomp"]),
              catalog, read_state(vn)["components"])
          == {"gonemod/gonecomp#gonecomp"})
    resv = do_uninstall(vn, catalog, ["gonemod/gonecomp"], dry_run=False)
    check("V3 — uninstalling it needs no tree, and takes its file",
          resv["deleted"] == [gone_rel] and not (vn / gone_rel).exists()
          and "gonemod/gonecomp" not in read_state(vn)["components"],
          str(resv["deleted"]))
    check("V3 — the target is unblocked: the next install runs clean",
          do_install(vn, catalog, ["fixmod/goodcomp"], ["claude"],
                     dry_run=False)["written"] == [])
    ctx.keep(locals())


def part_level_install_remove(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nP — part-level install / remove (schema 2)")
    pdup = tmp / "ws-dup"
    pdup.mkdir()
    try:
        do_install(pdup, catalog, ["fixmod/dupcomp"], ["claude"],
                   dry_run=False)
        check("D-dup — duplicate part-id refuses", False, "no refusal")
    except Refuse as exc:
        check("D-dup — duplicate part-id refuses",
              exc.code == "part-id-duplicate", exc.code)
        check("D-dup — zero files written",
              not any(pdup.rglob("*.md")) and not (pdup / STATE_REL).exists())

    try:
        _select_parts(catalog["fixmod/goodcomp"], None, ["no-such-part"])
        pu = "no refusal"
    except Refuse as exc:
        pu = exc.code
    except Exception as exc:
        pu = type(exc).__name__
    check("P-unknown — unknown part-id refuses",
          pu == "part-unknown", pu)

    pws = tmp / "ws-parts"
    pws.mkdir()
    rp = do_install(pws, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                    dry_run=False, parts=["fixskill"])
    pdisk = {q.relative_to(pws).as_posix()
             for q in pws.rglob("*") if q.is_file()}
    check("P-add — only the requested part's files land",
          ".claude/skills/fixskill/SKILL.md" in pdisk
          and ".claude/rules/fixrule.md" not in pdisk
          and not (pws / ".mcp.json").exists(),
          str(sorted(pdisk)))
    prec = read_state(pws)["components"]["fixmod/goodcomp"]
    check("P-add — book carries only that part",
          set(prec["parts"]) == {"fixskill"}, str(sorted(prec["parts"])))
    rp2 = do_install(pws, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                     dry_run=False)
    check("P-add — re-add with no parts list refreshes booked, does not fill",
          set(read_state(pws)["components"]["fixmod/goodcomp"]["parts"])
          == {"fixskill"}
          and not (pws / ".claude/rules/fixrule.md").exists()
          and rp2["written"] == [],
          str(sorted(read_state(pws)["components"]["fixmod/goodcomp"]["parts"])))
    do_install(pws, catalog, ["fixmod/goodcomp"], list(HARNESSES),
               dry_run=False, parts=["fixrule", "fixmcp", "fixhook"])
    check("P-add — later add MERGES parts",
          set(read_state(pws)["components"]["fixmod/goodcomp"]["parts"])
          == {"fixskill", "fixrule", "fixmcp", "fixhook"})
    ctx.keep(locals())


def part_level_claim_release(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nC — part-level claim release")
    mcp_before = json.loads((pws / ".mcp.json").read_text())
    check("C-setup — MCP key is present before the part rm",
          "fix" in mcp_before.get("mcpServers", {}), str(mcp_before))
    do_uninstall(pws, catalog, ["fixmod/goodcomp"], dry_run=False,
                 parts=["fixmcp"])
    pst = read_state(pws)
    check("C-leak — rm of the config part releases the MCP key",
          (not (pws / ".mcp.json").exists()
           or "fix" not in json.loads(
               (pws / ".mcp.json").read_text()).get("mcpServers", {}))
          and _claim_id(".mcp.json", ["mcpServers", "fix"])
          not in pst["shared_claims"],
          str(pst["shared_claims"]))
    check("C-leak — sibling hook claim stays, skill file stays",
          (pws / ".claude/skills/fixskill/SKILL.md").is_file()
          and _claim_id(".claude/settings.json", ["hooks", "PreToolUse"])
          in pst["shared_claims"]
          and "fixmcp" not in pst["components"]["fixmod/goodcomp"]["parts"]
          and "fixhook" in pst["components"]["fixmod/goodcomp"]["parts"])
    hook_claims = pst["components"]["fixmod/goodcomp"]["parts"]["fixhook"].get(
        "claims") or []
    check("C-leak — claims are tagged on the part that minted them",
          any("hooks" in c for c in hook_claims), str(hook_claims))

    do_uninstall(pws, catalog, ["fixmod/goodcomp"], dry_run=False,
                 parts=["fixskill", "fixrule", "fixhook"])
    check("P-rm — removing the last parts unbooks the component",
          "fixmod/goodcomp" not in (read_state(pws).get("components") or {})
          or not (pws / STATE_REL).exists())
    ctx.keep(locals())


def vanished_component_part_rm(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nC2 — vanished-component part rm still releases claims")
    pv = tmp / "ws-vanish-part"
    pv.mkdir()
    do_install(pv, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
    gone_cat = {k: v for k, v in catalog.items() if k != "fixmod/goodcomp"}
    do_uninstall(pv, gone_cat, ["fixmod/goodcomp"], dry_run=False,
                 parts=["fixmcp"])
    pvst = read_state(pv)
    check("C2 — vanished folder, rm config part: MCP key gone, rest stays",
          (not (pv / ".mcp.json").exists()
           or "fix" not in json.loads(
               (pv / ".mcp.json").read_text()).get("mcpServers", {}))
          and (pv / ".claude/skills/fixskill/SKILL.md").is_file()
          and "fixmcp" not in pvst["components"]["fixmod/goodcomp"]["parts"]
          and "fixskill" in pvst["components"]["fixmod/goodcomp"]["parts"],
          str(sorted(pvst["components"]["fixmod/goodcomp"]["parts"])))
    check("C2-rebuild — vanished part-rm keeps sibling hook claim",
          _claim_id(".claude/settings.json", ["hooks", "PreToolUse"])
          in pvst["shared_claims"],
          str(pvst["shared_claims"]))

    vu = tmp / "ws-v1-part"
    vu.mkdir()
    do_install(vu, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
    st = read_state(vu)
    rec = st["components"]["fixmod/goodcomp"]
    rec.pop("parts", None)
    rec["files"] = sorted(rec_files(rec)) if "files" not in rec else rec["files"]
    write_state(vu, st)
    gone_vu = {k: v for k, v in catalog.items() if k != "fixmod/goodcomp"}
    try:
        do_uninstall(vu, gone_vu, ["fixmod/goodcomp"], dry_run=False,
                     parts=["fixskill"])
        check("P-unbooked-v1 — vanished v1 part-rm refuses", False,
              "no refusal")
    except Refuse as exc:
        check("P-unbooked-v1 — vanished v1 part-rm refuses",
              exc.code == "part-unbooked", exc.code)
    ctx.keep(locals())


def v1_to_v2_upgrade(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nU-live — v1→v2 upgrade against a COPY of a real book")
    # DISCOVERED from the cwd, the same walk the CLI itself uses. It was a
    # literal `/home/<someone>/<their vault>` — an instance path baked into
    # content that ships in the rbtv repo, where the General rule forbids
    # exactly that. The practical cost was worse than the rule: on every
    # machine but one the path did not exist, so the whole block was inert
    # and its `live book present` arm failed for a reason no one could act
    # on. Discovery makes it run wherever a workspace actually is.
    live_root, _ = discover_target(Path.cwd())
    live_book = live_root / STATE_REL
    if live_book.is_file():
        before = live_book.read_bytes()
        dest_root = tmp / "ws-live-upgrade"
        dest = dest_root / STATE_REL
        dest.parent.mkdir(parents=True)
        dest.write_bytes(before)
        raw = json.loads(dest.read_text(encoding="utf-8"))
        old_claims = list(raw.get("shared_claims") or [])
        src_harnesses = {
            cid: list(rec.get("harnesses") or [])
            for cid, rec in raw["components"].items()}
        src_parts = {
            cid: set((rec.get("parts") or {}))
            for cid, rec in raw["components"].items()}
        src_files = {cid: rec_files(rec)
                     for cid, rec in raw["components"].items()}
        rewrite_legacy_skill_ids(raw)
        old_ids = set(raw["components"])
        live_cat, _ = scan_all(live_root / ".rbtv" / "mirror",
                               REPO_ROOT)
        upgraded = upgrade_book(raw, catalog_parts_map(live_cat))
        write_state(dest_root, upgraded)
        got = json.loads(dest.read_text(encoding="utf-8"))
        check("U-live live file untouched",
              live_book.read_bytes() == before)
        check("U-live schema 2, prefix gone",
              got["schema"] == SCHEMA and "prefix" not in got)
        present = [cid for cid in old_ids if cid in live_cat]
        check("U-live still-present cids keep their parts maps",
              present
              and all("parts" in got["components"][cid]
                      and set(got["components"][cid]["parts"])
                      == src_parts.get(cid, set())
                      for cid in present),
              str(present[:5]))
        check("U-live shared_claims unchanged",
              got["shared_claims"] == old_claims)
        dropped = old_ids - set(got["components"])
        check("U-live empty uncatalogued already flushed (no leftover drop)",
              dropped == set(),
              str(sorted(dropped)))
        try:
            plan_files(got["components"], live_cat)
            live_refuse = None
        except Refuse as exc:
            live_refuse = f"{exc.code}: {exc.message}"
        check("U-live plan_files refuses nothing after the drop",
              live_refuse is None, str(live_refuse))
        check("U-live known_files dual-read equals booked files ∪ guidance",
              known_files(got) == set().union(*src_files.values())
              | set(raw.get("guidance_files") or []))
        # THE RETIRED-HARNESS STRIP IS NOT TESTED HERE, and saying so is
        # the point: its coverage is the D4 block and `H-rewrite`, which
        # build books carrying the retired name themselves. This arm used
        # to assert the strip too, by requiring the LIVE book to still
        # list `kimi` — an assertion about how OLD a machine's data is,
        # not about behaviour. The `kimi` CLI was retired 2026-08-14; once
        # any install rewrote the record without it the arm could never
        # pass again, and it reported a healthy migration as a failure.
        # A real book of unknown age can only prove age-independent
        # things, so those are what is left.
        hub_skills = [
            cid for cid in src_harnesses
            if cid.startswith(f"{HUB_DIR}/{HUB_ID_FOLDER['skill']}/")]
        check("U-live upgrade carries every record and invents no "
              "harness this tool does not know",
              len(got["components"]) == len(src_harnesses)
              and all(set(got["components"][cid]["harnesses"])
                      <= set(HARNESSES) for cid in got["components"]),
              str({cid: got["components"][cid]["harnesses"]
                   for cid in list(got["components"])[:3]}))
        if hub_skills:
            check("U-live hub skill ids land under the hub module",
                  all(got["components"][cid].get("module") == HUB_DIR
                      for cid in hub_skills),
                  str({cid: got["components"][cid].get("module")
                       for cid in hub_skills[:3]}))
        else:
            skip("U-live hub skill ids land under the hub module",
                 "this workspace books no _hub skill")
    else:
        skip("U-live — upgrade against a real book",
             f"no installed workspace at or above {Path.cwd()}")
    ctx.keep(locals())
