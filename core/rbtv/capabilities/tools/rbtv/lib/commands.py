"""One handler per verb, and the dispatch that runs them."""
from __future__ import annotations

import argparse
import json
import sys
from functools import wraps
from pathlib import Path

from discovery import LAUNCH_FIELDS, Refuse, scan_all

from . import present, subagents
from .constants import (
    AGENT_RECORD,
    ANSI,
    BASIS_NONE,
    GUIDANCE_FILE,
    GUIDANCE_NAMES,
    HARNESSES,
    REPO_ROOT,
    STATE_REL,
    UPDATE_SCOPES,
)
from .guidance import _norm_prefix
from .target import DISCOVER_CWD, discover_installation, resolve_target
from .state import (book_harnesses, is_agent_target, read_state, selected_packs,
                    selected_files, state_path, file_membership, write_state)
from .catalog import catalog_packs, check_packs, pack_files
from .selection import (
    _has_negative,
    _split_part_keys,
    iter_catalog_parts,
    iter_booked_files,
    resolve_name,
    resolve_selection,
)
from .operations import do_install, do_uninstall
from .pathlinks import bin_dir
from .shared_links import release_installation_links, installation_mutation_lock
from .listing import (_description, build_list, build_show,
                      do_list, json_view, pack_members, print_list, print_show)
from .agents import (OWN_FILES, add_agent, agent_state, cast_agent_list, configure_agent,
                     is_path, on_values, remove_agent, update_agent)
from .doctor import do_doctor, doctor_exit
from .report import LIST_LIMIT, print_result
from .recovery import shell_quote
from .interactive import interactive
from .parser import SETTING_VERB, build_parser


_quote = shell_quote


def _parse_harnesses(raw: str) -> list[str]:
    """A comma-separated `--harness` value -> the canonical, filtered list."""
    picked = [h.strip() for h in raw.split(",") if h.strip()]
    unknown = [h for h in picked if h not in HARNESSES]
    if unknown:
        raise Refuse("harness-unknown",
                     f"unknown harness(es): {', '.join(unknown)} — known: "
                     + ", ".join(HARNESSES))
    return [h for h in HARNESSES if h in picked]


def _emit(data: dict, as_json: bool, target: Path | None = None,
          source: str | None = None, *, verb: str = "",
          details: bool = False, facts: dict | None = None) -> None:
    if target is not None:
        data = {**data, "target": str(target.resolve()), "source": source}
    data.setdefault("next", "rbtv status --target " + _quote(target)
                    if target is not None else "rbtv status")
    if as_json:
        print(json.dumps(data, indent=2))
    else:
        # `verb` picks the title (D9 §1) and `details` lifts the list
        # shortening; `facts` carries text-only figures (before/after counts).
        # None of them is part of the JSON contract.
        print_result({**data, "_verb": verb, "_details": details,
                      "_facts": facts or {}})


def _prose(text: str, *, indent: str = "") -> None:
    """Explanatory prose wrapped to the terminal under a two-space hang;
    commands, IDs and paths inside it are never split."""
    print("\n".join(present.wrap(text, indent=indent, hang=indent + "  ")))


def _text_refusal(exc: Refuse) -> str:
    """The text refusal's message: the refusal's message, then the sentence
    saying nothing was done (`exc.unchanged`, "Nothing was changed." unless the
    refusal sets another). The message itself, which JSON carries as
    `message`, never holds that sentence."""
    text = exc.message.rstrip()
    if not text.endswith("."):
        text += "."
    return text + " " + getattr(exc, "unchanged", "Nothing was changed.")


def _print_refused(code: str, message: str, *, outcome: str = "refused") -> None:
    """The ONE place a plain-text refusal begins: the shared title, then a
    blank line, then the `REFUSED [code] message` line every refusal path
    already prints. Every non-JSON stderr refusal — a parser validation
    error, a retired form, a target/OSError, or a command `Refuse` — calls
    this first so none of them can print `REFUSED …` bare. JSON's single
    undecorated value never goes through this — only the human-text path.
    `outcome` is the title word: a failure part-way through a run is
    "failed", never "refused", because writes before it may have applied."""
    print(present.title(outcome), file=sys.stderr)
    print(file=sys.stderr)
    print("\n".join(present.wrap(f"{outcome.upper()} [{code}] {message}",
                                  hang="  ")), file=sys.stderr)


def _error_data(exc: Refuse, target: Path | None = None,
                catalog: dict | None = None, *, takes_target: bool = True) -> dict:
    """The refusal's JSON body. `takes_target` is False for the agent verbs,
    which take no --target: their suggested commands then carry none."""
    flag = " --target " + _quote(target) if target is not None and takes_target else ""
    error = {"code": exc.code, "message": exc.message}
    if exc.path:
        error["path"] = exc.path
    if hasattr(exc, "candidates"):
        types = {part["key"]: part["method"] for part in
                 iter_catalog_parts(catalog or {})}
        error["suggestions"] = [
            {"id": key, "type": types.get(key)} for key in exc.candidates]
    if hasattr(exc, "preview"):
        error["preview"] = exc.preview
    out = {"ok": False, "error": error, "changed": False}
    if target is not None:
        out["target"] = str(target.resolve())
    if hasattr(exc, "next"):
        out["next"] = exc.next
    elif error.get("suggestions"):
        out["next"] = "rbtv show " + _quote(error["suggestions"][0]["id"]) + flag
    elif exc.code in {"name-unknown", "file-unknown", "component-unknown"}:
        out["next"] = "rbtv list" + flag
    elif exc.code == "pack-unknown":
        out["next"] = "rbtv list --type pack" + flag
    return out


def mutation_locked(handler):
    """Cover selection/settings reads and the operation with one target lock."""
    @wraps(handler)
    def run(args, target, catalog, shadowed, *, ask=None):
        if getattr(args, "dry_run", False):
            return handler(args, target, catalog, shadowed, ask=ask)
        with installation_mutation_lock(target):
            return handler(args, target, catalog, shadowed, ask=ask)
    return run




def cmd_list(args, target: Path, catalog: dict, shadowed: list,
             *, ask=None) -> int:
    del ask, shadowed
    limit, offset = args.limit, args.offset
    if limit < 1 or limit > 100 or offset < 0:
        raise Refuse("list-window-invalid",
                     "--limit must be 1-100 and --offset must be zero or more")
    state = read_state(target)
    state["_target"] = str(target.resolve())
    data = build_list(catalog, state, query=args.query,
                      modules=args.module, components=args.component,
                      methods=args.method,
                      installed=bool(args.installed or args.verb == "li"),
                      search=args.verb == "search", full=args.full,
                      limit=limit, offset=offset)
    data.update(target=str(target.resolve()), source=getattr(args, "_why", "unknown"))
    if offset >= data["total"] and data["total"]:
        raise Refuse("offset-out-of-range",
                     f"--offset {offset} is past {data['total']} matching files. "
                     "Run `rbtv list --offset 0 --target "
                     + _quote(target) + "`")
    command = ["rbtv " + ("search" if args.verb == "search" else "list")]
    if args.query:
        command.append(_quote(args.query))
    for flag, values in (("--module", args.module), ("--component", args.component),
                         ("--type", args.method)):
        command.extend(f"{flag} {_quote(value)}" for value in values)
    if args.installed or args.verb == "li":
        command.append("--installed")
    has_more = offset + data["returned"] < data["total"]
    if has_more:
        command.extend((f"--limit {limit}", f"--offset {offset + data['returned']}",
                        "--target " + _quote(target)))
    elif not data["total"]:
        command = ["rbtv list --target " + _quote(target)]
    else:
        # Always a returned exact ID: a search query or a placeholder is
        # not something `show` accepts.
        first = data["files"][0]
        show_arg = ("--pack " if first.get("type") == "pack" else "") + _quote(first["id"])
        command = ["rbtv show " + show_arg
                   + " --target " + _quote(target)]
    data["next"] = " ".join(command)
    searching = args.verb == "search"
    if args.json:
        print(json.dumps(json_view(data, searching=searching), indent=2))
    else:
        # Presentation-only bookkeeping (never part of the JSON contract):
        # which title/next-label branch to render.
        print_list({**data, "searching": searching, "full": args.full,
                   "installed_only": bool(args.installed or args.verb == "li"),
                   "has_more": has_more, "methods": args.method})
    return 0


