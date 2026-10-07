"""Whole-folder skills: a mirror `_skills/<name>/` folder is a component without a record."""
from __future__ import annotations

import json

from discovery import HUB_DIR, Refuse, SKILLS_DIR, SKILL_FILE, scan_tree

from lib.constants import MANAGED_BANNER, MANAGED_MARK, STATE_REL
from lib.catalog import module_id
from lib.content import _is_ours
from lib.state import read_state, rec_files
from lib.selection import _sel, resolve_selection, file_key
from lib.operations import do_install, do_uninstall


def skills_folder_copied_whole(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nS — D15: a _skills/ skill is copied whole into each harness's skills folder")
    sk = tmp / "ws-skill-folder"
    sk.mkdir()
    rsk = do_install(sk, catalog, ["_hub/skills/vendored"],
                     ["claude", "codex"], dry_run=False)
    src = ctx.mirror / SKILLS_DIR / "vendored"
    want_sk = {f"{root}/{member}"
               for root in (".claude/skills/vendored", ".agents/skills/vendored")
               for member in ("SKILL.md", "LICENSE.txt", "references/deep.md",
                              "logo.png")}
    on_disk = {q.relative_to(sk).as_posix()
               for q in sk.rglob("*") if q.is_file()} - {STATE_REL.as_posix(),
                                                          ".codex/config.toml"}
    check("S1 — every member lands under every harness's skills folder; "
          "__pycache__ is left behind",
          on_disk == want_sk,
          f"missing={sorted(want_sk - on_disk)} extra={sorted(on_disk - want_sk)}")
    check("S2 — every member but SKILL.md is byte-identical to the source",
          all((sk / ".claude/skills/vendored" / member).read_bytes()
              == (src / member).read_bytes()
              for member in ("LICENSE.txt", "references/deep.md", "logo.png")))
    copy = (sk / ".claude/skills/vendored/SKILL.md").read_text(encoding="utf-8")
    source_text = (src / SKILL_FILE).read_text(encoding="utf-8")
    check("S2 — the copied SKILL.md is the source with the marker after its "
          "own frontmatter, and nothing else changed",
          copy.startswith("---\nname: vendored\ndescription: A vendored skill\n---\n"
                          + MANAGED_BANNER)
          and copy.replace(MANAGED_BANNER, "") == source_text, copy[:400])
    check("S3 — the whole folder is ours through that one marker",
          all(_is_ours(sk, rel) for rel in want_sk),
          str(sorted(rel for rel in want_sk if not _is_ours(sk, rel))))
    check("S3 — the source folder is never modified",
          MANAGED_MARK not in source_text)
    check("S4 — it is booked and reported like any other file",
          rec_files(read_state(sk)["components"]["_hub/skills/vendored"]) == want_sk
          and rsk["report"]["skill_folders"] == [
              {"component": "_hub/skills/vendored", "files": 4,
               "roots": [".agents/skills/vendored", ".claude/skills/vendored"]}]
          and "vendored" in read_state(sk)["components"]["_hub/skills/vendored"]["selected"],
          str(rsk["report"]["skill_folders"]))
    check("S5 — a re-install is idempotent, binary and all",
          do_install(sk, catalog, ["_hub/skills/vendored"],
                     ["claude", "codex"], dry_run=False)["written"] == [])
    rsk2 = do_uninstall(sk, catalog, ["_hub/skills/vendored"], dry_run=False)
    check("S6 — uninstall takes the whole folder and prunes the dirs",
          set(rsk2["deleted"]) == want_sk
          and not (sk / ".claude/skills/vendored").exists()
          and not (sk / ".agents/skills/vendored").exists(),
          str(sorted(set(rsk2["deleted"]) ^ want_sk)))
    # RELEASE, folder-wide: strip the one marker and the whole copy is the human's.
    do_install(sk, catalog, ["_hub/skills/vendored"], ["claude"], dry_run=False)
    taken = (sk / ".claude/skills/vendored/SKILL.md").read_text(encoding="utf-8").replace(
        MANAGED_BANNER, "")
    (sk / ".claude/skills/vendored/SKILL.md").write_text(taken, encoding="utf-8")
    rsk3 = do_uninstall(sk, catalog, ["_hub/skills/vendored"], dry_run=False)
    check("S7 — stripping the one marker RELEASES the whole folder",
          rsk3["deleted"] == []
          and sorted(rsk3["released"]) == sorted(
              rel for rel in want_sk if rel.startswith(".claude/"))
          and (sk / ".claude/skills/vendored/logo.png").exists(),
          str(rsk3["released"]))
    # J0: a _skills/ folder counts only in an installation's mirror.
    jtree = tmp / "j0-tree"
    (jtree / SKILLS_DIR / "stray").mkdir(parents=True)
    (jtree / SKILLS_DIR / "stray" / SKILL_FILE).write_text(
        "---\nname: stray\ndescription: x\n---\nbody\n", encoding="utf-8")
    check("S-J0 — a _skills/ folder in the rbtv tree is ignored; in a mirror it counts",
          "_hub/skills/stray" not in scan_tree(jtree, "repo")
          and "_hub/skills/stray" in scan_tree(jtree, "mirror"))
    ctx.keep(locals())


def hub_alias(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nH — `-m hub` reaches the whole-folder skills")
    hub_keys = {file_key(cid, catalog[cid]["component"])
                for cid, c in catalog.items() if c["module"] == HUB_DIR}
    check("H-alias — -m hub maps to module _hub (the one mapping)",
          hub_keys == {"_hub/skills/vendored#vendored"}
          and resolve_selection(_sel(verb="add", module=["hub"]), catalog, None)
          == hub_keys
          and module_id("hub") == HUB_DIR
          and module_id("_hub") == HUB_DIR
          and module_id("core") == "core",
          str(hub_keys))
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
        },
    }), encoding="utf-8")
    raw_before = (rw / STATE_REL).read_text(encoding="utf-8")
    rst = read_state(rw)
    check("H-rewrite — keys move, module becomes _hub, kimi stripped",
          set(rst["components"]) == {"_hub/skills/vendored"}
          and rst["components"]["_hub/skills/vendored"]["module"] == HUB_DIR
          and rst["components"]["_hub/skills/vendored"]["harnesses"]
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
