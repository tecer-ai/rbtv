"""Installer discovery — modules, components and their units, read from the
folder layout. Roots are ARGUMENTS. The installer keeps `REPO_ROOT` (the repo
that ships install.py); the caller passes the workspace mirror and that root.
One scan, one merge (mirror wins), one unit reader.

A module is a folder holding `<module>/<module>.json`; a component is a folder
inside it holding `<component>/<component>.json`. The folder a file sits in
decides how it is exposed: `skills/`, `rules/`, `commands/`, `agents/`,
`hooks/`, `mcp-servers/`, `capabilities/tools/<tool>/`, `folder-instructions/`.
Whole-folder skills live only in the mirror, under `_skills/<name>/`.

This module deliberately sits BESIDE install.py rather than inside its `lib/`
package: the installer puts this directory on `sys.path` and imports it by bare
name (`from discovery import`).
"""
from __future__ import annotations

import json
from pathlib import Path

from lib import frontmatter, schema


WS_PREFIX = "ws:"
HUB_DIR = "_hub"          # only the id prefix of whole-folder skills, `_hub/skills/<name>`
SKILLS_DIR = "_skills"
SKILL_FILE = "SKILL.md"

# Folder -> method, for the units that are one `<name>.md` or `<name>.json` file.
MD_FOLDERS = {"skills": "skill", "rules": "rule",
              "commands": "command", "agents": "agent"}
JSON_FOLDERS = {"hooks": "hook", "mcp-servers": "mcp-server"}
FOLDER_INSTRUCTIONS = "folder-instructions"
TOOLS_DIR = Path("capabilities") / "tools"
COMPONENT_FOLDERS = (*MD_FOLDERS, *JSON_FOLDERS, "capabilities",
                     FOLDER_INSTRUCTIONS)


