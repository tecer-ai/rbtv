"""`_hub/` units: folders that are a component without a manifest."""
from __future__ import annotations

import json
from pathlib import Path

from discovery import HUB_DIR, Refuse, SKILLS_DIR, SKILL_FILE

from lib.constants import MANAGED_BANNER, MANAGED_MARK, STATE_REL
from lib.catalog import is_installable, module_id
from lib.content import _is_ours
from lib.pathlinks import bin_dir
from lib.state import read_state, rec_files
from lib.selection import _sel, part_key, resolve_selection
from lib.operations import do_install, do_uninstall


def skills_folder_copied_whole(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nS — D15: a _skills/ folder is copied WHOLE, not thin-loaded")
    sk = tmp / "ws-skill-folder"
    sk.mkdir()
    rsk = do_install(sk, catalog, ["_hub/skills/vendored"],
                     ["claude", "codex"], dry_run=False)
    src = tree / SKILLS_DIR / "vendored"
    want_sk = {f"{root}/{member}"
               for root in (".claude/skills/vendored",
                            ".agents/skills/vendored")
               for member in ("SKILL.md", "LICENSE.txt",
                              "references/deep.md", "logo.png")}
    on_disk = {q.relative_to(sk).as_posix()
               for q in sk.rglob("*") if q.is_file()} - {STATE_REL.as_posix()}
    check("S1 — every member lands under every harness's skills dir",
          on_disk == want_sk,
          f"missing={sorted(want_sk - on_disk)} extra={sorted(on_disk - want_sk)}")
    check("S1 — __pycache__ (and its junk) is never copied",
          not any("__pycache__" in rel for rel in on_disk), str(on_disk))
    check("S2 — non-SKILL.md members are BYTE-IDENTICAL to the source",
          (sk / ".claude/skills/vendored/logo.png").read_bytes()
          == (src / "logo.png").read_bytes()
          and (sk / ".claude/skills/vendored/references/deep.md").read_text()
          == (src / "references/deep.md").read_text(),
          "a verbatim copy is not verbatim")
    check("S2 — the copied SKILL.md is the ONE file we stamp",
          MANAGED_MARK in (sk / ".claude/skills/vendored/SKILL.md").read_text()
          and (sk / ".claude/skills/vendored/SKILL.md").read_text()
          .startswith("---\nname: vendored\n")
          and MANAGED_MARK not in (sk / ".claude/skills/vendored/"
                                   "references/deep.md").read_text())
    check("S3 — the whole folder is OURS through that one marker",
          all(_is_ours(sk, rel) for rel in want_sk),
          str(sorted(rel for rel in want_sk if not _is_ours(sk, rel))))
    check("S3 — the source folder is never modified",
          MANAGED_MARK not in (src / SKILL_FILE).read_text())
    check("S4 — it is booked and reported like any other unit",
          rec_files(read_state(sk)["components"]["_hub/skills/vendored"])
          == want_sk
          and rsk["report"]["skill_folders"][0]["files"] == 4
          and "vendored" in read_state(sk)["components"]
          ["_hub/skills/vendored"]["parts"],
          str(rsk["report"]["skill_folders"]))
    check("S5 — a re-install is idempotent, binary and all",
          do_install(sk, catalog, ["_hub/skills/vendored"],
                     ["claude", "codex"], dry_run=False)["written"] == [])
    rsk2 = do_uninstall(sk, catalog, ["_hub/skills/vendored"], dry_run=False)
    check("S6 — uninstall takes the WHOLE folder and prunes the dirs",
          set(rsk2["deleted"]) == want_sk
          and not (sk / ".claude/skills/vendored").exists()
          and not (sk / ".agents/skills/vendored").exists(),
          str(sorted(set(rsk2["deleted"]) ^ want_sk)))
    # RELEASE, folder-wide: strip the one marker and the whole copy is the
    # human's — uninstall must not delete any of it.
    do_install(sk, catalog, ["_hub/skills/vendored"], ["claude"],
               dry_run=False)
    taken = (sk / ".claude/skills/vendored/SKILL.md").read_text().replace(
        MANAGED_BANNER, "")
    (sk / ".claude/skills/vendored/SKILL.md").write_text(taken,
                                                         encoding="utf-8")
    rsk3 = do_uninstall(sk, catalog, ["_hub/skills/vendored"], dry_run=False)
    check("S7 — stripping the one marker RELEASES the whole folder",
          rsk3["deleted"] == []
          and sorted(rsk3["released"]) == sorted(
              rel for rel in want_sk if rel.startswith(".claude/"))
          and (sk / ".claude/skills/vendored/logo.png").exists(),
          str(rsk3["released"]))
    ctx.keep(locals())


def hub_units(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nH — _hub/<method>/<name> discovery, refusals, R6 rewrite")
    expect_hub = {
        "skill": "_hub/skills/hubskill",
        "command": "_hub/command/hubcmd",
        "rule": "_hub/rules/hubrule",
        "hook": "_hub/hook/hubhook",
        "sub-agent": "_hub/sub-agent/hubagent",
        "agents.md": "_hub/agents.md/hubguide",
        "config": "_hub/config/hubmcp",
        "path": "_hub/path/hubbin.py",
    }
    for method, cid in expect_hub.items():
        rec = catalog.get(cid) or {}
        check(f"H-discover-{method} — id {cid}",
              rec.get("kind") == "hub" and rec.get("method") == method
              and rec.get("module") == HUB_DIR
              and not rec.get("hub_refusal")
              and is_installable(rec),
              str(rec))
    check("H-discover-path-file — suffix kept; PATH name is the part-id",
          catalog["_hub/path/hubbin.py"]["component"] == "hubbin.py")
    check("H-refuse-pool — discovered and named, not skipped",
          catalog["_hub/pool/hubpool"].get("hub_refusal")
          == "hub-pool-inexpressible"
          and not is_installable(catalog["_hub/pool/hubpool"])
          and "_hub/pool/hubpool" in data["hub_refusals"],
          str(catalog.get("_hub/pool/hubpool")))
    check("H-refuse-path-dir — discovered and named, not skipped",
          catalog["_hub/path/hubbindir"].get("hub_refusal")
          == "hub-path-directory"
          and not is_installable(catalog["_hub/path/hubbindir"])
          and "_hub/path/hubbindir" in data["hub_refusals"],
          str(catalog.get("_hub/path/hubbindir")))
    hp = tmp / "ws-hub-pool"
    hp.mkdir()
    try:
        do_install(hp, catalog, ["_hub/pool/hubpool"], ["claude"],
                   dry_run=False)
        check("H-refuse-pool-install — typed refusal", False, "no refusal")
    except Refuse as exc:
        check("H-refuse-pool-install — typed refusal",
              exc.code == "hub-pool-inexpressible"
              and not (hp / STATE_REL).exists(), exc.code)
    hd = tmp / "ws-hub-pathdir"
    hd.mkdir()
    try:
        do_install(hd, catalog, ["_hub/path/hubbindir"], ["claude"],
                   dry_run=False)
        check("H-refuse-path-dir-install — typed refusal", False,
              "no refusal")
    except Refuse as exc:
        check("H-refuse-path-dir-install — typed refusal",
              exc.code == "hub-path-directory"
              and not (hd / STATE_REL).exists(), exc.code)
    hub_keys = {part_key(cid, catalog[cid]["component"])
                for cid, c in catalog.items()
                if c["module"] == HUB_DIR and is_installable(c)}
    check("H-alias — -m hub maps to module _hub (the one mapping)",
          resolve_selection(_sel(verb="add", module=["hub"]), catalog, None)
          == hub_keys
          and module_id("hub") == HUB_DIR
          and module_id("_hub") == HUB_DIR
          and module_id("core") == "core")

    hw = tmp / "ws-hub-realize"
    hw.mkdir()
    hr = do_install(hw, catalog, [
        "_hub/skills/hubskill", "_hub/command/hubcmd",
        "_hub/rules/hubrule", "_hub/sub-agent/hubagent",
        "_hub/hook/hubhook", "_hub/config/hubmcp",
        "_hub/agents.md/hubguide", "_hub/path/hubbin.py",
    ], ["claude"], dry_run=False)
    check("H-realize-skill — verbatim folder copy",
          (hw / ".claude/skills/hubskill/SKILL.md").is_file()
          and MANAGED_MARK in (hw / ".claude/skills/hubskill/SKILL.md")
          .read_text())
    check("H-realize-command — pointer/loader via MATRIX",
          (hw / ".claude/commands/hubcmd.md").is_file()
          and "Read `" in (hw / ".claude/commands/hubcmd.md").read_text())
    check("H-realize-rule — copy-verbatim + marker",
          "# HUB RULE" in (hw / ".claude/rules/hubrule.md").read_text()
          and MANAGED_MARK in (hw / ".claude/rules/hubrule.md").read_text())
    check("H-realize-sub-agent — pointer/loader via MATRIX",
          (hw / ".claude/agents/hubagent.md").is_file()
          and "Read `" in (hw / ".claude/agents/hubagent.md").read_text())
    check("H-realize-hook — shared claim, not a whole file",
          "SessionStart" in json.loads(
              (hw / ".claude/settings.json").read_text()).get("hooks", {}))
    check("H-realize-config — MCP key claimed",
          "hubfix" in json.loads((hw / ".mcp.json").read_text())
          .get("mcpServers", {}))
    check("H-realize-path — catalogued, nothing under target, linked by part-id",
          not any(r["method"] == "path"
                  for r in hr["report"]["skipped_inventory_rows"])
          and not (hw / "hubbin.py").exists()
          and "hubbin.py" in read_state(hw)["components"]
          ["_hub/path/hubbin.py"]["parts"]
          and (bin_dir() / "hubbin.py").is_symlink()
          and (bin_dir() / "hubbin.py").resolve()
          == Path(catalog["_hub/path/hubbin.py"]["path"]).resolve())
    check("H-realize-agents.md — fragment rides the guidance report",
          any(p[0] == "hubguide"
              for p in hr["report"].get("agents_parts") or []))
    ctx.keep(locals())


def hub_book_key_rewrite(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nH-rewrite — R6 _skills book key becomes _hub/skills on load")
    rw = tmp / "ws-r6-rewrite"
    rw.mkdir()
    (rw / STATE_REL).parent.mkdir(parents=True)
    legacy_four = ["claude", "codex", "opencode", "kimi"]
    three = ["claude", "codex", "opencode"]
    (rw / STATE_REL).write_text(json.dumps({
        "schema": 1, "installer": "install2.py",
        "components": {
            "_skills/vendored": {
                "module": "_skills", "component": "vendored",
                "harnesses": legacy_four, "files": [
                    ".claude/skills/vendored/SKILL.md"],
                "tree": "repo", "tree_root": str(tree),
            },
            "_skills/hubskill": {
                "module": "_skills", "component": "hubskill",
                "harnesses": three, "files": [
                    ".claude/skills/hubskill/SKILL.md"],
                "tree": "repo", "tree_root": str(tree),
            },
        },
    }), encoding="utf-8")
    raw_before = (rw / STATE_REL).read_text(encoding="utf-8")
    rst = read_state(rw)
    check("H-rewrite — keys move, module becomes _hub, kimi stripped",
          set(rst["components"])
          == {"_hub/skills/vendored", "_hub/skills/hubskill"}
          and rst["components"]["_hub/skills/vendored"]["module"] == HUB_DIR
          and rst["components"]["_hub/skills/vendored"]["harnesses"]
          == three
          and rst["components"]["_hub/skills/hubskill"]["harnesses"]
          == three
          and "_skills/vendored" not in rst["components"],
          str(sorted(rst["components"])))
    check("H-rewrite — file on disk unchanged until the next write",
          (rw / STATE_REL).read_text(encoding="utf-8") == raw_before)
    try:
        rrw = do_install(rw, catalog, ["_hub/skills/vendored"],
                         three, dry_run=False)
        vanished = False
    except Refuse as exc:
        rrw = None
        vanished = exc.code == "component-vanished"
        check("H-rewrite — install after rewrite", False,
              f"{exc.code}: {exc.message}")
    if rrw is not None:
        persisted = json.loads((rw / STATE_REL).read_text(encoding="utf-8"))
        check("H-rewrite — no component-vanished; persisted under new key",
              not vanished
              and "_hub/skills/vendored" in persisted["components"]
              and "_skills/vendored" not in persisted["components"]
              and persisted["components"]["_hub/skills/vendored"]
              ["harnesses"] == three,
              str(sorted(persisted["components"])))

    hx = tmp / "ws-hub-coll"
    hx.mkdir()
    (hx / STATE_REL).parent.mkdir(parents=True)
    (hx / STATE_REL).write_text(json.dumps({
        "schema": 1, "installer": "install2.py",
        "components": {
            "_skills/vendored": {
                "module": "_skills", "component": "vendored",
                "harnesses": ["claude"], "files": []},
            "_hub/skills/vendored": {
                "module": "_hub", "component": "vendored",
                "harnesses": ["claude"], "files": []},
        },
    }), encoding="utf-8")
    try:
        read_state(hx)
        check("H-rewrite-collision — both keys refuse", False, "no refusal")
    except Refuse as exc:
        check("H-rewrite-collision — both keys refuse",
              exc.code == "hub-id-collision", exc.code)
    ctx.keep(locals())
