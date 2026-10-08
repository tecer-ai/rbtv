"""Turning the chosen components into the exact set of files and claims a run
would write.
"""
from __future__ import annotations

from pathlib import Path

from discovery import Refuse, SKILL_FILE, file_rows

from . import frontmatter
from .constants import (
    CANONICAL_METHODS,
    CLAUDE_MCP_FILE,
    CLAUDE_SETTINGS_FILE,
    CODEX_CONFIG_FILE,
    CODEX_HOOKS_FILE,
    GUIDANCE_FILE,
    HARNESSES,
    HOOK_HARNESSES,
    MATRIX,
    OPENCODE_CONFIG_FILE,
    CODEX_PROJECT_DOC_MAX_BYTES,
    SKILL_FOLDER_SKIP,
    TOOLS_RULE,
)
from .catalog import _file_specs
from .content import (
    _claude_mcp_entry,
    _codex_mcp_toml_block,
    _content_for,
    _mark,
    _opencode_mcp_entry,
    sub_agent_content,
    tools_rule_content,
)
from .state import _wanted_files
from .target import discover_installation, is_agent_target
from .recovery import vanished_component_message


def _installation_of(target: Path | None) -> Path | None:
    """The installation whose `.rbtv/` a file written under `target` reaches:
    the target itself, or, for an agent folder, the installation above it."""
    if target is not None and is_agent_target(target):
        return discover_installation(target.parent)[0]
    return target