def cmd_ls(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    return cmd_list(args, target, catalog, shadowed, ask=ask)


def cmd_search(args, target: Path, catalog: dict, shadowed: list,
               *, ask=None) -> int:
    if not args.query:
        refusal = Refuse("query-required", "search needs words to match against "
                         "names and descriptions.")
        refusal.next = "rbtv search -h"
        raise refusal
    return cmd_list(args, target, catalog, shadowed, ask=ask)


def cmd_li(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    return cmd_list(args, target, catalog, shadowed, ask=ask)


def cmd_show(args, target: Path, catalog: dict, shadowed: list,
             *, ask=None) -> int:
    del ask, shadowed
    state = read_state(target)
    state["_target"] = str(target.resolve())
    requested_packs = set(args.pack)
    if requested_packs:
        if args.name or len(requested_packs) != 1:
            raise Refuse("usage", "show --pack needs exactly one pack name and no NAME")
        packs = catalog_packs(catalog)
        name = next(iter(requested_packs))
        if name not in packs:
            pack_files(catalog, {name})
        pack = packs[name]
        data = {"ok": True, "target": str(target.resolve()),
                "source": getattr(args, "_why", "unknown"),
                "selection": {"scope": "pack", "id": name,
                              "description": pack["description"],
                              "component": pack["component"],
                              "files": pack_members(catalog, state, pack),
                              "path": pack["path"],
                              "enabled": name in selected_packs(state)},
                "next": f"rbtv list --type pack --target {_quote(target)}"}
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print_show(data)
        return 0
    if not args.name:
        raise Refuse("usage", "show needs NAME or --pack PACK")
    known_modules = {part["module"] for part in iter_catalog_parts(catalog)}
    named_module = ("_hub" if args.name == "hub" else args.name)
    if named_module in known_modules:
        if args.method:
            raise Refuse("type-mismatch", "--type requires the name of a file; list "
                         + args.name + " --type " + args.method[0])
        view = build_list(catalog, state, query=args.name, full=args.full, limit=100)
        comp = next((c for c in catalog.values()
                     if c.get("module") == named_module), None)
        description = _description(comp.get("module_description", ""), args.full) if comp else ""
        selection = {"scope": "module", "id": args.name,
                     "description": description,
                     "components": view["files"],
                     "installed_files": sum(r["installed_files"] for r in view["files"]),
                     "source_files": sum(r["source_files"] for r in view["files"])}
        # A real component drilled into (screen 21's pattern), never the
        # module itself again — `list` was a dead end that never advanced
        # the reader toward an actual file.
        next_cmd = (f"rbtv show {view['files'][0]['id']} --target {_quote(target)}"
                   if view["files"] else
                   f"rbtv list {args.name} --target {_quote(target)}")
        data = {"ok": True, "target": str(target.resolve()),
                "source": getattr(args, "_why", "unknown"),
                "selection": selection,
                "next": next_cmd}
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print_show(data)
        return 0
    selected = resolve_name(args.name, catalog, state.get("components"),
                            methods=set(args.method) or None)
    data = {"ok": True, "target": str(target.resolve()),
            "source": getattr(args, "_why", "unknown"),
            "selection": build_show(selected, catalog, state, args.full)}
    parts = data["selection"]["files"]
    if selected["kind"] == "part":
        # Approved screens 20/55: an installed file's next step is a health
        # check, never a removal suggestion just because it happens to be
        # installed. An uninstalled file's next step is the setup that
        # would install it.
        data["next"] = ("cast list" if parts[0]["type"] == "agent" else
                        f"rbtv doctor --target {_quote(target)}" if parts[0]["installed"] else
                        f"rbtv add {selected['id']} --target {_quote(target)}")
    else:
        # Screen 21: a component's next step drills into one of its real
        # included files, never a generic re-listing of itself.
        data["next"] = (f"rbtv show {parts[0]['key']} --target {_quote(target)}"
                        if parts else
                        f"rbtv list {selected['id']} --target {_quote(target)}")
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_show(data)
    return 0


def _catalog_counts(catalog: dict) -> dict:
    """The source-catalog counts every status view reports."""
    modules = {("hub" if (comp.get("module") or cid.split("/")[0]) == "_hub"
                else comp.get("module") or cid.split("/")[0])
               for cid, comp in catalog.items()}
    return {"modules": len(modules), "components": len(catalog),
            "files": len(iter_catalog_parts(catalog)),
            "packs": len(catalog_packs(catalog))}


def _print_catalog(counts: dict) -> None:
    print("Local source catalog on this machine")
    _prose(f"{counts['modules']} modules, {counts['components']} components, "
           f"{counts['files']} files, {counts['packs']} packs; source availability "
           "does not mean installed here.", indent="  ")


def _print_sub_agents(recorded: dict) -> None:
    """The agents installed as harness-native sub-agents: one line each, naming
    the harnesses it is written for and the model and effort of each."""
    for line in subagents.installed_lines(recorded):
        _prose(line)


def _status_agent(args, target: Path, catalog: dict) -> int:
    """Status of an agent folder: its own record, not the installation's."""
    record = agent_state(target)
    named = set(record["units"])
    seen = set(named)
    from_packs = []
    for name in sorted(record["packs"]):
        keys = sorted(pack_files(catalog, {name}) - seen)
        seen |= set(keys)
        from_packs.append((name, keys))
    counts = _catalog_counts(catalog)
    harness = record["harness"]
    data = {"ok": True, "target": str(target.resolve()),
            "target_source": getattr(args, "_why", "unknown"),
            "agent": {"name": record["name"], "harness": harness,
                      "model": record["model"], "effort": record["effort"],
                      "voice": record.get("voice"),
                      "packs": sorted(record["packs"]), "installed_files": sorted(seen),
                      "sub_agents": subagents.recorded(record)},
            "source_catalog": counts,
            "next": f"rbtv doctor --target {_quote(target)}"}
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    print(present.title("status"))
    print()
    print(f"Target: {data['target']} ({present.target_source_label(getattr(args, '_why', None))})")
    print("Kind: agent")
    print("Name: " + record["name"])
    print(f"Harness: {harness} ({present.HARNESS_MEANING.get(harness, harness)})")
    print("Model: " + record["model"])
    print("Effort: " + str(record["effort"]))
    print("Voice: " + (record.get("voice") or "not set"))
    print("Packs on: " + (", ".join(sorted(record["packs"])) or "none"))
    _print_sub_agents(data["agent"]["sub_agents"])
    print(f"Installed files: {len(seen)}")
    if record["packs"]:
        print("  Named: " + (", ".join(sorted(named)) or "none"))
        for name, keys in from_packs:
            print(f"  From pack {name}: {len(keys)}")
    else:
        for key in sorted(named):
            print("  " + key)
    print("Saved record: agent.json")
    print()
    _print_catalog(counts)
    print()
    print("File and shortcut health: not checked by status.")
    print("Next: " + data["next"])
    return 0


def cmd_status(args, target: Path, catalog: dict, shadowed: list,
               *, ask=None) -> int:
    del ask, shadowed
    if is_agent_target(target):
        return _status_agent(args, target, catalog)
    installed = do_list(target, catalog)
    comps = installed["components"]
    count = sum(len(rec.get("units") or {}) for rec in comps.values())
    settings = installed["settings"]
    counts = _catalog_counts(catalog)
    data = {"ok": True, "target": str(target.resolve()),
            "target_source": ("explicit" if getattr(args, "_why", None) == "--target"
                              else getattr(args, "_why", "unknown")),
            "installation": {"configured": settings["recorded"],
                             "harnesses": settings["harnesses"] or [],
                             "guidance": settings["artifact"],
                             "guidance_excludes": settings["guidance_excludes"],
                             "packs": settings["packs"],
                             "sub_agents": subagents.recorded(read_state(target)),
                             "installed_components": len(comps),
                             "installed_files": count,
                             "health": "not_checked"},
            "source_catalog": counts,
            "next": f"rbtv doctor --target {_quote(target)}"}
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        why = getattr(args, "_why", None)
        print(present.title("status"))
        print()
        print(f"Target: {data['target']} ({present.target_source_label(why)})")
        print("Kind: root")
        if settings["recorded"]:
            harnesses = ", ".join(
                f"{h} ({present.HARNESS_MEANING.get(h, h)})"
                for h in settings["harnesses"])
            print("Saved receiving tools: " + harnesses)
            print("Maintained guidance: " + (settings["artifact"] or "none"))
            _prose("Guidance folders excluded from copying: "
                   + (", ".join(settings["guidance_excludes"]) or "none"))
            print("Packs on: " + (", ".join(settings["packs"]) or "none"))
            _print_sub_agents(data["installation"]["sub_agents"])
            print()
            print("Recorded installation in this target")
            print(f"  Components with selected files: {len(comps)}")
            print(f"  Files: {count}")
            print(f"  Saved record: {STATE_REL}")
        else:
            print("Installation: no saved configuration or selected files")
            print()
            print("First use: choose receiving tools and a maintained guidance file.")
            print("  " + "; ".join(f"{h} = {present.HARNESS_MEANING[h]}"
                                    for h in HARNESSES))
            _prose("CLAUDE.md or AGENTS.md must exist in this target; "
                   "none disables copying.", indent="  ")
        print()
        _print_catalog(counts)
        print()
        print("File and shortcut health: not checked by status.")
        print("Next: " + data["next"])
    return 0


def _gate_add_harness(target: Path, state: dict, raw: str | None) -> list[str]:
    """Accept a repeated setup value when it agrees with the saved value."""
    booked = book_harnesses(state)
    if booked is not None and raw is not None:
        if _parse_harnesses(raw) != booked:
            raise Refuse(
                "setting-locked",
                "this installation already targets " + ", ".join(booked)
                + "; change it with `rbtv configure --harness "
                + _quote(raw) + " --target " + _quote(target)
                + "` before adding components",
                str(target / STATE_REL))
    if booked is None:
        if raw is None:
            raise Refuse(
                "harness-required",
                "first install on this installation: pass --harness with a "
                "comma-separated subset of " + ", ".join(HARNESSES)
                + ". It is recorded once for the whole installation; every later "
                f"`add` refuses the flag and `{SETTING_VERB['harness']}` "
                "changes it")
        booked = _parse_harnesses(raw)
        if not booked:
            raise Refuse("harness-unknown", "--harness selected no harness")
    return booked


def _gate_add_artifact(target: Path, state: dict, raw: str | None) -> str | None:
    """D16 — same contract for the root guidance basis. A pre-D16 book that
    never recorded one is asked here: unset used to MEAN `none` silently."""
    booked = "guidance_basis" in state
    if booked and raw is not None:
        if raw != state.get("guidance_basis"):
            raise Refuse(
                "setting-locked",
                "this installation already uses guidance "
                + str(state.get("guidance_basis") or BASIS_NONE)
                + "; change it with `rbtv configure --guidance "
                + _quote(raw) + " --target " + _quote(target) + "`",
                str(target / STATE_REL))
    if not booked and raw is None:
        raise Refuse(
            "artifact-required",
            "first install on this installation: pass --guidance with "
            + " or ".join((*GUIDANCE_NAMES, BASIS_NONE))
            + " — the root guidance file YOU author, from which the others are "
              f"generated. `{BASIS_NONE}` means author nothing and generate "
              "nothing. Recorded once; thereafter "
              f"`{SETTING_VERB['guidance']}`")
    return raw


def _replan_all(target: Path, catalog: dict, harnesses: list[str],
                dry_run: bool, *, guidance_basis: str | None = None,
                guidance_excludes: list[str] | None = None,
                scope: str = "all", selected: list[str] | None = None) -> dict:
    """D16 — re-plan EVERY booked component under a changed installation setting.
    `apply` removes what the old book held and the new plan does not, so a
    dropped harness really loses its files. A component whose folder vanished
    upstream is left in the book untouched: `plan_files` still refuses the run
    with `component-vanished`, the same refusal `add` gives."""
    records = read_state(target).get("components") or {}
    picked = [cid for cid in sorted(records) if cid in catalog]
    return do_install(target, catalog, picked, harnesses, dry_run,
                      guidance_basis=guidance_basis,
                      guidance_excludes=guidance_excludes, scope=scope,
                      selected=selected)


def _file_keys(catalog: dict, state: dict) -> set[str]:
    """The key of every installed file: what the `Installed files` count counts."""
    return {row["key"] for row in iter_booked_files(catalog, state.get("components") or {})}


def _pack_facts(catalog: dict, names: set[str], *, on: bool) -> list[tuple[str, str, bool]]:
    """`Pack: NAME (component) on|off` rows for the packs a command named."""
    packs = catalog_packs(catalog)
    return [(name, packs[name]["component"], on) for name in sorted(names)]


def _available_selection(catalog: dict, state: dict) -> tuple[set[str], set[str], list[str]]:
    """Return source-backed selections and the recorded selections now gone."""
    available = {row["key"] for row in iter_catalog_parts(catalog)}
    packs = catalog_packs(catalog)
    files = selected_files(state)
    enabled_packs = selected_packs(state)
    missing_files = sorted(files - available)
    missing_packs = sorted(enabled_packs - set(packs))
    missing = missing_files + [f"pack {name}" for name in missing_packs]
    return files & available, enabled_packs & set(packs), missing


def _save_selected_files(target: Path, add: set[str] | None = None,
                         remove: set[str] | None = None,
                         add_packs: set[str] | None = None,
                         remove_packs: set[str] | None = None) -> None:
    """Persist the root's independent file selection after a real mutation."""
    state = read_state(target)
    state["units"] = sorted((selected_files(state) | set(add or ()))
                            - set(remove or ()))
    state["packs"] = sorted((selected_packs(state) | set(add_packs or ()))
                            - set(remove_packs or ()))
    write_state(target, state)


def _require_recorded(target: Path, state: dict) -> list[str]:
    if is_agent_target(target):
        return [state["harness"]]
    booked = book_harnesses(state)
    if booked is None:
        raise Refuse(
            "installation-unrecorded",
            "this installation has no recorded settings yet — nothing has been "
            "installed here. The first add needs both --harness and "
            "--guidance; run `rbtv list` to choose a file",
            str(target / STATE_REL))
    return booked


def _joined_harness_gaps(state: dict, before: list[str] | None, after: list[str],
                         target: Path) -> list[dict]:
    """The sub-agents a harness that just joined the target does not have."""
    joined = [h for h in after if h not in (before or [])]
    return subagents.missing_for(state, joined, after, target)


def _apply_harness(args, target: Path, catalog: dict, op: str,
                   raw: str) -> int:
    state = read_state(target)
    current = _require_recorded(target, state)
    delta = _parse_harnesses(raw)
    if not delta:
        raise Refuse("harness-unknown", "no harness named")
    wanted = (set(current) | set(delta) if op == "add"
              else set(current) - set(delta))
    new = [h for h in HARNESSES if h in wanted]
    if not new:
        raise Refuse(
            "harness-list-empty",
            "that would leave this installation targeting no harness at all. "
            "Removing every harness is an uninstall — `rbtv rm -A`",
            str(target / STATE_REL))
    if new == current:
        _emit({"ok": True, "changed": False, "dry_run": bool(args.dry_run),
               "message": f"this installation already targets {', '.join(new)}"},
              bool(args.json), target, getattr(args, "_why", "unknown"),
              verb="configure", details=getattr(args, "details", False))
        return 0
    data = _replan_all(target, catalog, new,
                       bool(getattr(args, "dry_run", False)))
    data["sub_agents_missing"] = _joined_harness_gaps(state, current, new, target)
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="configure", details=getattr(args, "details", False))
    return 0


def _apply_artifact(args, target: Path, catalog: dict, value: str) -> int:
    state = read_state(target)
    harnesses = _require_recorded(target, state)
    if value not in (*GUIDANCE_NAMES, BASIS_NONE):
        raise Refuse(
            "artifact-unknown",
            f"{value!r} is not a guidance basis. Name one of: "
            + ", ".join((*GUIDANCE_NAMES, BASIS_NONE))
            + f" — `{BASIS_NONE}` means author nothing and generate nothing")
    if state.get("guidance_basis", object()) == value:
        _emit({"ok": True, "changed": False, "dry_run": bool(args.dry_run),
               "message": f"guidance is already {value}"},
              bool(args.json), target, getattr(args, "_why", "unknown"),
              verb="configure", details=getattr(args, "details", False))
        return 0
    data = _replan_all(target, catalog, harnesses,
                       bool(getattr(args, "dry_run", False)),
                       guidance_basis=value)
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="configure", details=getattr(args, "details", False))
    return 0


