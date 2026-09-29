"""The command grammar, stable name selection and noninteractive removal."""
from __future__ import annotations

import contextlib
import io

from discovery import Refuse

from lib.constants import STATE_REL
from lib.selection import (
    _sel,
    resolve_selection,
)
from lib.operations import do_install
from lib.parser import build_parser
from lib.commands import (
    _HANDLERS,
    cmd_add,
    cmd_doctor,
    cmd_dupe,
    cmd_li,
    cmd_ls,
    cmd_rm,
    main,
)


def parser_selectors_index(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nCLI — parser, selectors, stable names, confirmation")
    for verb in ("add", "remove", "rm", "list", "status", "show",
                 "ls", "li", "harness", "artifact",
                 "dupe-artifacts", "doctor", "selftest", "interactive"):
        argv = (["add", "-A"] if verb == "add" else
                ["show", "fixskill"] if verb == "show" else [verb])
        ns = build_parser().parse_args(argv)
        check(f"CLI-reach-{verb}", ns.verb == verb
              and verb in _HANDLERS, ns.verb)
    empty = tmp / "ws-cli-empty"
    empty.mkdir()
    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        rc_ls = cmd_ls(build_parser().parse_args(["ls"]), empty, catalog, [])
        rc_li = cmd_li(build_parser().parse_args(["li"]), empty, catalog, [])
        try:
            cmd_dupe(build_parser().parse_args(["dupe-artifacts"]),
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
    check("CLI-reach-handler-dupe", rc_dupe == "workspace-unrecorded",
          str(rc_dupe))
    check("CLI-reach-handler-add", rc_add == "setup-required",
          str(rc_add))
    check("CLI-reach-handler-rm", rc_rm == "ok", str(rc_rm))
    check("CLI-reach-handler-doctor", rc_doc == 0, str(rc_doc))

    for flag, meth in (("-xs", "skill"), ("-xr", "rule"),
                       ("-xc", "command"), ("-xsa", "sub-agent")):
        a = build_parser().parse_args(["add", flag])
        b = build_parser().parse_args(["add", "-x", meth])
        check(f"CLI-alias-{flag}", a.method == b.method == [meth],
              f"{a.method} vs {b.method}")

    # A comma list must be IDENTICAL to the repeated form, for every
    # selector — not just for -x, which is the only one that split before.
    # The red control is the pre-change parser: with `append` restored on
    # any of these four, the comma token arrives as one bogus id and the
    # equality fails.
    for _flag, _dest in (("-m", "module"), ("-c", "component"),
                         ("-nm", "exclude_module"),
                         ("-nc", "exclude_component"),
                         ("-x", "method"), ("-nx", "exclude_method")):
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
        "core/communication": {
            "module": "core", "component": "communication",
            "manifest": True, "kind": "component", "rows": [
                {"part-id": "audio", "method": "path"},
                {"part-id": "plain-language", "method": "rule"},
                {"part-id": "non-technical-user", "method": "rule"},
                {"part-id": "concise-chat", "method": "rule"},
                {"part-id": "audio-aware", "method": "skill"}]},
        "core/sub-agents": {
            "module": "core", "component": "sub-agents",
            "manifest": True, "kind": "component", "rows": [
                {"part-id": "cast", "method": "path"},
                {"part-id": "sub-agents", "method": "skill"},
                {"part-id": "swarm", "method": "skill"},
                {"part-id": "panel", "method": "skill"}]},
        "web/browse": {
            "module": "web", "component": "browse",
            "manifest": True, "kind": "component", "rows": [
                {"part-id": "browse", "method": "skill"},
                {"part-id": "chrome-devtools", "method": "config"}]},
        "web/capture": {
            "module": "web", "component": "capture",
            "manifest": True, "kind": "component", "rows": [
                {"part-id": "capture", "method": "skill"}]},
        "_hub/skills/ponytail": {
            "module": "_hub", "component": "ponytail",
            "manifest": False, "kind": "hub"},
        "badmod/silent": {
            "module": "badmod", "component": "silent",
            "manifest": False, "kind": "component"},
    }
    SEL_BOOK = {
        "core/communication": {
            "module": "core", "component": "communication",
            "parts": {"audio-aware": {"method": "skill"},
                      "plain-language": {"method": "rule"}}},
        "web/browse": {"module": "web", "component": "browse"},
        "ghost/gone": {"module": "ghost", "component": "gone"},
    }

    def R(verb="add", book=None, **kw):
        return resolve_selection(_sel(verb=verb, **kw), SEL_CAT, book)

    check("SEL-and",
          R(module=["core"], method=["skill"]) == {
              "core/communication#audio-aware",
              "core/sub-agents#sub-agents",
              "core/sub-agents#swarm",
              "core/sub-agents#panel"})
    check("SEL-or",
          R(component=["core/communication", "web/browse"],
            method=["skill", "rule"]) == {
              "core/communication#plain-language",
              "core/communication#non-technical-user",
              "core/communication#concise-chat",
              "core/communication#audio-aware",
              "web/browse#browse"})
    check("SEL-exclude",
          R(all=True, exclude_module=["core"], method=["skill"]) == {
              "web/browse#browse",
              "web/capture#capture",
              "_hub/skills/ponytail#ponytail"})
    # -nx must SUBTRACT, not merely trigger the confirmation prompt.
    # Without this arm, neutering the method-exclusion filter left the whole
    # suite green: N-confirm asserts the prompt fired and that answering "n"
    # changed nothing, which passes whether or not the filter ever ran.
    _all_parts = R(all=True)
    _no_skill = R(all=True, exclude_method=["skill"])
    check("SEL-exclude-method — -nx subtracts the method",
          _no_skill < _all_parts
          and "web/browse#browse" not in _no_skill
          and "_hub/skills/ponytail#ponytail" not in _no_skill
          and "core/communication#plain-language" in _no_skill,
          f"kept={sorted(_no_skill - _all_parts)} "
          f"dropped={sorted(_all_parts - _no_skill)}")
    _all = R(all=True)
    _no_browse = R(all=True, exclude_component=["web/browse"])
    check("SEL-exclude-component — -nc subtracts the component",
          _no_browse < _all
          and "web/browse#browse" not in _no_browse
          and "web/browse#chrome-devtools" not in _no_browse
          and "core/communication#audio-aware" in _no_browse,
          f"dropped={sorted(_all - _no_browse)}")
    check("SEL-rm-booked",
          R(verb="rm", book=SEL_BOOK, component=["core/communication"])
          == {"core/communication#audio-aware",
              "core/communication#plain-language"})
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
          R(names=["audio-aware"]) == {"core/communication#audio-aware"})
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
        "rows": [{"part-id": "capture", "method": "skill"}]}
    try:
        resolve_selection(_sel(names=["capture"]), duplicate)
        ambiguous = "no refusal"
    except Refuse as exc:
        ambiguous = exc.code
    check("SEL-ambiguous-direct-name",
          ambiguous == "name-ambiguous", ambiguous)

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
                ["rm", "-A", "-nx", "skill"]), nws, catalog, [], ask=_say_n)
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
                ["rm", "--dry-run", "-A", "-nx", "skill"]),
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