class Refuse(Exception):
    """A loud, machine-readable, PRE-WRITE refusal."""

    def __init__(self, code: str, message: str, path: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path

    def payload(self) -> dict:
        out: dict = {"ok": False,
                     "refusal": {"code": self.code, "message": self.message}}
        if self.path:
            out["refusal"]["path"] = self.path
        return out


def _read_json(path: Path, code: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refuse(code, f"{path}: not readable JSON ({exc})", str(path)) from exc


def _checked(value: object, template: str, path: Path, code: str) -> None:
    problems = schema.errors(value, schema.load(template))
    if problems:
        raise Refuse(code, f"{path}: " + "; ".join(problems), str(path))


def _record(path: Path, template: str) -> dict:
    """A module or component record, read and checked against its schema."""
    data = _read_json(path, "record-invalid")
    _checked(data, template, path, "record-invalid")
    return data  # type: ignore[return-value]


def _is_component_dir(path: Path) -> bool:
    return (path / f"{path.name}.json").is_file() or any(
        (path / folder).is_dir() for folder in COMPONENT_FOLDERS)


def discover_skill_folders(root: Path, tree: str) -> dict[str, dict]:
    """Whole-folder skills under `<root>/_skills/<name>/` (a `SKILL.md` and its
    files, the open skill format). id = `_hub/skills/<name>`."""
    found: dict[str, dict] = {}
    skills = root / SKILLS_DIR
    if not skills.is_dir():
        return found
    for child in sorted(skills.iterdir()):
        if child.name.startswith(".") or not (child / SKILL_FILE).is_file():
            continue
        cid = f"{HUB_DIR}/skills/{child.name}"
        found[cid] = {
            "id": cid, "tree": tree, "tree_root": str(root),
            "module": HUB_DIR, "component": child.name, "path": str(child),
            "kind": "hub", "method": "skill", "manifest": False,
        }
    return found


def scan_tree(root: Path, tree: str) -> dict[str, dict]:
    """Every component under one tree root, by id `<module>/<component>`:
    a folder holding its own `<component>.json`, inside a folder holding its own
    `<module>.json`. {} when the root is absent. A module or component folder
    without its record is refused, never skipped."""
    found: dict[str, dict] = {}
    if not root.is_dir():
        return found
    found.update(discover_skill_folders(root, tree))
    for top in sorted(root.iterdir()):
        if not top.is_dir() or top.name.startswith(".") \
                or top.name in {HUB_DIR, SKILLS_DIR}:
            continue
        subs = [sub for sub in sorted(top.iterdir())
                if sub.is_dir() and not sub.name.startswith(".")
                and _is_component_dir(sub)]
        if not subs:
            continue
        module_json = top / f"{top.name}.json"
        if not module_json.is_file():
            raise Refuse("module-record-missing",
                         f"module folder {top} has components but no "
                         f"{module_json.name}", str(module_json))
        module = _record(module_json, "module-json")
        for sub in subs:
            record_path = sub / f"{sub.name}.json"
            if not record_path.is_file():
                raise Refuse("component-record-missing",
                             f"component folder {sub} has no {record_path.name}",
                             str(record_path))
            data = _record(record_path, "component-json")
            cid = f"{top.name}/{sub.name}"
            found[cid] = {
                "id": cid, "tree": tree, "tree_root": str(root),
                "module": top.name, "component": sub.name, "path": str(sub),
                "kind": "component", "manifest": True,
                "description": data["description"],
                "dependencies": data["dependencies"],
                "module_description": module["description"],
            }
    return found


def scan_all(mirror_root: Path, repo_root: Path) -> tuple[dict[str, dict], list[dict]]:
    """Both trees merged, mirror winning on a shared id (D3).

    Returns (components-by-id, shadowed) — `shadowed` names every repo component
    the mirror hid, so the precedence is reported rather than silent.
    """
    repo = scan_tree(repo_root, "repo")
    mirror = scan_tree(mirror_root, "mirror")
    shadowed = [
        {"id": cid, "shadowed_path": repo[cid]["path"],
         "winner_path": mirror[cid]["path"]}
        for cid in sorted(set(repo) & set(mirror))
    ]
    merged = dict(repo)
    merged.update(mirror)
    return merged, shadowed


def _unit(comp: dict, method: str, path: Path, template: str) -> dict:
    """One `<name>.md` or `<name>.json` unit: its record checked against the
    schema, its `name` equal to the file name."""
    comp_dir = Path(comp["path"])
    if path.suffix == ".md":
        data, _body = frontmatter.split(path.read_text(encoding="utf-8"))
        if data is None:
            raise Refuse("unit-invalid", f"{path}: no frontmatter", str(path))
    else:
        data = _read_json(path, "unit-invalid")
    _checked(data, template, path, "unit-invalid")
    if method != "folder-instructions" and data["name"] != path.stem:
        raise Refuse("unit-invalid",
                     f"{path}: name {data['name']!r} is not the file name "
                     f"{path.stem!r}", str(path))
    description = (f"folder instructions for {data['target']}"
                   if method == "folder-instructions" else data["description"])
    return {"id": path.stem, "method": method,
            "entry": path.relative_to(comp_dir).as_posix(),
            "description": description, "data": data}


def unit_rows(comp: dict) -> list[dict]:
    """Every unit of one component, read from its folders: [{id, method, entry,
    description, data}]. `entry` is relative to the component folder; `data` is
    the unit's checked frontmatter or JSON record (none for a tool). A file that
    fails its schema, or whose name is not its file name, refuses; so does a
    name used by two units of one component."""
    comp_dir = Path(comp["path"])
    rows: list[dict] = []
    # `<folder>/<folder>.md` is the folder's index file, not a unit.
    for folder, method in MD_FOLDERS.items():
        for path in sorted((comp_dir / folder).glob("*.md")):
            if path.stem != folder:
                rows.append(_unit(comp, method, path, method))
    for folder, method in JSON_FOLDERS.items():
        for path in sorted((comp_dir / folder).glob("*.json")):
            if path.stem != folder:
                rows.append(_unit(comp, method, path, method))
    for path in sorted((comp_dir / FOLDER_INSTRUCTIONS).glob("*.md")):
        if path.stem != FOLDER_INSTRUCTIONS:
            rows.append(_unit(comp, "folder-instructions", path,
                              "folder-instructions"))
    for record in sorted((comp_dir / TOOLS_DIR).glob("*/*.json")):
        if record.stem != record.parent.name:
            continue
        data = _read_json(record, "unit-invalid")
        _checked(data, "tool-json", record, "unit-invalid")
        if data["name"] != record.parent.name:
            raise Refuse("unit-invalid",
                         f"{record}: name {data['name']!r} is not its folder "
                         f"name {record.parent.name!r}", str(record))
        if data["entry"].startswith(WS_PREFIX):
            # From the installation root; resolved when the tool is placed on PATH.
            wpath = Path(data["entry"][len(WS_PREFIX):])
            if wpath.is_absolute() or ".." in wpath.parts:
                raise Refuse("entry-point-escape",
                             f"{record}: entry {data['entry']!r} must stay "
                             "inside the installation root", str(record))
            entry_rel = data["entry"]
        else:
            entry = record.parent / data["entry"]
            if Path(data["entry"]).is_absolute() or not entry.resolve(
                    ).is_relative_to(comp_dir.resolve()):
                raise Refuse("entry-point-escape",
                             f"{record}: entry {data['entry']!r} leaves the "
                             "component's folder", str(record))
            if not entry.is_file():
                raise Refuse("unit-invalid",
                             f"{record}: entry {data['entry']!r} is not a file",
                             str(record))
            entry_rel = entry.relative_to(comp_dir).as_posix()
        rows.append({"id": data["name"], "method": "tool",
                     "entry": entry_rel,
                     "description": data["description"], "data": data})
    names = [r["id"] for r in rows]
    dups = sorted({n for n in names if names.count(n) > 1})
    if dups:
        raise Refuse("unit-duplicate",
                     f"{comp.get('id', '?')}: the name {', '.join(dups)} is "
                     "used by more than one unit — a name is one unit",
                     str(comp_dir))
    return rows
