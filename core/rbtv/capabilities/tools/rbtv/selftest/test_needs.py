"""Needs resolution, the positive half: `rbtv add` and `rbtv agent add` of a
component whose `needs` names an operation install the one component that
provides it; with two supplying components a person is asked, and the agent path takes
`--<port> NAME` (`--messaging talker`) and refuses without it, naming the
choices. Phase 2 of the connector architecture, test 3."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch

from discovery import Refuse, scan_all

from lib.agents import add_agent
from lib.commands import _HANDLERS, main
from lib.parser import build_parser
from lib.state import read_state

from .fixture import _file_md, _module, _w
from .test_agents import _agent, _claude_model


def _record(root: Path, module: str, comp: str, **fields: object) -> Path:
    _module(root, module)
    record = {"description": f"The {comp} component", "dependencies": []}
    record.update(fields)
    _w(root / module / comp / f"{comp}.json", json.dumps(record))
    return root / module / comp


def _tool(folder: Path, name: str) -> None:
    tool = folder / "capabilities" / "tools" / name
    _w(tool / f"{name}.json", json.dumps({"name": name, "description": f"The {name} command", "entry": "run.py"}))
    _w(tool / "run.py", "#!/usr/bin/env python3\nprint('hi')\n")
    (tool / "run.py").chmod(0o755)


def _tree(root: Path, suppliers: list[str]) -> dict:
    """A tree with `core/wanter` needing message.send and the named messaging connectors providing it."""
    for name in suppliers:
        _tool(_record(root, "connectors", name, type="messaging", provides=["message.send"]), name)
    wanter = _record(root, "core", "wanter", needs=["message.send"])
    _file_md(wanter / "rules/want.md", "want", "The wanting rule", "# want\n")
    mirror = root.parent / f"{root.name}-mirror"
    mirror.mkdir(exist_ok=True)
    catalog, _shadowed = scan_all(mirror, root)
    return catalog


def _add(target: Path, catalog: dict, *argv: str, ask=None) -> tuple[int | str, str, str]:
    """`rbtv add ...` against the fixture catalog: (exit code or refusal code, stdout, refusal message)."""
    args = build_parser().parse_args(["add", *argv, "--harness", "claude", "--guidance", "none", "--target", str(target)])
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = _HANDLERS["add"](args, target, catalog, [], ask=ask)
    except Refuse as exc:
        return exc.code, out.getvalue(), exc.message
    return code, out.getvalue(), ""


def _booked(target: Path) -> list[str]:
    return sorted((read_state(target).get("components") or {}).keys())


def needs_resolution(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    print("\nNR — needs resolution: installing what a component needs")

    one = _tree(tmp / "nr-one", ["talker"])
    target = tmp / "nr-one-installation"
    target.mkdir()
    code, said, message = _add(target, one, "core/wanter")
    check("NR-one — add of a component that needs message.send installs the one connector that provides it",
          code == 0 and _booked(target) == ["connectors/talker", "core/wanter"], f"{code} {message} {_booked(target)} {said[:200]}")
    check("NR-one-said — the result names the connector it added for the need",
          "connectors/talker" in said and "message.send" in said, said[:300])

    # A need already met by an installed component adds nothing more.
    again_code, again_said, again_message = _add(target, one, "core/wanter", "--json")
    check("NR-met — a second add finds the need met and adds nothing",
          again_code == 0 and json.loads(again_said)["needs"] == []
          and _booked(target) == ["connectors/talker", "core/wanter"], f"{again_code} {again_message} {again_said[:200]}")

    two = _tree(tmp / "nr-two", ["chat", "chat2"])
    target2 = tmp / "nr-two-installation"
    target2.mkdir()
    code, said, message = _add(target2, two, "core/wanter")
    check("NR-two-refused — two supplying components and no terminal: refused, naming the choices and the flag",
          code == "needs-choice" and "chat" in message and "chat2" in message
          and "--messaging chat" in message and _booked(target2) == [], f"{code} {message} {_booked(target2)}")

    code, said, message = _add(target2, two, "core/wanter", "--messaging", "chat2")
    check("NR-two-flag — --messaging NAME picks the supplying component on the agent path",
          code == 0 and _booked(target2) == ["connectors/chat2", "core/wanter"], f"{code} {message} {_booked(target2)}")

    code, said, message = _add(tmp / "nr-two-bad", two, "core/wanter", "--messaging", "signal")
    check("NR-two-unknown — a flag naming a component that does not provide the need is refused",
          code == "needs-choice" and "signal" in message and "chat" in message, f"{code} {message}")

    target3 = tmp / "nr-two-asked"
    target3.mkdir()
    asked: list = []

    def ask(question: str, choices: list[str]) -> str:
        asked.append((question, list(choices)))
        return "chat"

    code, said, message = _add(target3, two, "core/wanter", ask=ask)
    check("NR-two-asked — a person is asked between the two supplying components and the answer is installed",
          code == 0 and asked and asked[0][1] == ["chat", "chat2"] and "message.send" in asked[0][0]
          and _booked(target3) == ["connectors/chat", "core/wanter"], f"{code} {message} {asked} {_booked(target3)}")

    # The agent path: rbtv agent add takes the same flag and refuses without it.
    claude_model = _claude_model()
    known = {"claude": {claude_model: {"rungs": ["low", "high"], "selected": True}}}
    with patch("lib.agents.cast_catalog", return_value=known), \
            patch("lib.agents.cast_effort_word", side_effect=lambda *asked_: "high"):
        ws = tmp / "nr-agent-installation"
        ws.mkdir()
        _agent(ws / ".rbtv/agents/scout")
        try:
            add_agent(ws, "scout", ["want"], set(), two, False)
            refused = None
        except Refuse as exc:
            refused = exc
        check("NR-agent-refused — rbtv agent add of a needing file with two supplying components is refused without --messaging",
              refused is not None and refused.code == "needs-choice" and "--messaging chat" in refused.message,
              f"{refused and refused.code} {refused and refused.message}")
        result = add_agent(ws, "scout", ["want"], set(), two, False, port_choices={"messaging": "chat2"})
        home_state = read_state(ws / ".rbtv/agents/scout")
        check("NR-agent-flag — rbtv agent add --messaging chat2 installs that connector in the agent folder",
              "connectors/chat2" in (home_state.get("components") or {}) and "connectors/chat2#chat2" in result["files"],
              f"{sorted(home_state.get('components') or {})} {result.get('files')}")
        ws1 = tmp / "nr-agent-one"
        ws1.mkdir()
        _agent(ws1 / ".rbtv/agents/scout")
        result = add_agent(ws1, "scout", ["want"], set(), one, False)
        check("NR-agent-one — with one supplying component the agent path installs it with no flag",
              "connectors/talker#talker" in result["files"], str(result.get("files")))

        # Exercise the real dispatch and parser against repository plus mirror. The port exists only
        # in the mirror, including a serves port, so repository-only flag discovery cannot pass.
        repo = tmp / "nr-port-repo"
        ws = tmp / "nr-port-installation"
        wanter = _record(repo, "core", "wanter", needs=["beam.send"])
        _file_md(wanter / "rules/want.md", "want", "The wanting rule", "# want\n")
        mirror = ws / ".rbtv" / "mirror"
        for name in ("light", "light2"):
            comp = _record(mirror, "connectors", name, type="optical", serves=["beam"], provides=["beam.send"])
            _file_md(comp / f"rules/{name}.md", name, "The light rule", "# light\n")
        _agent(ws / ".rbtv/agents/scout")

        def invoke(words):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                code = main(words)
            return code, json.loads(output.getvalue())

        with patch("lib.commands.REPO_ROOT", repo), contextlib.chdir(ws):
            code, data = invoke(["add", "core/wanter", "--optical", "light2", "--harness", "claude", "--guidance", "none", "--target", str(ws), "--json"])
            check("NR-mirror-port — add accepts a mirror-only port flag and installs the chosen component",
                  code == 0 and _booked(ws) == ["connectors/light2", "core/wanter"], f"{code} {data}")
            code, data = invoke(["agent", "add", "scout", "want", "--optical", "light", "--json"])
            check("NR-mirror-agent — agent add accepts the installation mirror's port flag",
                  code == 0 and "connectors/light" in (read_state(ws / ".rbtv/agents/scout").get("components") or {}), f"{code} {data}")
            # A serves-only port also gets a flag, even though its noun differs from type.
            code, data = invoke(["add", "core/wanter", "--beam", "light", "--target", str(ws), "--dry-run", "--json"])
            check("NR-mirror-serves — a mirror-only serves port has a flag",
                  code == 0, f"{code} {data}")

    # Fresh dispatch, never an already installed need: mixed main types share only serves.
    for in_mirror in (False, True):
        suffix = "mirror" if in_mirror else "repo"
        repo = tmp / f"nr-mixed-{suffix}-repo"
        ws = tmp / f"nr-mixed-{suffix}-installation"
        wanter = _record(repo, "core", "wanter", needs=["message.send"])
        _file_md(wanter / "rules/want.md", "want", "The wanting rule", "# want\n")
        for name, kind, serves in (("slack", "messaging", []), ("archive", "storage", ["messaging"])):
            source = ws / ".rbtv/mirror" if in_mirror and name == "archive" else repo
            comp = _record(source, "connectors", name, type=kind, serves=serves, provides=["message.send"])
            _file_md(comp / f"rules/{name}.md", name, "The connector rule", "# connector\n")
        ws.mkdir(parents=True, exist_ok=True)
        with patch("lib.commands.REPO_ROOT", repo), contextlib.chdir(ws):
            words = ["add", "core/wanter", "--harness", "claude", "--guidance", "none", "--target", str(ws), "--json"]
            code, data = invoke(words)
            check(f"NR-mixed-{suffix}-refusal — fresh mixed types name the accepted --messaging flag",
                  code == 1 and "--messaging slack" in json.dumps(data) and _booked(ws) == [], f"{code} {data}")
            code, data = invoke([*words, "--messaging", "slack"])
            check(f"NR-mixed-{suffix}-selection — fresh --messaging slack installs the selected connector",
                  code == 0 and _booked(ws) == ["connectors/slack", "core/wanter"], f"{code} {data}")

    # No operation-noun fallback: flags come solely from declared ports, even with several in common.
    from lib.selection import resolve_needs
    multi = {"core/w": {"needs": ["beam.send"]},
             "connectors/a": {"component": "a", "type": "optical", "serves": ["beam"], "provides": ["beam.send"]},
             "connectors/b": {"component": "b", "type": "optical", "serves": ["beam"], "provides": ["beam.send"]}}
    try:
        selected = resolve_needs(multi, ["core/w"], [], {"beam": "b"})
    except Refuse:
        selected = []
    check("NR-serves-fresh — an explicit common serves flag resolves an unmet need",
          bool(selected) and selected[0]["component"] == "connectors/b", str(selected))
    for label, catalog, choices in [("ports", multi, {}), ("conflict", multi, {"beam": "a", "optical": "b"}),
                                     ("none", {**multi, "connectors/b": {**multi["connectors/b"], "type": "storage", "serves": []}}, {})]:
        try:
            resolve_needs(catalog, ["core/w"], [], choices)
            reason = ""
        except Refuse as exc:
            reason = exc.message
        check(f"NR-port-ambiguity-{label} — refuse ambiguous declared ports explicitly",
              "port" in reason and {"ports": "ambiguous", "conflict": "conflicting", "none": "no common"}[label] in reason, reason)