def _apply_exclude(args, target: Path, catalog: dict, op: str,
                   dirs: list[str]) -> int:
    state = read_state(target)
    harnesses = _require_recorded(target, state)
    current = [_norm_prefix(d) for d in (state.get("guidance_excludes") or [])]
    delta = [_norm_prefix(d) for d in dirs]
    if op == "add":
        new = sorted(set(current) | set(delta))
    else:
        unknown = [d for d in delta if d not in current]
        if unknown:
            raise Refuse(
                "exclude-unknown",
                "not excluded, so there is nothing to remove: "
                + ", ".join(unknown)
                + (f" — currently excluded: {', '.join(current)}" if current
                   else " — nothing is excluded"),
                str(target / STATE_REL))
        new = sorted(set(current) - set(delta))
    if new == sorted(current):
        _emit({"ok": True, "changed": False, "dry_run": bool(args.dry_run),
               "message": (", ".join(new) or "nothing") + " excluded"},
              bool(args.json), target, getattr(args, "_why", "unknown"),
              verb="configure", details=getattr(args, "details", False))
        return 0
    data = _replan_all(target, catalog, harnesses,
                       bool(getattr(args, "dry_run", False)),
                       guidance_excludes=new)
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="configure", details=getattr(args, "details", False))
    return 0


