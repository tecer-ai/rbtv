"""One install: what it writes, what it refuses, what a dry run says, and what
an uninstall takes back."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from discovery import Refuse

from lib.constants import (
    FENCE_ID,
    HARNESSES,
    LEGACY_PREFIX,
    MANAGED_BANNER,
    MANAGED_MARK,
    SCHEMA,
    STATE_REL,
)
from lib.claims import _claim_id
from lib.content import _is_ours
from lib.pathlinks import bin_dir
from lib.state import read_state, rec_files
from lib.operations import do_install, do_uninstall
from lib.report import print_result


def green_arm_all_harnesses(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\ngreen arm — install all three harnesses")
    res = do_install(target, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                     dry_run=False)
    expect = {
        ".claude/skills/fixskill/SKILL.md",
        ".agents/skills/fixskill/SKILL.md",
        ".claude/commands/fixcmd.md",
        ".codex/prompts/fixcmd.md",
        ".opencode/commands/fixcmd.md",
        ".claude/rules/fixrule.md",
        ".agents/behavior-rules/fixrule.md",
        ".claude/agents/fixagent.md",
        ".opencode/agents/fixagent.md",
    }
    shared = {".claude/settings.json", ".codex/hooks.json", ".mcp.json",
              ".codex/config.toml", "opencode.json"}
    on_disk = {p.relative_to(target).as_posix()
               for p in target.rglob("*") if p.is_file()}
    want = expect | shared | set(legacy) | {STATE_REL.as_posix()}
    check("every CMP-12 realization landed under its BARE part id, and "
          "nothing else",
          on_disk == want,
          f"missing={sorted(want - on_disk)} extra={sorted(on_disk - want)}")
    check("D12 — no artifact carries the retired rbtv2- prefix",
          not any(Path(rel).name.startswith(LEGACY_PREFIX)
                  or Path(rel).parent.name.startswith(LEGACY_PREFIX)
                  for rel in expect), str(sorted(expect)))
    check("D12 — every artifact carries the ownership marker instead",
          all(MANAGED_MARK in (target / rel).read_text() for rel in expect)
          and all(_is_ours(target, rel) for rel in expect),
          str(sorted(rel for rel in expect
                     if MANAGED_MARK not in (target / rel).read_text())))
    check("D12 — the marker sits BELOW the frontmatter, which still parses",
          (target / ".claude/skills/fixskill/SKILL.md")
          .read_text().startswith("---\nname: fixskill\n")
          and (target / ".claude/skills/fixskill/SKILL.md")
          .read_text().split("---\n")[2].lstrip().startswith("<!--"),
          (target / ".claude/skills/fixskill/SKILL.md").read_text()[:200])
    check("`pool` minted nothing; `path` still writes nothing under target",
          not (target / ".claude/skills/fixtool").exists()
          and not (target / ".claude/skills/fixpool").exists()
          and [r["method"] for r
               in res["report"]["skipped_inventory_rows"]] == ["pool"]
          and not (target / "fixtool").exists()
          and not (target / "tool/thing.py").exists(),
          str(res["report"]["skipped_inventory_rows"]))
    check("green — path part-id is the link name, not the basename",
          (bin_dir() / "fixtool").is_symlink()
          and not (bin_dir() / "thing.py").exists()
          and (bin_dir() / "fixtool").resolve()
          == (tree / "fixmod/goodcomp/tool/thing.py").resolve()
          and read_state(target)["components"]["fixmod/goodcomp"]
          .get("path_links") == ["fixtool"],
          str(list(bin_dir().iterdir()) if bin_dir().is_dir() else None))
    check("skill loader carries a YAML-safe description",
          '"A fixture skill: with a colon"'
          in (target / ".claude/skills/fixskill/SKILL.md").read_text())
    check("rule copied VERBATIM under one marker line",
          (target / ".claude/rules/fixrule.md").read_text()
          == MANAGED_BANNER + (tree / "fixmod/goodcomp/rule-entry.md"
                               ).read_text(),
          (target / ".claude/rules/fixrule.md").read_text()[:200])
    check("F3 — NO code path mints the retired .agents/rbtv2-exposure.md",
          not (target / ".agents/rbtv2-exposure.md").exists()
          and not any("exposure.md" in rel for rel in expect),
          str(sorted(expect)))
    check("with no basis, the exposure block is REPORTED per guidance file "
          "an installed harness reads",
          sorted(res["report"]["guidance_manual"]) == ["AGENTS.md",
                                                       "CLAUDE.md"]
          and "Step 0" in res["report"]["guidance_manual"]["AGENTS.md"]
          and "Step 0" not in res["report"]["guidance_manual"]["CLAUDE.md"]
          and "fixguide"
          in res["report"]["guidance_manual"]["CLAUDE.md"],
          str(sorted(res["report"]["guidance_manual"])))
    check("root guidance file NEVER written (D8)",
          not (target / "CLAUDE.md").exists()
          and not (target / "AGENTS.md").exists())
    check("claude settings gained OUR keys beside the foreign one",
          json.loads((target / ".claude/settings.json").read_text())
          == {"foreignKey": 1, "enableAllProjectMcpServers": True,
              "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
                  {"type": "command", "command": "true"}]}]}})
    check("mcp.json gained the prefixed server beside the foreign one",
          sorted(json.loads((target / ".mcp.json").read_text())["mcpServers"])
          == sorted(["fix", "foreign"]))
    check("codex config.toml carries a fenced block with the url form",
          f"# {FENCE_ID}:start" in (target / ".codex/config.toml").read_text()
          and 'url = "https://example.invalid/mcp"'
          in (target / ".codex/config.toml").read_text())
    check("old-installer rbtv- siblings untouched by the install",
          all((target / rel).read_text() == body
              for rel, body in legacy.items()))

    state = read_state(target)
    rec = state["components"]["fixmod/goodcomp"]
    check("install.json books every per-component file",
          rec_files(rec) == expect - set(state["guidance_files"]),
          str(sorted(rec_files(rec) ^ (expect - set(state["guidance_files"])))))
    check("schema 2 books parts keyed by bare part-id, no rec.files",
          state.get("schema") == SCHEMA
          and "files" not in rec
          and set(rec["parts"]) >= {"fixskill", "fixcmd", "fixrule",
                                    "fixagent", "fixhook", "fixmcp",
                                    "fixguide", "fixtool", "fixpool"}
          and rec["parts"]["fixskill"]["method"] == "skill"
          and rec["parts"]["fixmcp"]["method"] == "config"
          and ".claude/skills/fixskill/SKILL.md"
          in rec["parts"]["fixskill"]["files"],
          str(sorted(rec.get("parts") or {})))
    check("install.json books every shared-file claim",
          sorted(state["shared_claims"]) == sorted([
              _claim_id(".claude/settings.json",
                        ["enableAllProjectMcpServers"]),
              _claim_id(".claude/settings.json", ["hooks", "PreToolUse"]),
              _claim_id(".codex/hooks.json", ["hooks", "PreToolUse"]),
              _claim_id(".mcp.json", ["mcpServers", "fix"]),
              _claim_id("opencode.json", ["mcp", "fix"]),
              _claim_id(".codex/config.toml", None),
          ]), str(sorted(state["shared_claims"])))
    check("install.json books the source tree + harnesses",
          rec["tree"] == "repo" and rec["tree_root"] == str(tree)
          and rec["harnesses"] == list(HARNESSES))
    check("re-install is idempotent",
          do_install(target, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                     dry_run=False)["written"] == [])
    ctx.keep(locals())


def red_unknown_method(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nred arm — unknown method")
    try:
        do_install(target, catalog, ["badmod/badcomp"], list(HARNESSES),
                   dry_run=False)
        check("unknown method refuses", False, "no refusal raised")
    except Refuse as exc:
        check("unknown method refuses", exc.code == "method-unknown", exc.code)
        check("unknown-method refusal wrote nothing",
              "badcomp" not in json.dumps(read_state(target)))
    ctx.keep(locals())


def red_foreign_collision(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nred arm — collision with content we did not write")
    fresh = tmp / "workspace2"
    (fresh / ".claude" / "rules").mkdir(parents=True)
    (fresh / ".claude/rules/fixrule.md").write_text(
        "hand-placed\n", encoding="utf-8")
    (fresh / ".mcp.json").write_text(json.dumps(
        {"mcpServers": {"fix": {"url": "https://squatter.invalid"}}}),
        encoding="utf-8")
    before = {p.relative_to(fresh).as_posix(): p.read_text()
              for p in fresh.rglob("*") if p.is_file()}
    try:
        do_install(fresh, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False)
        check("collision refuses", False, "no refusal raised")
    except Refuse as exc:
        check("collision refuses", exc.code == "collision", exc.code)
        check("both the file AND the shared key are named",
              ".claude/rules/fixrule.md" in exc.message
              and ".mcp.json::mcpServers." + "fix" in exc.message,
              exc.message)
    after = {p.relative_to(fresh).as_posix(): p.read_text()
             for p in fresh.rglob("*") if p.is_file()}
    check("collision refusal left ZERO files and changed nothing",
          before == after, str(sorted(set(after) ^ set(before))))
    ctx.keep(locals())


def harness_filter(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nharness filter")
    only = tmp / "workspace3"
    only.mkdir()
    do_install(only, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
    disk = {p.relative_to(only).as_posix()
            for p in only.rglob("*") if p.is_file()}
    check("codex/opencode files absent under --harness claude",
          not any(d.startswith((".codex/", ".opencode/", ".agents/skills"))
                  for d in disk), str(sorted(disk)))
    ctx.keep(locals())


def dry_run_prints_the_report_rows(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\n7.622 — a DRY RUN prints the report rows a real run prints")
    rr = tmp / "ws-report-rows"
    rr.mkdir()
    rr_dry = do_install(rr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                        dry_run=True)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_result(rr_dry)
    dry_out = buf.getvalue()
    rr_real = do_install(rr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                         dry_run=False)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_result(rr_real)
    real_out = buf.getvalue()
    check("7.622 — setup: the fixture HAS rows of both kinds to print",
          bool(rr_dry["report"]["skipped_inventory_rows"])
          and bool(rr_dry["report"]["no_realization"]),
          str(rr_dry["report"]))
    check("7.622 — every skipped-inventory row is named in the dry run",
          all(f"`{row['method']}` row {row['component']}/{row['part']}"
              in dry_out
              for row in rr_dry["report"]["skipped_inventory_rows"]),
          dry_out)
    check("7.622 — every no-realization row is named in the dry run",
          all(f"{row['harness']} has no realization for method "
              f"{row['method']} ({row['component']}/{row['part']})"
              in dry_out
              for row in rr_dry["report"]["no_realization"]),
          dry_out)
    check("7.622 — the dry run carries the SAME row count as the real run",
          sum(1 for ln in dry_out.splitlines() if ln.startswith("  · "))
          == sum(1 for ln in real_out.splitlines()
                 if ln.startswith("  · ")),
          f"dry={dry_out}\nreal={real_out}")
    check("7.622 — planned rows read as planned, real rows as done",
          "would skip `pool` row" in dry_out
          and "would mint nothing" in dry_out
          and "skipped `pool` row" in real_out
          and "nothing minted" in real_out,
          dry_out + "\n=====\n" + real_out)
    check("7.622 — the JSON shape is untouched by the printing change",
          set(rr_dry["report"]) == set(rr_real["report"])
          and rr_dry["report"]["skipped_inventory_rows"]
          == rr_real["report"]["skipped_inventory_rows"],
          str(sorted(set(rr_dry["report"]) ^ set(rr_real["report"]))))
    ctx.keep(locals())


def uninstall(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nuninstall")
    res = do_uninstall(target, catalog, ["fixmod/goodcomp"], dry_run=False)
    left = sorted(p.relative_to(target).as_posix()
                  for p in target.rglob("*") if p.is_file())
    check("only the foreign content survives",
          left == sorted(set(legacy) | {".claude/settings.json",
                                        ".mcp.json"}), str(left))
    check("the old installer's rbtv- artifacts are byte-identical",
          all((target / rel).read_text() == body
              for rel, body in legacy.items()))
    check("foreign JSON keys survive, ours are gone",
          json.loads((target / ".claude/settings.json").read_text())
          == {"foreignKey": 1}
          and json.loads((target / ".mcp.json").read_text())
          == {"mcpServers": {"foreign": {"url": "https://x.invalid"}}})
    check("shared files we fully owned are gone",
          not (target / ".codex").exists()
          and not (target / "opencode.json").exists()
          and not (target / ".agents").exists())
    check("the book is gone once nothing of ours remains",
          not (target / STATE_REL).exists())
    check("uninstall reported every deletion",
          set(res["deleted"]) == expect,
          str(sorted(set(res["deleted"]) ^ expect)))
    ctx.keep(locals())