def plan_files(records: dict[str, dict], catalog: dict[str, dict],
               target: Path | None = None
               ) -> tuple[dict[str, str | bytes], dict[str, list], list[dict], dict]:
    """The COMPLETE set of whole files AND shared-file claims the installed set
    implies (D7). Every gate fires here, before any write — a refusal leaves
    zero files.

    Returns (rel -> content, rel -> owning component ids, claims, report).
    """
    files: dict[str, str | bytes] = {}
    owners: dict[str, list] = {}
    servers: dict[str, dict] = {}
    server_harnesses: set[str] = set()
    server_owners: dict[str, list] = {}
    hooks: dict[str, list] = {}
    hook_harnesses: set[str] = set()
    hook_owners: dict[str, list] = {}
    sections: list[dict] = []
    instruction_owners: dict[str, list] = {}
    denied_skill_owners: dict[str, list] = {}
    tools: list[dict] = []
    report: dict = {"no_realization": [], "skill_folders": [], "path_rows": [],
                    "sub_agents_unset": []}
    codex_used = False
    installation = _installation_of(target)

    def claim_file(rel: str, content: str | bytes, cid: str, pid: str) -> None:
        if rel in files and files[rel] != content:
            other = owners[rel][0]
            other_cid = other[0] if isinstance(other, tuple) else other
            raise Refuse(
                "file-collision",
                f"components {other_cid!r} and {cid!r} both realize "
                f"{rel!r} with different content — two components exposing the "
                "same file name is a conflict, not something to resolve "
                "by write order",
                rel)
        files[rel] = content
        owners.setdefault(rel, []).append((cid, pid))

    def claim_skill_folder(comp: dict, cid: str, harnesses: list[str]) -> None:
        """D15 — a `_skills/<name>/` skill is copied whole into each harness's
        skills folder. `SKILL.md` is the one file stamped (`_mark`), with its
        own frontmatter kept (harness-specific keys survive); every other
        member arrives byte for byte, so its relative files resolve inside the
        copy."""
        comp_dir = Path(comp["path"])
        named = comp["component"]
        if named.startswith("rbtv-"):
            raise Refuse(
                "name-reserved",
                f"{cid}: a skill folder named {named!r} starts with `rbtv-`, "
                "a prefix reserved for rbtv's own files. Rename the folder",
                str(comp_dir))
        source = comp_dir / SKILL_FILE
        text = source.read_text(encoding="utf-8")
        if frontmatter.split(text)[0] is None:
            raise Refuse("file-invalid", f"{source}: no frontmatter", str(source))
        members: list[tuple[str, str | bytes]] = [(SKILL_FILE, _mark(text))]
        for path in sorted(comp_dir.rglob("*")):
            member = path.relative_to(comp_dir)
            if (path.is_symlink() or not path.is_file() or path == source
                    or any(part in SKILL_FOLDER_SKIP for part in member.parts)):
                continue
            members.append((member.as_posix(), path.read_bytes()))
        roots = {MATRIX["skill"][h].rsplit("/", 1)[0].format(name=named)
                 for h in harnesses if MATRIX["skill"].get(h)}
        for root_rel in sorted(roots):
            for member, body in members:
                claim_file(f"{root_rel}/{member}", body, cid, named)
        report["skill_folders"].append(
            {"component": cid, "files": len(members), "roots": sorted(roots)})

    for cid in sorted(records):
        rec = records[cid]
        comp = catalog.get(cid)
        if comp is None:
            raise Refuse(
                "component-vanished",
                vanished_component_message(cid, rec.get("tree"), target),
                str(target))
        comp_dir = Path(comp["path"])
        harnesses = [h for h in HARNESSES if h in rec["harnesses"]]
        codex_used = codex_used or "codex" in harnesses

        wanted = _wanted_files(rec)
        if comp.get("kind") == "hub":
            pid = comp["component"]
            if wanted is not None and pid not in wanted:
                continue
            claim_skill_folder(comp, cid, harnesses)
            continue
        _file_specs(comp)
        for row in file_rows(comp):
            pid, method = row["id"], row["method"]
            entry_rel, desc = row["entry"], row["description"]
            if wanted is not None and pid not in wanted:
                continue
            if method not in CANONICAL_METHODS:
                raise Refuse(
                    "method-unknown",
                    f"{cid}: file {pid!r} has method {method!r}, which is "
                    f"outside the vocabulary ({' · '.join(CANONICAL_METHODS)}) "
                    "— refusing before any write", str(comp_dir / entry_rel))
            if method == "tool":
                report["path_rows"].append(
                    {"component": cid, "part": pid, "type": method,
                     "entry_point": entry_rel, "comp_dir": str(comp_dir)})
                tools.append({"owner": (cid, pid), "harnesses": harnesses,
                              "row": (comp["module"], pid, desc)})
                continue
            if pid.startswith("rbtv-"):
                raise Refuse(
                    "name-reserved",
                    f"{cid}: file {pid!r} starts with `rbtv-`, a prefix "
                    "reserved for rbtv's own files. Rename the file",
                    str(comp_dir / entry_rel))
            data = row["data"]

            if method == "agent":
                # An agent added with `rbtv add` is a harness-native sub-agent, written
                # only for the harnesses its record holds a model and an effort for.
                values = ((rec.get("selected") or {}).get(pid) or {}).get("sub_agent") or {}
                written = [h for h in harnesses if h in values]
                entry_abs = str((comp_dir / entry_rel).resolve())
                if not written:
                    report["sub_agents_unset"].append(f"{cid}#{pid}")
                for harness in written:
                    rel = MATRIX[method][harness].format(name=pid)
                    claim_file(rel, sub_agent_content(
                        rel, harness, pid, desc, entry_abs, values[harness]),
                        cid, pid)
                continue

            if method == "folder-instructions":
                _front, body = frontmatter.split(
                    (comp_dir / entry_rel).read_text(encoding="utf-8"))
                sections.append({"owner": (cid, pid), "harnesses": harnesses,
                                 "label": f"{comp['module']}/{comp['component']}",
                                 "target": data["target"],
                                 "body": body.strip("\r\n")})
                continue
            if method == "mcp-server":
                spec = ({"url": data["url"]} if "url" in data else
                        {k: data[k] for k in ("command", "args", "env")
                         if data.get(k)})
                if pid in servers and servers[pid] != spec:
                    raise Refuse(
                        "mcp-server-conflict",
                        f"MCP server {pid!r} is declared differently by "
                        "more than one installed component — one "
                        "registration, one home",
                        str(comp_dir / entry_rel))
                servers[pid] = spec
                if (cid, pid) not in server_owners.setdefault(pid, []):
                    server_owners[pid].append((cid, pid))
                server_harnesses |= set(harnesses)
                continue
            if method == "hook":
                handler = {"type": "command", "command": data["command"]}
                if "timeout" in data:
                    handler["timeout"] = data["timeout"]
                group = {"hooks": [handler]}
                if "matcher" in data:
                    group = {"matcher": data["matcher"], **group}
                hooks.setdefault(data["event"], []).append(group)
                if (cid, pid) not in hook_owners.setdefault(data["event"], []):
                    hook_owners[data["event"]].append((cid, pid))
                hook_harnesses |= set(harnesses)
                for harness in harnesses:
                    if harness not in HOOK_HARNESSES:
                        report["no_realization"].append(
                            {"component": cid, "part": pid, "type": method,
                             "harness": harness})
                continue

            for harness in harnesses:
                template = MATRIX[method].get(harness)
                if template is None:
                    report["no_realization"].append(
                        {"component": cid, "part": pid, "type": method,
                         "harness": harness})
                    continue
                rel = template.format(name=pid)
                claim_file(rel, _content_for(
                    rel, method, pid, desc, comp_dir, entry_rel, installation),
                    cid, pid)
                if method == "rule" and harness == "opencode":
                    instruction_owners.setdefault(rel, []).append((cid, pid))
                    if "codex" in harnesses:
                        denied_skill_owners.setdefault(pid, []).append((cid, pid))

    # D31: the installed tools, listed in one rule that every one of them owns,
    # so the file is rewritten when the set changes and leaves with the last.
    listed = [tool["row"] for tool in tools]
    for tool in tools:
        for harness in tool["harnesses"]:
            rel = MATRIX["rule"][harness].format(name=TOOLS_RULE)
            claim_file(rel, tools_rule_content(rel, TOOLS_RULE, listed),
                       *tool["owner"])
            if harness == "opencode":
                instruction_owners.setdefault(rel, []).append(tool["owner"])
                if "codex" in tool["harnesses"]:
                    denied_skill_owners.setdefault(TOOLS_RULE, []).append(tool["owner"])

    # ── D7/D12: shared-file claims, recomputed from the whole set ──
    claims: list[dict] = []

    def claim_json(rel: str, key: list[str], value, owner=None) -> None:
        rec = {"path": rel, "fmt": "json", "key": key, "value": value}
        if owner is not None:
            rec["owner"] = owner
        claims.append(rec)

    def _owners_of(table: dict, key: str) -> list:
        return list(table.get(key) or [])

    def _all_owners(table: dict) -> list:
        seen: list = []
        for key in sorted(table):
            for owner in table[key]:
                if owner not in seen:
                    seen.append(owner)
        return seen

    if codex_used:
        claims.append({"path": CODEX_CONFIG_FILE, "fmt": "text",
                       "comment": "#", "key": None, "label": "codex-limits",
                       "value": f"project_doc_max_bytes = {CODEX_PROJECT_DOC_MAX_BYTES}",
                       "first": True})
    if servers:
        if "claude" in server_harnesses:
            for name in sorted(servers):
                for owner in _owners_of(server_owners, name) or [None]:
                    claim_json(CLAUDE_MCP_FILE, ["mcpServers", name],
                               _claude_mcp_entry(servers[name]), owner)
            # measured 2026-08-08, claude 2.1.226: without the flag every
            # project server sits "Pending approval".
            for owner in _all_owners(server_owners) or [None]:
                claim_json(CLAUDE_SETTINGS_FILE,
                           ["enableAllProjectMcpServers"], True, owner)
        if "codex" in server_harnesses:
            for owner in _all_owners(server_owners) or [None]:
                rec = {"path": CODEX_CONFIG_FILE, "fmt": "text",
                       "comment": "#", "key": None,
                       "value": _codex_mcp_toml_block(servers)}
                if owner is not None:
                    rec["owner"] = owner
                claims.append(rec)
        if "opencode" in server_harnesses:
            for name in sorted(servers):
                for owner in _owners_of(server_owners, name) or [None]:
                    claim_json(OPENCODE_CONFIG_FILE, ["mcp", name],
                               _opencode_mcp_entry(servers[name]), owner)
    if hooks:
        for event in sorted(hooks):
            ev_owners = _owners_of(hook_owners, event) or [None]
            if "claude" in hook_harnesses:
                for owner in ev_owners:
                    claim_json(CLAUDE_SETTINGS_FILE, ["hooks", event],
                               hooks[event], owner)
            if "codex" in hook_harnesses:
                # codex 0.144.5 measured shape: the claude `hooks` object
                # verbatim (d-seat-exposes-frontmatter measurement amendment).
                for owner in ev_owners:
                    claim_json(CODEX_HOOKS_FILE, ["hooks", event],
                               hooks[event], owner)
        # opencode has no hooks surface — nothing is minted for it.
    # OpenCode loads a rule only when opencode.json lists its file: one key
    # holding every rule copy, relative to the folder opencode.json sits in
    # (the file can be committed and read on another machine), claimed once
    # per owning rule.
    for owner in _all_owners(instruction_owners):
        claim_json(OPENCODE_CONFIG_FILE, ["instructions"],
                   sorted(instruction_owners), owner)
    # OpenCode also lists the skills in `.agents/skills/`, where Codex's copy
    # of a rule sits. A rule both harnesses receive is denied there as a
    # skill, so OpenCode holds it once, through `instructions`. Measured
    # 2026-10-08, opencode 1.17.18: a denied skill leaves the agent's list.
    for name in sorted(denied_skill_owners):
        for owner in denied_skill_owners[name]:
            claim_json(OPENCODE_CONFIG_FILE, ["permission", "skill", name],
                       "deny", owner)

    # A component's folder instructions: one marked section per component in
    # the instructions file of every installed harness, inside the target
    # folder. Text outside the markers is never touched.
    for section in sections:
        folder = "" if section["target"] == "." else section["target"] + "/"
        for name in sorted({GUIDANCE_FILE[h] for h in section["harnesses"]
                            if h in GUIDANCE_FILE}):
            claims.append({"path": folder + name, "fmt": "text",
                           "comment": "<!--", "key": None,
                           "label": section["label"],
                           "value": section["body"],
                           "owner": section["owner"]})

    report["shared_files"] = sorted({c["path"] for c in claims})
    return files, owners, claims, report
