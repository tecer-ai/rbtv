"""Installer discovery — D2 components + D15 hub units, no root derivation.

Roots are ARGUMENTS. The installer keeps `REPO_ROOT` (the repo that ships
install.py). The materializer passes the workspace mirror and `rbtv.json`'s
`rbtv_path`. One scan, one merge (mirror wins), one manifest reader.

Hub discovery (`discover_hub`, D15) lives here because `scan_tree` calls it.

This module deliberately sits BESIDE install.py rather than inside its `lib/`
package: `ignite/team-kit/materialize-seats.py` imports it from this directory
by bare name, so the path is a contract with another tool (D1).
"""
from __future__ import annotations

import csv
from pathlib import Path


EXPOSURE_NAME = "exposure.csv"
EXPOSURE_COLS = (
    "part-id", "part-kind", "method", "rbtv-cli",
    "entry-point", "description", "write-roots",
)

HUB_DIR = "_hub"
SKILLS_DIR = "_skills"
SKILL_FILE = "SKILL.md"
HUB_FOLDERS = {
    "skill": "skill", "skills": "skill",
    "command": "command",
    "rule": "rule", "rules": "rule",
    "hook": "hook", "sub-agent": "sub-agent",
    "agents.md": "agents.md", "config": "config", "path": "path",
    "pool": "pool",
}
HUB_ID_FOLDER = {
    "skill": "skills", "command": "command", "rule": "rules",
    "hook": "hook", "sub-agent": "sub-agent", "agents.md": "agents.md",
    "config": "config", "path": "path", "pool": "pool",
}


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


def _hub_unit_name(method: str, path: Path) -> str:
    return path.name if method == "path" else (path.stem if path.is_file() else path.name)


def _is_hub_unit(method: str, path: Path) -> bool:
    if path.name.startswith("."):
        return False
    if method == "skill":
        return path.is_dir() and (path / SKILL_FILE).is_file()
    if method == "pool":
        return path.is_file() or path.is_dir()
    if method == "path":
        return path.is_file() or path.is_dir()
    if method in {"command", "rule", "sub-agent", "agents.md"}:
        return path.is_file() and path.suffix == ".md"
    return path.is_file()  # hook | config


def _hub_refusal(method: str, path: Path) -> str:
    if method == "pool":
        return "hub-pool-inexpressible"
    if method == "path" and path.is_dir():
        return "hub-path-directory"
    return ""


def discover_hub(root: Path, tree: str) -> dict[str, dict]:
    """Hub units under one tree. id = `_hub/<id-folder>/<name>` (never the
    on-disk relpath). `_skills/<name>/` is a legacy alias of `_hub/skills/`."""
    found: dict[str, dict] = {}
    if not root.is_dir():
        return found

    def put(path: Path, method: str, *, legacy: bool) -> None:
        name = _hub_unit_name(method, path)
        if not name or name.startswith("."):
            return
        cid = f"{HUB_DIR}/{HUB_ID_FOLDER[method]}/{name}"
        rec = {
            "id": cid, "tree": tree, "tree_root": str(root),
            "module": HUB_DIR, "component": name, "path": str(path),
            "kind": "hub", "method": method, "manifest": False,
            "legacy_skills_dir": legacy,
        }
        refusal = _hub_refusal(method, path)
        if refusal:
            rec["hub_refusal"] = refusal
        prev = found.get(cid)
        if prev and prev.get("legacy_skills_dir") and not legacy:
            found[cid] = rec
        elif prev is None:
            found[cid] = rec

    hub = root / HUB_DIR
    if hub.is_dir():
        for folder in sorted(hub.iterdir()):
            method = HUB_FOLDERS.get(folder.name)
            if not method or not folder.is_dir():
                continue
            for child in sorted(folder.iterdir()):
                if _is_hub_unit(method, child):
                    put(child, method, legacy=False)
    skills = root / SKILLS_DIR
    if skills.is_dir():
        for child in sorted(skills.iterdir()):
            if _is_hub_unit("skill", child):
                put(child, "skill", legacy=True)
    return found


def _is_component_dir(path: Path) -> bool:
    """D2 — a directory holding `exposure.csv`. Combined with scan_tree's
    depth-2 walk, that is the whole component rule."""
    return (path / EXPOSURE_NAME).is_file()


def scan_tree(root: Path, tree: str) -> dict[str, dict]:
    """Every component under one tree root, by id (D2) — a directory at
    EXACTLY depth 2 that holds `exposure.csv`. {} when the root is absent.
    Depth-1 (module-root) manifests and depth-3 files are invisible here.
    Hub units are a separate branch (D15)."""
    found: dict[str, dict] = {}
    if not root.is_dir():
        return found

    def record(dir_path: Path, kind: str = "component") -> None:
        rel = dir_path.relative_to(root).as_posix()
        found[rel] = {
            "id": rel,
            "tree": tree,
            "tree_root": str(root),
            "module": rel.split("/")[0],
            "component": rel.split("/")[-1],
            "path": str(dir_path),
            "kind": kind,
            "manifest": (dir_path / EXPOSURE_NAME).is_file(),
        }

    found.update(discover_hub(root, tree))
    for top in sorted(root.iterdir()):
        if not top.is_dir() or top.name.startswith("."):
            continue
        if top.name in {HUB_DIR, SKILLS_DIR}:
            continue
        # Depth 2 ONLY — a component folder lives inside a module folder (D2).
        for sub in sorted(top.iterdir()):
            if sub.is_dir() and not sub.name.startswith(".") and _is_component_dir(sub):
                record(sub)
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


def exposure_rows(component: dict) -> list[dict]:
    path = Path(component["path"]) / EXPOSURE_NAME
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        # `#` comment lines: both real manifests use them for their own header.
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    reader = csv.DictReader(lines)
    got = tuple(reader.fieldnames or ())
    if got != EXPOSURE_COLS:
        raise Refuse(
            "manifest-malformed",
            f"{path}: columns are {','.join(got) or '(none)'} — "
            f"want {','.join(EXPOSURE_COLS)}",
            str(path))
    return [dict(r) for r in reader]
