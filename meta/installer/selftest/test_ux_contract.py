"""Public command contracts shared by humans and unattended callers."""
from __future__ import annotations

import contextlib
import io
import json
import shlex
from unittest.mock import patch

from lib import commands
from lib.constants import STATE_REL, _RUNTIME
from lib.recovery import shell_quote
from lib.shared_links import owner_file


def public_contract(ctx) -> None:
    catalog = ctx.frame()[0]
    target = ctx.tmp / "public command workspace"
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
        assert retry.startswith("rbtv install ")
        lexer = shlex.shlex(retry[len("rbtv install "):], posix=True)
        lexer.whitespace_split = True
        lexer.escape = ""  # PowerShell's single-quoted Windows paths keep backslashes
        return list(lexer)

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
              and exact["scope"] == typed["scope"] == "items"
              and [r["id"] for r in exact["items"]]
              == ["fixmod/goodcomp#fixskill"]
              and all(r["module"] == "fixmod" for r in typed["items"]))
    _, searched = run("search", "fixskill")
    ctx.check("UX-search-is-broad-item-discovery",
              searched["scope"] == "items"
              and searched["items"][0]["id"] == "fixmod/goodcomp#fixskill")
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
              status["installation"]["installed_items"] == 0
              and status["installation"]["health"] == "not_checked"
              and status["source_catalog"]["items"] > 0)
    _, first = run("list", "fixmod/goodcomp", "--limit", "2")
    _, second = run("list", "fixmod/goodcomp", "--limit", "2", "--offset", "2")
    ctx.check("UX-bounded-pagination", first["returned"] == 2
              and first["total"] > 2 and second["offset"] == 2
              and not ({x["id"] for x in first["items"]}
                       & {x["id"] for x in second["items"]})
              and "--offset 2" in first["next"])
    _, alias = run("ls", "fixmod/goodcomp", "--limit", "2")
    ctx.check("UX-ls-identical-to-list", alias == first)
    _, details = run("show", "fixskill", "--type", "skill")
    ctx.check("UX-show-public-resolver", details["selection"]["id"]
              == "fixmod/goodcomp#fixskill"
              and details["selection"]["unit_id"] == "fixskill"
              and details["selection"]["scope"] == "item"
              and details["selection"]["type"] == "skill"
              and "method" not in details["selection"])
    code, unknown = run("show", "no-such-item-7z")
    ctx.check("UX-unknown-name-has-targeted-recovery",
              code == 1 and unknown["error"]["code"] == "name-unknown"
              and unknown["next"].startswith("rbtv install list --target ")
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
    for old, new in (("harness", "--harness"),
                     ("artifact", "--guidance")):
        value = "codex" if old == "harness" else "none"
        code, moved = run("set", old, value, "--dry-run")
        retry = retry_args(moved["next"])
        followed_code, followed = run(*retry, explicit=False)
        ctx.check(f"UX-retired-set-{old}-has-executable-quoted-retry",
                  code == 2 and moved["error"]["code"] == "grammar-retired"
                  and retry[:2] == ["configure", new]
                  and retry[2] == value
                  and str(target) in retry
                  and followed_code == 0 and followed["dry_run"]
                  and (target / STATE_REL).read_bytes() == before_retired,
                  str(moved))
    code, old_flag = run("list", "fixmod", "--kind=rule")
    flag_retry = retry_args(old_flag["next"])
    followed_code, filtered = run(*flag_retry, explicit=False)
    ctx.check("UX-retired-option-equals-form-has-executable-retry",
              code == 2 and old_flag["error"]["code"] == "grammar-retired"
              and "--type=rule" in flag_retry
              and followed_code == 0 and filtered["scope"] == "items"
              and (target / STATE_REL).read_bytes() == before_retired)
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
              installed_item["next"] == f"rbtv install doctor --target {tq}",
              str(installed_item))
    ctx.check("UX-show-installed-item-real-receiving-tools",
              installed_item["selection"]["harnesses"] == ["codex"],
              str(installed_item["selection"].get("harnesses")))
    part0 = installed_item["selection"]["units"][0]
    src = part0.get("source_path", "")
    ctx.check("UX-show-item-unambiguous-source-path",
              bool(src) and "/" in src.replace("\\", "/")
              and src != part0.get("entry_point"),
              src)
    _, comp_detail = run("show", "fixmod/goodcomp")
    ctx.check("UX-show-component-next-drills-into-real-item",
              comp_detail["next"].startswith("rbtv install show fixmod/goodcomp#")
              and any(comp_detail["next"] == f"rbtv install show {p['key']} --target {tq}"
                      for p in comp_detail["selection"]["units"]),
              str(comp_detail))
    _, mod_detail = run("show", "fixmod")
    ctx.check("UX-show-module-next-drills-into-real-component",
              mod_detail["next"].startswith("rbtv install show fixmod/")
              and any(mod_detail["next"] == f"rbtv install show {c['id']} --target {tq}"
                      for c in mod_detail["selection"]["components"]),
              str(mod_detail))
    _, installed = run("list", "--installed")
    _, installed_alias = run("li")
    ctx.check("UX-installed-alias-identical", installed == installed_alias
              and [x["id"] for x in installed["items"]] == ["fixmod"])
    _, installed_module = run("list", "fixmod", "--installed")
    goodcomp = next(r for r in installed_module["items"]
                    if r["id"] == "fixmod/goodcomp")
    ctx.check("UX-installed-aggregate-retains-source-denominator",
              goodcomp["installed_items"] == 1
              and goodcomp["source_items"] > goodcomp["installed_items"])
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
              and not missing["items"][0]["source_available"]
              and missing["items"][0]["id"] == "fixmod/goodcomp#fixskill")
    code, guidance = run("update", "guidance", selected_catalog=gone_catalog)
    ctx.check("UX-source-missing-does-not-block-guidance-copy",
              code == 0 and guidance["scope"] == "guidance")
    code, scaffold = run("update", "scaffolding", selected_catalog=gone_catalog)
    ctx.check("UX-source-missing-blocks-scaffolding",
              code == 1 and scaffold["error"]["code"] == "component-vanished")
    code, removed = run("remove", "fixmod/goodcomp#fixskill",
                        selected_catalog=gone_catalog)
    ctx.check("UX-vanished-item-removable", code == 0 and removed["ok"]
              and not (target / ".agents/skills/fixskill/SKILL.md").exists())
    code, repeat = run("remove", "fixskill")
    ctx.check("UX-repeat-removal-is-no-op", code == 0 and repeat["ok"])
    with patch.dict("os.environ", {"IGNITE_AGENT_HOME": ""}):
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

    target = ctx.tmp / "deleted owner workspace"
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