def _has_selectors(args) -> bool:
    return bool(getattr(args, "all", False) or getattr(args, "module", None)
                or getattr(args, "component", None)
                or getattr(args, "method", None)
                or getattr(args, "exclude_module", None)
                or getattr(args, "exclude_component", None)
                or getattr(args, "exclude_method", None))


def _settings_form(args, target: Path, catalog: dict, verb: str,
                   noun: list[str]) -> int:
    """Route a NOUN-carrying `add`/`rm`/`set` to the setting it names.

    A settings form takes no component selectors: the two are different jobs
    and running them in one command would make a partly-applied failure
    ambiguous — which half landed? So the mix REFUSES rather than guessing an
    order.
    """
    head, rest = noun[0], noun[1:]
    if verb in ("add", "rm") and _has_selectors(args):
        raise Refuse(
            "noun-with-selectors",
            f"`{verb} {head}` changes a INSTALLATION SETTING and takes no "
            "component selectors — run the two as separate commands so a "
            "failure in one cannot leave the other half-applied")

    if head == "harness":
        if verb == "set":
            raise Refuse(
                "setting-wrong-verb",
                "the harness set holds MANY values, so it is edited a piece "
                f"at a time: {SETTING_VERB['harness']}")
        if not rest:
            raise Refuse(
                "harness-unknown",
                f"name the harness(es) to {verb}: comma-separated subset of "
                + ", ".join(HARNESSES))
        return _apply_harness(args, target, catalog, verb, ",".join(rest))

    if head == "guidance":
        if rest and rest[0] == "exclude":
            if not rest[1:]:
                raise Refuse(
                    "exclude-empty",
                    f"name the folder(s) to {verb}, relative to the install "
                    "root")
            return _apply_exclude(args, target, catalog, verb, rest[1:])
        raise Refuse("setting-wrong-verb",
                     "choose the maintained guidance file with "
                     + SETTING_VERB["guidance"])

    if head == "artifact":
        raise Refuse("noun-retired", "artifact is now guidance. Run `rbtv "
                     + verb + " guidance exclude FOLDER` to change excluded folders")

    known = "harness, guidance exclude"
    raise Refuse(
        "noun-unknown",
        f"`{head}` names no installation setting. Known: {known}. "
        "To choose COMPONENTS, use the selector flags (-c/-m/-x/-A) with no "
        "noun — run `rbtv " + verb + " --help`")


@mutation_locked
def cmd_configure(args, target: Path, catalog: dict, shadowed: list,
            *, ask=None) -> int:
    del ask, shadowed
    noun = list(getattr(args, "noun", None) or [])
    raw_h = getattr(args, "harness", None)
    raw_g = getattr(args, "artifact", None)
    if raw_h is not None or raw_g is not None:
        if noun:
            raise Refuse("usage", "configure accepts --harness and --guidance flags")
        state = read_state(target)
        current = book_harnesses(state)
        if current is None and (raw_h is None or raw_g is None):
            raise Refuse("setup-required", "fresh configuration needs both --harness "
                         "and --guidance; for example: rbtv configure "
                         "--harness codex --guidance none --target " + _quote(target))
        wanted_h = _parse_harnesses(raw_h) if raw_h is not None else current
        if not wanted_h:
            raise Refuse("harness-unknown", "--harness selected no harness")
        wanted_g = raw_g if raw_g is not None else state.get("guidance_basis")
        if current is not None and wanted_h == current and wanted_g == state.get("guidance_basis"):
            data = {"ok": True, "changed": False, "dry_run": bool(args.dry_run)}
        else:
            data = _replan_all(target, catalog, wanted_h, bool(args.dry_run),
                               guidance_basis=wanted_g)
            data["sub_agents_missing"] = _joined_harness_gaps(
                state, current, wanted_h, target)
        count = len(_file_keys(catalog, state))
        _emit(data, bool(args.json), target, getattr(args, "_why", "unknown"),
              verb="configure", details=getattr(args, "details", False),
              facts={"files": (count, count), "harnesses_before": current})
        return 0
    raise Refuse("noun-missing", "configure needs --harness, --guidance, or both")


@mutation_locked
def cmd_add(args, target: Path, catalog: dict, shadowed: list,
            *, ask=None) -> int:
    del ask, shadowed
    noun = list(getattr(args, "noun", None) or [])
    if is_agent_target(target):
        agent_state(target)
    if noun and noun[0] in ("harness", "guidance", "artifact"):
        return _settings_form(args, target, catalog, "add", noun)
    requested_packs = set(args.pack)
    if not (_has_selectors(args) or noun or requested_packs):
        raise SystemExit(2)
    args.names = noun
    keys = resolve_selection(args, catalog, None) if (_has_selectors(args) or noun) else set()
    # An agent named here is added as a harness-native sub-agent, with --on.
    # A selection by component, module or type skips an agent and says so.
    named = subagents.named_agents(catalog, keys) if noun else []
    skipped_agents = sorted({row["key"] for row in subagents.named_agents(catalog, keys)}
                            - {row["key"] for row in named})
    keys -= set(skipped_agents)
    picked, parts = _split_part_keys(keys)
    state = read_state(target)
    _available_files, _available_packs, stale = _available_selection(catalog, state)
    if not is_agent_target(target) and book_harnesses(state) is None and (
            getattr(args, "harness", None) is None
            or getattr(args, "artifact", None) is None):
        raise Refuse(
            "setup-required",
            "first add needs both --harness (which AI tools receive files) "
            "and --guidance (CLAUDE.md, AGENTS.md, or none). Example: "
            "rbtv add " + (parts[0] if parts else "--pack <name>")
            + " --harness codex --guidance none --target " + _quote(target))
    harnesses = ([state["harness"]] if is_agent_target(target)
                 else _gate_add_harness(target, state, getattr(args, "harness", None)))
    basis = ("none" if is_agent_target(target)
             else _gate_add_artifact(target, state, getattr(args, "artifact", None)))
    sub_agents = on_values(
        list(getattr(args, "on", None) or []), named, harnesses, target,
        "rbtv agent configure -h" if is_agent_target(target) else
        "rbtv configure --harness " + ",".join(HARNESSES) + " --target " + _quote(target))
    pack_parts = pack_files(catalog, requested_packs)
    all_parts = sorted(set(parts) | pack_parts)
    picked, _unused = _split_part_keys(all_parts)
    data = do_install(
        target, catalog, picked, harnesses,
        bool(getattr(args, "dry_run", False)),
        guidance_basis=basis,
        parts=all_parts, sub_agents=sub_agents)
    if not bool(getattr(args, "dry_run", False)):
        _save_selected_files(target, add=set(parts), add_packs=requested_packs)
    data["selected_files"] = all_parts
    data["sub_agents"] = subagents.describe(
        named, sub_agents, subagents.recorded(state), harnesses, catalog, target)
    data["skipped_agents"] = skipped_agents
    data["recorded_source_gone"] = stale
    before = _file_keys(catalog, state)
    facts = {"files": (len(before), len(before | set(all_parts))),
             "harnesses_before": book_harnesses(state),
             "packs": _pack_facts(catalog, requested_packs, on=True)}
    if len(all_parts) > 1:
        changed = len(set(all_parts) - before)
        facts.update(changed=changed, unchanged=facts["files"][1] - changed)
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="add",
          details=getattr(args, "details", False), facts=facts)
    return 0


