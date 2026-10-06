"""The command grammar, stable name selection and noninteractive removal."""
from __future__ import annotations

import contextlib
import io
import json

from discovery import Refuse, scan_all

from lib.constants import CATALOG_TYPES, STATE_REL
from lib.selection import (
    _sel,
    resolve_selection,
)
from lib.operations import do_install
from lib.parser import build_parser
from lib.commands import (
    _HANDLERS,
    _text_refusal,
    cmd_add,
    cmd_agent,
    cmd_doctor,
    cmd_update,
    cmd_li,
    cmd_ls,
    cmd_rm,
    main,
)
from lib.report import print_result
from lib.state import read_state

from .fixture import _component, _file_md
from .test_agents import _agent


def parser_selectors_index(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nCLI — parser, selectors, stable names, confirmation")
    for verb in ("add", "remove", "rm", "list", "status", "show",
                 "ls", "li",
                 "configure", "update", "search", "doctor", "selftest", "interactive"):
        argv = (["add", "-A"] if verb == "add" else
                ["show", "fixskill"] if verb == "show" else
                ["update", "guidance"] if verb == "update" else [verb])
        ns = build_parser().parse_args(argv)
        check(f"CLI-reach-{verb}", ns.verb == verb
              and verb in _HANDLERS, ns.verb)
    # No retired verb is recognised: each one is wrong usage, before any read.
    for verb in ("harness", "artifact", "set", "dupe-artifacts", "install"):
        try:
            build_parser().parse_args([verb])
            check(f"CLI-retired-verb-{verb}-is-unknown", False, "parsed")
        except Refuse as exc:
            check(f"CLI-retired-verb-{verb}-is-unknown",
                  exc.code == "usage" and "invalid choice" in exc.message
                  and "moved" not in exc.message, exc.message)
    empty = tmp / "ws-cli-empty"
    empty.mkdir()
    shown = {}
    for fmt in ("json", "text"):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            argv = ["show", "fixmod/goodcomp"] + (["--json"] if fmt == "json" else [])
            _HANDLERS["show"](build_parser().parse_args(argv), empty, catalog, [])
        shown[fmt] = out.getvalue()
    check("CLI-show-component — a component's dependencies are shown, in JSON and text",
          '"dependencies": []' in shown["json"]
          and "Dependencies: none" in shown["text"], shown["text"][:300])
    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        rc_ls = cmd_ls(build_parser().parse_args(["ls"]), empty, catalog, [])
        rc_li = cmd_li(build_parser().parse_args(["li"]), empty, catalog, [])
        try:
            cmd_update(build_parser().parse_args(["update", "guidance"]),
                     empty, catalog, [])
            rc_dupe = "ok"
        except Refuse as exc:
            rc_dupe = exc.code
        try:
            cmd_add(
                build_parser().parse_args(["add", "-c", "fixmod/goodcomp",
                                           "--dry-run"]),
                empty, catalog, [])
            rc_add = "ok"
        except Refuse as exc:
            rc_add = exc.code
        try:
            cmd_rm(build_parser().parse_args(
                ["rm", "-c", "fixmod/goodcomp", "--dry-run"]),
                   empty, catalog, [])
            rc_rm = "ok"
        except Refuse as exc:
            rc_rm = exc.code
        rc_doc = cmd_doctor(None, empty, catalog, [])
    check("CLI-reach-handler-ls", rc_ls == 0)
    check("CLI-reach-handler-li", rc_li == 0)
    check("CLI-reach-handler-dupe", rc_dupe == "installation-unrecorded",
          str(rc_dupe))
    check("CLI-reach-handler-add", rc_add == "setup-required",
          str(rc_add))
    check("CLI-reach-handler-rm", rc_rm == "ok", str(rc_rm))
    check("CLI-reach-handler-doctor", rc_doc == 0, str(rc_doc))

    # A whole word after one dash is no option: a type, and an exclusion, are
    # named with their long forms or the one-letter -x.
    for words in (["-xs"], ["-xr"], ["-xc"], ["-xa"], ["-nx", "skill"],
                  ["-nm", "fixmod"], ["-nc", "fixmod/goodcomp"]):
        try:
            build_parser().parse_args(["add", *words])
            got = None
        except Refuse as exc:
            got = exc.code
        check(f"CLI-no-two-letter-form — {words[0]} is refused", got is not None, str(got))

    # A comma list must be IDENTICAL to the repeated form, for every
    # selector — not just for -x, which is the only one that split before.
    # The red control is the pre-change parser: with `append` restored on
    # any of these four, the comma token arrives as one bogus id and the
    # equality fails.
    for _flag, _dest in (("-m", "module"), ("-c", "component"),
                         ("--exclude-module", "exclude_module"),
                         ("--exclude-component", "exclude_component"),
                         ("-x", "method"), ("--exclude-type", "exclude_method")):
        _v = ("skill", "rule") if _dest.endswith("method") else ("aa", "bb")
        _one = build_parser().parse_args(
            ["rm", _flag, ",".join(_v)])
        _two = build_parser().parse_args(
            ["rm", _flag, _v[0], _flag, _v[1]])
        check(f"CLI-comma-{_flag}",
              getattr(_one, _dest) == getattr(_two, _dest) == list(_v),
              f"{getattr(_one, _dest)} vs {getattr(_two, _dest)}")
    # Whitespace around a comma is a human typing a list, not a new id.
    check("CLI-comma-spaces",
          build_parser().parse_args(["rm", "-c", "aa, bb ,"]).component
          == ["aa", "bb"])

    SEL_CAT = {
        "meta/communication": {
            "module": "core", "component": "communication",
            "manifest": True, "kind": "component", "rows": [
                {"id": "audio", "method": "tool"},
                {"id": "plain-language", "method": "rule"},
                {"id": "non-technical-user", "method": "rule"},
                {"id": "concise-chat", "method": "rule"},
                {"id": "audio-aware", "method": "skill"}]},
        "core/cast": {
            "module": "core", "component": "sub-agents",
            "manifest": True, "kind": "component", "rows": [
                {"id": "cast", "method": "tool"},
                {"id": "sub-agents", "method": "skill"},
                {"id": "swarm", "method": "skill"},
                {"id": "panel", "method": "skill"}]},
        "web/browse": {
            "module": "web", "component": "browse",
            "manifest": True, "kind": "component", "rows": [
                {"id": "browse", "method": "skill"},
                {"id": "chrome-devtools", "method": "mcp-server"}]},
        "web/capture": {
            "module": "web", "component": "capture",
            "manifest": True, "kind": "component", "rows": [
                {"id": "capture", "method": "skill"}]},
        "_hub/skills/ponytail": {
            "module": "_hub", "component": "ponytail",
            "manifest": False, "kind": "hub"},
    }
    SEL_BOOK = {
        "meta/communication": {
            "module": "core", "component": "communication",
            "selected": {"audio-aware": {"method": "skill"},
                      "plain-language": {"method": "rule"}}},
        "web/browse": {"module": "web", "component": "browse"},
        "ghost/gone": {"module": "ghost", "component": "gone"},
    }

    def R(verb="add", book=None, **kw):
        return resolve_selection(_sel(verb=verb, **kw), SEL_CAT, book)

    check("SEL-and",
          R(module=["core"], method=["skill"]) == {
              "meta/communication#audio-aware",
              "core/cast#sub-agents",
              "core/cast#swarm",
              "core/cast#panel"})
    check("SEL-or",
          R(component=["meta/communication", "web/browse"],
            method=["skill", "rule"]) == {
              "meta/communication#plain-language",
              "meta/communication#non-technical-user",
              "meta/communication#concise-chat",
              "meta/communication#audio-aware",
              "web/browse#browse"})
    check("SEL-exclude",
          R(all=True, exclude_module=["core"], method=["skill"]) == {
              "web/browse#browse",
              "web/capture#capture",
              "_hub/skills/ponytail#ponytail"})
    # --exclude-type must SUBTRACT, not merely trigger the confirmation prompt.
    # Without this arm, neutering the method-exclusion filter left the whole
    # suite green: N-confirm asserts the prompt fired and that answering "n"
    # changed nothing, which passes whether or not the filter ever ran.
    _all_parts = R(all=True)
    _no_skill = R(all=True, exclude_method=["skill"])
    check("SEL-exclude-method — --exclude-type subtracts the method",
          _no_skill < _all_parts
          and "web/browse#browse" not in _no_skill
          and "_hub/skills/ponytail#ponytail" not in _no_skill
          and "meta/communication#plain-language" in _no_skill,
          f"kept={sorted(_no_skill - _all_parts)} "
          f"dropped={sorted(_all_parts - _no_skill)}")
    _all = R(all=True)
    _no_browse = R(all=True, exclude_component=["web/browse"])
    check("SEL-exclude-component — --exclude-component subtracts the component",
          _no_browse < _all
          and "web/browse#browse" not in _no_browse
          and "web/browse#chrome-devtools" not in _no_browse
          and "meta/communication#audio-aware" in _no_browse,
          f"dropped={sorted(_all - _no_browse)}")
    check("SEL-rm-booked",
          R(verb="rm", book=SEL_BOOK, component=["meta/communication"])
          == {"meta/communication#audio-aware",
              "meta/communication#plain-language"})
    try:
        R(component=["no/comp"])
        unk = "no refusal"
    except Refuse as exc:
        unk = exc.code
    check("SEL-refuse-unknown", unk == "component-unknown", unk)
    try:
        R(module=["core"], component=["web/browse"])
        empty_and = "no refusal"
    except Refuse as exc:
        empty_and = exc.code
    check("SEL-refuse-empty-and", empty_and == "selection-empty", empty_and)
    not_in = R(verb="rm", book=SEL_BOOK, component=["web/capture"])
    check("SEL-not-installed-is-no-op", not not_in, str(not_in))

    # Stable names replace listing-dependent numeric slots.
    for token in ("1", "1-3"):
        try:
            R(component=[token])
            code = "no refusal"
        except Refuse as exc:
            code = exc.code
        check(f"SEL-retired-numeric-{token}", code == "index-retired", code)
    check("SEL-direct-part-name",
          R(names=["audio-aware"]) == {"meta/communication#audio-aware"})
    check("SEL-full-component-name",
          R(names=["web/browse"]) == {"web/browse#browse",
                                      "web/browse#chrome-devtools"})
    check("SEL-component-short-explicit",
          R(component=["capture"]) == {"web/capture#capture"})
    check("SEL-direct-name-is-part",
          R(names=["capture"]) == {"web/capture#capture"})
    duplicate = dict(SEL_CAT)
    duplicate["other/capture"] = {
        "module": "other", "component": "capture",
        "manifest": True, "kind": "component",
        "rows": [{"id": "capture", "method": "skill"}]}
    try:
        resolve_selection(_sel(names=["capture"]), duplicate)
        ambiguous = "no refusal"
    except Refuse as exc:
        ambiguous = exc.code
    check("SEL-ambiguous-direct-name",
          ambiguous == "name-ambiguous", ambiguous)

    # A selection by component skips an agent the component ships (naming it
    # needs --on; test_subagents.py covers that).
    agent_cat = dict(SEL_CAT)
    agent_cat["web/research"] = {
        "module": "web", "component": "research", "manifest": True,
        "kind": "component", "rows": [{"id": "research", "method": "agent"}]}
    agent_root = tmp / "ws-agent-root"
    agent_root.mkdir()

    # Pack discovery reads each component's folder; these have none to read.
    agent_cat = {cid: {"path": str(tmp / "no-such-folder"), **comp}
                 for cid, comp in agent_cat.items()}
    by_component = io.StringIO()
    with contextlib.redirect_stdout(by_component):
        cmd_add(_sel(verb="add", component=["research"], pack=[], dry_run=True,
                     json=False, harness="claude", artifact="none"),
                agent_root, agent_cat, [])
    check("ADD-agent-by-component-skipped — a component selection skips its agent and says so",
          "skipped agent(s) a component ships" in by_component.getvalue()
          and "web/research#research" in by_component.getvalue(),
          by_component.getvalue())

    nws = tmp / "ws-nconfirm"
    nws.mkdir()
    do_install(nws, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
    book_before = (nws / STATE_REL).read_bytes()
    skill_p = nws / ".claude/skills/fixskill/SKILL.md"
    rule_p = nws / ".claude/rules/fixrule.md"
    asked: list[str] = []

    def _say_n(prompt: str) -> str:
        asked.append(prompt)
        return "n"

    with contextlib.redirect_stdout(io.StringIO()):
        try:
            cmd_rm(build_parser().parse_args(
                ["rm", "-A", "--exclude-type", "skill"]), nws, catalog, [], ask=_say_n)
            refused = "no refusal"
        except Refuse as exc:
            refused = exc.code
    check("N-confirm-required — disk AND book untouched",
          refused == "confirmation-required" and not asked
          and (nws / STATE_REL).read_bytes() == book_before
          and skill_p.is_file() and rule_p.is_file(),
          f"refusal={refused} asked={asked}")

    asked.clear()

    def _boom(prompt: str) -> str:
        asked.append(prompt)
        raise AssertionError("dry-run must not ask")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_dry = cmd_rm(
            build_parser().parse_args(
                ["rm", "--dry-run", "-A", "--exclude-type", "skill"]),
            nws, catalog, [], ask=_boom)
    check("N-dry-run — prints and never asks",
          rc_dry == 0 and not asked
          and "Would remove" in buf.getvalue()
          and (nws / STATE_REL).read_bytes() == book_before
          and skill_p.is_file(),
          f"rc={rc_dry} asked={asked} out={buf.getvalue()[:200]!r}")

    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        rc_usage = main(["add", "--target", str(empty)])
        rc_refuse = main(["add", "--target", str(empty), "-c", "no/comp"])
    check("CLI-usage-exit-2", rc_usage == 2, str(rc_usage))
    check("CLI-refuse-exit-1", rc_refuse == 1, str(rc_refuse))
    ctx.keep(locals())


def result_classes(ctx) -> None:
    """The result and refusal texts of this round: the refusal sentence, the
    pack refusal of `remove`, the scope refusals of `agent update`, the own
    files of `agent add`, and the Files rows of an update preview."""
    check, tmp = ctx.check, ctx.tmp
    (catalog, _data, _legacy, _expect, _basis, _mirrors, _mtr,
     _mk, _rf, _pws) = ctx.frame()

    print("\nCLI — refusal sentence, pack refusal, agent scope, result rows")
    text = _text_refusal(Refuse("name-unknown", "unknown name 'x'"))
    check("RC-sentence — the text refusal ends with 'Nothing was changed.'",
          text == "unknown name 'x'. Nothing was changed.", text)
    listing = Refuse("cast-missing", "cast is not on PATH, so the agents cannot be listed.")
    listing.unchanged = "Nothing was listed."
    check("RC-sentence — a listing refusal says it listed nothing",
          _text_refusal(listing) == "cast is not on PATH, so the agents cannot be listed. Nothing was listed.",
          _text_refusal(listing))

    ws = tmp / "ws-result-classes"
    ws.mkdir()
    refusal = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_rm(build_parser().parse_args(["remove", "--pack", "nosuchpack"]),
                   ws, catalog, [])
    except Refuse as exc:
        refusal = exc
    check("RC-pack-remove — remove --pack of an unknown pack is pack-unknown",
          refusal is not None and refusal.code == "pack-unknown"
          and refusal.message == "unknown pack 'nosuchpack'. Run `rbtv list --type pack` to see packs.",
          str(refusal and (refusal.code, refusal.message)))

    gone = ws / "ws-not-installed"
    gone.mkdir()
    shown = io.StringIO()
    with contextlib.redirect_stdout(shown):
        code = cmd_rm(build_parser().parse_args(["remove", "fixskill"]),
                      gone, catalog, [])
    check("RC-remove-not-installed — a known file not installed is a result, exit 0",
          code == 0 and "nothing to remove" in shown.getvalue()
          and "Not installed:" in shown.getvalue() and "Installed files:  0 (unchanged)"
          in shown.getvalue() and not any(gone.iterdir()), shown.getvalue())

    usage = None
    try:
        build_parser().parse_args(["agent", "install"])
    except Refuse as exc:
        usage = exc
    check("RC-agent-verb — an unknown agent sub-verb is named COMMAND",
          usage is not None and usage.message.startswith(
              "argument COMMAND: invalid choice: 'install'"),
          str(usage and usage.message))

    scope = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_agent(build_parser().parse_args(["agent", "update", "plans/x"]),
                      ws, catalog, [])
    except Refuse as exc:
        scope = exc
    check("RC-agent-scope — agent update without a scope is refused before any lookup",
          scope is not None and scope.code == "usage"
          and scope.message == "the scope is required: choose guidance, scaffolding or all"
          and scope.next == "rbtv agent update -h",
          str(scope and (scope.code, scope.message)))

    from lib.agents import _agent_files
    home = tmp / "ws-result-classes-agent"
    home.mkdir()
    own = _agent_files(home, {"harness": "claude"}, True)
    check("RC-own-files — agent add names settings.json and .gitignore when missing",
          "settings.json" in own and ".gitignore" in own, str(own))

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print_result({"dry_run": True, "_verb": "update", "scope": "all",
                      "target": str(ws), "added": [], "removed": ["meta/b#kiss"],
                      "installed": ["core/rbtv"], "_details": True,
                      "planned_changes": {}, "selected_files": [],
                      "_facts": {"files": (2, 1)}})
    lines = out.getvalue().splitlines()
    check("RC-update-files — a preview's Files lists files, not components",
          "  meta/b#kiss" in lines and "  core/rbtv" not in lines,
          out.getvalue())


def cli_defects(ctx) -> None:
    """Task 3a4: the list traceback, bare update with --target, agent refusals
    without --target, agent update membership and guidance mismatch, and
    remove of a file that is not installed."""
    check, tmp = ctx.check, ctx.tmp
    (catalog, _data, _legacy, _expect, _basis, _mirrors, _mtr,
     _mk, _rf, _pws) = ctx.frame()

    print("\nCLI — 3a4 defects: list types, update scope, agent refusals, membership")

    def run(argv: list[str], cwd_target=None) -> tuple[int | None, str, str, str | None]:
        """main() with output captured: exit code, stdout, stderr, and any
        exception that escaped main() (a traceback is one of those)."""
        out, err = io.StringIO(), io.StringIO()
        code, escaped = None, None
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(argv)
        except Exception as exc:  # the defect under test: a command that crashes
            escaped = f"{type(exc).__name__}: {exc}"
        return code, out.getvalue(), err.getvalue(), escaped

    inst = tmp / "d-installation"
    inst.mkdir()
    code, _out, err, escaped = run(["list", "--type", "file", "--installed", "--target", str(inst)])
    check("D1-type — an unknown --type is a usage refusal, never a traceback",
          escaped is None and code == 2 and "'file' is unknown" in err,
          f"{escaped} / {code} / {err[:200]}")
    crashed = []
    for verb in ("list", "li", "ls"):
        for kind in CATALOG_TYPES:
            code, _out, _err, escaped = run([verb, "--type", kind, "--installed", "--target", str(inst)])
            if escaped or code != 0:
                crashed.append(f"{verb} --type {kind}: {escaped or code}")
    check("D1-types — every --type value lists with --installed, exit 0",
          not crashed, "; ".join(crashed))

    bare_code, _o, bare_err, _e = run(["update"])
    for argv in (["update", "--target", str(inst)], ["--target", str(inst), "update"]):
        code, _out, err, escaped = run(argv)
        check(f"D2-scope — {' '.join(argv[:-1]) or argv[0]} with no scope answers as bare update",
              escaped is None and code == 2 and "invalid choice" not in err
              and "the following arguments are required: {guidance,scaffolding,all}" in err
              and err == bare_err, f"{code} {err[:200]}")

    ws = tmp / "d-agent-ws"
    ws.mkdir()
    # Agent update reconciles the membership the agent.json lists against the
    # files booked on disk, and names what it added and removed.
    src = tmp / "d-agent-source"
    comp = _component(src, "moda", "comp")
    _file_md(comp / "rules/kiss.md", "kiss", "Kiss", "body\n")
    _file_md(comp / "rules/other.md", "other", "Other", "body\n")
    d_catalog, _ = scan_all(tmp / "d-agent-mirror", src)
    home = ws / ".rbtv/agents/scout"
    known = {"claude": {"m1": ["low", "high"]}, "codex": {"c1": ["low", "high"]}}
    from unittest.mock import patch
    from lib.agents import add_agent
    _agent(home, files=["moda/comp#kiss"])
    with patch("lib.agents.cast_catalog", return_value=known):
        add_agent(ws, "scout", [], set(), d_catalog, False)
    record = json.loads((home / "agent.json").read_text(encoding="utf-8"))
    record["files"] = ["moda/comp#other"]
    (home / "agent.json").write_text(json.dumps(record) + "\n", encoding="utf-8")
    shown = io.StringIO()
    with contextlib.redirect_stdout(shown):
        cmd_agent(build_parser().parse_args(["agent", "update", str(home), "all", "--dry-run"]),
                  ws, d_catalog, [])
    text = shown.getvalue()
    check("D4-membership-preview — a preview names the files it would add and remove",
          "Would add:" in text and "moda/comp#other" in text
          and "Would remove:" in text and "moda/comp#kiss" in text, text)
    shown = io.StringIO()
    with contextlib.redirect_stdout(shown):
        cmd_agent(build_parser().parse_args(["agent", "update", str(home), "all"]),
                  ws, d_catalog, [])
    text = shown.getvalue()
    check("D4-membership — the result names the files added and removed",
          "Added:" in text and "moda/comp#other" in text
          and "Removed:" in text and "moda/comp#kiss" in text
          and "(membership changed)" in text and "Was:" in text, text)
    record = json.loads((home / "agent.json").read_text(encoding="utf-8"))
    record["files"] = ["moda/comp#kiss"]
    (home / "agent.json").write_text(json.dumps(record) + "\n", encoding="utf-8")
    shown = io.StringIO()
    with contextlib.redirect_stdout(shown):
        cmd_agent(build_parser().parse_args(["agent", "update", str(home), "guidance"]),
                  ws, d_catalog, [])
    text = shown.getvalue()
    check("D4-guidance-mismatch — guidance scope names the mismatch and the fixing command",
          "does not match agent.json" in text and "On disk:" in text
          and "agent.json:" in text and "Next: rbtv agent update " in text
          and text.rstrip().endswith("scaffolding"), text)
    check("D4-state — the record was left as the agent wrote it",
          read_state(home)["files"] == ["moda/comp#kiss"], "")

    record = json.loads((home / "agent.json").read_text(encoding="utf-8"))
    record["files"] = ["moda/comp#other"]
    (home / "agent.json").write_text(json.dumps(record) + "\n", encoding="utf-8")
    code, out, _err, escaped = run(["agent", "remove", str(home), "nosuchfile", "--json", "--dry-run"])
    refusal = json.loads(out) if escaped is None and out.strip() else {}
    check("D3-agent-next — an agent removal refusal names an unknown file and offers an agent-safe next command",
          escaped is None and code == 1
          and refusal.get("error", {}).get("message") == "unknown file 'nosuchfile'"
          and refusal.get("next") == "rbtv list",
          f"{escaped} / {code} / refusal={refusal!r}")

    gone = tmp / "d-remove-ws"
    gone.mkdir()
    shown = io.StringIO()
    with contextlib.redirect_stdout(shown):
        code = cmd_rm(build_parser().parse_args(["remove", "fixskill"]), gone, catalog, [])
    text = shown.getvalue()
    check("D5-not-installed — remove of an uninstalled file says nothing to remove and names it",
          code == 0 and "nothing to remove" in text and "Not installed:" in text
          and "files removed" not in text and "Removed:" not in text, text)
