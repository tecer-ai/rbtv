"""Agent-folder resolution and the small agent-only boundary around root verbs."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from discovery import LAUNCH_FIELDS, Refuse

from . import frontmatter, schema, subagents
from .catalog import check_packs, pack_files
from .claims import _block_del
from .constants import (AGENT_RECORD, AGENT_SECTION_LABEL, EFFORT_INERT, GUIDANCE_FILE, HARNESSES, MATRIX,
                        PROMPT_FILE,
                        SHARED_FILE_DESTINATIONS)
from .files_key import files_key
from .fsio import write_file
from .link_paths import absolute_links
from .operations import do_install, do_uninstall
from .selection import (_split_part_keys, close_names_sentence, iter_booked_files,
                        iter_catalog_parts, resolve_name)
from .state import read_state, file_membership, write_state

AGENTS_REL = Path(".rbtv") / "agents"


def _ignore_text() -> str:
    """The agent-local ignores, derived from every harness's output paths."""
    folders = {
        path.partition("{name}")[0].rstrip("/") + "/"
        for paths in MATRIX.values()
        for path in paths.values()
        if path is not None
    }
    harness_paths = (sorted(folders | set(SHARED_FILE_DESTINATIONS))
                     + sorted(set(GUIDANCE_FILE.values())))
    machine_data = ("state.sqlite*", "turns/", "conversations/*/session*")
    return ("# rbtv: harness files and machine data\n"
            + "\n".join((*harness_paths, ".gitignore", *machine_data)) + "\n")


IGNORE_TEXT = _ignore_text()
# The folder's own files, created when missing; the result lists them.
OWN_BODIES = {"settings.json": "{}\n", ".gitignore": IGNORE_TEXT}
OWN_FILES = tuple(OWN_BODIES)


def agent_home(root: Path, name: str) -> Path:
    return root / AGENTS_REL / name


def is_path(raw: str) -> bool:
    """An AGENT argument is a path when it has a slash or a backslash, or is a
    dot name. This and `agent_home` state cast's rules (`lib/agent.js` of the
    cast tool); the self-test runs cast's code and fails when they differ."""
    return "/" in raw or "\\" in raw or raw in (".", "..")


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
                      f"{PROMPT_FILE} and agent.json.", "rbtv agent add -h", str(home))
    require_prompt(home)
    return home


def require_prompt(home: Path) -> None:
    """Refuse an agent folder without its prompt file. A folder that still
    holds the file under its old name gets the rename command."""
    if (home / PROMPT_FILE).is_file():
        return
    old = "agent.md"
    message = f"{home / PROMPT_FILE} is missing."
    next_cmd = "rbtv agent add -h"
    if (home / old).is_file():
        message += (f" This folder still has {old}, the old name of the prompt file. If another "
                    "machine already renamed it, pull first; otherwise rename it with: "
                    f"git mv {old} {PROMPT_FILE} (inside {home}), and change any .gitignore "
                    f"line that names {old}.")
        next_cmd = f"git mv {old} {PROMPT_FILE}"
    raise _refuse("prompt-missing", message, next_cmd, str(home))


def unplaced_shipped_agent(root: Path, raw: str, catalog: dict) -> dict | None:
    """The catalog row of the agent a component ships under this name, when its
    named home does not exist yet; None for a path or a folder that exists."""
    if is_path(raw) or agent_home(root, raw).exists():
        return None
    matches = [part for part in iter_catalog_parts(catalog)
               if part["file_id"] == raw and part["method"] == "agent"]
    return matches[0] if len(matches) == 1 else None


