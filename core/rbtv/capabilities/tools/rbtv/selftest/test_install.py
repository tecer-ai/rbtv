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
from lib.apply import apply
from lib.content import _is_ours, _mark, rule_skill_description
from lib.pathlinks import bin_dir, link_path, link_points_at
from lib.state import read_state, rec_files
from lib.operations import do_install, do_uninstall
from lib.report import print_result

from .fixture import FIXAGENT_ON


def green_arm_all_harnesses(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\ngreen arm — install all three harnesses")
    res = do_install(target, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                     dry_run=False, sub_agents=FIXAGENT_ON)
    expect = {
        ".claude/skills/fixskill/SKILL.md",
        ".agents/skills/fixskill/SKILL.md",
        ".claude/commands/fixcmd.md",
        ".codex/prompts/fixcmd.md",
        ".opencode/commands/fixcmd.md",
        ".claude/rules/fixrule.md",
        ".agents/skills/fixrule/SKILL.md",
        ".claude/agents/fixagent.md",
        ".opencode/agents/fixagent.md",
        ".codex/agents/fixagent.toml",
    }
    shared = {".claude/settings.json", ".codex/hooks.json", ".mcp.json",
              ".codex/config.toml", "opencode.json"}
    on_disk = {p.relative_to(target).as_posix()
               for p in target.rglob("*") if p.is_file()}
    want = expect | shared | {"AGENTS.md", "CLAUDE.md"} | set(legacy) | {STATE_REL.as_posix()}
    check("every CMP-12 realization landed under its BARE part id, and "
          "nothing else",
          on_disk == want,
          f"missing={sorted(want - on_disk)} extra={sorted(on_disk - want)}")
    check("D12 — no artifact carries the retired rbtv2- prefix",
          not any(Path(rel).name.startswith(LEGACY_PREFIX)
                  or Path(rel).parent.name.startswith(LEGACY_PREFIX)
                  for rel in expect), str(sorted(expect)))
    check("D12 — every artifact carries the ownership marker instead",
          all(MANAGED_MARK in (target / rel).read_text(encoding="utf-8") for rel in expect)
          and all(_is_ours(target, rel) for rel in expect),
          str(sorted(rel for rel in expect
                     if MANAGED_MARK not in (target / rel).read_text(encoding="utf-8"))))
    check("D12 — the marker sits BELOW the frontmatter, which still parses",
          (target / ".claude/skills/fixskill/SKILL.md")
          .read_text(encoding="utf-8").startswith("---\nname: fixskill\n")
          and (target / ".claude/skills/fixskill/SKILL.md")
          .read_text(encoding="utf-8").split("---\n")[2].lstrip().startswith("<!--"),
          (target / ".claude/skills/fixskill/SKILL.md").read_text(encoding="utf-8")[:200])
    check("a tool writes nothing under target",
          not (target / ".claude/skills/fixtool").exists()
          and not (target / "fixtool").exists()
          and not (target / "tool/thing.py").exists(),
          str(res["report"]["path_rows"]))
    public_rows = [row for key in ("no_realization", "path_rows")
                   for row in res["report"][key]]
    check("report rows classify files by public type",
          bool(public_rows)
          and all("type" in row and "method" not in row
                  for row in public_rows),
          str(public_rows))
    check("green — path part-id is the link name, not the basename",
          link_points_at(link_path(bin_dir(), "fixtool"),
                         (tree / "fixmod/goodcomp/capabilities/tools/fixtool/thing.py").resolve())
          and not link_path(bin_dir(), "thing.py").exists()
          and read_state(target)["components"]["fixmod/goodcomp"]
          .get("path_links") == ["fixtool"],
          str(list(bin_dir().iterdir()) if bin_dir().is_dir() else None))
    toml = (target / ".codex/agents/fixagent.toml").read_text(encoding="utf-8")
    agent_source = str((tree / "fixmod/goodcomp/agents/fixagent/agent.md").resolve())
    agent_source_toml = json.dumps(agent_source)[1:-1]
    check("Codex's agent definition is TOML, marked, and points at the agent file",
          toml.startswith("# rbtv-managed")
          and 'name = "fixagent"' in toml
          and 'description = "The fixture agent"' in toml
          and agent_source_toml in toml
          and "developer_instructions = " in toml, toml)
    claude_agent = (target / ".claude/agents/fixagent.md").read_text(encoding="utf-8")
    opencode_agent = (target / ".opencode/agents/fixagent.md").read_text(encoding="utf-8")
    check("SA-notation — each harness's sub-agent file names the model and the "
          "effort in that harness's own setting",
          'model = "id/codex-m"\n' in toml and 'model_reasoning_effort = "high"\n' in toml
          and 'model: "id/claude-m"\n' in claude_agent and 'effort: "high"\n' in claude_agent
          and 'model: "id/opencode-m"\n' in opencode_agent
          and 'variant: "high"\n' in opencode_agent
          and claude_agent.startswith("---\nname: fixagent\n"),
          toml + claude_agent + opencode_agent)
    check("SA-unset — an agent chosen with no model and effort writes no file and is reported",
          res["report"]["sub_agents_unset"] == ["fixmod/goodcomp#research"]
          and not (target / ".claude/agents/research.md").exists(),
          str(res["report"]["sub_agents_unset"]))
    check("a skill is a copy: the generated name and YAML-safe description, the "
          "marker, then the source's body",
          (target / ".claude/skills/fixskill/SKILL.md").read_text(encoding="utf-8")
          == '---\nname: fixskill\ndescription: "A fixture skill: with a colon"\n---\n'
          + MANAGED_BANNER + "\n# the skill\n")
    check("a command is a copy: the description alone for Claude Code and OpenCode, "
          "no frontmatter for Codex",
          all((target / rel).read_text(encoding="utf-8")
              == '---\ndescription: "The fixture command"\n---\n'
              + MANAGED_BANNER + "\n# the command\n"
              for rel in (".claude/commands/fixcmd.md", ".opencode/commands/fixcmd.md"))
          and (target / ".codex/prompts/fixcmd.md").read_text(encoding="utf-8")
          == MANAGED_BANNER + "\n# the command\n",
          (target / ".codex/prompts/fixcmd.md").read_text(encoding="utf-8"))
    check("rule copied VERBATIM, the marker line just below its frontmatter",
          (target / ".claude/rules/fixrule.md").read_text(encoding="utf-8")
          == _mark((tree / "fixmod/goodcomp/rules/fixrule.md"
                    ).read_text(encoding="utf-8")),
          (target / ".claude/rules/fixrule.md").read_text(encoding="utf-8")[:200])
    check("Codex gets the rule as a skill: its name, the rule-skill description, "
          "the marker, then the rule's body",
          (target / ".agents/skills/fixrule/SKILL.md").read_text(encoding="utf-8")
          == "---\nname: fixrule\ndescription: "
          + json.dumps(rule_skill_description("fixrule")) + "\n---\n"
          + MANAGED_BANNER + "\n# THE RULE\n\nAlways do the thing.\n"
          and all(word in rule_skill_description("fixrule") for word in (
              "CONTAINS: ", " fixrule ", " PURPOSE: ", " ALWAYS LOAD WHEN: ",
              " DO NOT LOAD WHEN: ")),
          (target / ".agents/skills/fixrule/SKILL.md").read_text(encoding="utf-8"))
    check("OpenCode gets the rule through opencode.json: the one rule copy, "
          "by a path relative to the installation",
          json.loads((target / "opencode.json").read_text(encoding="utf-8"))
          ["instructions"] == [".claude/rules/fixrule.md"],
          (target / "opencode.json").read_text(encoding="utf-8"))
    check("F3 — NO code path mints the retired .agents/rbtv2-exposure.md",
          not (target / ".agents/rbtv2-exposure.md").exists()
          and not any("exposure.md" in rel for rel in expect),
          str(sorted(expect)))
    check("with no copy basis, the managed sections are reported from the plan",
          res["report"]["guidance_sections"] == ["AGENTS.md", "CLAUDE.md"]
          and f"{FENCE_ID}:start fixmod/goodcomp" in (target / "CLAUDE.md").read_text(encoding="utf-8")
          and "guidance_manual" not in res["report"]
          and "THE RULE" not in (target / "AGENTS.md").read_text(encoding="utf-8")
          and "THE RULE" not in (target / "CLAUDE.md").read_text(encoding="utf-8")
          and "guidance for the root" in (target / "CLAUDE.md").read_text(encoding="utf-8"),
          str(res["report"]["guidance_sections"]))
    check("managed guidance sections are installed without replacing owner files",
          all(f"{FENCE_ID}:start" in (target / name).read_text(encoding="utf-8")
              for name in ("CLAUDE.md", "AGENTS.md")))
    check("claude settings gained OUR keys beside the foreign one",
          json.loads((target / ".claude/settings.json").read_text(encoding="utf-8"))
          == {"foreignKey": 1, "enableAllProjectMcpServers": True,
              "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
                  {"type": "command", "command": "true"}]}]}})
    check("mcp.json gained the prefixed server beside the foreign one",
          sorted(json.loads((target / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"])
          == sorted(["fixmcp", "foreign"]))
    check("codex config.toml carries a fenced block with the url form",
          f"# {FENCE_ID}:start" in (target / ".codex/config.toml").read_text(encoding="utf-8")
          and 'url = "https://example.invalid/mcp"'
          in (target / ".codex/config.toml").read_text(encoding="utf-8"))
    check("old-installer rbtv- siblings untouched by the install",
          all((target / rel).read_text(encoding="utf-8") == body
              for rel, body in legacy.items()))

    state = read_state(target)
    rec = state["components"]["fixmod/goodcomp"]
    check("install.json books every per-component file",
          rec_files(rec) == expect - set(state["guidance_files"]),
          str(sorted(rec_files(rec) ^ (expect - set(state["guidance_files"])))))
    check("schema 2 books parts keyed by bare part-id, no rec.files",
          state.get("schema") == SCHEMA
          and "files" not in rec
          and set(rec["selected"]) >= {"fixskill", "fixcmd", "fixrule",
                                    "fixagent", "fixhook", "fixmcp",
                                    "fixguide", "fixtool"}
          and rec["selected"]["fixskill"]["method"] == "skill"
          and rec["selected"]["fixmcp"]["method"] == "mcp-server"
          and ".claude/skills/fixskill/SKILL.md"
          in rec["selected"]["fixskill"]["files"],
          str(sorted(rec.get("selected") or {})))
    check("install.json books every shared-file claim",
          sorted(state["shared_claims"]) == sorted([
              _claim_id(".claude/settings.json",
                        ["enableAllProjectMcpServers"]),
              _claim_id(".claude/settings.json", ["hooks", "PreToolUse"]),
              _claim_id(".codex/hooks.json", ["hooks", "PreToolUse"]),
              _claim_id(".mcp.json", ["mcpServers", "fixmcp"]),
              _claim_id("opencode.json", ["mcp", "fixmcp"]),
              _claim_id(".codex/config.toml", None),
              _claim_id(".codex/config.toml", None, "codex-limits"),
              _claim_id("opencode.json", ["instructions"]),
              _claim_id("AGENTS.md", None, "fixmod/goodcomp"),
              _claim_id("CLAUDE.md", None, "fixmod/goodcomp"),
          ]), str(sorted(state["shared_claims"])))
    check("install.json books the portable source kind + harnesses",
          rec["tree"] == "repo" and "tree_root" not in rec
          and rec["harnesses"] == list(HARNESSES))
    check("the installation's .rbtv/ holds mirror/, runtime/ and memory/",
          all((target / ".rbtv" / name).is_dir()
              for name in ("mirror", "runtime", "memory")))
    check("re-install is idempotent",
          do_install(target, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                     dry_run=False)["written"] == [])
    toml_ws = tmp / "ws-codex-limit"
    (toml_ws / ".codex").mkdir(parents=True)
    (toml_ws / ".codex/config.toml").write_text("[features]\nhooks = true\n",
                                               encoding="utf-8")
    do_install(toml_ws, catalog, ["fixmod/goodcomp"], ["codex"], dry_run=False)
    toml = (toml_ws / ".codex/config.toml").read_text(encoding="utf-8")
    check("the Codex AGENTS.md limit is a root key, above the owner's tables",
          toml.startswith(f"# {FENCE_ID}:start codex-limits\n"
                          "project_doc_max_bytes = 131072\n")
          and "[features]\nhooks = true\n" in toml
          and toml.index("[features]") < toml.index("[mcp_servers.fixmcp]"),
          toml)
    check("…and two blocks in one TOML file are stable across runs",
          do_install(toml_ws, catalog, ["fixmod/goodcomp"], ["codex"],
                     dry_run=False)["shared_written"] == []
          and (toml_ws / ".codex/config.toml").read_text(encoding="utf-8") == toml)
    before_preview = {p.relative_to(target).as_posix(): p.read_bytes()
                      for p in target.rglob("*") if p.is_file()}
    preview = do_install(target, catalog, ["fixmod/goodcomp"],
                         list(HARNESSES), dry_run=True)
    after_preview = {p.relative_to(target).as_posix(): p.read_bytes()
                     for p in target.rglob("*") if p.is_file()}
    planned = preview["planned_changes"]
    check("identical reinstall previews zero file and shared changes",
          not (planned["write_files"] or planned["delete_files"]
               or planned["write_shared_files"]
               or planned["delete_shared_files"])
          and planned["unchanged_files"]
          and planned["unchanged_shared_files"]
          and before_preview == after_preview,
          str(planned))
    changed_file = target / ".claude/skills/fixskill/SKILL.md"
    changed_shared = target / ".claude/settings.json"
    old_file, old_shared = changed_file.read_bytes(), changed_shared.read_bytes()
    changed_file.write_text("stale harness file\n", encoding="utf-8")
    changed_shared.write_text('{"foreignKey": 1}\n', encoding="utf-8")
    changed_before = (changed_file.read_bytes(), changed_shared.read_bytes())
    changed_preview = do_install(target, catalog, ["fixmod/goodcomp"],
                                 list(HARNESSES), dry_run=True)
    changed_plan = changed_preview["planned_changes"]
    check("preview names changed file and shared setting without writing",
          ".claude/skills/fixskill/SKILL.md" in changed_plan["write_files"]
          and ".claude/settings.json" in changed_plan["write_shared_files"]
          and (changed_file.read_bytes(), changed_shared.read_bytes())
          == changed_before,
          str(changed_plan))
    changed_file.write_bytes(old_file)
    changed_shared.write_bytes(old_shared)

    overlap = tmp / "ws-shared-file-overlap"
    overlap.mkdir()
    overlap_files = {"CLAUDE.md": "Owner instructions\n"}
    overlap_claims = [{"path": "CLAUDE.md", "fmt": "text",
                       "comment": "<!--", "key": None,
                       "value": "Managed instructions"}]
    overlap_preview = apply(overlap, overlap_files, overlap_claims, {}, True)
    overlap_plan = overlap_preview["planned_changes"]
    overlap_result = apply(overlap, overlap_files, overlap_claims, {}, False)
    overlap_body = (overlap / "CLAUDE.md").read_text(encoding="utf-8")
    check("shared preview renders over the planned file body",
          overlap_plan["write_files"] == ["CLAUDE.md"]
          and overlap_plan["write_shared_files"] == ["CLAUDE.md"]
          and overlap_result["written"] == ["CLAUDE.md"]
          and overlap_result["shared_written"] == ["CLAUDE.md"]
          and overlap_body.startswith("Owner instructions\n")
          and f"{FENCE_ID}:start" in overlap_body,
          str(overlap_plan))

    # A booked shared file the file plan itself deletes (a full uninstall of
    # a mirrored root): absent-to-absent is NO remaining shared action, never
    # "unchanged" beside the same name under deleted — and the receipt keys
    # stay exactly the ones apply() always produced.
    shrink = tmp / "ws-shared-file-plan-deletes-it"
    shrink.mkdir()
    (shrink / "AGENTS.md").write_text(
        "<!-- GENERATED by install.py — DO NOT EDIT. -->\n\n"
        f"<!-- {FENCE_ID}:start rule fixmod/goodcomp#fixrule -->\n"
        "managed\n"
        f"<!-- {FENCE_ID}:end rule fixmod/goodcomp#fixrule -->\n",
        encoding="utf-8")
    shrink_state = {"components": {},
                    "shared_claims": ["AGENTS.md::#block:rule fixmod/goodcomp"
                                      "#fixrule"],
                    "guidance_files": ["AGENTS.md"]}
    shrink_preview = apply(shrink, {}, [], shrink_state, True)
    shrink_plan = shrink_preview["planned_changes"]
    shrink_real = apply(shrink, {}, [], shrink_state, False)
    check("a shared file the file plan deletes is reported once, as deleted",
          shrink_plan["delete_files"] == ["AGENTS.md"]
          and shrink_plan["unchanged_shared_files"] == []
          and shrink_plan["write_shared_files"] == []
          and shrink_plan["delete_shared_files"] == []
          and shrink_real["deleted"] == ["AGENTS.md"]
          and shrink_real["shared_skipped"] == []
          and not (shrink / "AGENTS.md").exists(),
          f"preview={shrink_plan} real={shrink_real}")
    check("the corrected shared classification keeps the receipt's keys",
          set(shrink_preview) == {"written", "skipped", "deleted", "shared",
                                  "adopted", "adopted_sections", "released",
                                  "shared_removed", "dry_run",
                                  "planned_changes"}
          and set(shrink_plan) == {"write_files", "delete_files",
                                   "unchanged_files", "write_shared_files",
                                   "delete_shared_files",
                                   "unchanged_shared_files"}
          and set(shrink_real) == {"written", "skipped", "deleted", "shared",
                                   "shared_removed", "shared_written",
                                   "shared_deleted", "shared_skipped",
                                   "adopted", "adopted_sections", "released",
                                   "dry_run"},
          str(sorted(set(shrink_real))))
    ctx.keep(locals())


def red_unknown_method(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nred arm — invalid file")
    try:
        do_install(target, catalog, ["badmod/badcomp"], list(HARNESSES),
                   dry_run=False)
        check("an invalid file refuses", False, "no refusal raised")
    except Refuse as exc:
        check("an invalid file refuses", exc.code == "file-invalid", exc.code)
        check("invalid-file refusal wrote nothing",
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
        {"mcpServers": {"fixmcp": {"url": "https://squatter.invalid"}}}),
        encoding="utf-8")
    before = {p.relative_to(fresh).as_posix(): p.read_text(encoding="utf-8")
              for p in fresh.rglob("*") if p.is_file()}
    try:
        do_install(fresh, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False)
        check("collision refuses", False, "no refusal raised")
    except Refuse as exc:
        check("collision refuses", exc.code == "collision", exc.code)
        check("both the file AND the shared key are named",
              ".claude/rules/fixrule.md" in exc.message
              and ".mcp.json::mcpServers." + "fixmcp" in exc.message,
              exc.message)
    after = {p.relative_to(fresh).as_posix(): p.read_text(encoding="utf-8")
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
    check("7.622 — setup: the fixture HAS rows to print",
          bool(rr_dry["report"]["no_realization"]),
          str(rr_dry["report"]))
    dry_flat = " ".join(dry_out.split())
    check("7.622 — every no-realization row is named in the dry run",
          all(f"{row['harness']} cannot use " in dry_flat
              and f"{row['component']}#{row['part']}" in dry_flat
              for row in rr_dry["report"]["no_realization"])
          and dry_out.index("cannot use") < dry_out.index("\nNotes")
          if "\nNotes" in dry_out else "cannot use" in dry_out,
          dry_out)
    check("7.622 — the dry run carries the SAME row count as the real run",
          sum(1 for ln in dry_out.splitlines() if ln.startswith("  · "))
          == sum(1 for ln in real_out.splitlines()
                 if ln.startswith("  · ")),
          f"dry={dry_out}\nreal={real_out}")
    check("7.622 — planned rows read as planned, real rows as done",
          "no file would be written" in dry_out
          and "no file was written" in real_out
          and "Would refresh:" in dry_out
          and not dry_out.startswith("Installed:"),
          dry_out + "\n=====\n" + real_out)
    check("7.622 — the JSON shape is untouched by the printing change",
          set(rr_dry["report"]) == set(rr_real["report"])
          and rr_dry["report"]["no_realization"]
          == rr_real["report"]["no_realization"],
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
          all((target / rel).read_text(encoding="utf-8") == body
              for rel, body in legacy.items()))
    check("foreign JSON keys survive, ours are gone",
          json.loads((target / ".claude/settings.json").read_text(encoding="utf-8"))
          == {"foreignKey": 1}
          and json.loads((target / ".mcp.json").read_text(encoding="utf-8"))
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