def _remove_not_installed(args, target: Path, catalog: dict, state: dict,
                          noun: list[str], dry: bool, stale: list[str]) -> int:
    """`remove NAME` where NAME is a known file that is not installed: there is
    nothing to take away, so the result names it and changes no file. A name
    the catalog does not know was refused before this point."""
    book = state.get("components")
    installed = _file_keys(catalog, state)
    named = sorted({part["key"] for name in noun
                    for part in resolve_name(name, catalog, book)["files"]}
                   - installed)
    if not named:
        _emit({"ok": True, "uninstalled": [], "dry_run": dry,
               "recorded_source_gone": stale,
               "message": "no installed files matched this request"},
              bool(args.json), target, getattr(args, "_why", "unknown"),
              verb="remove", details=getattr(args, "details", False))
        return 0
    count = len(installed)
    _emit({"ok": True, "uninstalled": [], "not_installed": named,
           "recorded_source_gone": stale,
           "dry_run": dry, "written": [], "deleted": [], "skipped": []},
          bool(args.json), target, getattr(args, "_why", "unknown"),
          verb="remove", details=getattr(args, "details", False),
          facts={"files": (count, count)})
    return 0


@mutation_locked
def cmd_rm(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    del shadowed, ask
    noun = list(getattr(args, "noun", None) or [])
    if is_agent_target(target):
        agent_state(target)
    if noun and noun[0] in ("harness", "guidance", "artifact"):
        return _settings_form(args, target, catalog, "rm", noun)
    requested_packs = set(args.pack)
    check_packs(catalog, requested_packs)
    if not (_has_selectors(args) or noun or requested_packs):
        raise SystemExit(2)
    args.names = noun
    state = read_state(target)
    _available_files, available_packs, stale = _available_selection(catalog, state)
    book = state.get("components")
    keys = resolve_selection(args, catalog, book) if (_has_selectors(args) or noun) else set()
    dry = bool(getattr(args, "dry_run", False))
    path_release = bool(args.all and getattr(args, "_why", None) == "--target"
                        and not state_path(target).is_file())
    preview_links = (release_installation_links(bin_dir(), target, dry=True)
                     if path_release else {})
    shared_count = len(set(preview_links.get("released") or [])
                       | set(preview_links.get("unlinked") or [])
                       | set(preview_links.get("kept_shared") or []))
    current_packs = available_packs
    removed_parts = set(keys)
    wanted_files = (selected_files(state) - removed_parts) | pack_files(
        catalog, current_packs - requested_packs)
    booked_files = {row["key"] for row in iter_booked_files(catalog, book or {})}
    # A pack remains an active selection until `--pack` turns it off.  This
    # applies even to broad file selectors: removing a file cannot silently
    # contradict an enabled pack, and update must not immediately add it back.
    keys = booked_files - wanted_files
    if not keys and not shared_count and not requested_packs:
        return _remove_not_installed(args, target, catalog, state, noun, dry, stale)
    broad = bool(args.all or args.module or args.method or _has_negative(args))
    if broad and not requested_packs and not (dry or getattr(args, "yes", False)):
        flags = ["--all"] if args.all else []
        flags += [f"--module {_quote(m)}" for m in args.module]
        flags += [f"--component {_quote(c)}" for c in args.component]
        flags += [f"--type {_quote(m)}" for m in args.method]
        flags += [f"--exclude-module {_quote(m)}" for m in args.exclude_module]
        flags += [f"--exclude-component {_quote(c)}" for c in args.exclude_component]
        flags += [f"--exclude-type {_quote(m)}" for m in args.exclude_method]
        retry = "rbtv remove " + " ".join(
            [_quote(name) for name in noun] + flags
            + ["--yes", "--target", _quote(target)])
        preview = sorted(keys)[:20]
        exc = Refuse(
            "confirmation-required",
            f"broad removal selected {len(keys)} file{'' if len(keys) == 1 else 's'}"
            + (f" and {shared_count} registered shared shortcut(s)" if shared_count else "")
            + "; preview: "
            + (", ".join(preview) or "(none)")
            + (f"; {len(keys)-20} more" if len(keys) > 20 else "")
            + f". Review with --dry-run, then run: {retry}")
        exc.preview = {"total": len(keys), "files": preview,
                       "next": retry}
        raise exc
    before = _file_keys(catalog, state)
    facts = {"files": (len(before), len(before - set(keys))),
             "packs": _pack_facts(catalog, requested_packs, on=False)}
    if not keys:
        report = {"path": (preview_links if dry else
                           release_installation_links(bin_dir(), target, dry=False))}
        if not dry and state_path(target).is_file():
            _save_selected_files(target, remove=removed_parts,
                                 remove_packs=requested_packs)
        _emit({"ok": True, "uninstalled": [], "dry_run": dry,
               "report": report,
               "message": "released shared shortcut claims for this target"},
              bool(args.json), target, getattr(args, "_why", "unknown"),
              verb="remove", details=getattr(args, "details", False))
        return 0
    picked, parts = _split_part_keys(keys)
    data = do_uninstall(target, catalog, picked, dry, parts=parts)
    if not dry and state_path(target).is_file():
        _save_selected_files(target, remove=removed_parts,
                             remove_packs=requested_packs)
    data["selected_files"] = parts
    data["recorded_source_gone"] = stale
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="remove",
          details=getattr(args, "details", False), facts=facts)
    return 0


@mutation_locked
def cmd_update(args, target: Path, catalog: dict, shadowed: list,
               *, ask=None) -> int:
    del ask, shadowed
    if is_agent_target(target):
        agent_state(target)
    state = read_state(target)
    hs = _require_recorded(target, state)
    selected, packs, unavailable = _available_selection(catalog, state)
    chosen = selected | pack_files(catalog, packs)
    members = file_membership(target, catalog, state, chosen)
    data = _replan_all(target, catalog, hs,
                       bool(getattr(args, "dry_run", False)),
                       scope=args.scope,
                       selected=sorted(chosen) if args.scope in ("scaffolding", "all") else None)
    data["report"]["source_gone"] = unavailable
    if not bool(getattr(args, "dry_run", False)) and args.scope in ("scaffolding", "all"):
        saved = read_state(target)
        saved["units"] = sorted(selected)
        saved["packs"] = sorted(packs)
        write_state(target, saved)
    records = state.get("components") or {}
    data["recorded_files"] = len(iter_booked_files(catalog, records))
    data["source_missing"] = sorted(cid for cid in records if cid not in catalog)
    data["added"] = sorted(members["added"]) if args.scope != "guidance" else []
    data["removed"] = sorted(members["removed"]) if args.scope != "guidance" else []
    facts = {"files": (len(members["booked"]), len(chosen)),
             "listed_missing": sorted(members["listed_missing"]),
             "on_disk_unlisted": sorted(members["on_disk_unlisted"])}
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="update",
          details=getattr(args, "details", False), facts=facts)
    return 0


