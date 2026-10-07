"""Installer discovery — modules, components and their files, read from the
folder layout. Roots are ARGUMENTS. The installer keeps `REPO_ROOT` (the repo
that ships install.py); the caller passes the installation mirror and that root.
One scan, one merge (mirror wins), one file reader.

A module is a folder holding `<module>/<module>.json`; a component is a folder
inside it holding `<component>/<component>.json`. The folder a file sits in
decides how it is exposed: `skills/`, `rules/`, `commands/`, `agents/<name>/`,
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
from lib.constants import AGENT_RECORD, PROMPT_FILE
from lib.files_key import files_key


WS_PREFIX = "ws:"
HUB_DIR = "_hub"          # only the id prefix of whole-folder skills, `_hub/skills/<name>`
SKILLS_DIR = "_skills"
SKILL_FILE = "SKILL.md"

# Folder -> method, for the files that are one `<name>.md` or `<name>.json` file.
MD_FOLDERS = {"skills": "skill", "rules": "rule", "commands": "command"}
JSON_FOLDERS = {"hooks": "hook", "mcp-servers": "mcp-server"}
FOLDER_INSTRUCTIONS = "folder-instructions"
# The former second source format of an agent, one file per agent. A component
# that still holds one is refused and told the one format, `agents/<name>/`.
RETIRED_AGENT_FOLDER = "sub-agents"
# Values an agent has only in an installation, never in a component's source.
LAUNCH_FIELDS = ("harness", "model", "effort")
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
    # `git pull` cannot remove ignored Python bytecode.  A renamed component
    # can therefore leave an otherwise empty folder behind, but that remnant
    # is not source and must not trigger the missing-record safety gate.
    if _cache_only(path):
        return False
    return (path / f"{path.name}.json").is_file() or any(
        (path / folder).is_dir() for folder in COMPONENT_FOLDERS)


def _cache_only(path: Path) -> bool:
    """Whether a leftover folder contains only Python bytecode caches."""
    try:
        entries = list(path.iterdir())
    except OSError:
        return False
    return bool(entries) and all(
        _cache_only(entry) if entry.is_dir()
        else entry.is_file() and entry.suffix == ".pyc"
        for entry in entries)


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


def module_folders(root: Path) -> list[str]:
    """The names of the module folders directly under one tree root: each holds
    its own `<module>.json`. [] when the root is absent."""
    if not root.is_dir():
        return []
    return sorted(top.name for top in root.iterdir()
                  if top.is_dir() and not top.name.startswith(".")
                  and top.name not in {HUB_DIR, SKILLS_DIR}
                  and (top / f"{top.name}.json").is_file())


def scan_tree(root: Path, tree: str) -> dict[str, dict]:
    """Every component under one tree root, by id `<module>/<component>`:
    a folder holding its own `<component>.json`, inside a folder holding its own
    `<module>.json`. {} when the root is absent. A module or component folder
    without its record is refused, never skipped."""
    found: dict[str, dict] = {}
    if not root.is_dir():
        return found
    if tree == "mirror":
        # Whole-folder skills belong to one installation, so only its mirror holds them.
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
    # A component's name alone names its folders under `.rbtv/config/` and
    # `.rbtv/runtime/`, so two modules cannot each hold one of the same name.
    owners: dict[str, str] = {}
    for cid, comp in sorted(merged.items()):
        if comp["kind"] != "component":
            continue
        first = owners.setdefault(comp["component"], cid)
        if first != cid:
            raise Refuse("component-duplicate",
                         f"components {first} and {cid} share the name "
                         f"{comp['component']!r}; rename one", comp["path"])
    pack_rows(merged)
    return merged, shadowed


def pack_rows(catalog: dict[str, dict]) -> list[dict]:
    """Validated pack declarations in the merged catalog, one name globally.

    This is deliberately derived from component folders each time: a mirror
    component replaces both its files and its packs, and update sees edits to
    a declaration without a second cache to invalidate.
    """
    provided: set[str] = set()
    unreadable: dict[str, Refuse] = {}
    for cid, comp in catalog.items():
        try:
            provided.update(f"{cid}#{row['id']}" for row in file_rows(comp))
        except Refuse as exc:
            # An unrelated invalid component already remains discoverable and
            # blocks only its own install; packs keep that same boundary. Its
            # refusal is kept: a pack that names its files fails for that reason.
            unreadable[cid] = exc
    rows: list[dict] = []
    names: dict[str, Path] = {}
    for cid, comp in sorted(catalog.items()):
        packs = Path(comp["path"]) / "packs"
        for path in sorted(packs.glob("*.json")):
            data = files_key(_read_json(path, "pack-invalid"))
            _checked(data, "pack", path, "pack-invalid")
            if path.stem in names:
                raise Refuse("pack-duplicate",
                             f"pack {path.stem!r} is declared by both {names[path.stem]} and {path}",
                             str(path))
            names[path.stem] = path
            missing = sorted(set(data["files"]) - provided)
            for file in missing:
                if file.split("#", 1)[0] in unreadable:
                    raise unreadable[file.split("#", 1)[0]]
            if missing:
                raise Refuse("pack-file-unknown",
                             f"pack {path.stem!r} names unavailable file(s): {', '.join(missing)}",
                             str(path))
            rows.append({"name": path.stem, "component": cid,
                         "module": comp["module"], "tree": comp["tree"],
                         "path": str(path), "description": data["description"],
                         "files": list(data["files"])})
    return rows


def _file_row(comp: dict, method: str, path: Path, template: str) -> dict:
    """One `<name>.md` or `<name>.json` file: its record checked against the
    schema, its `name` equal to the file name."""
    comp_dir = Path(comp["path"])
    if path.suffix == ".md":
        data, _body = frontmatter.split(path.read_text(encoding="utf-8"))
        if data is None:
            raise Refuse("file-invalid", f"{path}: no frontmatter", str(path))
    else:
        data = _read_json(path, "file-invalid")
    _checked(data, template, path, "file-invalid")
    if method != "folder-instructions" and data["name"] != path.stem:
        raise Refuse("file-invalid",
                     f"{path}: name {data['name']!r} is not the file name "
                     f"{path.stem!r}", str(path))
    description = (f"folder instructions for {data['target']}"
                   if method == "folder-instructions" else data["description"])
    return {"id": path.stem, "method": method,
            "entry": path.relative_to(comp_dir).as_posix(),
            "description": description, "data": data}


def file_rows(comp: dict) -> list[dict]:
    """Every file of one component, read from its folders: [{id, method, entry,
    description, data}]. `entry` is relative to the component folder; `data` is
    the file's checked frontmatter or JSON record (none for a tool). A file that
    fails its schema, or whose name is not its file name, refuses; so does a
    name used by two files of one component."""
    comp_dir = Path(comp["path"])
    rows: list[dict] = []
    # `<folder>/<folder>.md` is the folder's index file, which is not installed.
    for folder, method in MD_FOLDERS.items():
        for path in sorted((comp_dir / folder).glob("*.md")):
            if path.stem != folder:
                rows.append(_file_row(comp, method, path, method))
    for path in sorted((comp_dir / RETIRED_AGENT_FOLDER).glob("*.md")):
        raise Refuse("agent-source-retired",
                     f"{path}: an agent is no longer shipped as one file in "
                     f"{RETIRED_AGENT_FOLDER}/. Ship it as the folder "
                     f"agents/{path.stem}/ with {PROMPT_FILE} and {AGENT_RECORD}",
                     str(path))
    for home in sorted((comp_dir / "agents").glob("*/")):
        prompt, record = home / PROMPT_FILE, home / AGENT_RECORD
        if not (prompt.is_file() and record.is_file()):
            raise Refuse("file-invalid", f"{home}: an agent needs {PROMPT_FILE} and {AGENT_RECORD}", str(home))
        front, _body = frontmatter.split(prompt.read_text(encoding="utf-8"))
        _checked(front or {}, "prompt", prompt, "file-invalid")
        data = files_key(_read_json(record, "file-invalid"))
        _checked(data, "agent-json", record, "file-invalid")
        launch = [name for name in LAUNCH_FIELDS if name in data]
        if launch:
            raise Refuse("agent-source-launch",
                         f"{record}: an agent a component ships names no harness, "
                         "model or effort; they exist only in an installation. "
                         "Remove: " + ", ".join(launch), str(record))
        if home.name != front["name"] or home.name != data["name"]:
            raise Refuse("file-invalid", f"{home}: folder, {PROMPT_FILE} and {AGENT_RECORD} names must agree", str(home))
        rows.append({"id": home.name, "method": "agent",
                     "entry": prompt.relative_to(comp_dir).as_posix(),
                     "description": data["description"], "data": data})
    for folder, method in JSON_FOLDERS.items():
        for path in sorted((comp_dir / folder).glob("*.json")):
            if path.stem != folder:
                rows.append(_file_row(comp, method, path, method))
    for path in sorted((comp_dir / FOLDER_INSTRUCTIONS).glob("*.md")):
        if path.stem != FOLDER_INSTRUCTIONS:
            rows.append(_file_row(comp, "folder-instructions", path,
                              "folder-instructions"))
    for record in sorted((comp_dir / TOOLS_DIR).glob("*/*.json")):
        if record.stem != record.parent.name:
            continue
        data = _read_json(record, "file-invalid")
        _checked(data, "tool-json", record, "file-invalid")
        if data["name"] != record.parent.name:
            raise Refuse("file-invalid",
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
                raise Refuse("file-invalid",
                             f"{record}: entry {data['entry']!r} is not a file",
                             str(record))
            entry_rel = entry.relative_to(comp_dir).as_posix()
        rows.append({"id": data["name"], "method": "tool",
                     "entry": entry_rel,
                     "description": data["description"], "data": data})
    names = [r["id"] for r in rows]
    dups = sorted({n for n in names if names.count(n) > 1})
    if dups:
        raise Refuse("file-duplicate",
                     f"{comp.get('id', '?')}: the name {', '.join(dups)} is "
                     "used by more than one file — a name is one file",
                     str(comp_dir))
    return rows
