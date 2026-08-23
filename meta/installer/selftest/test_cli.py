"""The command grammar: verbs, selectors and the numeric index."""
from __future__ import annotations

import contextlib
import io

from discovery import Refuse

from lib.constants import STATE_REL
from lib.selection import (
    RANGE_SPAN_MAX,
    _index_nums,
    _sel,
    read_index,
    resolve_selection,
    write_index,
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

    print("\nCLI — parser, selectors, index, R7 guard")
    for verb in ("add", "rm", "ls", "li", "harness", "artifact",
                 "dupe-artifacts", "doctor", "selftest", "interactive"):
        argv = [verb] if verb != "add" else ["add", "-A"]
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
    check("CLI-reach-handler-add", rc_add == "harness-required",
          str(rc_add))
    check("CLI-reach-handler-rm", rc_rm == "not-installed", str(rc_rm))
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
    try:
        R(verb="rm", book=SEL_BOOK, component=["web/capture"])
        not_in = "no refusal"
    except Refuse as exc:
        not_in = exc.code
    check("SEL-refuse-not-installed", not_in == "not-installed", not_in)

    idx_ws = tmp / "ws-index"
    idx_ws.mkdir()
    write_index(idx_ws, SEL_CAT)
    other = dict(SEL_CAT)
    other["zz/extra"] = {
        "module": "zz", "component": "extra", "manifest": True,
        "kind": "component",
        "rows": [{"part-id": "x", "method": "skill"}]}
    try:
        resolve_selection(
            _sel(verb="add", component=["1"], index=read_index(idx_ws)),
            other, None)
        stale = "no refusal"
    except Refuse as exc:
        stale = exc.code
    check("index-stale", stale == "index-stale", stale)

    try:
        resolve_selection(_sel(verb="add", component=["1"]), SEL_CAT, None)
        im = "no refusal"
    except Refuse as exc:
        im = exc.code
    except Exception as exc:
        im = type(exc).__name__
    check("index-missing", im == "index-missing", im)

    idx = write_index(idx_ws, SEL_CAT)
    try:
        resolve_selection(
            _sel(verb="add", component=["999"], index=idx), SEL_CAT, None)
        iu = "no refusal"
    except Refuse as exc:
        iu = exc.code
    except Exception as exc:
        iu = type(exc).__name__
    check("index-unknown", iu == "index-unknown", iu)

    try:
        resolve_selection(
            _sel(verb="add", component=["1"], index=idx), SEL_CAT, None)
        ik = "no refusal"
    except Refuse as exc:
        ik = exc.code
    except Exception as exc:
        ik = type(exc).__name__
    check("index-kind-mismatch — slot 1 is module, not component",
          ik == "index-kind-mismatch", ik)

    # RANGES. The unit under test is _index_nums — the ONE place that
    # decides whether a token names ls/li numbers at all. Every arm below
    # would go red on the pre-range parser: it recognised `t.isdigit()`
    # only, so `3-7` fell through as a component NAME.
    check("RANGE-single", _index_nums("7") == ["7"])
    check("RANGE-inclusive-both-ends", _index_nums("3-7")
          == ["3", "4", "5", "6", "7"], str(_index_nums("3-7")))
    check("RANGE-degenerate", _index_nums("5-5") == ["5"])
    # The whole reason a range is digits-on-both-sides: real ids carry
    # hyphens, and mistaking one for a range would select the wrong parts
    # silently rather than refusing.
    for _name in ("ponytail-audit", "web/browse", "sub-agent", "5-",
                  "-5", "1-2-3", "a-1", "1-b"):
        check(f"RANGE-name-not-range {_name}",
              _index_nums(_name) is None, str(_index_nums(_name)))
    try:
        _index_nums("7-3")
        inv = "no refusal"
    except Refuse as exc:
        inv = exc.code
    check("RANGE-inverted refuses", inv == "index-range-inverted", inv)
    try:
        _index_nums(f"1-{RANGE_SPAN_MAX + 2}")
        wide = "no refusal"
    except Refuse as exc:
        wide = exc.code
    check("RANGE-too-wide refuses before expanding",
          wide == "index-range-too-wide", wide)
    check("RANGE-at-the-cap still expands",
          len(_index_nums(f"1-{RANGE_SPAN_MAX}")) == RANGE_SPAN_MAX)
    # End to end through the resolver: a range must select exactly what the
    # same numbers listed one by one select.
    _idx3 = write_index(idx_ws, SEL_CAT)
    _slots = sorted(
        int(n) for n, sl in (_idx3.get("n") or {}).items()
        if sl["kind"] in ("component", "part"))

    def _outcome(comps: list[str]):
        """The resolver's verdict — the selection OR the refusal code.

        Both are outcomes a caller sees, and the property under test is
        that a range and the same numbers listed one by one produce the
        SAME one. Comparing only successful selections would let a range
        that refuses where the list succeeds slip through green.
        """
        try:
            return ("ok", resolve_selection(
                _sel(verb="add", component=comps, index=_idx3),
                SEL_CAT, None))
        except Refuse as exc:
            return ("refused", exc.code)

    # The pair must be one where the LISTED form actually SELECTS something.
    # Taking the first two component slots blind picked a span containing an
    # uninstallable fixture, and the arm then compared refusal-to-refusal —
    # equal, green, and proving nothing about a range that works.
    _pair = next(
        ((lo, hi) for lo in _slots for hi in _slots if hi > lo
         and _outcome([str(n) for n in range(lo, hi + 1)])[0] == "ok"),
        None)
    if _pair:
        _lo, _hi = _pair
        _range = _outcome([f"{_lo}-{_hi}"])
        _listed = _outcome([str(n) for n in range(_lo, _hi + 1)])
        check("RANGE-equals-the-listed-numbers",
              _range == _listed and _range[0] == "ok" and _range[1],
              f"{_lo}-{_hi}: {_range} vs {_listed}")
    else:
        check("RANGE-equals-the-listed-numbers", False,
              f"fixture offers no selectable span: {_slots}")
    try:
        resolve_selection(
            _sel(verb="add", component=["1-999"], index=_idx3),
            SEL_CAT, None)
        ru = "no refusal"
    except Refuse as exc:
        ru = exc.code
    check("RANGE-unknown-slot inside a range refuses",
          ru in ("index-unknown", "index-kind-mismatch"), ru)

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
        rc_n = cmd_rm(
            build_parser().parse_args(
                ["rm", "-A", "-nx", "skill"]),
            nws, catalog, [], ask=_say_n)
    check("N-confirm-n — disk AND book untouched",
          rc_n == 0 and asked
          and (nws / STATE_REL).read_bytes() == book_before
          and skill_p.is_file() and rule_p.is_file(),
          f"rc={rc_n} asked={asked}")

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
          and "would remove" in buf.getvalue()
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
