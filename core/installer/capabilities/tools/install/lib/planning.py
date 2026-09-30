"""Turning the chosen components into the exact set of files and claims a run
would write.
"""
from __future__ import annotations

from pathlib import Path

from discovery import Refuse, SKILL_FILE, unit_rows

from . import frontmatter
from .constants import (
    CANONICAL_METHODS,
    GUIDANCE_FILE,
    HARNESSES,
    HOOK_HARNESSES,
    MATRIX,
    RULE_SECTION_HARNESSES,
    CODEX_PROJECT_DOC_MAX_BYTES,
    SKILL_FOLDER_SKIP,
)
from .catalog import _unit_specs
from .content import (
    _claude_mcp_entry,
    _codex_mcp_toml_block,
    _content_for,
    _mark,
    _opencode_mcp_entry,
)
from .state import _wanted_units
from .recovery import vanished_component_message


def plan_files(records: dict[str, dict], catalog: dict[str, dict],
               target: Path | None = None
               ) -> tuple[dict[str, str], dict[str, list], list[dict], dict]:
    """The COMPLETE set of whole files AND shared-file claims the installed set
    implies (D7). Every gate fires here, before any write — a refusal leaves
    zero files.

    Returns (rel -> content, rel -> owning component ids, claims, report).
    """
    files: dict[str, str] = {}
    owners: dict[str, list] = {}
    servers: dict[str, dict] = {}
    server_harnesses: set[str] = set()
    server_owners: dict[str, list] = {}
    hooks: dict[str, list] = {}
    hook_harnesses: set[str] = set()
    hook_owners: dict[str, list] = {}
    sections: list[dict] = []
    report: dict = {"no_realization": [], "skill_folders": [], "path_rows": []}
    codex_used = False

    def claim_file(rel: str, content: str, cid: str, pid: str) -> None:
        if rel in files and files[rel] != content:
            other = owners[rel][0]
            other_cid = other[0] if isinstance(other, tuple) else other
            raise Refuse(
                "unit-collision",
                f"components {other_cid!r} and {cid!r} both realize "
                f"{rel!r} with different content — two components exposing the "
                "same unit name is a conflict, not something to resolve "
                "by write order",
                rel)
        files[rel] = content
        owners.setdefault(rel, []).append((cid, pid))

    def claim_skill_folder(comp: dict, cid: str, harnesses: list[str]) -> None:
        """D15 — copy the whole folder into each harness's skills directory.

        The root `SKILL.md` is the ONE file we stamp (`_mark`); everything else
        is copied byte-for-byte, so a reference, a licence or a binary asset
        arrives unchanged. Paths shared by several harnesses dedupe on the
        template, exactly as the thin-loader `skill` row already does."""
        comp_dir = Path(comp["path"])
        named = comp["component"]
        if named.startswith("rbtv-"):
            raise Refuse(
                "unit-name-reserved",
                f"{cid}: a skill folder named {named!r} would land under "
                "`rbtv-*`, which the OLD installer sweeps out of "
                "`.claude/skills/` on every run — rename the folder (D12)",
                str(comp_dir))
        members: list[tuple[str, str | bytes]] = []
        for path in sorted(comp_dir.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            member = path.relative_to(comp_dir)
            if any(part in SKILL_FOLDER_SKIP for part in member.parts):
                continue
            raw = path.read_bytes()
            if member.as_posix() == SKILL_FILE:
                body: str | bytes = _mark(raw.decode("utf-8"))
            else:
                try:
                    body = raw.decode("utf-8")
                except UnicodeDecodeError:
                    body = raw               # a binary asset rides along whole
            members.append((member.as_posix(), body))
        roots = {MATRIX["skill"][h].rsplit("/", 1)[0].format(name=named)
                 for h in harnesses if MATRIX["skill"].get(h)}
        for root_rel in sorted(roots):
            for member, body in members:
                claim_file(f"{root_rel}/{member}", body, cid, named)
        report["skill_folders"].append(
            {"component": cid, "files": len(members),
             "roots": sorted(roots)})

    for cid in sorted(records):
        rec = records[cid]
        comp = catalog.get(cid)
        if comp is None:
            raise Refuse(
                "component-vanished",
                vanished_component_message(cid, rec.get("tree_root"), target),
                str(rec.get("tree_root", "")))
        comp_dir = Path(comp["path"])
        harnesses = [h for h in HARNESSES if h in rec["harnesses"]]
        codex_used = codex_used or "codex" in harnesses

        wanted = _wanted_units(rec)
        if comp.get("kind") == "hub":
            pid = comp["component"]
            if wanted is not None and pid not in wanted:
                continue
            claim_skill_folder(comp, cid, harnesses)
            continue
        _unit_specs(comp)
        for row in unit_rows(comp):
            pid, method = row["id"], row["method"]
            entry_rel, desc = row["entry"], row["description"]
            if wanted is not None and pid not in wanted:
                continue
            if method not in CANONICAL_METHODS:
                raise Refuse(
                    "method-unknown",
                    f"{cid}: unit {pid!r} has method {method!r}, which is "
                    f"outside the vocabulary ({' · '.join(CANONICAL_METHODS)}) "
                    "— refusing before any write", str(comp_dir / entry_rel))
            if method == "tool":
                report["path_rows"].append(
                    {"component": cid, "part": pid, "type": method,
                     "entry_point": entry_rel, "comp_dir": str(comp_dir)})
                continue
            if pid.startswith("rbtv-"):
                raise Refuse(
                    "unit-name-reserved",
                    f"{cid}: unit {pid!r} starts with `rbtv-`, the "
                    "prefix the OLD installer sweeps out of "
                    "`.claude/{rules,commands,agents,skills}` on every run "
                    "(generator.py::clear_previous_install) — a file minted "
                    "under that name would be deleted behind this installer's "
                    "back. Rename the unit (D12)",
                    str(comp_dir / entry_rel))
            entry_abs = str((comp_dir / entry_rel).resolve())
            data = row["data"]

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
                item = {"hooks": [handler]}
                if "matcher" in data:
                    item = {"matcher": data["matcher"], **item}
                hooks.setdefault(data["event"], []).append(item)
                if (cid, pid) not in hook_owners.setdefault(data["event"], []):
                    hook_owners[data["event"]].append((cid, pid))
                hook_harnesses |= set(harnesses)
                for harness in harnesses:
                    if harness not in HOOK_HARNESSES:
                        report["no_realization"].append(
                            {"component": cid, "part": pid, "type": method,
                             "harness": harness})
                continue

            if method == "rule":
                readers = [h for h in harnesses if h in RULE_SECTION_HARNESSES]
                if readers:
                    _front, body = frontmatter.split(
                        (comp_dir / entry_rel).read_text(encoding="utf-8"))
                    sections.append({"owner": (cid, pid), "harnesses": readers,
                                     "label": f"rule {comp['module']}/{comp['component']}#{pid}",
                                     "target": ".", "body": body.strip("\r\n")})
            for harness in harnesses:
                template = MATRIX[method].get(harness)
                if template is None:
                    if method == "rule" and harness in RULE_SECTION_HARNESSES:
                        continue
                    report["no_realization"].append(
                        {"component": cid, "part": pid, "type": method,
                         "harness": harness})
                    continue
                rel = template.format(name=pid)
                claim_file(rel, _content_for(
                    rel, method, pid, desc, entry_abs, comp_dir, entry_rel),
                    cid, pid)

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
        claims.append({"path": ".codex/config.toml", "fmt": "text",
                       "comment": "#", "key": None, "label": "codex-limits",
                       "value": f"project_doc_max_bytes = {CODEX_PROJECT_DOC_MAX_BYTES}",
                       "first": True})
    if servers:
        if "claude" in server_harnesses:
            for name in sorted(servers):
                for owner in _owners_of(server_owners, name) or [None]:
                    claim_json(".mcp.json", ["mcpServers", name],
                               _claude_mcp_entry(servers[name]), owner)
            # measured 2026-08-08, claude 2.1.226: without the flag every
            # project server sits "Pending approval".
            for owner in _all_owners(server_owners) or [None]:
                claim_json(".claude/settings.json",
                           ["enableAllProjectMcpServers"], True, owner)
        if "codex" in server_harnesses:
            for owner in _all_owners(server_owners) or [None]:
                rec = {"path": ".codex/config.toml", "fmt": "text",
                       "comment": "#", "key": None,
                       "value": _codex_mcp_toml_block(servers)}
                if owner is not None:
                    rec["owner"] = owner
                claims.append(rec)
        if "opencode" in server_harnesses:
            for name in sorted(servers):
                for owner in _owners_of(server_owners, name) or [None]:
                    claim_json("opencode.json", ["mcp", name],
                               _opencode_mcp_entry(servers[name]), owner)
    if hooks:
        for event in sorted(hooks):
            ev_owners = _owners_of(hook_owners, event) or [None]
            if "claude" in hook_harnesses:
                for owner in ev_owners:
                    claim_json(".claude/settings.json", ["hooks", event],
                               hooks[event], owner)
            if "codex" in hook_harnesses:
                # codex 0.144.5 measured shape: the claude `hooks` object
                # verbatim (d-seat-exposes-frontmatter measurement amendment).
                for owner in ev_owners:
                    claim_json(".codex/hooks.json", ["hooks", event],
                               hooks[event], owner)
        # opencode has no hooks surface — nothing is minted for it.

    # A component's folder instructions: one marked section per component in
    # the instructions file of every installed harness, inside the target
    # folder. Text outside the markers is never touched.
    # Component sections first, rule sections after: AGENTS.md can be a mirror
    # of CLAUDE.md, which carries only the component sections, so rules must be
    # the ones appended last or their place would flip between runs.
    for section in sorted(sections, key=lambda s: s["label"].startswith("rule ")):
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
