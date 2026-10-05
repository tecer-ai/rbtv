"""Agent-folder resolution and the small agent-only boundary around root verbs."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from discovery import LAUNCH_FIELDS, Refuse

from . import frontmatter, schema, subagents
from .catalog import check_packs, pack_units
from .claims import _block_del
from .constants import (AGENT_RECORD, EFFORT_INERT, GUIDANCE_FILE, HARNESSES, MATRIX,
                        SHARED_FILE_DESTINATIONS)
from .fsio import write_file
from .operations import do_install, do_uninstall
from .selection import _split_part_keys, iter_booked_units, iter_catalog_parts, resolve_name
from .state import read_state, unit_membership, write_state

AGENTS_REL = Path(".rbtv") / "agents"


def _ignore_text() -> str:
    """The agent-local ignores, derived from every harness's output paths."""
    folders = {
        path.partition("{name}")[0].rstrip("/") + "/"
        for paths in MATRIX.values()
        for path in paths.values()
        if path is not None
    }
    generated = (sorted(folders | set(SHARED_FILE_DESTINATIONS))
                 + sorted(set(GUIDANCE_FILE.values())))
    machine_data = ("state.sqlite*", "turns/", "conversations/*/session*")
    return ("# rbtv: generated files and machine data\n"
            + "\n".join((*generated, ".gitignore", *machine_data)) + "\n")


IGNORE_TEXT = _ignore_text()
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


def unplaced_shipped_agent(root: Path, raw: str, catalog: dict) -> dict | None:
    """The catalog row of the agent a component ships under this name, when its
    named home does not exist yet; None for a path or a folder that exists."""
    if is_path(raw) or agent_home(root, raw).exists():
        return None
    matches = [part for part in iter_catalog_parts(catalog)
               if part["unit_id"] == raw and part["method"] == "agent"]
    return matches[0] if len(matches) == 1 else None


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
    return _checked_agent(home, _read_agent(home))


def _read_agent(home: Path) -> dict:
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
    return state


def _checked_agent(home: Path, state: dict) -> dict:
    required = ("name", "description", *LAUNCH_FIELDS, "units", "packs")
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


def cast_model_id(harness: str, model: str, folder: Path) -> str:
    """The harness's own id for a model, as `cast` passes it on a launch: read
    from the command a `cast --dry-run` would start, so rbtv keeps no second
    model table. The effort given there is any number; the id does not depend
    on it."""
    exe = shutil.which("cast")
    if exe is None:
        raise _refuse("cast-missing", "cast is not on PATH, so the harness's own "
                      "name for the model cannot be read.", "rbtv doctor")
    done = subprocess.run(
        [exe, harness, model, "1", str(folder), "-p", "ok", "--dry-run"],
        capture_output=True, text=True, encoding="utf-8")
    try:
        argv = json.loads(done.stdout)["argv"]
        return argv[next(i for i, word in enumerate(argv) if word in ("--model", "-m")) + 1]
    except (ValueError, KeyError, TypeError, StopIteration, IndexError) as exc:
        raise Refuse("cast-unreadable", f"`cast {harness} {model} --dry-run` did not "
                     "name the model; repair cast, then retry") from exc


def launch_values(harness: str, model: str, effort: str, known: dict) -> dict:
    if harness not in HARNESSES or model not in (known.get(harness) or {}):
        raise _refuse("launch-invalid", f"{harness} has no model {model!r}. "
                      "See `cast list`", "cast list")
    rungs = known[harness][model]
    if not rungs:
        return {"harness": harness, "model": model, "effort": EFFORT_INERT}
    if effort.isdigit() and 1 <= int(effort) <= 5:
        effort = rungs[min(int(effort), len(rungs)) - 1]
    if effort not in rungs:
        raise _refuse("launch-invalid", f"{model} does not accept effort {effort!r}. "
                      "See `cast list`", "cast list")
    return {"harness": harness, "model": model, "effort": effort}


def on_values(on: list[str], named: list[dict], receiving: list[str],
              target: Path, configure_cmd: str) -> dict[str, dict]:
    """The checked `--on` values of the agents a command names as units, with
    the check and the model names an rbtv agent's values get. `cast` is read
    only when there is a value to check."""
    return subagents.values_for(
        on, named, receiving, target, known=cast_catalog() if on and named else {},
        check=launch_values, model_id=cast_model_id, configure_cmd=configure_cmd)


def _launch_flags(name: str, has: bool, given: dict | None) -> dict:
    """The --harness, --model and --effort `agent add` was given: all three
    when the agent's record has none, and none when it has them."""
    flags = {key: value for key, value in (given or {}).items() if value is not None}
    if has and flags:
        raise _refuse(
            "launch-already-set",
            f"{name} already has a harness, a model and an effort in its "
            "agent.json. --harness, --model and --effort are for an agent "
            "that has none; change them with rbtv agent configure",
            f"rbtv agent configure {name} "
            + " ".join(f"--{key} {value}" for key, value in flags.items()))
    if not has and len(flags) < len(LAUNCH_FIELDS):
        raise _refuse(
            "launch-required",
            f"{name} has no harness, model or effort in its agent.json; an agent "
            "a component ships never has. Give all three: --harness, --model "
            "and --effort", "cast list")
    return flags


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
        # `do_install` has already booked every generated file and shared claim.
        # Keep that record and change only the authored launch values.
        saved = read_state(home) if changed_harness else after
        for key in ("harness", "model", "effort", "voice"):
            saved[key] = after.get(key)
        write_state(home, saved)
    return {"ok": True, "agent": after["name"], "home": str(home),
            "launch": _launch(after), "before": _launch(before),
            "packs": list(after["packs"]), "written": written,
            "units": sorted(wanted), "units_removed": [],
            "unit_files": unit_files, "dry_run": dry,
            "harness_changed": changed_harness,
            # A sub-agent written for the former harness has no model and no
            # effort for the new one: each is named with the command that adds it.
            "sub_agents_missing": [
                {"id": key, "name": key.split("#", 1)[1], "harness": after["harness"],
                 "command": f"rbtv agent add {raw} {key.split('#', 1)[1]} "
                            f"--on {after['harness']}:MODEL:EFFORT"}
                for key in sorted(subagents.recorded(before))] if changed_harness else []}


