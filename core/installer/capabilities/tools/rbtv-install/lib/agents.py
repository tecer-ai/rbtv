"""Agent-folder resolution and the small agent-only boundary around root verbs."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from discovery import Refuse

from . import frontmatter, schema
from .catalog import check_packs, pack_units
from .claims import _block_del
from .constants import AGENT_RECORD, GUIDANCE_FILE, HARNESSES
from .fsio import write_file
from .operations import do_install, do_uninstall
from .selection import _split_part_keys, iter_booked_units, resolve_name
from .state import read_state, unit_membership, write_state

AGENTS_REL = Path(".rbtv") / "agents"
IGNORE_TEXT = ("# rbtv: generated files and machine data\n*\n!agent.md\n!agent.json\n"
               "!settings.json\n!memory/\n!memory/**\n!_artifacts/\n!_artifacts/**\n")
# The folder's own files, created when missing; the result lists them.
OWN_BODIES = {"settings.json": "{}\n", ".gitignore": IGNORE_TEXT}
OWN_FILES = tuple(OWN_BODIES)


def agent_home(root: Path, name: str) -> Path:
    return root / AGENTS_REL / name


def is_path(raw: str) -> bool:
    """An AGENT argument is a path when it has a slash or is a dot name."""
    return "/" in raw or raw in (".", "..")


def _refuse(code: str, message: str, next_cmd: str, path: str = "") -> Refuse:
    exc = Refuse(code, message, path)
    exc.next = next_cmd
    return exc


def resolve_agent(root: Path, raw: str) -> Path:
    """Resolve a named agent below an installation or a path managed in place."""
    home = Path(raw).expanduser().resolve() if is_path(raw) else agent_home(root, raw)
    if not home.exists():
        if is_path(raw):
            raise _refuse("agent-unknown", f"no agent folder at {home}.",
                          "rbtv agent list", str(home))
        raise _refuse("agent-unknown", f"no agent named {raw!r} under {root / AGENTS_REL}/, "
                      "and no component ships an agent of that name.",
                      "rbtv list --type agent")
    if not home.is_dir():
        raise Refuse("agent-folder-invalid", f"{home} is not an agent folder")
    if not (home / AGENT_RECORD).is_file():
        raise _refuse("agent-json-missing", f"no agent.json in {home}. An agent folder holds "
                      "agent.md and agent.json.", "rbtv agent add -h", str(home))
    if not (home / "agent.md").is_file():
        raise _refuse("agent-md-missing", f"no agent.md in {home}. An agent folder holds "
                      "agent.md and agent.json.", "rbtv agent add -h", str(home))
    return home


def _agent_front(home: Path) -> dict:
    path = home / "agent.md"
    try:
        front, _body = frontmatter.split(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise Refuse("agent-file-unreadable", f"cannot read {path}: {exc}", str(path)) from exc
    problems = schema.errors(front or {}, schema.load("agent"))
    if problems:
        raise Refuse("agent-file-invalid", f"{path}: " + "; ".join(problems), str(path))
    return front


def agent_state(home: Path) -> dict:
    """Read and validate an authored agent record before any operation."""
    record = home / AGENT_RECORD
    try:
        json.loads(record.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _refuse("agent-json-invalid", f"agent.json is not valid JSON (line {exc.lineno}, "
                      f"{exc.msg}).", "rbtv agent add -h", str(record)) from exc
    try:
        state = read_state(home)
    except Refuse as exc:
        if exc.code == "state-unreadable":
            raise Refuse("agent-record-invalid", exc.message + "; repair agent.json, then retry", exc.path) from exc
        raise
    required = ("name", "description", "harness", "model", "effort", "units", "packs")
    missing = [name for name in required if name not in state]
    if missing:
        raise Refuse("agent-record-invalid", "agent.json is missing " + ", ".join(missing)
                     + ". Add those fields, then retry", str(home / AGENT_RECORD))
    front = _agent_front(home)
    names = {"folder": home.name, "agent.md": front["name"], "agent.json": state["name"]}
    if len(set(names.values())) != 1:
        raise _refuse("agent-name-mismatch", "the three names disagree.\n"
                      f"folder name:  {names['folder']}\nagent.md:     {names['agent.md']}\n"
                      f"agent.json:   {names['agent.json']}",
                      "make the three names the same, then retry the same command", str(home))
    problems = schema.errors({key: state[key] for key in required}, schema.load("agent-json"))
    if problems:
        raise Refuse("agent-record-invalid", f"{home / AGENT_RECORD}: " + "; ".join(problems)
                     + ". Repair it, then retry", str(home / AGENT_RECORD))
    return state


def cast_catalog() -> dict[str, dict[str, list[str]]]:
    exe = shutil.which("cast")
    if exe is None:
        raise _refuse("cast-missing", "cast is not on PATH, so model and effort cannot be checked "
                      "against cast list.", "rbtv doctor")
    done = subprocess.run([exe, "list", "--json"], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(done.stdout)
    except ValueError as exc:
        raise Refuse("cast-unreadable", "`cast list --json` did not return JSON; repair cast, then retry") from exc


def launch_values(harness: str, model: str, effort: str, known: dict) -> dict:
    if harness not in HARNESSES or model not in (known.get(harness) or {}):
        raise _refuse("launch-invalid", f"{harness} has no model {model!r}. "
                      "See `cast list`", "cast list")
    rungs = known[harness][model]
    if not rungs:
        return {"harness": harness, "model": model, "effort": "inert"}
    if effort.isdigit() and 1 <= int(effort) <= 5:
        effort = rungs[min(int(effort), len(rungs)) - 1]
    if effort not in rungs:
        raise _refuse("launch-invalid", f"{model} does not accept effort {effort!r}. "
                      "See `cast list`", "cast list")
    return {"harness": harness, "model": model, "effort": effort}


def _keys(names: list[str], catalog: dict, book: dict | None = None) -> set[str]:
    return {unit["key"] for name in names for unit in resolve_name(name, catalog, book)["units"]}


def _agent_section(home: Path, harness: str, dry: bool) -> list[str]:
    path = home / GUIDANCE_FILE[harness]
    from .claims import _block_set
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    wanted = _block_set(text, "Your instructions are in `agent.md` in this folder. Follow them.", "<!--", preserve_outside=True, label="agent")
    if not dry and wanted != text:
        write_file(path, wanted, newline="\n")
    return [path.name] if wanted != text else []


def _agent_files(home: Path, state: dict, dry: bool) -> list[str]:
    """Create the folder's own settings and ignore files when missing, then write
    the harness instruction section. Returns the names written: the own files
    that were missing, then the instruction file. Own files are not generated
    files; the result lists them apart (see commands._print_agent)."""
    created = []
    for name, body in OWN_BODIES.items():
        path = home / name
        if not path.exists():
            created.append(name)
            if not dry:
                write_file(path, body, newline="\n")
    return created + _agent_section(home, state["harness"], dry)


def _remove_agent_section(home: Path, harness: str, dry: bool) -> list[str]:
    """Release only the generated agent section from a former harness file."""
    path = home / GUIDANCE_FILE[harness]
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    wanted = _block_del(text, "<!--", preserve_outside=True, label="agent")
    if wanted == text:
        return []
    if not dry:
        if wanted.strip():
            write_file(path, wanted, newline="\n")
        else:
            path.unlink()
    return [path.name]


def _launch(state: dict) -> dict:
    return {key: state[key] for key in ("harness", "model", "effort")} | {
        "voice": state.get("voice")}


def configure_agent(root: Path, raw: str, harness: str | None,
                    model: str | None, effort: str | None, voice: str | None,
                    catalog: dict, dry: bool) -> dict:
    """Change an agent's authored launch settings and replan only a harness flip."""
    if all(value is None for value in (harness, model, effort, voice)):
        raise _refuse("usage", "at least one of --harness, --model, --effort, --voice is required",
                      "rbtv agent configure -h")
    home = resolve_agent(root, raw)
    before = agent_state(home)
    after = dict(before)
    for key, value in (("harness", harness), ("model", model),
                       ("effort", effort), ("voice", voice)):
        if value is not None:
            after[key] = value
    launch = launch_values(after["harness"], after["model"],
                           str(after["effort"]), cast_catalog())
    after.update(launch)
    changed_harness = before["harness"] != after["harness"]
    wanted = _keys(list(after["units"]), catalog) | pack_units(catalog, set(after["packs"]))
    picked, parts = _split_part_keys(wanted)
    unit_files = (do_install(home, catalog, picked, [after["harness"]], dry,
                             guidance_basis="none", parts=parts,
                             selected=parts) if changed_harness else {
                                 "harnesses": [after["harness"]], "written": [],
                                 "deleted": [], "skipped": [], "selected_units": []})
    written = ["agent.json"] if before != after else []
    if changed_harness:
        if GUIDANCE_FILE[before["harness"]] != GUIDANCE_FILE[after["harness"]]:
            released = _remove_agent_section(home, before["harness"], dry)
            if released:
                unit_files["deleted"] = sorted(set(unit_files.get("deleted", [])) | set(released))
        written += _agent_files(home, after, dry)
    if not dry and before != after:
        write_state(home, after)
    return {"ok": True, "agent": after["name"], "home": str(home),
            "launch": _launch(after), "before": _launch(before),
            "packs": list(after["packs"]), "written": written,
            "units": sorted(wanted), "units_removed": [],
            "unit_files": unit_files, "dry_run": dry,
            "harness_changed": changed_harness}