def _agent_front(home: Path) -> dict:
    require_prompt(home)
    path = home / PROMPT_FILE
    try:
        front, _body = frontmatter.split(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise Refuse("agent-file-unreadable", f"cannot read {path}: {exc}", str(path)) from exc
    problems = schema.errors(front or {}, schema.load("prompt"))
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
    required = ("name", "description", *LAUNCH_FIELDS, "files", "packs")
    missing = [name for name in required if name not in state]
    if missing:
        raise Refuse("agent-record-invalid", "agent.json is missing " + ", ".join(missing)
                     + ". Add those fields, then retry", str(home / AGENT_RECORD))
    front = _agent_front(home)
    names = {"folder": home.name, "prompt": front["name"], "agent.json": state["name"]}
    if len(set(names.values())) != 1:
        raise _refuse("agent-name-mismatch", "the three names disagree.\n"
                      f"folder name:  {names['folder']}\n{PROMPT_FILE}:    {names['prompt']}\n"
                      f"agent.json:   {names['agent.json']}",
                      "make the three names the same, then retry the same command", str(home))
    problems = schema.errors({key: state[key] for key in required}, schema.load("agent-json"))
    if problems:
        raise Refuse("agent-record-invalid", f"{home / AGENT_RECORD}: " + "; ".join(problems)
                     + ". Repair it, then retry", str(home / AGENT_RECORD))
    return state


def cast_catalog(folder: Path) -> dict[str, dict[str, dict]]:
    """The models cast supports, by harness then model: `{"rungs": the model's
    effort words, "selected": whether the installation selected it}`. cast
    answers `selected` for the installation that holds its current folder, so
    it is run from `folder`: the agent's folder, or the installation."""
    exe = shutil.which("cast")
    if exe is None:
        raise _refuse("cast-missing", "cast is not on PATH, so model and effort cannot be checked "
                      "against cast models list.", "rbtv doctor")
    done = subprocess.run([exe, "models", "list", "--supported", "--json"], cwd=folder,
                          capture_output=True, text=True, encoding="utf-8")
    try:
        answer = json.loads(done.stdout)
    except ValueError:
        answer = None
    if done.returncode != 0:
        # Under --json cast words its refusal on standard output.
        said = answer["message"] if isinstance(answer, dict) and answer.get("message") else done.stderr
        raise _refuse("cast-refused", "`cast models list` refused: " + " ".join(said.split()),
                      "rbtv doctor")
    try:
        known: dict[str, dict[str, dict]] = {}
        for row in answer["models"]:
            known.setdefault(row["harness"], {})[row["model"]] = {
                "rungs": row["rungs"], "selected": row["selected"]}
        return known
    except (KeyError, TypeError) as exc:
        raise Refuse("cast-unreadable", "`cast models list --supported --json` did not return "
                     "its list of models; repair cast, then retry") from exc


def cast_model_id(harness: str, model: str, folder: Path) -> str:
    """The harness's own id for a model, as `cast` passes it on a launch: read
    from the command a `cast --dry-run` would start, so rbtv keeps no second
    model table. The effort given there is any number; the id does not depend
    on it. cast runs from `folder`, whose installation decides whether the
    model may be launched."""
    exe = shutil.which("cast")
    if exe is None:
        raise _refuse("cast-missing", "cast is not on PATH, so the harness's own "
                      "name for the model cannot be read.", "rbtv doctor")
    done = subprocess.run(
        [exe, harness, model, "1", str(folder), "-p", "ok", "--dry-run"],
        cwd=folder, capture_output=True, text=True, encoding="utf-8")
    try:
        argv = json.loads(done.stdout)["argv"]
        return argv[next(i for i, word in enumerate(argv) if word in ("--model", "-m")) + 1]
    except (ValueError, KeyError, TypeError, StopIteration, IndexError) as exc:
        raise Refuse("cast-unreadable", f"`cast {harness} {model} --dry-run` did not "
                     "name the model; repair cast, then retry") from exc


def cast_effort_word(harness: str, model: str, number: str, folder: Path) -> str | None:
    """The model's own effort word for an effort number, as `cast` resolves it
    on a launch: read from a `cast --dry-run` run from `folder`, so rbtv keeps
    no second copy of what a number means. None when cast refuses the number."""
    exe = shutil.which("cast")
    if exe is None:
        raise _refuse("cast-missing", "cast is not on PATH, so the effort number cannot be "
                      "turned into the model's own word.", "rbtv doctor")
    done = subprocess.run([exe, harness, model, number, "-p", "ok", "--dry-run"],
                          cwd=folder, capture_output=True, text=True, encoding="utf-8")
    if done.returncode:
        return None
    try:
        return json.loads(done.stdout)["effort_word"]
    except (ValueError, KeyError, TypeError) as exc:
        raise Refuse("cast-unreadable", f"`cast {harness} {model} {number} --dry-run` did not "
                     "name the effort word; repair cast, then retry") from exc


def launch_values(harness: str, model: str, effort: str, known: dict, folder: Path) -> dict:
    """The checked harness, model and effort word. `known` is `cast_catalog`
    read from `folder`, where cast is also asked what an effort number means."""
    if harness not in HARNESSES or model not in (known.get(harness) or {}):
        raise _refuse("launch-invalid", f"{harness} {model!r} is not a model cast supports. "
                      "See `cast models list --supported`", "cast models list --supported")
    if not known[harness][model]["selected"]:
        raise _refuse("launch-invalid", f"{harness} {model!r} is not selected in this "
                      f"installation. Select it with `cast models add {harness} {model}`",
                      f"cast models add {harness} {model}")
    rungs = known[harness][model]["rungs"]
    if not rungs:
        return {"harness": harness, "model": model, "effort": EFFORT_INERT}
    if effort.isdigit():
        effort = cast_effort_word(harness, model, effort, folder) or effort
    if effort not in rungs:
        raise _refuse("launch-invalid", f"{model} does not accept effort {effort!r}. "
                      "See `cast models list`", "cast models list")
    return {"harness": harness, "model": model, "effort": effort}


def on_values(on: list[str], named: list[dict], receiving: list[str],
              target: Path, configure_cmd: str) -> dict[str, dict]:
    """The checked `--on` values of the agents a command names as files, with
    the check and the model names an rbtv agent's values get. `cast` is read
    only when there is a value to check."""
    return subagents.values_for(
        on, named, receiving, target, known=cast_catalog(target) if on and named else {},
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
            "and --effort", "cast models list")
    return flags


def _keys(names: list[str], catalog: dict, book: dict | None = None,
          *, suggest_installed: bool = False) -> set[str]:
    return {file["key"] for name in names
            for file in resolve_name(name, catalog, book,
                                     suggest_installed=suggest_installed)["files"]}


def _agent_section(home: Path, harness: str, dry: bool) -> list[str]:
    path = home / GUIDANCE_FILE[harness]
    from .claims import _block_set
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    wanted = _block_set(text, f"Your instructions are in `{PROMPT_FILE}` in this folder. Follow them.", "<!--", preserve_outside=True, label=AGENT_SECTION_LABEL)
    if not dry and wanted != text:
        write_file(path, wanted, newline="\n")
    return [path.name] if wanted != text else []


def _agent_files(home: Path, state: dict, dry: bool) -> list[str]:
    """Create the folder's own settings and ignore files when missing, then write
    the harness instruction section. Returns the names written: the own files
    that were missing, then the instruction file. Own files are not harness
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
    wanted = _block_del(text, "<!--", preserve_outside=True, label=AGENT_SECTION_LABEL)
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
                           str(after["effort"]), cast_catalog(home), home)
    after.update(launch)
    changed_harness = before["harness"] != after["harness"]
    wanted = _keys(list(after["files"]), catalog) | pack_files(catalog, set(after["packs"]))
    picked, parts = _split_part_keys(wanted)
    harness_files = (do_install(home, catalog, picked, [after["harness"]], dry,
                             guidance_basis="none", parts=parts,
                             selected=parts) if changed_harness else {
                                 "harnesses": [after["harness"]], "written": [],
                                 "deleted": [], "skipped": [], "selected_files": []})
    written = ["agent.json"] if before != after else []
    if changed_harness:
        if GUIDANCE_FILE[before["harness"]] != GUIDANCE_FILE[after["harness"]]:
            released = _remove_agent_section(home, before["harness"], dry)
            if released:
                harness_files["deleted"] = sorted(set(harness_files.get("deleted", [])) | set(released))
        written += _agent_files(home, after, dry)
    if not dry and before != after:
        # `do_install` has already booked every harness file and shared claim.
        # Keep that record and change only the authored launch values.
        saved = read_state(home) if changed_harness else after
        for key in ("harness", "model", "effort", "voice"):
            saved[key] = after.get(key)
        write_state(home, saved)
    return {"ok": True, "agent": after["name"], "home": str(home),
            "launch": _launch(after), "before": _launch(before),
            "packs": list(after["packs"]), "written": written,
            "files": sorted(wanted), "files_removed": [],
            "harness_files": harness_files, "dry_run": dry,
            "harness_changed": changed_harness,
            # A sub-agent written for the former harness has no model and no
            # effort for the new one: each is named with the command that adds it.
            "sub_agents_missing": [
                {"id": key, "name": key.split("#", 1)[1], "harness": after["harness"],
                 "command": f"rbtv agent add {raw} {key.split('#', 1)[1]} "
                            f"--on {after['harness']}:MODEL:EFFORT"}
                for key in sorted(subagents.recorded(before))] if changed_harness else []}


def cast_agent_list(root: Path, raw: str | None, as_json: bool, full: bool, width: int,
                    folder: str | None = None) -> str:
    """What `cast list --agents` prints for this installation, or `cast list
    --agent` for one agent. The list of agents
    has one source, in cast, so nothing here reads the agent folders to list
    them. `raw` names one agent to show in full; it is resolved as for the
    other agent verbs and handed to cast as a path. `folder` is --target: cast
    reads it, and `raw` is then a name cast looks up among that folder's agents."""
    exe = shutil.which("cast")
    if exe is None:
        exc = _refuse("cast-missing", "cast is not on PATH, so the agents cannot be listed.",
                      "rbtv doctor")
        exc.unchanged = "Nothing was listed."
        raise exc
    if raw is None:
        words = [exe, "list", "--agents"]
    elif folder is not None:
        words = [exe, "list", "--agent", raw]
    else:
        # Forward slashes on every system: cast takes a value with a slash as a path.
        words = [exe, "list", "--agent", resolve_agent(root, raw).as_posix()]
    if folder is not None:
        # cast runs from the installation; the folder was typed from the current one.
        words += ["--target", str(Path(folder).expanduser().resolve())]
    if full:
        words.append("--full")
    if as_json:
        words.append("--json")
    done = subprocess.run(words, cwd=root, env={**os.environ, "COLUMNS": str(width)},
                          capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        # cast's first line says what it refused; its own closing lines and next
        # step belong to cast's screen, and rbtv's refusal carries its own.
        exc = _refuse("cast-refused", "`cast list` refused: " + done.stderr.strip().split("\n")[0],
                      "rbtv doctor" if folder is None else "rbtv agent list -h")
        exc.unchanged = "Nothing was listed."
        raise exc
    return done.stdout


def add_agent(root: Path, raw: str, names: list[str], packs: set[str], catalog: dict,
              dry: bool, given: dict | None = None, on: tuple[str, ...] = ()) -> dict:
    """Apply an agent folder, placing it first when a component ships it.
    `given` holds --harness, --model and --effort; `on` the --on values of the
    agents named among the files."""
    part = unplaced_shipped_agent(root, raw, catalog)
    home = agent_home(root, raw) if part else resolve_agent(root, raw)
    if part:
        source = Path(catalog[part["component"]]["path"]) / "agents" / raw
        state = {"files": [], "packs": [],
                 **files_key(json.loads((source / AGENT_RECORD.name).read_text(encoding="utf-8")))}
    else:
        state = _read_agent(home)
    launch = _launch_flags(raw, all(key in state for key in LAUNCH_FIELDS), given)
    if not launch and not part:
        _checked_agent(home, state)
    check_packs(catalog, packs, "rbtv list --type pack")
    # A shipped agent not yet placed has no folder: its installation answers.
    asked_from = root if part else home
    known = cast_catalog(asked_from)
    if launch:
        launch = launch_values(launch["harness"], launch["model"], launch["effort"], known,
                               asked_from)
        state.update(launch)
    else:
        launch_values(state["harness"], state["model"], str(state["effort"]), known, asked_from)
    placed = None
    if part:
        placed = {"id": part["key"], "files": [PROMPT_FILE.name, AGENT_RECORD.name]}
        if not dry:
            home.mkdir(parents=True, exist_ok=True)
            write_file(home / PROMPT_FILE,
                       absolute_links((source / PROMPT_FILE).read_text(encoding="utf-8"), root),
                       newline="\n")
            write_file(home / AGENT_RECORD, json.dumps(state, indent=2) + "\n", newline="\n")
            state = agent_state(home)
    elif launch:
        _checked_agent(home, state)
    explicit = _keys(names, catalog)
    declared = _keys(list(state["files"]), catalog)
    before = declared | pack_files(catalog, set(state["packs"]))
    enabled = set(state["packs"]) | packs
    wanted = declared | explicit | pack_files(catalog, enabled)
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
        after["files"], after["packs"] = sorted(declared | explicit), sorted(enabled)
        write_state(home, after)
    added, packs_on = sorted(wanted - before), sorted(packs - set(state["packs"]))
    touched = bool(added or packs_on or written or launch
                   or result.get("written") or result.get("deleted"))
    return {"ok": True, "agent": state["name"], "home": str(home), "launch": _launch(state), "placed": placed,
            "packs": sorted(enabled), "written": (["agent.json"] if touched and not dry else []) + written,
            "files": sorted(wanted), "files_removed": [], "was": len(before), "added": added,
            "packs_on": packs_on, "harness_files": result, "dry_run": dry,
            "sub_agents": subagents.describe(named, sub_agents, recorded, receiving,
                                             catalog, home)}


def update_agent(root: Path, raw: str, scope: str, catalog: dict, dry: bool) -> dict:
    """Reconcile the folder with agent.json. The membership is read before the
    install writes; `guidance` adds and removes nothing, so it only reports a
    mismatch (listed_missing, on_disk_unlisted) for the caller to name."""
    home = resolve_agent(root, raw)
    state = agent_state(home)
    wanted = _keys(list(state["files"]), catalog) | pack_files(catalog, set(state["packs"]))
    members = file_membership(home, catalog, state, wanted)
    picked, parts = _split_part_keys(wanted)
    result = do_install(home, catalog, picked, [state["harness"]], dry, guidance_basis="none", parts=parts, scope=scope, selected=parts if scope in ("scaffolding", "all") else None)
    written = _agent_files(home, state, dry) if scope != "guidance" else []
    guidance = scope == "guidance"
    return {"ok": True, "agent": state["name"], "home": str(home), "launch": _launch(state),
            "packs": list(state["packs"]), "scope": scope, "written": written,
            "files": sorted(wanted), "files_removed": [], "harness_files": result, "dry_run": dry,
            "added": [] if guidance else sorted(members["added"]),
            "removed": [] if guidance else sorted(members["removed"]),
            "on_disk": sorted(members["booked"]),
            "listed_missing": sorted(members["listed_missing"]),
            "on_disk_unlisted": sorted(members["on_disk_unlisted"])}


def remove_agent(root: Path, raw: str, names: list[str], packs: set[str], all_files: bool, yes: bool, catalog: dict, dry: bool) -> dict:
    if not (names or packs or all_files):
        raise Refuse("usage", "agent remove needs a NAME, --pack, or --all")
    home = resolve_agent(root, raw)
    state = agent_state(home)
    if all_files and not yes:
        pack_part = f", pack {', '.join(state['packs'])}" if state["packs"] else ""
        before = _keys(list(state["files"]), catalog, state.get("components")) | pack_files(catalog, set(state["packs"]))
        count = f"{len(before)} file{'' if len(before) == 1 else 's'}"
        raise Refuse("confirm-required", f"--all removes every file from {state['name']} "
                     f"({count}{pack_part}). Re-run with --yes:\n"
                     f"rbtv agent remove {raw} --all --yes")
    check_packs(catalog, packs, "rbtv list --type pack")
    before = _keys(list(state["files"]), catalog, state.get("components")) | pack_files(catalog, set(state["packs"]))
    try:
        removed = (set(state["files"]) if all_files else
                   _keys(names, catalog, state.get("components"), suggest_installed=True))
    except Refuse as exc:
        if exc.code != "name-unknown":
            raise
        unknown = names[0] if names else ""
        refusal = _refuse("name-unknown", f"unknown file {unknown!r}. "
                          + close_names_sentence(exc.candidates), "rbtv list")
        refusal.candidates = exc.candidates
        raise refusal from exc
    enabled = set() if all_files else set(state["packs"]) - packs
    explicit = set() if all_files else set(state["files"]) - removed
    wanted = explicit | pack_files(catalog, enabled)
    booked = {row["key"] for row in iter_booked_files(catalog, state.get("components") or {})}
    gone = booked - wanted
    picked, parts = _split_part_keys(gone)
    result = do_uninstall(home, catalog, picked, dry, parts=parts) if parts else {"ok": True, "uninstalled": [], "dry_run": dry, "report": {}}
    if not dry:
        after = read_state(home)
        after["files"], after["packs"] = sorted(explicit), sorted(enabled)
        write_state(home, after)
    packs_off = sorted(set(state["packs"]) if all_files else set(state["packs"]) & packs)
    return {"ok": True, "agent": state["name"], "home": str(home), "launch": _launch(state),
            "packs": sorted(enabled), "written": [], "files": sorted(wanted),
            "files_removed": sorted(gone), "harness_files": result, "kept": [PROMPT_FILE.name, AGENT_RECORD.name],
            "dry_run": dry, "was": len(before), "all": all_files, "packs_off": packs_off,
            "absent_packs": sorted(packs - set(state["packs"]))}
