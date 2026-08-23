"""Turning the chosen components into the exact set of files and claims a run
would write.
"""
from __future__ import annotations

import json
from pathlib import Path

from discovery import EXPOSURE_NAME, Refuse, SKILL_FILE, exposure_rows

from .constants import (
    CANONICAL_METHODS,
    HARNESSES,
    INVENTORY_METHODS,
    MATRIX,
    SKILL_FOLDER_SKIP,
)
from .catalog import _hub_refuse_message, _part_specs
from .content import (
    _codex_mcp_toml_block,
    _content_for,
    _mark,
    _opencode_mcp_entry,
)
from .state import _wanted_parts


def plan_files(records: dict[str, dict], catalog: dict[str, dict]
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
    agents_parts: list[tuple[str, str, str]] = []
    rule_parts: list[tuple[str, str]] = []
    report: dict = {"skipped_inventory_rows": [], "no_realization": [],
                    "skill_folders": [], "path_rows": []}

    def claim_file(rel: str, content: str, cid: str, pid: str) -> None:
        if rel in files and files[rel] != content:
            other = owners[rel][0]
            other_cid = other[0] if isinstance(other, tuple) else other
            raise Refuse(
                "part-collision",
                f"components {other_cid!r} and {cid!r} both realize "
                f"{rel!r} with different content — two components exposing the "
                "same part id is a manifest conflict, not something to resolve "
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
                "part-id-reserved",
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
                f"component {cid!r} is recorded as installed but no longer "
                f"exists under {rec.get('tree_root')!r} (renamed or deleted "
                "upstream). Every run at this target refuses until the book "
                "agrees with the trees. Recover with EITHER: restore the "
                f"folder; or `uninstall --component {cid}`, which needs no "
                "tree — the book holds its files",
                str(rec.get("tree_root", "")))
        comp_dir = Path(comp["path"])
        harnesses = [h for h in HARNESSES if h in rec["harnesses"]]

        wanted = _wanted_parts(rec)
        if comp.get("kind") == "hub":
            if comp.get("hub_refusal"):
                raise Refuse(comp["hub_refusal"],
                             _hub_refuse_message(comp), comp["path"])
            if comp.get("method") == "skill":
                pid = comp["component"]
                if wanted is not None and pid not in wanted:
                    continue
                claim_skill_folder(comp, cid, harnesses)
                continue
            src = Path(comp["path"])
            if src.is_file():
                comp_dir = src.parent
            rows = [{"part-id": comp["component"],
                     "method": comp["method"],
                     "entry-point": src.name,
                     "description": ""}]
        else:
            _part_specs(comp, strict=True)
            rows = exposure_rows(comp)
        for row in rows:
            pid = (row.get("part-id") or "").strip()
            method = (row.get("method") or "").strip()
            entry_rel = (row.get("entry-point") or "").strip()
            desc = (row.get("description") or "").strip()
            if not pid:
                continue
            if wanted is not None and pid not in wanted:
                continue
            if method not in CANONICAL_METHODS:
                raise Refuse(
                    "method-unknown",
                    f"{cid}: exposure row {pid!r} declares method "
                    f"{method or '(empty)'!r}, which is outside the canonical "
                    f"vocabulary ({' · '.join(CANONICAL_METHODS)}) — "
                    "d-exposure-method-canon; refusing before any write",
                    str(comp_dir / EXPOSURE_NAME))
            if method in INVENTORY_METHODS:
                # D9 — pool is inventory only. path is collected below.
                report["skipped_inventory_rows"].append(
                    {"component": cid, "part": pid, "method": method,
                     "entry_point": entry_rel})
                continue
            if method == "path":
                report["path_rows"].append(
                    {"component": cid, "part": pid, "method": method,
                     "entry_point": entry_rel, "comp_dir": str(comp_dir)})
                continue
            if not entry_rel:
                raise Refuse(
                    "entry-point-missing",
                    f"{cid}: exposure row {pid!r} ({method}) declares no "
                    "entry-point — there is nothing to realize",
                    str(comp_dir / EXPOSURE_NAME))
            # D11 — a `file.csv#row` reference is checked at its file half.
            entry_file = entry_rel.split("#", 1)[0]
            if not (comp_dir / entry_file).is_file():
                raise Refuse(
                    "entry-point-missing",
                    f"{cid}: exposure row {pid!r} ({method}) points at "
                    f"{entry_rel!r}, which resolves to no file under the "
                    "component — refusing before any write",
                    str(comp_dir / entry_file))
            entry_abs = str((comp_dir / entry_file).resolve())
            entry_ref = entry_abs + (("#" + entry_rel.split("#", 1)[1])
                                     if "#" in entry_rel else "")
            if pid.startswith("rbtv-"):
                raise Refuse(
                    "part-id-reserved",
                    f"{cid}: exposure row {pid!r} starts with `rbtv-`, the "
                    "prefix the OLD installer sweeps out of "
                    "`.claude/{rules,commands,agents,skills}` on every run "
                    "(generator.py::clear_previous_install) — a file minted "
                    "under that name would be deleted behind this installer's "
                    "back. Rename the part (D12)",
                    str(comp_dir / EXPOSURE_NAME))
            named = pid

            if method == "agents.md":
                agents_parts.append((named, desc, entry_ref))
                continue
            if method == "config":
                data = _read_json(comp_dir / entry_file, "config", cid, pid)
                decl = data.get("mcpServers") if isinstance(data, dict) else None
                if decl is None:
                    continue  # another config payload kind — not ours to place
                if not isinstance(decl, dict) or not all(
                        isinstance(v, dict) for v in decl.values()):
                    raise Refuse(
                        "config-declaration-invalid",
                        f"{cid}: config entry-point {entry_rel!r} carries an "
                        "`mcpServers` that is not an object of server objects "
                        "— not the neutral schema "
                        "(d-mcp-registration-is-config)",
                        str(comp_dir / entry_file))
                for name, spec in decl.items():
                    # D12: the registration is claimed under its declared name;
                    # a foreign key of the same name refuses (D6), it is never
                    # renamed around.
                    key = name
                    if key in servers and servers[key] != spec:
                        raise Refuse(
                            "config-server-conflict",
                            f"MCP server {key!r} is declared differently by "
                            "more than one installed component — one "
                            "registration, one home",
                            str(comp_dir / entry_file))
                    servers[key] = spec
                    if (cid, pid) not in server_owners.setdefault(key, []):
                        server_owners[key].append((cid, pid))
                server_harnesses |= set(harnesses)
                continue
            if method == "hook":
                data = _read_json(comp_dir / entry_file, "hook", cid, pid)
                decl = data.get("hooks") if isinstance(data, dict) else None
                if not isinstance(decl, dict):
                    raise Refuse(
                        "hook-declaration-invalid",
                        f"{cid}: hook entry-point {entry_rel!r} carries no "
                        "`hooks` object — the neutral shape is claude's "
                        "settings `hooks` block",
                        str(comp_dir / entry_file))
                for event, entries in decl.items():
                    hooks.setdefault(event, []).extend(
                        entries if isinstance(entries, list) else [entries])
                    if (cid, pid) not in hook_owners.setdefault(event, []):
                        hook_owners[event].append((cid, pid))
                hook_harnesses |= set(harnesses)
                continue

            realized: dict[str, str] = {}
            for harness in harnesses:
                template = MATRIX[method].get(harness)
                if template is None:
                    report["no_realization"].append(
                        {"component": cid, "part": pid, "method": method,
                         "harness": harness})
                    continue
                rel = template.format(name=named)
                claim_file(rel, _content_for(
                    rel, method, named,
                    desc or f"{pid} — exposed via {cid}/{EXPOSURE_NAME}",
                    entry_abs, comp_dir, entry_file), cid, pid)
                realized[harness] = rel
            if method == "rule" and realized:
                # The REALIZED path per harness, not the part id: a component
                # installed for claude only put no file under
                # `.agents/behavior-rules/`, so codex's forced read must not
                # enumerate one (a MANDATORY Step 0 pointing at a missing file).
                rule_parts.append((named, desc, realized))

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

    if servers:
        if "claude" in server_harnesses:
            for name in sorted(servers):
                for owner in _owners_of(server_owners, name) or [None]:
                    claim_json(".mcp.json", ["mcpServers", name],
                               servers[name], owner)
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
        # kimi: no project-local MCP auto-load (measured — `cli/mcp.py` stores
        # servers at `~/.kimi/mcp.json`). The root `.mcp.json` above IS its
        # realization, passed at launch: `kimi --mcp-config-file .mcp.json`.
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
        # opencode has no hooks surface; kimi's hooks are user-scope
        # (`~/.kimi/config.toml` `hooks = [...]`) — neither is minted here.

    # D8 — the exposure surface is the GENERATED GUIDANCE FILE, not a file of
    # this installer's invention. The parts ride the report to `_add_mirror`,
    # which knows the harnesses and therefore which guidance file gets what.
    report["agents_parts"] = agents_parts
    report["rule_parts"] = rule_parts
    report["shared_files"] = sorted({c["path"] for c in claims})
    return files, owners, claims, report


def _read_json(path: Path, method: str, cid: str, pid: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refuse(
            f"{method}-declaration-invalid",
            f"{cid}: {method} entry-point for {pid!r} is not readable JSON "
            f"({exc}) — refusing before any write",
            str(path)) from exc