_RESULT_LABEL = {"ok": "OK", "warn": "WARN", "fail": "FAIL"}


def _print_doctor_section(checks: list[dict], *, color: bool) -> None:
    """A Check/Scope/Result table (no Detail column — that text is recovery
    guidance, and a normal-width Detail column truncates it, deleting the
    only thing a FAIL row exists to say) plus the FULL, untruncated detail
    text for every check that is not a plain OK, each on its own line below
    the table so a real command stays copy-pasteable."""
    def paint(row_index: int, text: str) -> str:
        level = checks[row_index]["level"]
        return f"{ANSI[level]}{text}{ANSI['reset']}" if color else text

    headers = ["Check", "Scope", "Result"]
    rows = [[c["name"], c["scope"], _RESULT_LABEL[c["level"]]] for c in checks]
    for line in present.render_table(headers, rows, paint=paint):
        print(line)
    notable = [c for c in checks if c["level"] != "ok"]
    if notable:
        print()
        for c in notable:
            _prose(f"{_RESULT_LABEL[c['level']]} — {c['name']}: {c['detail']}")


def _print_doctor(data: dict, *, color: bool) -> None:
    """Doctor's terminal rendering: a Check/Scope/Result table with full
    recovery text below it, the optional cleanup-audit section split out
    (D9 §5), and a next step truthful about what was actually checked. Reads
    `do_doctor`'s check records as data only — `lib/doctor.py` itself is not
    touched; this replaces its own `render_doctor` as the printed path."""
    checks = data["checks"]
    main = [c for c in checks if c["scope"] != "Other installation"]
    audit = [c for c in checks if c["scope"] == "Other installation"]

    print(present.title("doctor"))
    print()
    print(f"Target: {data['target']} ({present.target_source_label(data.get('why'))})")
    print()
    _print_doctor_section(main, color=color)
    n_ok = sum(1 for c in main if c["level"] == "ok")
    n_warn = sum(1 for c in main if c["level"] == "warn")
    n_fail = sum(1 for c in main if c["level"] == "fail")
    print()
    counts = f"{n_ok} OK"
    if n_warn:
        counts += f", {n_warn} WARN"
    if n_fail:
        counts += f", {n_fail} FAIL"
    lookup = [c for c in main if c["scope"] == "Current PATH"]
    if not lookup:
        discovery = "No selected command shortcut needed a PATH lookup."
    elif any(c["level"] == "fail" for c in lookup):
        discovery = "Selected command discovery FAILED for at least one shortcut."
    else:
        discovery = "Selected command discovery verified."
    _prose(f"{len(main)} checks: {counts}. {discovery} Runtime dependencies "
           "and arbitrary command execution were not tested.")
    if audit:
        print()
        print("Optional cleanup audit")
        _print_doctor_section(audit, color=color)
        n_audit_warn = sum(1 for c in audit if c["level"] != "ok")
        print()
        _prose(f"Optional audit: {n_audit_warn} warning(s). No cleanup was "
               "performed.")
    print()
    if n_fail:
        repair = next((c["repair"] for c in main if c.get("repair")), None)
        _prose("Repair: " + repair if repair else
               "Repair: follow the FAIL recovery text above, then rerun doctor.")
    else:
        print("Next: rbtv list --installed --target " + _quote(data["target"]))


def cmd_doctor(args, target: Path, catalog: dict, shadowed: list,
               *, ask=None) -> int:
    del ask
    why = getattr(args, "_why", DISCOVER_CWD) if args else DISCOVER_CWD
    repo_tree = REPO_ROOT
    mirror_tree = target / ".rbtv" / "mirror"
    data = do_doctor(target, why, catalog, shadowed, repo_tree, mirror_tree,
                     cleanup_audit=bool(args and getattr(args, "cleanup_audit", False)))
    if args and getattr(args, "json", False):
        print(json.dumps(data, indent=2))
    else:
        # --pretty stays as a compatibility alias that forces color on a
        # non-TTY (e.g. piped to `less -R`); a real terminal gets it anyway.
        color = sys.stdout.isatty() or bool(args and getattr(args, "pretty", False))
        _print_doctor(data, color=color)
    return doctor_exit(data["checks"])


def cmd_interactive(args, target: Path, catalog: dict, shadowed: list,
                    *, ask=None) -> int:
    del args, shadowed, ask
    return interactive(target, catalog)


def cmd_selftest(args, target: Path, catalog: dict, shadowed: list,
                 *, ask=None) -> int:
    del args, target, catalog, shadowed, ask
    # imported HERE, not at module scope: `selftest` imports `lib`, so a
    # module-level import would be a cycle — and an ordinary run must not pay
    # to load 3,000 lines of checks it will never call.
    from selftest.runner import selftest
    return selftest()


# Facts the agent printers need for their rows; the JSON contract does not carry them.
_AGENT_TEXT_ONLY = ("was", "packs_on", "packs_off", "absent_packs", "all",
                    "harness_changed", "on_disk", "listed_missing", "on_disk_unlisted")
# The approved wording, broken where the approved screens break it.
AGENT_LIST_HINT = ["Lists are counted, not printed. To list every file and generated file, preview the",
                   "next change with --dry-run --details. --json always carries the full lists."]
AGENT_PREVIEW_HINT = ["Add --details to this preview to list every file and generated file. "
                      "--json always carries the full lists."]


def _agent_ids(values: list[str], details: bool) -> str:
    """File ids inline when short; a count past the list limit, or with
    --details (the full list is then printed in its own section)."""
    if details or len(values) > LIST_LIMIT:
        return f"{len(values)} files"
    return ", ".join(values) or "none"


def _agent_files(generated: dict, guidance: list[str], dry: bool) -> tuple[list[str], list[str], list[str]]:
    """Written, deleted and already-current file lists for one agent change.
    A preview reads the planned lists; a real run reads the applied ones."""
    if dry:
        plan = generated.get("planned_changes") or {}
        write, delete = plan.get("write_files") or [], plan.get("delete_files") or []
        same = plan.get("unchanged_files") or []
    else:
        write, delete = generated.get("written") or [], generated.get("deleted") or []
        same = generated.get("skipped") or []
    return list(dict.fromkeys(write + guidance)), delete, same


def _agent_generated(write: list[str], delete: list[str], same: list[str], dry: bool) -> str:
    verbs = ("would write", "would delete") if dry else ("wrote", "deleted")
    return f"{verbs[0]} {len(write)}, {verbs[1]} {len(delete)}, {len(same)} already up to date"


def _agent_details(write: list[str], delete: list[str], dry: bool) -> list[list[str]]:
    """The --details file list as blocks: each group under its own heading."""
    blocks = []
    for heading, paths in ((("Would write" if dry else "Wrote"), write),
                           (("Would delete" if dry else "Deleted"), delete)):
        if paths:
            blocks.append([f"  {heading} ({len(paths)})"] + [f"    {p}" for p in paths])
    return [["File list"] + [line for block in blocks for line in block]] if blocks else []


def _agent_tail(write: list[str], delete: list[str], dry: bool, details: bool,
                detail_blocks: list[list[str]], keep_note: bool) -> list[list[str]]:
    """The blocks after the summary rows: details lists, the folder-kept note,
    the count-only hint, and the no-files-written line of a preview."""
    tail = list(detail_blocks)
    if keep_note:
        tail.append(["The agent folder was not deleted."])
    if not details and write and not dry:
        tail.append(AGENT_LIST_HINT)
    elif not details and (write or delete) and dry:
        tail.append(AGENT_PREVIEW_HINT)
    if dry:
        tail.append(["Paths are relative to the agent folder.", "No files were written."]
                    if details and (write or delete) else ["No files were written."])
    return tail


def _print_agent_blocks(blocks: list[list[str]], next_cmd: str) -> None:
    for block in blocks:
        print()
        print("\n".join(block))
    print()
    print("Next: " + next_cmd)


