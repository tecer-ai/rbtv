"""Agent-local source, shipped rbtv/ copy, and the foundations pack."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

from discovery import Refuse, scan_all
from lib.agents import add_agent, remove_agent, update_agent
from lib.constants import MATRIX, REPO_ROOT, TOOLS_RULE
from lib.pathlinks import bin_dir

from .fixture import _component, _file_md, _w

_KNOWN = {"claude": {"example-model": {"rungs": ["low", "high"], "selected": True}},
          "codex": {"c1": {"rungs": ["low", "high"], "selected": True}},
          "opencode": {"example-model": {"rungs": ["low", "high"], "selected": True}}}
_LAUNCH = {"harness": "claude", "model": "example-model", "effort": "high"}
_EXCLUDE = "exclude_foundations"
_SHIPPED = "shipped_rbtv"


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
        "model": "example-model", "effort": "high", "files": [], "packs": []}) + "\n")


def _snap(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def _refused(call):
    try:
        call()
    except Refuse as exc:
        return exc
    return None


def _catalog(root: Path) -> dict:
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
    catalog, _ = scan_all(root.parent / "al-mirror", root)
    return catalog


def agent_local(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    catalog = _catalog(tmp / "al-source")
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
    harness_ok = all(
        (home / MATRIX[method][harness].format(name=name)).is_file()
        for method, name in (("skill", "own"), ("rule", "ownrule"), ("command", "owncmd"))
        for harness in ("claude", "codex", "opencode"))
    settings = (home / ".claude/settings.json").read_text(encoding="utf-8") if (
        home / ".claude/settings.json").is_file() else ""
    mcp = (home / ".mcp.json").read_text(encoding="utf-8") if (home / ".mcp.json").is_file() else ""
    opencode = (home / "opencode.json").read_text(encoding="utf-8") if (
        home / "opencode.json").is_file() else ""
    try:
        from discovery import attach_local
        bound = attach_local(catalog, home)
        local_id_ok = bound["local/scout"]["tree"] == "local"
    except (ImportError, KeyError, Refuse):
        local_id_ok = False
    check("AL-01 local source installs for every harness",
          harness_ok and "PreToolUse" in settings and "ownmcp" in mcp
          and "ownmcp" in opencode and local_id_ok,
          "")
    record = json.loads((home / "agent.json").read_text(encoding="utf-8"))
    check("AL-02 local files stay out of the record and invalid source writes nothing",
          harness_ok and "local/scout#own" not in record.get("files", []),
          str(record.get("files")))

    bad = ws / ".rbtv/agents/bad"
    _agent(bad, "bad")
    _w(bad / "rbtv/skills/broken.md", "---\nname: broken\n---\n\nno description\n")
    before = _snap(ws)
    with _casts()[0], _casts()[1]:
        refused = _refused(lambda: update_agent(ws, "bad", "all", catalog, False))
    check("AL-03 invalid local source refuses before any write",
          refused is not None and "broken.md" in refused.message
          and "Rename" not in refused.message and _snap(ws) == before,
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
          and "Rename" in refused.message and _snap(ws) == before,
          "" if refused is None else refused.message)

    installed = (home / MATRIX["skill"]["claude"].format(name="own")).is_file()
    _w(home / "memory/note.md", "memory\n")
    _w(home / "runtime/state.txt", "runtime\n")
    _w(home / "unmanaged.txt", "leave me\n")
    stray = home / ".claude/skills/stray/SKILL.md"
    _w(stray, "<!-- rbtv-managed — generated -->\nstray\n")
    _w(home / "CLAUDE.md",
       "<!-- rbtv:start stale-label -->\nstale\n<!-- rbtv:end stale-label -->\n")
    with _casts()[0], _casts()[1]:
        update_agent(ws, "scout", "all", catalog, False)
    stray_gone = not stray.exists()
    fence_gone = "stale-label" not in (home / "CLAUDE.md").read_text(encoding="utf-8")
    (local / "skills/own.md").unlink()
    with _casts()[0], _casts()[1]:
        update_agent(ws, "scout", "all", catalog, False)
    check("AL-05 removal deletes only generated output this scan owns",
          installed and not (home / MATRIX["skill"]["claude"].format(name="own")).exists()
          and stray_gone and fence_gone
          and (local / "rules/ownrule.md").is_file()
          and (home / "settings.json").is_file()
          and (home / "memory/note.md").read_text(encoding="utf-8") == "memory\n"
          and (home / "runtime/state.txt").read_text(encoding="utf-8") == "runtime\n"
          and (home / "unmanaged.txt").read_text(encoding="utf-8") == "leave me\n"
          and (home / "prompt.md").read_text(encoding="utf-8") == "Prompt.\n",
          "")

    tools_rule = ""
    rule_path = home / MATRIX["rule"]["claude"].format(name=TOOLS_RULE)
    if rule_path.is_file():
        tools_rule = rule_path.read_text(encoding="utf-8")
    _w(tool / "owntool.py", "print('no shebang')\n")
    (tool / "owntool.py").chmod(0o755)
    before = _snap(home)
    with _casts()[0], _casts()[1]:
        refused = _refused(lambda: update_agent(ws, "scout", "all", catalog, False))
    check("AL-06 local tool is listed, not linked, and a bad executable refuses",
          "rbtv/capabilities/tools/owntool/owntool.py" in tools_rule
          and "this agent" in tools_rule and not list(bin_dir().glob("owntool*"))
          and refused is not None and refused.code == "path-not-runnable"
          and _snap(home) == before,
          "" if refused is None else refused.message)
    _w(tool / "owntool.py", "#!/usr/bin/env python3\nprint('own')\n")
    (tool / "owntool.py").chmod(0o755)

    ship = tmp / "al-ship"
    box = _component(ship, "ship", "box")
    _w(box / "agents/porter/prompt.md", "Porter.\n")
    _w(box / "agents/porter/agent.json", json.dumps({
        "name": "porter", "description": "Shipped porter."}) + "\n")
    _skill(box / "agents/porter/rbtv/skills/kept.md", "kept", "shipped kept\n")
    _skill(box / "agents/porter/rbtv/skills/edited.md", "edited", "shipped edited\n")
    ship_cat, _ = scan_all(tmp / "al-ship-mirror", ship)
    ship_ws = tmp / "al-ship-install"
    ship_ws.mkdir()
    with _casts()[0], _casts()[1]:
        placed = add_agent(ship_ws, "porter", [], set(), ship_cat, False, _LAUNCH)
    porter = ship_ws / ".rbtv/agents/porter"
    placed_files = (placed.get("placed") or {}).get("files") or []
    porter_record = json.loads((porter / "agent.json").read_text(encoding="utf-8")) if (
        porter / "agent.json").is_file() else {}
    check("AL-07 shipped add copies rbtv/",
          (porter / "rbtv/skills/kept.md").is_file()
          and any(name.startswith("rbtv/") for name in placed_files)
          and _SHIPPED in porter_record,
          str(placed_files))

    _w(box / "agents/porter/rbtv/skills/kept.md",
       "---\nname: kept\ndescription: \"The kept skill\"\n---\n\nshipped kept again\n")
    _w(porter / "rbtv/skills/edited.md",
       "---\nname: edited\ndescription: \"The edited skill\"\n---\n\nlocal edit\n")
    prompt_before = (porter / "prompt.md").read_bytes()
    with _casts()[0], _casts()[1]:
        update_agent(ship_ws, "porter", "all", ship_cat, False)
    kept_text = (porter / "rbtv/skills/kept.md").read_text(encoding="utf-8") if (
        porter / "rbtv/skills/kept.md").is_file() else ""
    edited_text = (porter / "rbtv/skills/edited.md").read_text(encoding="utf-8") if (
        porter / "rbtv/skills/edited.md").is_file() else ""
    check("AL-08 update keeps a local edit and refreshes an unedited file",
          "shipped kept again" in kept_text and "local edit" in edited_text
          and (porter / "prompt.md").is_file()
          and (porter / "prompt.md").read_bytes() == prompt_before,
          "")

    _w(box / "agents/porter/rbtv/skills/edited.md",
       "---\nname: edited\ndescription: \"The edited skill\"\n---\n\nshipped edit\n")
    edited_path = porter / "rbtv/skills/edited.md"
    local_edit = edited_path.read_bytes() if edited_path.is_file() else b""
    with _casts()[0], _casts()[1]:
        refused = _refused(lambda: update_agent(ship_ws, "porter", "all", ship_cat, False))
    side = porter / "rbtv/skills/edited.md.shipped"
    check("AL-09 both sides changed keeps both versions",
          refused is not None and refused.code == "shipped-conflict"
          and edited_path.is_file() and edited_path.read_bytes() == local_edit
          and side.is_file() and b"shipped edit" in side.read_bytes(),
          "" if refused is None else refused.message)

    ignore_ok = False
    if shutil.which("git") is None:
        check("AL-10 gitignore update", False, "git is unavailable")
    else:
        repo = tmp / "al-ignore"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        agent = repo / ".rbtv/agents/scout"
        _agent(agent, "scout")
        _w(agent / ".gitignore",
           "# keep me\n# rbtv: harness files and machine data\nstate.sqlite*\n")
        with _casts()[0], _casts()[1]:
            update_agent(repo, "scout", "all", catalog, False)
        text = (agent / ".gitignore").read_text(encoding="utf-8")

        def ignored(rel: str) -> bool:
            return subprocess.run(
                ["git", "check-ignore", "--quiet", "--no-index", "--", str(agent / rel)],
                cwd=repo, check=False).returncode == 0

        ignore_ok = (text.startswith("# keep me\n") and ignored("settings.json")
                     and ignored("runtime/x") and ignored("tmp/x")
                     and ignored("state.sqlite") and ignored("turns/t")
                     and ignored(".claude/skills/z/SKILL.md")
                     and not ignored("rbtv/skills/x.md") and not ignored("work/n.md")
                     and not ignored("memory/n.md")
                     and not ignored("_artifacts/board.md"))
        check("AL-10 gitignore update keeps unrelated lines and ignores runtime",
              ignore_ok, text)

    fresh = ws / ".rbtv/agents/fresh"
    _agent(fresh, "fresh")
    with _casts()[0], _casts()[1]:
        add_agent(ws, "fresh", [], set(), catalog, False)
    fresh_record = json.loads((fresh / "agent.json").read_text(encoding="utf-8"))
    once = ws / ".rbtv/agents/once"
    _agent(once, "once")
    with _casts()[0], _casts()[1]:
        add_agent(ws, "once", [], {"ignite"}, catalog, False)
    copies = list(once.rglob("agent-folder.md"))
    pack_ok = json.loads((REPO_ROOT / "core/rbtv/packs/foundations.json").read_text(
        encoding="utf-8"))["files"] == ["core/rbtv#agent-folder"]
    check("AL-11 foundations applies by default and overlaps once",
          pack_ok and "foundations" in fresh_record.get("packs", [])
          and any(fresh.rglob("agent-folder.md")) and len(copies) == 1,
          str([path.relative_to(once).as_posix() for path in copies]))

    with _casts()[0], _casts()[1]:
        remove_agent(ws, "fresh", [], {"foundations"}, False, False, catalog, False)
        update_agent(ws, "fresh", "all", catalog, False)
    gone = json.loads((fresh / "agent.json").read_text(encoding="utf-8"))
    stayed = gone.get(_EXCLUDE) is True and "foundations" not in gone.get("packs", [])
    stayed = stayed and not any(fresh.rglob("agent-folder.md"))
    gone.pop(_EXCLUDE, None)
    _w(fresh / "agent.json", json.dumps(gone, indent=2) + "\n")
    with _casts()[0], _casts()[1]:
        update_agent(ws, "fresh", "all", catalog, False)
    back = json.loads((fresh / "agent.json").read_text(encoding="utf-8"))
    check("AL-12 exclusion survives update and returns when deleted",
          stayed and _EXCLUDE not in back and "foundations" in back.get("packs", [])
          and any(fresh.rglob("agent-folder.md")),
          str(back.get("packs")))
