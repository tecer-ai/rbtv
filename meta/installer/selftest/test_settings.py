"""The two settings a workspace records once: harnesses and artifact."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from discovery import Refuse

from lib.constants import BASIS_NONE, STATE_REL
from lib.state import read_state
from lib.operations import do_install
from lib.listing import _settings_view
from lib.parser import SETTING_VERB, build_parser
from lib.commands import _HANDLERS, cmd_li


def workspace_settings(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nW — D16: harness + artifact are workspace settings")

    def _mkws(name: str):
        ws = tmp / name
        ws.mkdir()
        (ws / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        return ws

    def _run(ws: Path, argv: list[str]):
        """Drive the real CLI handler; return 0 or the refusal code."""
        return _run_msg(ws, argv)[0]

    def _run_msg(ws: Path, argv: list[str]):
        ns = build_parser().parse_args(argv)
        handler = _HANDLERS[ns.verb]
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                return handler(ns, ws, catalog, []), ""
            except Refuse as exc:
                return exc.code, exc.message

    w = _mkws("ws-d16")
    check("W1 — a first add with no --harness refuses, and writes nothing",
          _run(w, ["add", "-c", "fixmod/goodcomp"]) == "harness-required"
          and not (w / STATE_REL).exists())
    check("W2 — a first add with no --artifact refuses too",
          _run(w, ["add", "-c", "fixmod/goodcomp",
                   "--harness", "claude"]) == "artifact-required"
          and not (w / STATE_REL).exists())
    check("W3 — with both, the first add records them at TOP LEVEL",
          _run(w, ["add", "-c", "fixmod/goodcomp", "--harness",
                   "claude,codex", "--artifact", "CLAUDE.md"]) == 0
          and read_state(w)["harnesses"] == ["claude", "codex"]
          and read_state(w)["guidance_basis"] == "CLAUDE.md",
          str(read_state(w).get("harnesses")))
    check("W4 — every component record projects the workspace set",
          all(rec["harnesses"] == ["claude", "codex"]
              for rec in read_state(w)["components"].values()))
    check("W5 — a LATER add refuses --harness by name",
          _run(w, ["add", "-c", "fixmod/goodcomp",
                   "--harness", "claude"]) == "setting-locked")
    check("W6 — a LATER add refuses --artifact by name",
          _run(w, ["add", "-c", "fixmod/goodcomp",
                   "--artifact", "AGENTS.md"]) == "setting-locked")
    w7 = _run_msg(w, ["add", "-c", "fixmod/goodcomp",
                      "--harness", "claude"])
    check("W7 — the refusal names the verb that DOES change it",
          SETTING_VERB["harness"] in w7[1], w7[1])
    check("W8 — a later add with NO flags inherits the recorded set",
          _run(w, ["add", "-c", "fixmod/codexcomp"]) == 0
          and read_state(w)["components"]["fixmod/codexcomp"]["harnesses"]
          == ["claude", "codex"],
          str(read_state(w)["components"].get("fixmod/codexcomp")))

    codex_rule = ".agents/behavior-rules/fixrule.md"
    check("W9 — `rm harness` DELETES that harness's files (never a no-op)",
          (w / codex_rule).exists()
          and _run(w, ["rm", "harness", "codex"]) == 0
          and not (w / codex_rule).exists()
          and read_state(w)["harnesses"] == ["claude"]
          and all(rec["harnesses"] == ["claude"]
                  for rec in read_state(w)["components"].values()))
    check("W10 — the AGENTS.md mirror goes with the last harness reading it",
          not (w / "AGENTS.md").exists())
    check("W11 — `add harness` puts them back",
          _run(w, ["add", "harness", "codex"]) == 0
          and (w / codex_rule).exists()
          and (w / "AGENTS.md").exists()
          and read_state(w)["harnesses"] == ["claude", "codex"])
    check("W12 — a no-op change says so and writes nothing",
          _run(w, ["add", "harness", "codex"]) == 0
          and read_state(w)["harnesses"] == ["claude", "codex"])
    check("W13 — removing every harness refuses; it is an uninstall",
          _run(w, ["rm", "harness", "claude,codex"]) == "harness-list-empty"
          and read_state(w)["harnesses"] == ["claude", "codex"])
    check("W14 — an unknown harness refuses before any write",
          _run(w, ["add", "harness", "kimi"]) == "harness-unknown"
          and read_state(w)["harnesses"] == ["claude", "codex"])

    # A flip that would GENERATE over the file the human authors is the
    # D13 collision, and `set artifact` inherits it unchanged.
    w15 = _run_msg(w, ["set", "artifact", "AGENTS.md"])
    check("W15 — a flip that would overwrite hand-authored guidance "
          "refuses, and the recorded basis does not move",
          w15[0] == "guidance-mirror-collision"
          and read_state(w)["guidance_basis"] == "CLAUDE.md"
          and "rbtv install set artifact" in w15[1], str(w15))
    check("W16 — `set artifact none` turns the mirror off and takes the "
          "generated file with it",
          _run(w, ["set", "artifact", "none"]) == 0
          and read_state(w)["guidance_basis"] == BASIS_NONE
          and read_state(w)["guidance_files"] == []
          and not (w / "AGENTS.md").exists(),
          str(read_state(w).get("guidance_files")))
    check("W16b — setting it back regenerates it",
          _run(w, ["set", "artifact", "CLAUDE.md"]) == 0
          and (w / "AGENTS.md").exists()
          and read_state(w)["guidance_files"] == ["AGENTS.md"])

    (w / "skipme").mkdir(exist_ok=True)
    (w / "skipme" / "CLAUDE.md").write_text("nested\n", encoding="utf-8")
    _run(w, ["dupe-artifacts"])
    check("W17 — without an exclude, the nested folder IS mirrored",
          (w / "skipme" / "AGENTS.md").exists())
    check("W18 — `add artifact exclude` skips it and persists the list",
          _run(w, ["add", "artifact", "exclude", "skipme"]) == 0
          and read_state(w)["guidance_excludes"] == ["skipme"]
          and not (w / "skipme" / "AGENTS.md").exists())
    # Two entries, because with ONE the old driver's REPLACE and a proper
    # set-union are indistinguishable — that is the bug this verb exists
    # to kill: asking to skip one more folder un-skipped every other.
    (w / "skiptoo").mkdir(exist_ok=True)
    (w / "skiptoo" / "CLAUDE.md").write_text("nested too\n",
                                             encoding="utf-8")
    check("W18b — a SECOND exclude joins the first, never replaces it",
          _run(w, ["add", "artifact", "exclude", "skiptoo"]) == 0
          and read_state(w)["guidance_excludes"] == ["skipme", "skiptoo"]
          and not (w / "skiptoo" / "AGENTS.md").exists()
          and not (w / "skipme" / "AGENTS.md").exists(),
          str(read_state(w)["guidance_excludes"]))
    check("W19 — `rm artifact exclude` takes ONE and leaves the other",
          _run(w, ["rm", "artifact", "exclude", "skipme"]) == 0
          and read_state(w)["guidance_excludes"] == ["skiptoo"]
          and (w / "skipme" / "AGENTS.md").exists()
          and not (w / "skiptoo" / "AGENTS.md").exists(),
          str(read_state(w)["guidance_excludes"]))
    check("W19b — and removing the last one empties the list",
          _run(w, ["rm", "artifact", "exclude", "skiptoo"]) == 0
          and read_state(w)["guidance_excludes"] == []
          and (w / "skiptoo" / "AGENTS.md").exists())
    check("W20 — excluding what is not excluded refuses, never silently",
          _run(w, ["rm", "artifact", "exclude", "skipme"])
          == "exclude-unknown")

    # D16c — the settings are READ in `li`, and the two verbs that used
    # to print them are gone from the menu.
    _lib = io.StringIO()
    with contextlib.redirect_stdout(_lib):
        _rc_li = cmd_li(build_parser().parse_args(["li"]), w, catalog, [])
    _litext = _lib.getvalue()
    check("W21 — `li` heads its listing with all three settings",
          _rc_li == 0
          and "claude, codex" in _litext
          and "artifact  :" in _litext and "excluded  :" in _litext,
          _litext[:300])
    check("W21b — and names the command that changes each one, so a "
          "reader never has to go find the help",
          "add|rm harness" in _litext
          and "set artifact" in _litext
          and "add|rm artifact exclude" in _litext,
          _litext[:400])
    _lij = io.StringIO()
    with contextlib.redirect_stdout(_lij):
        cmd_li(build_parser().parse_args(["li", "--json"]), w, catalog, [])
    check("W21c — and they ride --json, so nothing that parsed the "
          "retired verbs loses the values",
          json.loads(_lij.getvalue())["settings"]
          == _settings_view(read_state(w)),
          str(json.loads(_lij.getvalue()).get("settings")))
    for _gone in ("harness", "artifact"):
        _c, _m = _run_msg(w, [_gone])
        check(f"W21d — bare `{_gone}` is retired and sends the reader "
              "to `li`",
              _c == "verb-moved" and "rbtv install li" in _m,
              f"{_c}: {_m}")
    # HIDDEN, not merely undocumented: a menu that still lists them has
    # not actually shrunk, which is the whole ask.
    # Match the verb ENTRY, never the word: `rm`'s and `set`'s own help
    # lines mention both nouns, and a substring test would fire on the
    # very sentences that teach the new forms.
    _menu_verbs = {ln.split()[0] for ln in
                   build_parser().format_help().splitlines()
                   if ln.startswith("    ") and not ln.startswith("     ")
                   and ln.split()}
    check("W21e — neither is a verb ENTRY in the menu any more",
          not ({"harness", "artifact"} & _menu_verbs),
          str(sorted(_menu_verbs)))
    check("W21f — and the menu still lists every verb that DOES act, so "
          "the trim removed exactly two entries",
          {"add", "rm", "set", "ls", "li", "doctor"} <= _menu_verbs,
          str(sorted(_menu_verbs)))

    # D16b — the ACTION word leads. Every arm below is about SPELLING;
    # W9-W20 above already prove the behaviour each form reaches.
    for _old, _new in (
            (["harness", "add", "codex"], "add harness codex"),
            (["harness", "rm", "codex"], "rm harness codex"),
            (["artifact", "set", "none"], "set artifact none"),
            (["artifact", "exclude", "add", "d"],
             "add artifact exclude d"),
            (["artifact", "exclude", "rm", "d"],
             "rm artifact exclude d")):
        _code, _msg = _run_msg(w, _old)
        check(f"W25 — `{' '.join(_old)}` is retired and names its "
              f"replacement",
              _code == "verb-moved" and f"rbtv install {_new}" in _msg,
              f"{_code}: {_msg}")
    # A retired form must CHANGE NOTHING on its way to the refusal —
    # a message that says "moved" while the write already happened is
    # worse than no message.
    _before = (read_state(w)["harnesses"],
               read_state(w).get("guidance_basis"),
               read_state(w).get("guidance_excludes"))
    _run(w, ["harness", "rm", "codex"])
    _run(w, ["artifact", "set", "none"])
    check("W26 — a retired form writes nothing before refusing",
          (read_state(w)["harnesses"],
           read_state(w).get("guidance_basis"),
           read_state(w).get("guidance_excludes")) == _before,
          str(_before))
    check("W27 — `set` with no noun refuses, naming the one it takes",
          _run_msg(w, ["set"])[0] == "noun-missing")
    check("W28 — a noun that names no setting refuses, never guessing "
          "it is a component",
          _run(w, ["add", "sub-agents"]) == "noun-unknown")
    check("W29 — the basis is a SET, and `add`/`rm` say so rather than "
          "silently replacing it",
          _run(w, ["add", "artifact", "CLAUDE.md"])
          == "setting-wrong-verb"
          and _run(w, ["rm", "artifact", "CLAUDE.md"])
          == "setting-wrong-verb")
    check("W30 — the harness set is MANY values, and `set` says so",
          _run(w, ["set", "harness", "codex"]) == "setting-wrong-verb")
    check("W31 — a settings noun mixed with component selectors refuses; "
          "neither half is applied",
          _run(w, ["add", "harness", "codex", "-c", "fixmod/goodcomp"])
          == "noun-with-selectors")
    check("W32 — a settings form still reaches its handler with the "
          "shared flags (--dry-run writes nothing)",
          _run(w, ["rm", "harness", "codex", "--dry-run"]) == 0
          and read_state(w)["harnesses"] == ["claude", "codex"],
          str(read_state(w)["harnesses"]))

    w2 = _mkws("ws-d16-virgin")
    check("W22 — every settings form refuses on a workspace with no book",
          _run(w2, ["add", "harness", "codex"]) == "workspace-unrecorded"
          and _run(w2, ["set", "artifact", "none"])
          == "workspace-unrecorded"
          and _run(w2, ["dupe-artifacts"]) == "workspace-unrecorded")
    _w2li = io.StringIO()
    with contextlib.redirect_stdout(_w2li):
        _rc2 = cmd_li(build_parser().parse_args(["li"]), w2, catalog, [])
    check("W22b — and `li` on that workspace SAYS nothing is recorded "
          "rather than printing an empty settings block",
          _rc2 == 0 and "none recorded" in _w2li.getvalue(),
          _w2li.getvalue()[:200])

    # MIGRATION — a pre-D16 book has harnesses only inside `components`.
    w3 = _mkws("ws-d16-legacy")
    do_install(w3, catalog, ["fixmod/goodcomp", "fixmod/codexcomp"],
               ["claude", "codex"], dry_run=False,
               guidance_basis="CLAUDE.md")
    pre16 = json.loads((w3 / STATE_REL).read_text(encoding="utf-8"))
    pre16.pop("harnesses")
    pre16["components"]["fixmod/goodcomp"]["harnesses"] = ["claude"]
    pre16["components"]["fixmod/codexcomp"]["harnesses"] = ["codex"]
    (w3 / STATE_REL).write_text(json.dumps(pre16, indent=2),
                                encoding="utf-8")
    check("W23 — migration lifts the UNION of the records, never a subset",
          read_state(w3)["harnesses"] == ["claude", "codex"])
    check("W24 — after migration the flag is locked, like any recorded set",
          _run(w3, ["add", "-c", "fixmod/goodcomp",
                    "--harness", "claude"]) == "setting-locked")
    ctx.keep(locals())