def _print_agent(data: dict, verb: str, target: Path, why: str | None,
                 *, path_arg: bool, details: bool) -> None:
    """The add, update and remove results (approved screens 207 to 257)."""
    dry = data["dry_run"]
    own = [name for name in data["written"] if name in OWN_FILES]
    guidance = [name for name in data["written"]
                if name not in OWN_FILES and name != AGENT_RECORD.name]
    write, delete, same = _agent_files(data["generated"], guidance, dry)
    touched = bool(write or delete or data.get("added") or data.get("packs_on")
                   or data.get("files_removed") or data["written"])
    launch = data["launch"]
    row_target = f"{data['home']} ({'path' if path_arg else 'name'})"
    rows = [("Target", row_target), ("Installation", f"{target} ({present.target_source_label(why)})")]
    files = data["files"]
    if verb == "add":
        title = ("agent add preview" if dry else "agent added" if touched
                 else "agent add, nothing to do")
        added = data["added"]
        if data["packs_on"]:
            rows.append(("Pack on", ", ".join(data["packs_on"])))
        if added:
            rows.append(("Added", _agent_ids(added, details)))
        if added:
            rows.append(("Installed files", f"{len(files)} (was {data['was']})"))
        elif write and not dry:
            rows.append(("Installed files", f"{len(files)} ({_agent_ids(files, details)})"))
        else:
            rows.append(("Installed files", f"{len(files)}, already recorded"))
        if data["packs"] and not data["packs_on"]:
            rows.append(("Packs", ", ".join(data["packs"]) + ", already on"))
        else:
            rows.append(("Packs", ", ".join(data["packs"]) or "none"))
        rows += subagents.rows(data["sub_agents"])
        if touched or dry:
            rows.append(("Harness", f"{launch['harness']} ({present.HARNESS_MEANING[launch['harness']]})"))
        if touched and not dry and not added:
            rows += [("Model", launch["model"]), ("Effort", str(launch["effort"]))]
        if not dry:
            rows.append(("Record", "agent.json updated" if touched else "agent.json already matches"))
        rows.append(("Generated files", _agent_generated(write, delete, same, dry)))
        if own:
            rows.append(("Own files", (f"would write {', '.join(own)}" if dry
                                       else f"wrote {', '.join(own)}")))
    elif verb == "update":
        title = ("update preview" if dry else "agent updated" if touched
                 else "agent update, nothing to do")
        if data["scope"] == "guidance":
            title = "agent update"
        rows.append(("Scope", data["scope"]))
        added, removed = data["added"], data["removed"]
        if added:
            rows.append(("Would add" if dry else "Added", _agent_ids(added, details)))
        if removed:
            rows.append(("Would remove" if dry else "Removed", _agent_ids(removed, details)))
        if (added or removed) and dry:
            rows.append(("Installed files", f"{len(files)} (would be {_agent_ids(files, details)})"))
        elif added or removed:
            rows.append(("Installed files", f"{len(files)} (membership changed)"))
            rows.append(("  Was", _agent_ids(data["on_disk"], details)))
            rows.append(("  Now", _agent_ids(files, details)))
        elif touched or _agent_mismatch(data):
            rows.append(("Installed files", f"{len(files)}"))
        else:
            rows.append(("Installed files", f"{len(files)}, already match agent.json"))
        if not touched and not dry:
            rows.append(("Packs", ", ".join(data["packs"]) or "none"))
        rows.append(("Guidance", "nothing to copy (no guidance file is set)"))
        if touched and not dry:
            rows.append(("Record", "already matched the pulled file"))
        rows.append(("Generated files", _agent_generated(write, delete, same, dry)))
    else:
        title = ("removal preview" if dry else "files removed" if touched
                 else "agent remove, nothing to do")
        removed = data["files_removed"]
        packs_off = data["packs_off"]
        if packs_off and not data["all"]:
            rows.append(("Pack off", ", ".join(packs_off)))
        if removed:
            rows.append(("Would remove" if dry else "Removed", _agent_ids(removed, details)))
        if data["all"] and packs_off:
            rows.append(("Packs", f"none ({', '.join(packs_off)} turned off)"))
        rows.append(("Installed files", f"{len(files)} (was {data['was']})" if data["was"] != len(files)
                     else f"{len(files)}, unchanged"))
        if not data["all"]:
            kept_packs = ", ".join(data["packs"])
            rows.append(("Packs", (f"{kept_packs} (kept)" if kept_packs and touched else kept_packs or "none")))
        if touched and not dry:
            rows.append(("Record", "agent.json updated"))
        if touched or dry:
            rows.append(("Generated files", _agent_generated(write, delete, same, dry)))
            rows.append(("Kept", ", ".join([data["home"], *data["kept"]])))
    print(present.title(title))
    print()
    print("\n".join(present.fields(rows)))
    if verb == "update" and data["scope"] == "guidance":
        blocks = [["Nothing to copy. No guidance file is set for this agent."]]
        if _agent_mismatch(data):
            blocks.append(present.wrap("Warning: the folder does not match agent.json. "
                                       "This scope does not add or remove files.")
                          + [f"  On disk:     {_agent_ids(data['on_disk'], details)}",
                             f"  agent.json:  {_agent_ids(files, details)}"])
        _print_agent_blocks(blocks, data["next"])
        return
    detail_blocks = _agent_details(write, delete, dry) if details else []
    if verb in ("add", "update") and details and files:
        detail_blocks.insert(0, ["Files"] + [f"  {u}" for u in files])
    if verb == "add":
        detail_blocks += [present.wrap(note) for note in subagents.notes(data["sub_agents"])]
    keep_note = verb == "remove" and touched and not dry
    _print_agent_blocks(_agent_tail(write, delete, dry, details, detail_blocks, keep_note),
                        data["next"])


def _print_agent_configure(data: dict, target: Path, why: str | None,
                           *, path_arg: bool, details: bool) -> None:
    """The configure result (approved screens 228 to 233)."""
    dry = data["dry_run"]
    before, after = data["before"], data["launch"]
    own = [name for name in data["written"] if name in OWN_FILES]
    guidance = [name for name in data["written"]
                if name not in OWN_FILES and name != AGENT_RECORD.name]
    write, delete, same = _agent_files(data["generated"], guidance, dry)
    changed = bool(data["written"])
    title = ("configure preview" if dry else "agent configured" if changed
             else "agent configure, nothing to do")
    harness = lambda side: f"{side['harness']} ({present.HARNESS_MEANING[side['harness']]})"
    rows = [("Target", f"{data['home']} ({'path' if path_arg else 'name'})"),
            ("Installation", f"{target} ({present.target_source_label(why)})"),
            ("Harness", f"{harness(before)} -> {harness(after)}"),
            ("Model", f"{before['model']} -> {after['model']}"),
            ("Effort", f"{before['effort']} -> {after['effort']}"),
            ("Voice", f"{before['voice'] or 'not set'} -> {after['voice'] or 'not set'}")]
    if data["harness_changed"]:
        rows.append(("Installed files", f"{len(data['files'])}, unchanged"))
    if not dry:
        rows.append(("Record", "agent.json updated" if changed else "agent.json already has these values"))
    if data["harness_changed"]:
        rows.append(("Generated files", _agent_generated(write, delete, same, dry)))
    else:
        rows.append(("Generated files", "none (harness unchanged)" if changed else "none"))
    print(present.title(title))
    print()
    print("\n".join(present.fields(rows)))
    detail_blocks = _agent_details(write, delete, dry) if details else []
    detail_blocks += [present.wrap(
        f"{gap['name']} is not written as a harness-native sub-agent for "
        f"{gap['harness']}: a model and an effort are needed. "
        f"Add it with: {gap['command']}") for gap in data["sub_agents_missing"]]
    _print_agent_blocks(_agent_tail(write, delete, dry, details, detail_blocks, False),
                        data["next"])


def _agent_next_text(data: dict, path_arg: bool) -> str:
    """The next command after an agent change: the same command again for a
    preview, otherwise the agent list (the agent in full for a path, since
    the list holds only the installation's own agents)."""
    if path_arg:
        return "rbtv agent list " + _quote(Path(data["home"]))
    return "rbtv agent list"