def list_agents(root: Path, folder: Path | None) -> dict:
    """Read agent records below one folder without validating their generated files."""
    search = folder if folder is not None else root / AGENTS_REL
    if not search.is_dir():
        if folder is None:
            return {"ok": True, "folder": str(search), "total": 0, "returned": 0, "agents": []}
        exc = _refuse("not-a-folder", f"no folder at {search}",
                      "rbtv agent list", str(search))
        exc.unchanged = "Nothing was listed."
        raise exc
    homes = ([search] if (search / AGENT_RECORD).is_file() else []) + sorted(
        path.parent for path in search.rglob(AGENT_RECORD.name))
    rows = []
    for home in dict.fromkeys(homes):
        record = home / AGENT_RECORD
        try:
            data = json.loads(record.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("the JSON value is not an object")
            row = {"name": data.get("name", home.name), "home": str(home),
                   "launch": {key: data.get(key) for key in ("harness", "model", "effort", "voice")},
                   "packs": data.get("packs", []), "units": data.get("units", [])}
            if not isinstance(row["packs"], list) or not isinstance(row["units"], list):
                raise ValueError("packs and units must be lists")
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            row = {"name": home.name, "home": str(home), "unreadable": str(exc)}
        rows.append(row)
    rows.sort(key=lambda row: (str(row["name"]), row["home"]))
    return {"ok": True, "folder": str(search), "total": len(rows), "returned": len(rows), "agents": rows}


def add_agent(root: Path, raw: str, names: list[str], packs: set[str], catalog: dict, dry: bool) -> dict:
    home = resolve_agent(root, raw)
    state = agent_state(home)
    check_packs(catalog, packs, "rbtv list --type pack")
    launch_values(state["harness"], state["model"], str(state["effort"]), cast_catalog())
    explicit = _keys(names, catalog)
    declared = _keys(list(state["units"]), catalog)
    before = declared | pack_units(catalog, set(state["packs"]))
    enabled = set(state["packs"]) | packs
    wanted = declared | explicit | pack_units(catalog, enabled)
    written = _agent_files(home, state, dry)
    picked, parts = _split_part_keys(wanted)
    result = do_install(home, catalog, picked, [state["harness"]], dry, guidance_basis="none", parts=parts)
    if not dry:
        after = read_state(home)
        after["units"], after["packs"] = sorted(declared | explicit), sorted(enabled)
        write_state(home, after)
    added, packs_on = sorted(wanted - before), sorted(packs - set(state["packs"]))
    touched = bool(added or packs_on or written or result.get("written") or result.get("deleted"))
    return {"ok": True, "agent": state["name"], "home": str(home), "launch": _launch(state),
            "packs": sorted(enabled), "written": (["agent.json"] if touched and not dry else []) + written,
            "units": sorted(wanted), "units_removed": [], "was": len(before), "added": added,
            "packs_on": packs_on, "unit_files": result, "dry_run": dry}


def update_agent(root: Path, raw: str, scope: str, catalog: dict, dry: bool) -> dict:
    """Reconcile the folder with agent.json. The membership is read before the
    install writes; `guidance` adds and removes nothing, so it only reports a
    mismatch (listed_missing, on_disk_unlisted) for the caller to name."""
    home = resolve_agent(root, raw)
    state = agent_state(home)
    wanted = _keys(list(state["units"]), catalog) | pack_units(catalog, set(state["packs"]))
    members = unit_membership(home, catalog, state, wanted)
    picked, parts = _split_part_keys(wanted)
    result = do_install(home, catalog, picked, [state["harness"]], dry, guidance_basis="none", parts=parts, scope=scope, selected=parts if scope in ("scaffolding", "all") else None)
    written = _agent_files(home, state, dry) if scope != "guidance" else []
    guidance = scope == "guidance"
    return {"ok": True, "agent": state["name"], "home": str(home), "launch": _launch(state),
            "packs": list(state["packs"]), "scope": scope, "written": written,
            "units": sorted(wanted), "units_removed": [], "unit_files": result, "dry_run": dry,
            "added": [] if guidance else sorted(members["added"]),
            "removed": [] if guidance else sorted(members["removed"]),
            "on_disk": sorted(members["booked"]),
            "listed_missing": sorted(members["listed_missing"]),
            "on_disk_unlisted": sorted(members["on_disk_unlisted"])}


def remove_agent(root: Path, raw: str, names: list[str], packs: set[str], all_units: bool, yes: bool, catalog: dict, dry: bool) -> dict:
    if not (names or packs or all_units):
        raise Refuse("usage", "agent remove needs a NAME, --pack, or --all")
    home = resolve_agent(root, raw)
    state = agent_state(home)
    if all_units and not yes:
        pack_part = f", pack {', '.join(state['packs'])}" if state["packs"] else ""
        before = _keys(list(state["units"]), catalog, state.get("components")) | pack_units(catalog, set(state["packs"]))
        count = f"{len(before)} unit{'' if len(before) == 1 else 's'}"
        raise Refuse("confirm-required", f"--all removes every unit from {state['name']} "
                     f"({count}{pack_part}). Re-run with --yes:\n"
                     f"rbtv agent remove {raw} --all --yes")
    check_packs(catalog, packs, "rbtv list --type pack")
    before = _keys(list(state["units"]), catalog, state.get("components")) | pack_units(catalog, set(state["packs"]))
    removed = set(state["units"]) if all_units else _keys(names, catalog, state.get("components"))
    enabled = set() if all_units else set(state["packs"]) - packs
    explicit = set() if all_units else set(state["units"]) - removed
    wanted = explicit | pack_units(catalog, enabled)
    booked = {row["key"] for row in iter_booked_units(catalog, state.get("components") or {})}
    gone = booked - wanted
    picked, parts = _split_part_keys(gone)
    result = do_uninstall(home, catalog, picked, dry, parts=parts) if parts else {"ok": True, "uninstalled": [], "dry_run": dry, "report": {}}
    if not dry:
        after = read_state(home)
        after["units"], after["packs"] = sorted(explicit), sorted(enabled)
        write_state(home, after)
    packs_off = sorted(set(state["packs"]) if all_units else set(state["packs"]) & packs)
    return {"ok": True, "agent": state["name"], "home": str(home), "launch": _launch(state),
            "packs": sorted(enabled), "written": [], "units": sorted(wanted),
            "units_removed": sorted(gone), "unit_files": result, "kept": ["agent.md", AGENT_RECORD.name],
            "dry_run": dry, "was": len(before), "all": all_units, "packs_off": packs_off,
            "absent_packs": sorted(packs - set(state["packs"]))}