def cast_agent_list(root: Path, raw: str | None, as_json: bool, width: int) -> str:
    """What `cast list --agents` prints for this installation, or `cast list
    --agent` for one agent. The list of agents
    has one source, in cast, so nothing here reads the agent folders to list
    them. `raw` names one agent to show in full; it is resolved as for the
    other agent verbs and handed to cast as a path."""
    exe = shutil.which("cast")
    if exe is None:
        exc = _refuse("cast-missing", "cast is not on PATH, so the agents cannot be listed.",
                      "rbtv doctor")
        exc.unchanged = "Nothing was listed."
        raise exc
    if raw is None:
        words = [exe, "list", "--agents"]
    else:
        # Forward slashes on every system: cast takes a value with a slash as a path.
        words = [exe, "list", "--agent", resolve_agent(root, raw).as_posix()]
    if as_json:
        words.append("--json")
    done = subprocess.run(words, cwd=root, env={**os.environ, "COLUMNS": str(width)},
                          capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        exc = _refuse("cast-refused", "`cast list` refused: " + " ".join(done.stderr.split()),
                      "rbtv doctor")
        exc.unchanged = "Nothing was listed."
        raise exc
    return done.stdout


def add_agent(root: Path, raw: str, names: list[str], packs: set[str], catalog: dict,
              dry: bool, given: dict | None = None, on: tuple[str, ...] = ()) -> dict:
    """Apply an agent folder, placing it first when a component ships it.
    `given` holds --harness, --model and --effort; `on` the --on values of the
    agents named among the units."""
    part = unplaced_shipped_agent(root, raw, catalog)
    home = agent_home(root, raw) if part else resolve_agent(root, raw)
    if part:
        source = Path(catalog[part["component"]]["path"]) / "agents" / raw
        state = {"units": [], "packs": [],
                 **json.loads((source / AGENT_RECORD.name).read_text(encoding="utf-8"))}
    else:
        state = _read_agent(home)
    launch = _launch_flags(raw, all(key in state for key in LAUNCH_FIELDS), given)
    if not launch and not part:
        _checked_agent(home, state)
    check_packs(catalog, packs, "rbtv list --type pack")
    known = cast_catalog()
    if launch:
        launch = launch_values(launch["harness"], launch["model"], launch["effort"], known)
        state.update(launch)
    else:
        launch_values(state["harness"], state["model"], str(state["effort"]), known)
    placed = None
    if part:
        placed = {"id": part["key"], "files": ["agent.md", AGENT_RECORD.name]}
        if not dry:
            home.mkdir(parents=True, exist_ok=True)
            write_file(home / "agent.md", (source / "agent.md").read_text(encoding="utf-8"),
                       newline="\n")
            write_file(home / AGENT_RECORD, json.dumps(state, indent=2) + "\n", newline="\n")
            state = agent_state(home)
    elif launch:
        _checked_agent(home, state)
    explicit = _keys(names, catalog)
    declared = _keys(list(state["units"]), catalog)
    before = declared | pack_units(catalog, set(state["packs"]))
    enabled = set(state["packs"]) | packs
    wanted = declared | explicit | pack_units(catalog, enabled)
    receiving = [state["harness"]]
    named = subagents.named_agents(catalog, explicit)
    sub_agents = on_values(list(on), named, receiving, home, f"rbtv agent configure {raw} -h")
    written = _agent_files(home, state, dry)
    picked, parts = _split_part_keys(wanted)
    recorded = subagents.recorded(state)
    result = do_install(home, catalog, picked, receiving, dry, guidance_basis="none",
                        parts=parts, sub_agents=sub_agents)
    if not dry:
        after = read_state(home)
        after.update(launch)
        after["units"], after["packs"] = sorted(declared | explicit), sorted(enabled)
        write_state(home, after)
    added, packs_on = sorted(wanted - before), sorted(packs - set(state["packs"]))
    touched = bool(added or packs_on or written or launch
                   or result.get("written") or result.get("deleted"))
    return {"ok": True, "agent": state["name"], "home": str(home), "launch": _launch(state), "placed": placed,
            "packs": sorted(enabled), "written": (["agent.json"] if touched and not dry else []) + written,
            "units": sorted(wanted), "units_removed": [], "was": len(before), "added": added,
            "packs_on": packs_on, "unit_files": result, "dry_run": dry,
            "sub_agents": subagents.describe(named, sub_agents, recorded, receiving,
                                             catalog, home)}


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
    try:
        removed = (set(state["units"]) if all_units else
                   _keys(names, catalog, state.get("components")))
    except Refuse as exc:
        if exc.code != "name-unknown":
            raise
        unknown = names[0] if names else ""
        refusal = _refuse("name-unknown", f"unknown unit {unknown!r}",
                          "rbtv list")
        refusal.candidates = getattr(exc, "candidates", [])
        raise refusal from exc
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
