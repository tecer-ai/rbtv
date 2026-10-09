"""Clone, check and fast-forward a component's external git checkout.

The checkout is `<component>/repository/`, from the component record's
`repository` field. Installation creates a missing checkout and never fetches
an existing one. `rbtv update repositories` fast-forwards a clean matching
checkout and never clones, resets, stashes or deletes.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from discovery import Refuse

from .constants import REPOSITORY_DIR
from .locks import mutation_lock
from .recovery import shell_quote

_STAMP = ".rbtv-setup"
_TIMEOUT_S = 120


def repository_components(catalog: dict, keys: set[str] | list[str]) -> list[dict]:
    """Selected components whose record names a repository, in id order."""
    found: list[dict] = []
    seen: set[str] = set()
    for key in sorted(keys):
        cid = key.partition("#")[0]
        comp = catalog.get(cid) or {}
        if not comp.get("repository") or cid in seen:
            continue
        seen.add(cid)
        found.append(comp)
    return found


def checkout_path(comp: dict) -> Path:
    return Path(comp["path"]) / REPOSITORY_DIR


def notes(item: dict) -> list[str]:
    """Human lines for one repository result. Paths stay whole words."""
    cid = item["component"]
    action = item.get("action")
    lines: list[str] = []
    if action == "cloned":
        lines.append(f"{cid}: cloned {item['branch']} into {item['path']}")
    elif action == "present":
        lines.append(
            f"{cid}: checkout already matches origin and {item['branch']}; not fetched")
    elif action == "would-clone":
        lines.append(f"{cid}: would clone {item['branch']} into {item['path']}")
    elif action == "updated":
        lines.append(f"{cid}: fast-forwarded {item['branch']}")
    elif action == "up-to-date":
        lines.append(f"{cid}: already matches origin {item['branch']}; not changed")
    elif action == "ahead":
        lines.append(
            f"{cid}: local branch is ahead of origin; not fast-forwarded or reset")
    elif action == "would-fetch":
        lines.append(
            f"{cid}: would fetch origin and fast-forward {item['branch']} only; "
            "no network in this preview")
    elif item.get("error"):
        err = item["error"]
        lines.append(f"{cid}: REFUSED [{err['code']}] {err['message']}")
    setup = item.get("setup")
    rel = item.get("requirements") or "requirements"
    if setup == "installed":
        lines.append(f"{cid}: installed Python packages from {rel}")
    elif setup == "skipped":
        lines.append(
            f"{cid}: Python environment already matches; packages not reinstalled")
    elif setup == "would-install":
        lines.append(f"{cid}: would install Python packages from {rel}")
    elif setup == "would-skip":
        lines.append(
            f"{cid}: Python environment already matches; packages would not be reinstalled")
    return lines


def public_item(item: dict) -> dict:
    keep = ("component", "url", "branch", "path", "action", "setup", "requirements")
    out = {key: item[key] for key in keep if item.get(key)}
    if item.get("error"):
        out["error"] = item["error"]
    return out


def refusal_for(items: list[dict]) -> Refuse | None:
    """One refusal for a failed checkout run, or None when every item succeeded.

    A checkout that was created sets `unchanged` so the text refusal does not
    say nothing changed. The items stay on the exception for the result screen.
    """
    failed = [item for item in items if item.get("error")]
    if not failed:
        return None
    err = failed[0]["error"]
    exc = Refuse(err["code"], err["message"], err.get("path") or "")
    exc.repositories = items
    if failed[0].get("next"):
        exc.next = failed[0]["next"]
    if any(item.get("mutated") for item in items):
        exc.repository_changed = True
        exc.outcome = "failed"
        exc.unchanged = failed[0].get("unchanged") or (
            "The installation was not changed. The checkout was not deleted.")
    return exc


class _Hooks:
    """Empty hooks directory, created only when a mutating git command runs."""

    def __init__(self) -> None:
        self.path: str | None = None

    def get(self) -> str:
        if self.path is None:
            self.path = tempfile.mkdtemp(prefix="rbtv-hooks-")
        return self.path

    def cleanup(self) -> None:
        if self.path and Path(self.path).is_dir():
            shutil.rmtree(self.path, ignore_errors=True)
            self.path = None


def apply_repositories(components: list[dict], *, dry: bool, mode: str,
                       target: Path) -> list[dict]:
    """Install or update each checkout. `mode` is `install` or `update`.

    A dry run does not create a directory, run a mutating git command, or
    contact a network. One component's failure does not skip the others.
    """
    if mode not in ("install", "update"):
        raise Refuse("usage", f"repository mode {mode!r} is not install or update")
    if not components:
        return []
    git = shutil.which("git")
    hooks = _Hooks()
    items: list[dict] = []
    try:
        for comp in components:
            if git is None:
                items.append(_fail(
                    comp, target, "repository-git-missing",
                    f"{comp['id']} needs git on PATH to clone or update its checkout",
                    mode))
                continue
            items.append(_one(comp, dry=dry, mode=mode, target=target, hooks=hooks))
        return items
    finally:
        hooks.cleanup()


def _one(comp: dict, *, dry: bool, mode: str, target: Path, hooks: _Hooks) -> dict:
    spec = comp["repository"]
    url, branch = spec["url"], spec["branch"]
    requirements = spec.get("requirements") or ""
    dest = checkout_path(comp)
    if url.startswith("-") or branch.startswith("-"):
        return _fail(
            comp, target, "repository-url",
            f"{comp['id']} repository url or branch starts with '-'. Not passed to git.",
            mode, path=str(dest))
    item = {"component": comp["id"], "url": url, "branch": branch,
            "path": str(dest), "requirements": requirements, "mutated": False}
    if mode == "install" and not dest.exists():
        if dry:
            item["action"] = "would-clone"
            item["setup"] = "would-install" if requirements else ""
            return item
        return _clone_and_setup(item, dest, url, branch, requirements, hooks, target)
    if mode == "update" and not dest.exists():
        return _fail(comp, target, "repository-missing",
                     f"{comp['id']} has no checkout at {dest}. Update does not clone.",
                     mode, path=str(dest))
    if dest.exists() and not dest.is_dir():
        return _fail(comp, target, "repository-invalid",
                     f"{comp['id']} has {dest} but it is not a directory. Not deleted.",
                     mode, path=str(dest))
    if dry:
        return _dry_existing(item, dest, url, branch, requirements, mode, target)
    return _with_lock(dest, lambda: _live_existing(
        item, dest, url, branch, requirements, mode, hooks, target))


def _dry_existing(item: dict, dest: Path, url: str, branch: str,
                  requirements: str, mode: str, target: Path) -> dict:
    """Read-only check. No git command that can update an index or a ref."""
    problem = _git_mismatch(dest, url, branch)
    if problem:
        code, message = problem
        item.update(_fail(item_comp(item), target, code, message, mode, path=str(dest)))
        return item
    if mode == "update":
        item["action"] = "would-fetch"
    else:
        item["action"] = "present"
    foreign = _unusable_venv(dest / ".venv") if requirements else ""
    if foreign:
        failed = _fail(
            item_comp(item), target, "repository-setup",
            f"{item['component']} checkout is at {dest}. {foreign}",
            mode, path=str(dest))
        item.update(failed)
        item["setup"] = "failed"
        return item
    item["setup"] = _dry_setup(dest, requirements)
    return item


def _live_existing(item: dict, dest: Path, url: str, branch: str,
                   requirements: str, mode: str, hooks: _Hooks, target: Path) -> dict:
    problem = _git_mismatch(dest, url, branch)
    if problem:
        code, message = problem
        failed = _fail(item_comp(item), target, code, message, mode, path=str(dest))
        item.update(failed)
        return item
    if mode == "install":
        item["action"] = "present"
        _apply_setup(item, dest, requirements, hooks, force=False)
        return item
    dirty = _dirty(dest)
    if dirty:
        shown = ", ".join(dirty[:5])
        failed = _fail(
            item_comp(item), target, "repository-dirty",
            f"{item['component']} has uncommitted changes ({shown}). "
            "Not stashed or deleted.",
            mode, path=str(dest))
        item.update(failed)
        return item
    before = _rev(dest, "HEAD")
    fetched = _git(["fetch", "origin",
                    f"refs/heads/{branch}:refs/remotes/origin/{branch}"],
                   cwd=dest, hooks=hooks.get())
    if fetched.returncode != 0:
        failed = _fail(
            item_comp(item), target, "repository-fetch",
            f"{item['component']} could not fetch origin {branch}: {_git_err(fetched)}. "
            "The checkout was not reset.",
            mode, path=str(dest))
        item.update(failed)
        return item
    kind = _ahead_behind(dest, branch)
    if kind == "diverged":
        failed = _fail(
            item_comp(item), target, "repository-diverged",
            f"{item['component']} branch {branch} has diverged from origin. Not reset.",
            mode, path=str(dest))
        item.update(failed)
        return item
    if kind == "behind":
        merged = _git(["merge", "--ff-only", f"origin/{branch}"],
                      cwd=dest, hooks=hooks.get())
        if merged.returncode != 0:
            failed = _fail(
                item_comp(item), target, "repository-diverged",
                f"{item['component']} branch {branch} could not fast-forward: "
                f"{_git_err(merged)}. Not reset.",
                mode, path=str(dest))
            item.update(failed)
            return item
        item["action"] = "updated"
        item["mutated"] = _rev(dest, "HEAD") != before
        _apply_setup(item, dest, requirements, hooks, force=item["mutated"])
        return item
    item["action"] = "ahead" if kind == "ahead" else "up-to-date"
    _apply_setup(item, dest, requirements, hooks, force=False)
    return item


def _with_lock(dest: Path, run):
    digest = hashlib.sha256(str(dest.resolve()).encode("utf-8")).hexdigest()[:24]
    lock = Path(tempfile.gettempdir()) / "rbtv-installer-locks" / f"repo-{digest}.lock"
    with mutation_lock(lock):
        return run()


def _clone_and_setup(item: dict, dest: Path, url: str, branch: str,
                     requirements: str, hooks: _Hooks, target: Path) -> dict:
    def run() -> dict:
        if dest.exists():
            return _live_existing(item, dest, url, branch, requirements, "install",
                                  hooks, target)
        return _clone_into(item, dest, url, branch, requirements, hooks, target)
    return _with_lock(dest, run)


def _clone_into(item: dict, dest: Path, url: str, branch: str,
                requirements: str, hooks: _Hooks, target: Path) -> dict:
    proc = _git(["clone", "--branch", branch, "--single-branch", url, str(dest)],
                hooks=hooks.get())
    if proc.returncode != 0 or not (dest / ".git").exists():
        failed = _fail(
            item_comp(item), target, "repository-clone",
            f"{item['component']} could not be cloned from {url} branch {branch} "
            f"into {dest}: {_git_err(proc)}.",
            "install", path=str(dest))
        item.update(failed)
        item["mutated"] = dest.exists()
        if item["mutated"]:
            item["unchanged"] = (
                "The installation was not changed. The checkout was not deleted.")
        return item
    item["mutated"] = True
    item["action"] = "cloned"
    current = _git(["remote", "get-url", "origin"], cwd=dest)
    if current.returncode == 0 and current.stdout.strip() != url:
        set_url = _git(["remote", "set-url", "origin", url], cwd=dest, hooks=hooks.get())
        if set_url.returncode != 0:
            failed = _fail(
                item_comp(item), target, "repository-remote",
                f"checkout origin is {current.stdout.strip()}; record says {url}. "
                "The checkout was not fetched, reset, or deleted.",
                "install", path=str(dest))
            item.update(failed)
            item["mutated"] = True
            item["unchanged"] = (
                "The installation was not changed. The checkout was not deleted.")
            return item
    problem = _git_mismatch(dest, url, branch)
    if problem:
        code, message = problem
        failed = _fail(item_comp(item), target, code, message, "install", path=str(dest))
        item.update(failed)
        item["mutated"] = True
        item["unchanged"] = (
            "The installation was not changed. The checkout was not deleted.")
        return item
    _apply_setup(item, dest, requirements, hooks, force=True)
    if item.get("error"):
        item["unchanged"] = (
            "The installation was not changed. The checkout was not deleted.")
        item["mutated"] = True
    return item


def _apply_setup(item: dict, dest: Path, requirements: str, hooks: _Hooks,
                 *, force: bool) -> None:
    del hooks
    if not requirements:
        item["setup"] = ""
        return
    try:
        req = _requirements_file(dest, requirements)
    except Refuse as exc:
        item["setup"] = "failed"
        item["error"] = {"code": exc.code, "message": exc.message, "path": exc.path}
        item["action"] = "failed"
        return
    if not req.is_file():
        item["setup"] = "failed"
        item["action"] = "failed"
        item["error"] = {
            "code": "repository-setup",
            "message": (f"{item['component']} checkout is at {dest}. "
                        f"{requirements} is not a file in the checkout."),
            "path": str(dest)}
        return
    if not force and _setup_intact(dest, req, requirements):
        item["setup"] = "skipped"
        return
    venv = dest / ".venv"
    foreign = _unusable_venv(venv)
    if foreign:
        _setup_refused(item, dest, foreign)
        return
    py = _venv_python(venv)
    if not py.is_file() or _run([str(py), "--version"]).returncode != 0:
        if venv.exists():
            _setup_refused(item, dest, f"{venv} has a broken Python interpreter. "
                           "It was not deleted; repair it or move it aside and repeat installation.")
            return
        made = _run([sys.executable, "-m", "venv", str(venv)])
        py = _venv_python(venv)
        if made.returncode != 0 or not py.is_file():
            item["setup"] = "failed"
            item["action"] = "failed"
            item["mutated"] = True
            item["error"] = {
                "code": "repository-setup",
                "message": (f"{item['component']} checkout is at {dest}. "
                            f"Could not create the Python environment: {_git_err(made)}."),
                "path": str(dest)}
            return
    installed = _run([str(py), "-m", "pip", "install", "-r", str(req),
                      "--disable-pip-version-check", "--no-input"])
    if installed.returncode != 0:
        item["setup"] = "failed"
        item["action"] = "failed"
        item["mutated"] = True
        item["error"] = {
            "code": "repository-setup",
            "message": (f"{item['component']} checkout is at {dest}. "
                        f"Could not install {requirements}: {_git_err(installed)}."),
            "path": str(dest)}
        return
    _write_stamp(venv, requirements, req)
    item["setup"] = "installed"
    item["mutated"] = True


def _dry_setup(dest: Path, requirements: str) -> str:
    if not requirements:
        return ""
    try:
        req = _requirements_file(dest, requirements)
    except Refuse:
        return "failed"
    if not req.is_file():
        return "would-install"
    venv = dest / ".venv"
    if _unusable_venv(venv):
        return "failed"
    stamp = venv / _STAMP
    if stamp.is_file() and stamp.read_text(encoding="utf-8") == _stamp_text(requirements, req):
        return "would-skip"
    return "would-install"


def _setup_intact(dest: Path, req: Path, requirements: str) -> bool:
    venv = dest / ".venv"
    py = _venv_python(venv)
    stamp = venv / _STAMP
    if not py.is_file() or not stamp.is_file():
        return False
    if stamp.read_text(encoding="utf-8") != _stamp_text(requirements, req):
        return False
    return _run([str(py), "--version"]).returncode == 0


def _stamp_text(requirements: str, req: Path) -> str:
    digest = hashlib.sha256(req.read_bytes()).hexdigest()
    return f"python={sys.executable}\nrequirements={requirements}\nsha256={digest}\n"


def _write_stamp(venv: Path, requirements: str, req: Path) -> None:
    (venv / _STAMP).write_text(_stamp_text(requirements, req), encoding="utf-8")


def _requirements_file(dest: Path, rel: str) -> Path:
    path = Path(rel)
    if path.is_absolute() or ".." in path.parts or not rel:
        raise Refuse(
            "repository-requirements",
            f"requirements {rel!r} must be a relative path inside the checkout",
            str(dest))
    root = dest.resolve()
    found = (dest / path).resolve()
    if not found.is_relative_to(root):
        raise Refuse(
            "repository-requirements",
            f"requirements {rel!r} leaves the checkout", str(dest))
    return found


def _unusable_venv(venv: Path) -> str:
    """Check layout without executing Python, including during dry runs."""
    if not venv.exists() and not venv.is_symlink():
        return ""
    if venv.is_dir() and not venv.is_symlink() and _venv_python(venv).is_file():
        return ""
    return (f"{venv} exists but is not a usable local Python environment. "
            "It was not deleted; repair it or move it aside and repeat installation.")


def _setup_refused(item: dict, dest: Path, message: str) -> None:
    item["setup"] = "failed"
    item["action"] = "failed"
    item["error"] = {
        "code": "repository-setup",
        "message": f"{item['component']} checkout is at {dest}. {message}",
        "path": str(dest)}


def _venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _git_mismatch(dest: Path, url: str, branch: str) -> tuple[str, str] | None:
    top = _git(["rev-parse", "--show-toplevel"], cwd=dest)
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != dest.resolve():
        return ("repository-invalid",
                f"is not a git checkout at {dest}. Not deleted.")
    remote = _git(["remote", "get-url", "origin"], cwd=dest)
    actual = remote.stdout.strip() if remote.returncode == 0 else ""
    if actual != url:
        return ("repository-remote",
                f"checkout origin is {actual or '(none)'}; record says {url}. "
                "The checkout was not fetched, reset, or deleted.")
    head = _git(["symbolic-ref", "--short", "HEAD"], cwd=dest)
    if head.returncode != 0 or head.stdout.strip() != branch:
        shown = head.stdout.strip() or "(detached)"
        return ("repository-branch",
                f"checkout branch is {shown}; record says {branch}. "
                "The checkout was not fetched, reset, or deleted.")
    return None


def _dirty(dest: Path) -> list[str]:
    proc = _git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=dest)
    if proc.returncode != 0:
        return [f"git status failed: {_git_err(proc)}"]
    found = []
    for line in proc.stdout.splitlines():
        path = _status_path(line)
        if path == ".venv" or path.startswith(".venv/"):
            continue
        found.append(path or line.strip())
    return found


def _status_path(line: str) -> str:
    body = line[3:].strip() if len(line) > 3 else line.strip()
    if " -> " in body:
        body = body.split(" -> ", 1)[1].strip()
    if body.startswith('"') and body.endswith('"'):
        body = body[1:-1]
    return body.replace("\\", "/")


def _ahead_behind(dest: Path, branch: str) -> str:
    proc = _git(["rev-list", "--left-right", "--count", f"HEAD...origin/{branch}"],
                cwd=dest)
    if proc.returncode != 0:
        return "diverged"
    parts = proc.stdout.split()
    if len(parts) != 2:
        return "diverged"
    left, right = int(parts[0]), int(parts[1])
    if left and right:
        return "diverged"
    if right:
        return "behind"
    if left:
        return "ahead"
    return "same"


def _rev(dest: Path, name: str) -> str:
    proc = _git(["rev-parse", name], cwd=dest)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _fail(comp: dict, target: Path, code: str, message: str, mode: str,
          path: str = "") -> dict:
    cid = comp["id"] if isinstance(comp, dict) else comp
    spec = comp.get("repository") or {} if isinstance(comp, dict) else {}
    dest = checkout_path(comp) if isinstance(comp, dict) and comp.get("path") else Path(path)
    flag = " --target " + shell_quote(target)
    if code == "repository-missing":
        nxt = "rbtv add " + shell_quote(cid) + flag
    elif code in ("repository-remote", "repository-branch", "repository-invalid"):
        nxt = "rbtv show " + shell_quote(cid) + flag
    elif mode == "update":
        nxt = "rbtv update repositories" + flag
    else:
        nxt = "rbtv add " + shell_quote(cid) + flag
    return {
        "component": cid,
        "url": spec.get("url", ""),
        "branch": spec.get("branch", ""),
        "path": str(dest),
        "requirements": spec.get("requirements") or "",
        "action": "refused",
        "mutated": False,
        "error": {"code": code,
                  "message": message if message.startswith(cid) else f"{cid} {message}",
                  "path": path},
        "next": nxt,
    }


def item_comp(item: dict) -> dict:
    return {"id": item["component"], "path": str(Path(item["path"]).parent),
            "repository": {"url": item.get("url", ""), "branch": item.get("branch", ""),
                           "requirements": item.get("requirements") or ""}}


def _git(args: list[str], *, cwd: Path | None = None, hooks: str | None = None
         ) -> subprocess.CompletedProcess:
    cmd = ["git", "--no-optional-locks"]
    if hooks:
        cmd += ["-c", f"core.hooksPath={hooks}"]
    if cwd is not None:
        cmd += ["-C", str(cwd)]
    cmd += args
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    return _bounded(cmd, env=env, cwd=None)


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return _bounded(args, env=None, cwd=None)


def _bounded(args: list[str], *, env: dict | None, cwd: Path | None
             ) -> subprocess.CompletedProcess:
    """A finished process. A timeout or a failed spawn is a return code, not a traceback."""
    try:
        return subprocess.run(
            args, cwd=cwd, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=_TIMEOUT_S, shell=False)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args, 124, stdout="", stderr=f"timed out after {_TIMEOUT_S}s")
    except OSError as exc:
        return subprocess.CompletedProcess(args, 1, stdout="", stderr=str(exc))


def _git_err(proc: subprocess.CompletedProcess) -> str:
    text = (proc.stderr or proc.stdout or "").strip().replace("\n", " ")
    return text[:200] or f"exited {proc.returncode}"
