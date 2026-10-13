"""Agent-local source, shipped rbtv/ copy, and the foundations pack."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

from discovery import Refuse, attach_local, scan_all
from lib.agents import (EXCLUDE_FIELD, SHIPPED_FIELD, add_agent, reconcile_ignore,
                        remove_agent, update_agent)
from lib.constants import MATRIX, REPO_ROOT, TOOLS_RULE
from lib.pathlinks import bin_dir

from .fixture import _component, _file_md, _w

_KNOWN = {"claude": {"haiku-5-5": {"rungs": ["low", "high"], "selected": True}},
          "codex": {"c1": {"rungs": ["low", "high"], "selected": True}},
          "opencode": {"glm-5.3": {"rungs": ["low", "high"], "selected": True}}}
_LAUNCH = {"harness": "claude", "model": "haiku-5-5", "effort": "high"}


def _casts():
    return (patch("lib.agents.cast_catalog", return_value=_KNOWN),
            patch("lib.agents.cast_model_id", return_value="native-id"))


def _skill(path: Path, name: str, body: str) -> None:
    _file_md(path, name, f"The {name} skill", body)


def _agent(home: Path, name: str) -> None:
    home.mkdir(parents=True, exist_ok=True)
    _w(home / "prompt.md", "Prompt.\n")
    _w(home / "agent.json", json.dumps({
        "name": name, "description": "Agent.", "harness": "claude",
        "model": "haiku-5-5", "effort": "high", "files": [], "packs": []}) + "\n")


def _snap(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def _refused(call) -> Refuse | None:
    try:
        call()
    except Refuse as exc:
        return exc
    return None


def _source(root: Path) -> tuple[dict, Path]:
    comp = _component(root, "ship", "box")
    _skill(comp / "skills/shared.md", "shared", "shared body\n")
    _w(comp / "agents/porter/prompt.md", "Porter.\n")
    _w(comp / "agents/porter/agent.json", json.dumps({
        "name": "porter", "description": "Shipped porter."}) + "\n")
    _skill(comp / "agents/porter/rbtv/skills/kept.md", "kept", "shipped kept\n")
    _skill(comp / "agents/porter/rbtv/skills/edited.md", "edited", "shipped edited\n")
    catalog, _ = scan_all(root.parent / "no-mirror", root)
    return catalog, comp


def agent_local(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    root = tmp / "al-source"
    comp = _component(root, "fix", "box")
    _skill(comp / "skills/shared.md", "shared", "same body\n")
    _skill(comp / "skills/other.md", "other", "other body\n")
    _w(comp / "packs/ignite.json", json.dumps({
        "description": "Fixture ignite pack overlapping foundations.",
        "files": ["core/rbtv#agent-folder", "fix/box#other"]}) + "\n")
    rbtv = _component(root, "core", "rbtv")
    _file_md(rbtv / "rules/agent-folder.md", "agent-folder",
             "CONTAINS: folder rule PURPOSE: keep the folder "
             "ALWAYS LOAD WHEN: editing the folder "
             "DO NOT LOAD WHEN: elsewhere",
             "Keep the folder.\n")
    _w(rbtv / "packs/foundations.json", json.dumps({
        "description": "Fixture foundations pack.",
        "files": ["core/rbtv#agent-folder"]}) + "\n")
    catalog, _ = scan_all(tmp / "al-mirror", root)
    ws = tmp / "al-install"
    ws.mkdir()
    home = ws / ".rbtv/agents/scout"
    _agent(home, "scout")
    local = home / "rbtv"
    _skill(local / "skills/own.md", "own", "own body\n")
    _file_md(local / "rules/ownrule.md", "ownrule", "the own rule", "Rule.\n")
    _file_md(local / "commands/owncmd.md", "owncmd", "the own command", "Cmd.\n")
    _w(local / "hooks/ownhook.json", json.dumps({
        "name": "ownhook", "description": "The own hook",
        "event": "PreToolUse", "command": "true"}) + "\n")
    _w(local / "mcp-servers/ownmcp.json", json.dumps({
        "name": "ownmcp", "description": "The own server",
        "url": "https://example.invalid/mcp"}) + "\n")
    tool = local / "capabilities/tools/owntool"
    _w(tool / "owntool.json", json.dumps({
        "name": "owntool", "description": "The own tool",
        "entry": "owntool.py"}) + "\n")
    _w(tool / "owntool.py", "#!/usr/bin/env python3\nprint('own')\n")
    (tool / "owntool.py").chmod(0o755)

    with _casts()[0], _casts()[1]:
        add_agent(ws, "scout", ["shared"], set(), catalog, False)
    skill = home / MATRIX["skill"]["claude"].format(name="own")
    rule = home / MATRIX["rule"]["claude"].format(name="ownrule")
    command = home / MATRIX["command"]["codex"].format(name="owncmd")
    check("AL-01 local source installs for every harness",
          skill.is_file() and (home / MATRIX["skill"]["codex"].format(name="own")).is_file()
          and rule.is_file() and (home / MATRIX["rule"]["codex"].format(name="ownrule")).is_file()
          and command.is_file()
          and (home / ".claude/commands/owncmd.md").is_file()
          and "PreToolUse" in (home / ".claude/settings.json").read_text(encoding="utf-8")
          and "ownmcp" in (home / ".mcp.json").read_text(encoding="utf-8")
          and "ownmcp" in (home / "opencode.json").read_text(encoding="utf-8"),
          "")
    record = json.loads((home / "agent.json").read_text(encoding="utf-8"))
    check("AL-02 local files stay out of agent.json files",
          "local/scout#own" not in record["files"] and "fix/box#shared" in record["files"],
          str(record["files"]))

    bad = ws / ".rbtv/agents/bad"
    _agent(bad, "bad")
    _w(bad / "rbtv/skills/broken.md", "---\nname: broken\n---\n\nno description\n")
    before = _snap(ws)
    with _casts()[0], _casts()[1]:
        refused = _refused(lambda: update_agent(ws, "bad", "all", catalog, False))
    check("AL-03 invalid local source refuses before any write",
          refused is not None and "broken.md" in refused.message
          and "description" in refused.message and _snap(ws) == before,
          "" if refused is None else refused.message)

    clash = ws / ".rbtv/agents/clash"
    _agent(clash, "clash")
    with _casts()[0], _casts()[1]:
        add_agent(ws, "clash", ["shared"], set(), catalog, False)
    _skill(clash / "rbtv/skills/shared.md", "shared", "same body\n")
    before = _snap(ws)
    with _casts()[0], _casts()[1]:
        refused = _refused(lambda: update_agent(ws, "clash", "all", catalog, False))
    check("AL-04 identical local and shared names refuse",
          refused is not None and refused.code == "file-collision"
          and "shared" in refused.message and "Rename" in refused.message
          and _snap(ws) == before,
          "" if refused is None else refused.message)

    _w(home / "memory/note.md", "memory\n")
    _w(home / "runtime/state.txt", "runtime\n")
    _w(home / "unmanaged.txt", "leave me\n")
    stray = home / ".claude/skills/stray/SKILL.md"
    _w(stray, "<!-- rbtv-managed — generated -->\nstray\n")
    _w(home / "CLAUDE.md",
       "<!-- rbtv:start stale-label -->\nstale\n<!-- rbtv:end stale-label -->\n")
    with _casts()[0], _casts()[1]:
        update_agent(ws, "scout", "all", catalog, False)
    (local / "skills/own.md").unlink()
    with _casts()[0], _casts()[1]:
        update_agent(ws, "scout", "all", catalog, False)
    check("AL-05 removal deletes only generated output this scan owns",
          not skill.exists() and not stray.exists()
          and "stale-label" not in (home / "CLAUDE.md").read_text(encoding="utf-8")
          and (local / "rules/ownrule.md").is_file()
          and (home / "settings.json").is_file()
          and (home / "memory/note.md").read_text(encoding="utf-8") == "memory\n"
          and (home / "runtime/state.txt").read_text(encoding="utf-8") == "runtime\n"
          and (home / "unmanaged.txt").read_text(encoding="utf-8") == "leave me\n"
          and (home / "prompt.md").read_text(encoding="utf-8") == "Prompt.\n",
          "")

    tools_rule = (home / MATRIX["rule"]["claude"].format(name=TOOLS_RULE)).read_text(encoding="utf-8")
    linked = list(bin_dir().glob("owntool*"))
    check("AL-06 local tool is listed and not linked",
          "rbtv/capabilities/tools/owntool/owntool.py" in tools_rule
          and "this agent" in tools_rule and not linked
          and "from the agent folder" in tools_rule,
          tools_rule)
    _w(tool / "owntool.py", "print('no shebang')\n")
    (tool / "owntool.py").chmod(0o755)
    before = _snap(home)
    with _casts()[0], _casts()[1]:
        refused = _refused(lambda: update_agent(ws, "scout", "all", catalog, False))
    check("AL-06 missing executable refuses",
          refused is not None and refused.code == "path-not-runnable"
          and _snap(home) == before,
          "" if refused is None else refused.message)
    _w(tool / "owntool.py", "#!/usr/bin/env python3\nprint('own')\n")
    (tool / "owntool.py").chmod(0o755)

    ship_root = tmp / "al-ship"
    ship_cat, _ship = _source(ship_root)
    ship_ws = tmp / "al-ship-install"
    ship_ws.mkdir()
    with _casts()[0], _casts()[1]:
        placed = add_agent(ship_ws, "porter", [], set(), ship_cat, False, _LAUNCH)
    porter = ship_ws / ".rbtv/agents/porter"
    check("AL-07 shipped add copies rbtv/",
          (porter / "rbtv/skills/kept.md").is_file()
          and (porter / "prompt.md").is_file()
          and any(name.startswith("rbtv/") for name in placed["placed"]["files"])
          and SHIPPED_FIELD in json.loads((porter / "agent.json").read_text(encoding="utf-8")),
          str(placed.get("placed")))

    _w(ship_root / "ship/box/agents/porter/rbtv/skills/kept.md",
       "---\nname: kept\ndescription: \"The kept skill\"\n---\n\nshipped kept again\n")
    _w(porter / "rbtv/skills/edited.md",
       "---\nname: edited\ndescription: \"The edited skill\"\n---\n\nlocal edit\n")
    prompt_before = (porter / "prompt.md").read_bytes()
    with _casts()[0], _casts()[1]:
        update_agent(ship_ws, "porter", "all", ship_cat, False)
    check("AL-08 update keeps a local edit and refreshes an unedited file",
          "shipped kept again" in (porter / "rbtv/skills/kept.md").read_text(encoding="utf-8")
          and "local edit" in (porter / "rbtv/skills/edited.md").read_text(encoding="utf-8")
          and (porter / "prompt.md").read_bytes() == prompt_before
          and (porter / "settings.json").is_file(),
          "")

    _w(ship_root / "ship/box/agents/porter/rbtv/skills/edited.md",
       "---\nname: edited\ndescription: \"The edited skill\"\n---\n\nshipped edit\n")
    local_edit = (porter / "rbtv/skills/edited.md").read_bytes()
    with _casts()[0], _casts()[1]:
        refused = _refused(lambda: update_agent(ship_ws, "porter", "all", ship_cat, False))
    side = porter / "rbtv/skills/edited.md.shipped"
    check("AL-09 both sides changed keeps both versions",
          refused is not None and refused.code == "shipped-conflict"
          and (porter / "rbtv/skills/edited.md").read_bytes() == local_edit
          and side.is_file() and b"shipped edit" in side.read_bytes(),
          "" if refused is None else refused.message)

    if shutil.which("git") is None:
        check("AL-10 gitignore update", False, "git is unavailable")
    else:
        repo = tmp / "al-ignore"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        agent = repo / ".rbtv/agents/scout"
        _agent(agent, "scout")
        _w(agent / ".gitignore", "# keep me\n" + (agent / ".gitignore").read_text(encoding="utf-8")
           if (agent / ".gitignore").is_file() else "# keep me\n")
        # The folder was just created without an ignore file.
        _w(agent / ".gitignore", "# keep me\n# rbtv: harness files and machine data\nstate.sqlite*\n")
        with _casts()[0], _casts()[1]:
            update_agent(repo, "scout", "all", catalog, False)
        text = (agent / ".gitignore").read_text(encoding="utf-8")

        def ignored(rel: str) -> bool:
            return subprocess.run(
                ["git", "check-ignore", "--quiet", "--no-index", "--", str(agent / rel)],
                cwd=repo, check=False).returncode == 0

        check("AL-10 gitignore update keeps unrelated lines and ignores runtime",
              text.startswith("# keep me\n") and ignored("settings.json")
              and ignored("runtime/x") and ignored("tmp/x")
              and ignored("state.sqlite") and ignored(".claude/skills/z/SKILL.md")
              and not ignored("rbtv/skills/x.md") and not ignored("work/n.md")
              and not ignored("memory/n.md") and not ignored("_artifacts/board.md")
              and reconcile_ignore("# author\n").startswith("# author\n"),
              text)

    fresh = ws / ".rbtv/agents/fresh"
    _agent(fresh, "fresh")
    (fresh / "agent.json").write_text(json.dumps({
        "name": "fresh", "description": "Agent.", "harness": "claude",
        "model": "haiku-5-5", "effort": "high", "files": [], "packs": []}) + "\n",
        encoding="utf-8")
    with _casts()[0], _casts()[1]:
        add_agent(ws, "fresh", [], set(), catalog, False)
    rule_count = list(fresh.rglob("agent-folder.md"))
    check("AL-11 foundations applies with no pack flag",
          any(path.name == "agent-folder.md" for path in rule_count)
          and "foundations" in json.loads((fresh / "agent.json").read_text(encoding="utf-8"))["packs"],
          str([path.relative_to(fresh).as_posix() for path in rule_count]))
    once = ws / ".rbtv/agents/once"
    _agent(once, "once")
    with _casts()[0], _casts()[1]:
        add_agent(ws, "once", [], {"ignite"}, catalog, False)
    copies = [path for path in once.rglob("agent-folder.md")]
    check("AL-11 foundations and ignite install the rule once",
          len(copies) == 1,
          str([path.relative_to(once).as_posix() for path in copies]))

    with _casts()[0], _casts()[1]:
        remove_agent(ws, "fresh", [], {("foundations")}, False, False, catalog, False)
        update_agent(ws, "fresh", "all", catalog, False)
    gone = json.loads((fresh / "agent.json").read_text(encoding="utf-8"))
    check("AL-12 remove foundations writes the exclusion and update leaves it",
          gone.get(EXCLUDE_FIELD) is True and "foundations" not in gone["packs"]
          and not any(fresh.rglob("agent-folder.md")),
          str(gone.get(EXCLUDE_FIELD)))
    gone.pop(EXCLUDE_FIELD)
    _w(fresh / "agent.json", json.dumps(gone, indent=2) + "\n")
    with _casts()[0], _casts()[1]:
        update_agent(ws, "fresh", "all", catalog, False)
    back = json.loads((fresh / "agent.json").read_text(encoding="utf-8"))
    check("AL-12 deleting the exclusion brings the rule back",
          EXCLUDE_FIELD not in back and "foundations" in back["packs"]
          and any(fresh.rglob("agent-folder.md")),
          str(back.get("packs")))

    real = REPO_ROOT / "core/rbtv/packs/foundations.json"
    listed = json.loads(real.read_text(encoding="utf-8"))["files"]
    check("AL-11 shipped foundations pack names the agent-folder rule",
          listed == ["core/rbtv#agent-folder"]
          and (REPO_ROOT / "core/rbtv/rules/agent-folder.md").is_file(),
          str(listed))
    # attach_local is the scan hook an agent-folder install uses.
    bound = attach_local(catalog, home)
    check("AL-01 local catalog id is not a component id",
          bound["local/scout"]["tree"] == "local" and "local/scout" not in catalog,
          "")
