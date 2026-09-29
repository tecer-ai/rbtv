"""Public command contracts shared by humans and unattended callers."""
from __future__ import annotations

import contextlib
import io
import json
from unittest.mock import patch

from lib import commands
from lib.constants import STATE_REL, _RUNTIME
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
    _, first = run("list", "--limit", "2")
    _, second = run("list", "--limit", "2", "--offset", "2")
    ctx.check("UX-bounded-pagination", first["returned"] == 2
              and first["total"] > 2 and second["offset"] == 2
              and not ({x["id"] for x in first["items"]}
                       & {x["id"] for x in second["items"]})
              and "--offset 2" in first["next"])
    _, alias = run("ls", "--limit", "2")
    ctx.check("UX-ls-identical-to-list", alias == first)
    _, details = run("show", "fixskill", "--kind", "skill")
    ctx.check("UX-show-public-resolver", details["selection"]["id"]
              == "fixmod/goodcomp#fixskill"
              and details["selection"]["part_id"] == "fixskill")
    code, usage = run("show")
    ctx.check("UX-parser-error-is-JSON", code == 2
              and usage.get("refusal", {}).get("code") == "usage")
    code, setup = run("add", "fixskill")
    ctx.check("UX-first-add-explains-both-settings", code == 1
              and all(flag in setup["refusal"]["message"]
                      for flag in ("--harness", "--guidance", "--target")))
    code, preview = run("add", "fixskill", "--harness", "codex",
                        "--guidance", "none", "--dry-run")
    ctx.check("UX-read-and-preview-write-nothing", code == 0
              and preview["dry_run"] and not list(target.rglob("*")))
    for attempt in range(2):
        code, added = run("add", "fixskill", "--harness", "codex",
                          "--guidance", "none")
        ctx.check(f"UX-add-repeat-{attempt}", code == 0 and added["ok"])
    _, installed = run("list", "--installed")
    _, installed_alias = run("li")
    ctx.check("UX-installed-alias-identical", installed == installed_alias
              and [x["id"] for x in installed["items"]]
              == ["fixmod/goodcomp#fixskill"])
    before = (target / STATE_REL).read_bytes()
    code, refusal = run("remove", "--all")
    ctx.check("UX-broad-removal-refuses-with-preview", code == 1
              and refusal["refusal"]["code"] == "confirmation-required"
              and "--yes" in refusal["refusal"]["preview"]["next"]
              and (target / STATE_REL).read_bytes() == before)
    gone_catalog = {key: value for key, value in catalog.items()
                    if key != "fixmod/goodcomp"}
    _, missing = run("list", "--installed", selected_catalog=gone_catalog)
    ctx.check("UX-vanished-item-stays-visible", missing["returned"] == 1
              and not missing["items"][0]["source_available"]
              and missing["items"][0]["id"] == "fixmod/goodcomp#fixskill")
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
              and invalid["refusal"]["code"] == "agent-home-invalid"
              and override == 0)
    with patch.dict(commands._HANDLERS, {
            "status": lambda *a, **k: (_ for _ in ()).throw(
                PermissionError("fixture write refused"))}):
        code, failed = run("status")
    ctx.check("UX-IO-error-is-JSON", code == 1
              and failed["refusal"]["code"] == "io-error"
              and "doctor" in failed["refusal"]["next"])

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
                  and refused["refusal"]["code"] == "confirmation-required"
                  and registry.exists() and not target.exists())
        code, released = run("remove", "--all", "--yes")
    ctx.check("UX-orphan-claim-released-even-with-shortcut-gone", code == 0
              and released["report"]["path"]["released"] == ["missing-shortcut"]
              and not registry.exists() and not target.exists())
