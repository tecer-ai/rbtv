"""Public command contracts shared by humans and unattended callers."""
from __future__ import annotations

import contextlib
import io
import json
import re
import shlex
from unittest.mock import patch

from lib import commands, help_pages, listing, present
from lib.constants import STATE_REL, _RUNTIME
from lib.recovery import shell_quote
from lib.report import print_result
from lib.shared_links import owner_file


def public_contract(ctx) -> None:
    catalog = ctx.frame()[0]
    target = ctx.tmp / "public command installation"
    target.mkdir()

    def run(*args, selected_catalog=None, explicit=True):
        argv = [*args, "--json"]
        if explicit:
            argv.extend(("--target", str(target)))
        out, err = io.StringIO(), io.StringIO()
        with patch.object(commands, "scan_all", return_value=(
                catalog if selected_catalog is None else selected_catalog, [])), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = commands.main(argv)
        try:
            data = json.loads(out.getvalue())
        except ValueError:
            ctx.check("UX-one-JSON-response", False, out.getvalue() + err.getvalue())
            return code, {}
        ctx.check("UX-no-prose-on-JSON-stderr", not err.getvalue(), err.getvalue())
        return code, data

    print("\nUX — public noninteractive command contracts")
    def retry_args(retry: str) -> list[str]:
        assert retry.startswith("rbtv ")
        lexer = shlex.shlex(retry[len("rbtv "):], posix=True)
        lexer.whitespace_split = True
        lexer.escape = ""  # PowerShell's single-quoted Windows paths keep backslashes
        return list(lexer)

    # --full: a list shows a description's first sentence; --full shows it whole,
    # in the JSON value and, as one labeled block per row, in the text.
    long_text = "First sentence of a description. " + "More words. " * 20 + "The last sentence."
    ctx.check("UX-full — a description is its first sentence by default",
              listing._description(long_text, False) == "First sentence of a description.")
    ctx.check("UX-full — --full gives the whole description on one line",
              listing._description(long_text + "\n", True) == long_text)
    code, plain = run("list", "--type", "skill")
    code_full, whole = run("list", "--type", "skill", "--full")
    ctx.check("UX-full — --full changes no row of the list",
              code == code_full == 0 and [row["id"] for row in plain["files"]] == [row["id"] for row in whole["files"]],
              str(whole)[:200])
    shown = io.StringIO()
    with patch.object(commands, "scan_all", return_value=(catalog, [])), contextlib.redirect_stdout(shown):
        commands.main(["list", "--type", "skill", "--full", "--target", str(target)])
    ctx.check("UX-full — the text is one labeled block per row, with no cut description",
              "\nDescription: " in shown.getvalue() and "…" not in shown.getvalue(), shown.getvalue()[:300])
    for verb in (("search", "fix", "--full"), ("show", "fixmod", "--full")):
        code, _ = run(*verb)
        ctx.check(f"UX-full — rbtv {verb[0]} takes --full", code == 0, str(code))

    code, searched_set = run("search", "set")
    ctx.check("UX-retired-verb-word-is-a-valid-search-term",
              code == 0 and searched_set["query"] == "set")
    code, named_set = run("show", "set")
    ctx.check("UX-retired-verb-word-is-a-valid-item-name",
              code == 1 and named_set["error"]["code"] != "grammar-retired")
    set_target = ctx.tmp / "set"
    set_target.mkdir()
    out = io.StringIO()
    with patch.object(commands, "scan_all", return_value=(catalog, [])), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        set_target_code = commands.main(
            ["status", "--json", "--target", str(set_target)])
    set_target_data = json.loads(out.getvalue())
    ctx.check("UX-retired-verb-word-is-a-valid-target-path",
              set_target_code == 0
              and set_target_data["target"] == str(set_target.resolve())
              and not list(set_target.rglob("*")))
    code, selftest_json = run("selftest", explicit=False)
    ctx.check("UX-selftest-json-refuses-purely",
              code == 2 and selftest_json["error"]["code"] == "usage")
    _, modules = run("list")
    _, components = run("list", "fixmod")
    _, exact = run("list", "fixskill")
    _, typed = run("list", "fixmod", "--type", "skill")
    ctx.check("UX-exact-hierarchy-and-type-depth",
              modules["scope"] == "modules"
              and components["scope"] == "components"
              and exact["scope"] == typed["scope"] == "files"
              and [r["id"] for r in exact["files"]]
              == ["fixmod/goodcomp#fixskill"]
              and all(r["module"] == "fixmod" for r in typed["files"]))
    _, searched = run("search", "fixskill")
    ctx.check("UX-search-is-broad-item-discovery",
              searched["scope"] == "files"
              and searched["files"][0]["id"] == "fixmod/goodcomp#fixskill")
    _, filtered_page = run("list", "fixmod", "--type", "rule",
                           "--limit", "1")
    ctx.check("UX-continuation-keeps-exact-scope-and-type",
              filtered_page["total"] > 1
              and f"list {shell_quote('fixmod')}" in filtered_page["next"]
              and f"--type {shell_quote('rule')}" in filtered_page["next"]
              and "--offset 1" in filtered_page["next"],
              str(filtered_page))
    _, module_detail = run("show", "fixmod")
    ctx.check("UX-show-module-summary",
              module_detail["selection"]["scope"] == "module"
              and module_detail["selection"]["components"])
    _, status = run("status")
    ctx.check("UX-status-separates-installed-from-source",
              status["installation"]["installed_files"] == 0
              and status["installation"]["health"] == "not_checked"
              and status["source_catalog"]["files"] > 0)
    _, first = run("list", "fixmod/goodcomp", "--limit", "2")
    _, second = run("list", "fixmod/goodcomp", "--limit", "2", "--offset", "2")
    ctx.check("UX-bounded-pagination", first["returned"] == 2
              and first["total"] > 2 and second["offset"] == 2
              and not ({x["id"] for x in first["files"]}
                       & {x["id"] for x in second["files"]})
              and "--offset 2" in first["next"])
    _, alias = run("ls", "fixmod/goodcomp", "--limit", "2")
    ctx.check("UX-ls-identical-to-list", alias == first)
    _, details = run("show", "fixskill", "--type", "skill")
    ctx.check("UX-show-public-resolver", details["selection"]["id"]
              == "fixmod/goodcomp#fixskill"
              and details["selection"]["file_id"] == "fixskill"
              and details["selection"]["scope"] == "file"
              and details["selection"]["type"] == "skill"
              and "method" not in details["selection"])
    code, unknown = run("show", "no-such-item-7z")
    ctx.check("UX-unknown-name-has-targeted-recovery",
              code == 1 and unknown["error"]["code"] == "name-unknown"
              and unknown["next"].startswith("rbtv list --target ")
              and str(target) in unknown["next"])
    code, usage = run("show")
    ctx.check("UX-parser-error-is-JSON", code == 2
              and usage.get("error", {}).get("code") == "usage")
    code, setup = run("add", "fixskill")
    ctx.check("UX-first-add-explains-both-settings", code == 1
              and all(flag in setup["error"]["message"]
                      for flag in ("--harness", "--guidance", "--target")))
    code, preview = run("add", "fixskill", "--harness", "codex",
                        "--guidance", "none", "--dry-run")
    ctx.check("UX-read-and-preview-write-nothing", code == 0
              and preview["dry_run"] and not list(target.rglob("*")))
    planned0 = preview["planned_changes"]
    ctx.check("UX-fresh-add-preview-shows-real-planned-changes",
              len(planned0["write_files"]) == 1
              and "fixskill" in planned0["write_files"][0]
              and not planned0["delete_files"]
              and not planned0["unchanged_files"],
              str(planned0))
    for attempt in range(2):
        code, added = run("add", "fixskill", "--harness", "codex",
                          "--guidance", "none")
        ctx.check(f"UX-add-repeat-{attempt}", code == 0 and added["ok"])
    before_retired = (target / STATE_REL).read_bytes()
    for old, value in (("set", "--harness"), ("harness", "codex"),
                       ("artifact", "none")):
        code, retired = run(old, value, "--dry-run")
        ctx.check(f"UX-retired-verb-{old}-is-wrong-usage-without-a-moved-line",
                  code == 2 and retired["error"]["code"] == "usage"
                  and "invalid choice" in retired["error"]["message"]
                  and "moved" not in str(retired)
                  and (target / STATE_REL).read_bytes() == before_retired,
                  str(retired))
    code, old_flag = run("list", "fixmod", "--kind=rule")
    ctx.check("UX-retired-option-is-refused-as-unknown",
              code == 2 and old_flag["error"]["code"] == "usage"
              and "--kind=rule" in old_flag["error"]["message"]
              and "moved" not in str(old_flag)
              and (target / STATE_REL).read_bytes() == before_retired,
              str(old_flag))
    _, reinstall_preview = run("add", "fixskill", "--harness", "codex",
                               "--guidance", "none", "--dry-run")
    planned1 = reinstall_preview["planned_changes"]
    ctx.check("UX-identical-reinstall-preview-shows-zero-changes",
              not planned1["write_files"] and not planned1["delete_files"]
              and not planned1["write_shared_files"]
              and not planned1["delete_shared_files"]
              and len(planned1["unchanged_files"]) == 1
              and "fixskill" in planned1["unchanged_files"][0],
              str(planned1))
    tq = shell_quote(str(target))
    _, installed_item = run("show", "fixskill", "--type", "skill")
    ctx.check("UX-show-installed-item-next-is-doctor-not-remove",
              installed_item["next"] == f"rbtv doctor --target {tq}",
              str(installed_item))
    ctx.check("UX-show-installed-item-real-receiving-tools",
              installed_item["selection"]["harnesses"] == ["codex"],
              str(installed_item["selection"].get("harnesses")))
    part0 = installed_item["selection"]["files"][0]
    src = part0.get("source_path", "")
    ctx.check("UX-show-item-unambiguous-source-path",
              bool(src) and "/" in src.replace("\\", "/")
              and src != part0.get("entry_point"),
              src)
    _, comp_detail = run("show", "fixmod/goodcomp")
    ctx.check("UX-show-component-next-drills-into-real-item",
              comp_detail["next"].startswith("rbtv show fixmod/goodcomp#")
              and any(comp_detail["next"] == f"rbtv show {p['key']} --target {tq}"
                      for p in comp_detail["selection"]["files"]),
              str(comp_detail))
    _, mod_detail = run("show", "fixmod")
    ctx.check("UX-show-module-next-drills-into-real-component",
              mod_detail["next"].startswith("rbtv show fixmod/")
              and any(mod_detail["next"] == f"rbtv show {c['id']} --target {tq}"
                      for c in mod_detail["selection"]["components"]),
              str(mod_detail))
    _, installed = run("list", "--installed")
    _, installed_alias = run("li")
    _, component_listing = run("list", "fixmod/goodcomp")
    ctx.check("UX-installed-alias-identical", installed == installed_alias)
    ctx.check("UX-installed-lists-files — `list --installed` with no NAME is one table of "
              "the installed files, with the fields of a component's listing, in the window",
              installed["scope"] == "files"
              and [x["id"] for x in installed["files"]] == ["fixmod/goodcomp#fixskill"]
              and installed["files"][0] == next(
                  row for row in component_listing["files"]
                  if row["id"] == "fixmod/goodcomp#fixskill")
              and installed["files"][0]["type"] == "skill"
              and installed["files"][0]["installed"] is True
              and installed["total"] == installed["returned"] == 1
              and installed["limit"] == 20 and installed["offset"] == 0, str(installed))
    code, no_hit = run("search", "fixskilz")
    ctx.check("UX-search-no-hit — a search with no hit has no row and names the nearest words",
              code == 0 and no_hit["files"] == [] and no_hit["total"] == 0
              and "fixskill" in no_hit["did_you_mean"]
              and 0 < len(no_hit["did_you_mean"]) <= 5
              and "did_you_mean" not in searched, str(no_hit))
    _, far_word = run("search", "zzzzqqqq")
    ctx.check("UX-search-no-close-word — a searched word with no close word gets none",
              far_word["total"] == 0 and far_word["did_you_mean"] == [], str(far_word))
    _, near = run("show", "fixskilz")
    _, far = run("show", "zzzzqqqq")
    _, near_removal = run("remove", "fixskilz")
    _, not_installed = run("remove", "fixrulz")
    ctx.check("UX-refusal-close-names — a refusal suggests only close names, says when none "
              "is close, and on remove suggests only installed names",
              any("fixskill" in s["id"] for s in near["error"]["suggestions"])
              and far["error"]["suggestions"] == []
              and "No close name exists." in far["error"]["message"]
              and far["next"] == f"rbtv list --target {tq}"
              and any("fixskill" in s["id"] for s in near_removal["error"]["suggestions"])
              and not_installed["error"]["suggestions"] == []
              and any("fixrule" in s["id"] for s in run("show", "fixrulz")[1]["error"]["suggestions"]),
              str((near, far, near_removal, not_installed)))
    ctx.check("UX-tool-meaning — a tool is described as a runnable CLI wherever types are listed",
              present.TYPE_MEANING["tool"] == "Runnable CLI exposed through a command shortcut."
              and not any("Runnable program" in page for page in help_pages.PAGES.values())
              and sum("Runnable CLI exposed through a command shortcut." in page
                      for page in help_pages.PAGES.values()) >= 5)
    _, installed_module = run("list", "fixmod", "--installed")
    goodcomp = next(r for r in installed_module["files"]
                    if r["id"] == "fixmod/goodcomp")
    ctx.check("UX-installed-aggregate-retains-source-denominator",
              goodcomp["installed_files"] == 1
              and goodcomp["source_files"] > goodcomp["installed_files"])
    before = (target / STATE_REL).read_bytes()
    code, refusal = run("remove", "--all")
    ctx.check("UX-broad-removal-refuses-with-preview", code == 1
              and refusal["error"]["code"] == "confirmation-required"
              and "--yes" in refusal["error"]["preview"]["next"]
              and (target / STATE_REL).read_bytes() == before)
    gone_catalog = {key: value for key, value in catalog.items()
                    if key != "fixmod/goodcomp"}
    _, missing = run("list", "fixmod/goodcomp", "--installed", selected_catalog=gone_catalog)
    ctx.check("UX-vanished-item-stays-visible", missing["returned"] == 1
              and not missing["files"][0]["source_available"]
              and missing["files"][0]["id"] == "fixmod/goodcomp#fixskill")
    code, guidance = run("update", "guidance", selected_catalog=gone_catalog)
    ctx.check("UX-source-missing-does-not-block-guidance-copy",
              code == 0 and guidance["scope"] == "guidance")
    code, scaffold = run("update", "scaffolding", selected_catalog=gone_catalog)
    ctx.check("UX-source-missing-scaffolding-removes-selection",
              code == 0 and scaffold["ok"]
              and scaffold["removed"] == ["fixmod/goodcomp#fixskill"]
              and not (target / ".agents/skills/fixskill/SKILL.md").exists())
    code, repeat = run("remove", "fixskill")
    ctx.check("UX-repeat-removal-is-no-op", code == 0 and repeat["ok"])
    with patch.dict("os.environ", {"RBTV_AGENT_HOME": ""}):
        code, invalid = run("status", explicit=False)
        override, _ = run("status")
    ctx.check("UX-invalid-agent-home-never-falls-back", code == 1
              and invalid["error"]["code"] == "agent-home-invalid"
              and override == 0)
    with patch.dict(commands._HANDLERS, {
            "status": lambda *a, **k: (_ for _ in ()).throw(
                PermissionError("fixture write refused"))}):
        code, failed = run("status")
    ctx.check("UX-IO-error-is-JSON", code == 1
              and failed["error"]["code"] == "io-error"
              and "doctor" in failed["next"])
    ctx.check("UX-IO-error-changed-is-unknown-not-false",
              failed.get("changed", False) is None, str(failed))

    target = ctx.tmp / "deleted owner installation"
    bindir = ctx.tmp / "public ownership" / "bin"
    registry = owner_file(bindir)
    registry.parent.mkdir()
    registry.write_text(json.dumps({"schema": 1, "links": {
        "missing-shortcut": {"target": str(ctx.tree / "missing-tool.py"),
                             "owners": [str(target)]}}}), encoding="utf-8")
    with patch.dict(_RUNTIME, {"bin": bindir}):
        code, refused = run("remove", "--all")
        ctx.check("UX-orphan-cleanup-needs-confirmation", code == 1
                  and refused["error"]["code"] == "confirmation-required"
                  and registry.exists() and not target.exists())
        code, released = run("remove", "--all", "--yes")
    ctx.check("UX-orphan-claim-released-even-with-shortcut-gone", code == 0
              and released["report"]["path"]["released"] == ["missing-shortcut"]
              and not registry.exists() and not target.exists())