def _agent_mismatch(data: dict) -> bool:
    """True when the folder's files and agent.json's files differ."""
    return bool(data["listed_missing"] or data["on_disk_unlisted"])


def _agent_repeat(args, scope: str | None = None) -> str:
    """The command a preview is followed by: the same change, without the
    preview flags. `scope` replaces an update's scope."""
    words = ["rbtv agent", args.agent_verb, _quote(args.agent)]
    if args.agent_verb == "configure":
        words += [f"--{key} {value}" for key, value in
                  (("harness", args.harness), ("model", args.model),
                   ("effort", args.effort), ("voice", args.voice)) if value is not None]
    elif args.agent_verb == "update":
        words.append(scope or args.scope)
    else:
        words += list(args.name) + [f"--pack {pack}" for pack in args.pack]
        if args.agent_verb == "add":
            words += [f"--{key} {getattr(args, key)}" for key in LAUNCH_FIELDS
                      if getattr(args, key) is not None]
            words += [f"--on {value}" for value in args.on]
        if args.agent_verb == "remove":
            words += ["--all"] * bool(args.all) + ["--yes"] * bool(args.yes)
    return " ".join(words)


@mutation_locked
def cmd_agent(args, target: Path, catalog: dict, shadowed: list,
              *, ask=None) -> int:
    del shadowed, ask
    dry = bool(getattr(args, "dry_run", False))
    verb = args.agent_verb
    why = getattr(args, "_why", "unknown")
    as_json = bool(getattr(args, "json", False))
    details = bool(getattr(args, "details", False))
    if verb == "list":
        shown = cast_agent_list(target, args.agent, as_json, args.full, present.terminal_width())
        if as_json:
            found = json.loads(shown)
            _emit({"ok": True, **({"agent": found} if args.agent else found), "next": "rbtv agent -h"},
                  True, target, why)
        else:
            sys.stdout.write(shown)
        return 0
    path_arg = is_path(args.agent)
    if verb == "update" and args.scope not in UPDATE_SCOPES:
        exc = Refuse("usage", "the scope is required: choose guidance, scaffolding or all"
                     if args.scope is None else
                     f"scope {args.scope!r} is not guidance, scaffolding or all")
        exc.next = "rbtv agent update -h"
        raise exc
    if verb == "add":
        data = add_agent(target, args.agent, list(args.name), set(args.pack), catalog, dry,
                         {key: getattr(args, key) for key in LAUNCH_FIELDS}, tuple(args.on))
    elif verb == "update":
        data = update_agent(target, args.agent, args.scope, catalog, dry)
    elif verb == "configure":
        data = configure_agent(target, args.agent, args.harness, args.model,
                               args.effort, args.voice, catalog, dry)
    else:
        data = remove_agent(target, args.agent, list(args.name), set(args.pack),
                            bool(args.all), bool(args.yes), catalog, dry)
    data["next"] = _agent_repeat(args) if dry else _agent_next_text(data, path_arg)
    if verb == "update" and args.scope == "guidance" and _agent_mismatch(data):
        # Guidance copies cannot fix a folder that does not match agent.json.
        data["next"] = _agent_repeat(args, scope="scaffolding")
    if as_json:
        _emit({k: v for k, v in data.items() if k not in _AGENT_TEXT_ONLY}, True, target, why)
    elif verb == "configure":
        _print_agent_configure(data, target, why, path_arg=path_arg, details=details)
    else:
        _print_agent(data, verb, target, why, path_arg=path_arg, details=details)
    return 0


_HANDLERS = {
    "add": cmd_add,
    "rm": cmd_rm,
    "remove": cmd_rm,
    "list": cmd_list,
    "search": cmd_search,
    "ls": cmd_ls,
    "li": cmd_li,
    "show": cmd_show,
    "status": cmd_status,
    "configure": cmd_configure,
    "update": cmd_update,
    "agent": cmd_agent,
    "doctor": cmd_doctor,
    "interactive": cmd_interactive,
    "selftest": cmd_selftest,
}


def main(argv: list[str] | None = None, *, ask=None) -> int:
    parser = build_parser()
    raw = list(argv) if argv is not None else sys.argv[1:]
    # `--json` decides how a refusal is printed, so it is read before the
    # parser runs. Everything after `--` is an operand, never the flag.
    operands = raw.index("--") if "--" in raw else len(raw)
    as_json = "--json" in raw[:operands]
    try:
        args = parser.parse_args(raw)
    except Refuse as exc:
        if as_json:
            print(json.dumps(_error_data(exc), indent=2))
        else:
            _print_refused(exc.code, _text_refusal(exc))
            print(f"next: {exc.next}", file=sys.stderr)
        return 2
    except SystemExit as exc:
        return int(exc.code or 0)

    if args.verb is None:
        parser.print_help()
        return 0
    if args.verb == "selftest":
        if as_json:
            print(json.dumps(_error_data(Refuse(
                "usage", "selftest has no --json output; run without --json"))))
            return 2
        from selftest.runner import selftest
        return selftest()

    try:
        if args.verb == "agent":
            if getattr(args, "target", None) is not None:
                raise Refuse("usage", "agent verbs take no --target")
            target, why = discover_installation(Path.cwd())
        else:
            target, why = resolve_target(getattr(args, "target", None), Path.cwd())
        args._why = why
        repo_tree = REPO_ROOT
        mirror_tree = target / ".rbtv" / "mirror"
        catalog, shadowed = scan_all(mirror_tree, repo_tree)
        if args.verb == "interactive":
            if as_json:
                raise Refuse("usage", "interactive mode has no --json output")
            if getattr(args, "dry_run", False):
                raise Refuse("usage", "interactive --dry-run is unsupported; use add or remove --dry-run")
            return interactive(target, catalog)
        handler = _HANDLERS.get(args.verb)
        if handler is None:
            parser.error(f"unknown verb {args.verb!r}")
        # A settings NOUN is the other legal shape of add/rm (D16b), so the
        # selector gate must let it through — this gate sits AHEAD of the
        # handler, and without the noun clause every `add harness codex`
        # died here as a usage error before the dispatch ever saw it.
        if (args.verb in ("add", "rm", "remove")
                and not getattr(args, "noun", None)
                and not _has_selectors(args)
                and not getattr(args, "pack", None)):
            parser.error(
                f"{args.verb} needs a name, --all, --module, --component "
                "--type, or --pack")
        return handler(args, target, catalog, shadowed, ask=ask)
    except Refuse as exc:
        takes_target = args.verb != "agent"
        if as_json:
            print(json.dumps(_error_data(exc, locals().get("target"),
                                         locals().get("catalog"),
                                         takes_target=takes_target), indent=2))
        else:
            _print_refused(exc.code, _text_refusal(exc))
            if exc.path:
                print(f"  at: {exc.path}", file=sys.stderr)
            next_cmd = _error_data(exc, locals().get("target"),
                                   locals().get("catalog"),
                                   takes_target=takes_target).get("next")
            if next_cmd:
                print(f"next: {next_cmd}", file=sys.stderr)
        return 2 if exc.code == "usage" else 1
    except OSError as exc:
        where = str(locals().get("target", Path.cwd()))
        message = (f"file operation failed: {exc}. A preceding installation write "
                   "may have applied; inspect the target before retrying")
        next_cmd = "rbtv doctor --target " + _quote(where)
        if as_json:
            # `changed` is null, not false: the failure can land after some
            # writes, so whether the installation changed is unknown.
            print(json.dumps({"ok": False, "error": {
                "code": "io-error", "message": message,
                "path": getattr(exc, "filename", None) or where,
                }, "target": where, "changed": None,
                "next": next_cmd}, indent=2))
        else:
            _print_refused("io-error", message, outcome="failed")
            print(f"next: {next_cmd}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        return int(exc.code or 0)
    except KeyboardInterrupt:
        if as_json:
            print(json.dumps({"ok": False, "error": {
                "code": "interrupted",
                "message": "operation interrupted; inspect status before retrying"}}))
        else:
            print("\ninterrupted; inspect status before retrying",
                  file=sys.stderr)
        return 1
