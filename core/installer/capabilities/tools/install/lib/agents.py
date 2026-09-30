"""Installing an agent: its agent file becomes `<root>/.rbtv/agents/<agent>/`.

The folder holds the agent file itself (`agent.md`, the one source from then on),
its launch values (`launch.json`), its settings, an ignore file for data tied to
one machine, the harness files of the units its frontmatter selects (installed
with the same machinery as any other target, recorded in the folder's own
`.rbtv/config/install.json`), and a marked "agent" section in its folder
instructions that points to `agent.md`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from discovery import Refuse

from . import frontmatter, schema
from .catalog import catalog_units_map
from .claims import _block_del, _block_set
from .constants import GUIDANCE_FILE, HARNESSES, STATE_REL
from .fsio import write_file
from .operations import do_install, do_uninstall
from .state import read_state, write_state

AGENTS_REL = Path(".rbtv") / "agents"

# Data tied to the machine that made it: harness session ids, the work queue,
# and the turn files. The user may edit this file to share them.
IGNORE_TEXT = (
    "# rbtv: data tied to one machine. Edit this file to share it.\n"
    "state.sqlite*\n"
    "turns/\n"
    "conversations/*/session*\n")

# frontmatter field -> the method of the units it selects
UNIT_FIELDS = (("skills", "skill"), ("rules", "rule"), ("commands", "command"),
               ("hooks", "hook"), ("mcp-servers", "mcp-server"))


def agent_home(root: Path, name: str) -> Path:
    return root / AGENTS_REL / name


def read_agent_file(path: Path) -> tuple[dict, bytes]:
    """The agent file's frontmatter, checked against its schema, and its bytes."""
    try:
        raw = path.read_bytes()
        front, _body = frontmatter.split(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise Refuse("agent-file-unreadable", f"{path}: {exc}", str(path)) from exc
    if front is None:
        raise Refuse("agent-file-invalid", f"{path}: no frontmatter", str(path))
    problems = schema.errors(front, schema.load("agent"))
    if problems:
        raise Refuse("agent-file-invalid", f"{path}: " + "; ".join(problems),
                     str(path))
    return front, raw


def cast_catalog() -> dict[str, dict[str, list[str]]]:
    """What `cast` launches: {harness: {model: [effort words]}}."""
    exe = shutil.which("cast")
    if exe is None:
        raise Refuse("cast-missing",
                     "the `cast` command is not on PATH, so the harness, model "
                     "and effort cannot be checked. Install it: "
                     "rbtv install add cast --harness claude --guidance none")
    done = subprocess.run([exe, "list", "--json"], capture_output=True,
                          text=True, encoding="utf-8")
    try:
        return json.loads(done.stdout)
    except ValueError as exc:
        raise Refuse("cast-unreadable",
                     f"`cast list --json` did not answer with JSON ({exc})") from exc


def launch_values(harness: str, model: str, effort: str,
                  known: dict[str, dict[str, list[str]]]) -> dict:
    """The harness, model and effort the agent runs with, as `launch.json` holds
    them. An effort number 1-5 becomes the model's own word for that step."""
    if harness not in HARNESSES:
        raise Refuse("launch-invalid",
                     f"harness {harness!r} is not one of {', '.join(HARNESSES)}")
    models = known.get(harness) or {}
    if model not in models:
        raise Refuse("launch-invalid",
                     f"{harness} has no model {model!r}. Known: "
                     + ", ".join(sorted(models))
                     + ". See `cast list`")
    rungs = models[model]
    if not rungs:
        return {"harness": harness, "model": model, "effort": "inert"}
    if effort.isdigit() and 1 <= int(effort) <= 5:
        effort = rungs[min(int(effort), len(rungs)) - 1]
    if effort not in rungs:
        raise Refuse("launch-invalid",
                     f"{model} accepts the efforts {', '.join(rungs)} (or 1-5), "
                     f"not {effort!r}")
    return {"harness": harness, "model": model, "effort": effort}


def resolve_units(catalog: dict[str, dict], front: dict) -> list[str]:
    """The `<component>#<unit>` key of every unit the frontmatter names. A name is
    the unit's own, or `<module>/<component>/<name>` when several share it."""
    units = catalog_units_map(catalog)
    keys: list[str] = []
    for field, method in UNIT_FIELDS:
        for name in front.get(field) or []:
            want = name.rsplit("/", 1)[-1]
            scope = name.rsplit("/", 1)[0] if "/" in name else None
            hits = sorted(f"{cid}#{u['id']}" for cid, specs in units.items()
                          for u in specs
                          if u["id"] == want and u["method"] == method
                          and (scope is None or cid == scope))
            if not hits:
                raise Refuse("unit-unknown",
                             f"the agent file selects the {method} "
                             f"{name!r}, which no component provides. "
                             f"Find it: rbtv install search {want}")
            if len(hits) > 1:
                raise Refuse("unit-ambiguous",
                             f"{name!r} names more than one {method}: "
                             + ", ".join(hits)
                             + ". Write it as <module>/<component>/<name>")
            keys.append(hits[0])
    return sorted(set(keys))


def section_body(folders: list[str]) -> str:
    lines = ["Your instructions are in `agent.md` in this folder. Follow them."]
    if folders:
        lines += ["", "Key folders, relative to the installation root:", ""]
        lines += [f"- `{f}`" for f in folders]
    return "\n".join(lines)


def _write_section(home: Path, harness: str, folders: list[str]) -> str:
    rel = GUIDANCE_FILE[harness]
    path = home / rel
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    write_file(path, _block_set(text, section_body(folders), "<!--",
                                preserve_outside=True, label="agent"),
               newline="\n")
    return rel


def _drop_section(home: Path, harness: str) -> None:
    path = home / GUIDANCE_FILE[harness]
    if not path.is_file():
        return
    text = _block_del(path.read_text(encoding="utf-8"), "<!--",
                      preserve_outside=True, label="agent")
    if text.strip():
        write_file(path, text, newline="\n")
    else:
        path.unlink()


def _install_units(home: Path, catalog: dict, keys: list[str], harness: str,
                   dry_run: bool, *, everything: bool = False) -> dict | None:
    """Install the units the agent file selects into the agent folder. Units an
    earlier call selected that it no longer does go (`agent_units` in the folder's
    install record says which were the agent file's); units installed on the side,
    such as Ignite's standard ones, stay. `everything` takes back every booked unit."""
    state = read_state(home)
    booked = {f"{cid}#{u}": cid
              for cid, rec in (state.get("components") or {}).items()
              for u in (rec.get("units") or {})}
    gone = set(booked) if everything else set(state.get("agent_units") or []) & set(booked) - set(keys)
    for cid in sorted({booked[k] for k in gone}):
        do_uninstall(home, catalog, [cid], dry_run,
                     parts=[k for k in sorted(gone) if booked[k] == cid])
    result = None
    if keys:
        result = do_install(home, catalog, sorted({k.split("#")[0] for k in keys}),
                            [harness], dry_run, guidance_basis="none", parts=keys)
    if not dry_run and (home / STATE_REL).is_file():
        state = read_state(home)
        state["agent_units"] = [] if everything else keys
        write_state(home, state)
    return result


def _result(name: str, home: Path, launch: dict, keys: list[str], dry_run: bool,
            written: list[str]) -> dict:
    return {"ok": True, "agent": name, "home": str(home), "launch": launch,
            "units": keys, "written": written, "dry_run": dry_run}


def add_agent(root: Path, file: Path, harness: str, model: str, effort: str,
              catalog: dict, dry_run: bool) -> dict:
    front, raw = read_agent_file(file)
    name = front["name"]
    home = agent_home(root, name)
    if (home / "agent.md").exists():
        raise Refuse("agent-exists",
                     f"agent {name!r} is already installed at {home}. Refresh it "
                     f"with: rbtv install agent update {name}", str(home))
    launch = launch_values(harness, model, effort, cast_catalog())
    keys = resolve_units(catalog, front)
    # settings.json belongs to the agent: an existing one (a folder converted
    # from an earlier install) is kept, and only a missing one is created.
    fresh_settings = not (home / "settings.json").exists()
    written = ["agent.md", "launch.json"] + (["settings.json"] if fresh_settings else []) \
        + [".gitignore", GUIDANCE_FILE[harness]]
    if not dry_run:
        home.mkdir(parents=True, exist_ok=True)
        (home / "agent.md").write_bytes(raw)
        write_file(home / "launch.json", json.dumps(launch, indent=2) + "\n",
                   newline="\n")
        if fresh_settings:
            write_file(home / "settings.json", "{}\n", newline="\n")
        write_file(home / ".gitignore", IGNORE_TEXT, newline="\n")
        _write_section(home, harness, front.get("folders") or [])
    _install_units(home, catalog, keys, harness, dry_run)
    return _result(name, home, launch, keys, dry_run, written)


def _existing(root: Path, name: str) -> tuple[Path, dict, dict]:
    home = agent_home(root, name)
    if not (home / "agent.md").is_file():
        raise Refuse("agent-unknown",
                     f"no agent {name!r} is installed under {root / AGENTS_REL}",
                     str(home))
    try:
        launch = json.loads((home / "launch.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refuse("agent-launch-unreadable",
                     f"{home / 'launch.json'}: {exc}", str(home)) from exc
    return home, launch, read_agent_file(home / "agent.md")[0]


def update_agent(root: Path, name: str, catalog: dict, dry_run: bool) -> dict:
    """Regenerate everything from the agent's own `agent.md`, keeping its launch
    values, settings and live data."""
    home, launch, front = _existing(root, name)
    keys = resolve_units(catalog, front)
    if not dry_run:
        _write_section(home, launch["harness"], front.get("folders") or [])
        if not (home / ".gitignore").exists():
            write_file(home / ".gitignore", IGNORE_TEXT, newline="\n")
    _install_units(home, catalog, keys, launch["harness"], dry_run)
    return _result(name, home, launch, keys, dry_run, [GUIDANCE_FILE[launch["harness"]]])


def remove_agent(root: Path, name: str, catalog: dict, dry_run: bool) -> dict:
    """Take back what the installer put in the folder. The agent file, the
    settings and everything the agent made stay: they are the agent's, not ours."""
    home, launch, _front = _existing(root, name)
    _install_units(home, catalog, [], launch["harness"], dry_run, everything=True)
    if not dry_run:
        _drop_section(home, launch["harness"])
        for generated in ("launch.json", ".gitignore"):
            (home / generated).unlink(missing_ok=True)
    result = _result(name, home, launch, [], dry_run, [])
    result["kept"] = sorted(p.name for p in home.iterdir()) if home.is_dir() else []
    return result