def result_screens(ctx) -> None:
    """Human result screens through the public command path: empty labels,
    exact-ID next steps, a failure that never claims nothing changed, and
    the owner's large-batch case (compact by default, --details complete,
    every warning kept)."""
    catalog = ctx.frame()[0]
    target = ctx.tmp / "result screens"
    target.mkdir()

    def text(*argv, columns="100"):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(commands, "scan_all", return_value=(catalog, [])), \
                patch.dict("os.environ", {"COLUMNS": columns}), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = commands.main([*argv, "--target", str(target)])
        return code, out.getvalue(), err.getvalue()

    def agent_text(*argv, columns="100"):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(commands, "scan_all", return_value=(catalog, [])), \
                patch.dict("os.environ", {"COLUMNS": columns}), \
                patch("lib.commands.Path.cwd", return_value=target), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = commands.main(argv)
        return code, out.getvalue(), err.getvalue()

    print("\nRESULT — human result screens")
    _, empty, _ = text("list", "--installed")
    ctx.check("RESULT-empty-installed-list-says-so",
              "No installed files in this target." in empty, empty)
    code, no_hit_text, _ = text("search", "fixskilz")
    ctx.check("RESULT-search-no-hit-names-nearest-words",
              code == 0 and "0 matches" in no_hit_text
              and "No file or pack matches. Did you mean: fixskill" in no_hit_text
              and "fixmod/goodcomp#" not in no_hit_text, no_hit_text)
    _, far_text, _ = text("search", "zzzzqqqq")
    ctx.check("RESULT-search-no-close-word-says-only-no-match",
              "No file or pack matches.\n" in far_text and "Did you mean" not in far_text,
              far_text)
    _, found, _ = text("search", "fixture")
    next_line = found.rstrip().splitlines()[-1]
    ctx.check("RESULT-search-next-is-a-returned-exact-id",
              next_line.startswith("Next: rbtv show 'fixmod/goodcomp#")
              and "'fixture'" not in next_line, next_line)
    _, modules, _ = text("list")
    ctx.check("RESULT-list-next-is-never-a-placeholder",
              "MODULE" not in modules and "Next: rbtv show " in modules,
              modules)
    with patch.dict(commands._HANDLERS, {
            "status": lambda *a, **k: (_ for _ in ()).throw(
                PermissionError("fixture write refused"))}):
        code, _, failed = text("status")
    ctx.check("RESULT-io-failure-is-titled-failed-not-refused",
              code == 1 and failed.startswith("rbtv — failed\n\nFAILED [io-error]")
              and "may have applied" in " ".join(failed.split()), failed)

    agent_home = target / ".rbtv" / "agents" / "resultagent"
    agent_home.mkdir(parents=True)
    (agent_home / "agent.md").write_text("---\nname: resultagent\n---\n\nCheck.\n",
                                            encoding="utf-8")
    (agent_home / "agent.json").write_text(
        '{"name":"resultagent","description":"Result check.",'
        '"harness":"claude","model":"m1","effort":"high",'
        '"files":["fixskill"],"packs":[]}\n', encoding="utf-8")
    add = ["agent", "add", "resultagent", "--dry-run"]
    with patch("lib.agents.cast_catalog",
               return_value={"claude": {"m1": {"rungs": ["low", "high"], "selected": True}}}):
        _, agent_default, _ = agent_text(*add)
        _, agent_full, _ = agent_text(*add, "--details")
    skill = ".claude/skills/fixskill/SKILL.md"
    ctx.check("RESULT-agent-preview-reports-harness-files-default-and-details",
              "Harness files:    would write 2" in agent_default
              and "File list" not in agent_default and skill not in agent_default
              and "Add --details to this preview" in agent_default
              and "File list" in agent_full
              and f"\n    {skill}\n" in agent_full
              and "fixmod/goodcomp#fixskill" in agent_full
              and "guidance copies" not in agent_full,
              agent_default + "\n=====\n" + agent_full)
    ctx.check("RESULT-agent-preview-writes-nothing",
              not (agent_home / ".claude").exists())

    # The owner's removal example (owner-example.txt): 40 files, dozens of
    # unchanged files, 25 shortcuts kept for uncertain ownership.
    files = [f"core/mod{n // 5}#item{n:02d}" for n in range(40)]
    kept = [f"tool-{n:02d}" for n in range(25)]
    unchanged = [f".agents/skills/s{n:02d}/SKILL.md" for n in range(60)]
    big = {"_verb": "remove", "dry_run": False, "target": str(target),
           "source": "--target", "selected_files": files,
           "uninstalled": ["core/mod0"],
           "written": [".claude/skills/a/SKILL.md"],
           "deleted": [f".agents/behavior-rules/r{n:02d}.md" for n in range(30)],
           "skipped": unchanged, "shared_written": [".codex/config.toml"],
           "shared_deleted": [], "shared_skipped": [],
           "shared_removed": [f".mcp.json::[\"mcpServers\", \"m{n}\"]" for n in range(5)],
           "report": {"no_realization": [{"harness": "codex", "type": "reference",
                                          "component": "office/meeting", "part": f"r{n}"}
                                         for n in range(12)],
                      "path": {"legacy_preserved": kept},
                      "gitignore": {"claimed": True, "count": 71},
                      "guidance_mirror": {"basis": None, "targets": []}},
           "next": "rbtv status"}

    def render(columns: str, **extra) -> str:
        out = io.StringIO()
        with patch.dict("os.environ", {"COLUMNS": columns}), \
                contextlib.redirect_stdout(out):
            print_result({**big, **extra})
        return out.getvalue()

    compact = render("100")
    flat = " ".join(compact.split())
    full = render("100", _details=True)
    ctx.check("RESULT-large-batch-default-is-compact",
              len(compact.splitlines()) * 3 < len(full.splitlines())
              and "Removed: 40 files" in flat
              and files[-1] not in compact and unchanged[0] not in compact
              and "--details" in compact, compact)
    ctx.check("RESULT-large-batch-default-keeps-every-warning",
              "Warnings" in compact and all(name in compact for name in kept),
              compact)
    ctx.check("RESULT-large-batch-counts-match-data",
              "Files: wrote 1, deleted 30, 60 already up to date" in flat
              and "Shared files: changed 1, deleted 0, 0 already up to date"
              in flat, flat)
    ctx.check("RESULT-unusable-files-are-always-named-warnings",
              all(f"office/meeting#r{n}" in compact for n in range(12))
              and compact.index("cannot use") < compact.index("\nNotes"),
              compact)
    ctx.check("RESULT-routine-lists-are-counts-by-default",
              "File list" not in compact and "Files" not in compact.split("\n")
              and "released 5 claim(s)" in flat
              and "--dry-run --details" in flat, compact)
    ctx.check("RESULT-details-lists-every-item-and-file",
              all(f"\n  {i}\n" in full for i in files)
              and all(f"\n    {u}\n" in full for u in unchanged)
              and "\n\n  Already up to date (60)\n" in full
              and "Lists are counted" not in full, full[-800:])
    narrow = render("40")
    wide = [ln for ln in narrow.splitlines()
            if len(ln) > 40  # a lone ID, path or `command` may not fit
            and " " in re.sub(r"`[^`]*`", "X", ln.strip().lstrip("· "))
            and not ln.startswith(("Target:", "Next:"))]
    ctx.check("RESULT-narrow-prose-wraps-and-never-splits-ids",
              not wide and all(name in narrow for name in kept), "\n".join(wide))
