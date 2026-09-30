"""One handler per verb, and the dispatch that runs them."""
from __future__ import annotations

import argparse
import json
import sys
from functools import wraps
from pathlib import Path

from discovery import Refuse, scan_all

from . import present
from .constants import (
    ANSI,
    BASIS_NONE,
    GUIDANCE_NAMES,
    HARNESSES,
    REPO_ROOT,
    STATE_REL,
)
from .guidance import _norm_prefix
from .target import DISCOVER_CWD, resolve_target
from .state import book_harnesses, read_state
from .selection import (
    _has_negative,
    _split_part_keys,
    iter_catalog_parts,
    iter_booked_units,
    resolve_name,
    resolve_selection,
)
from .operations import do_install, do_uninstall
from .pathlinks import bin_dir
from .shared_links import release_workspace_links, workspace_mutation_lock
from .listing import (_short_description, build_list, build_show,
                      do_list, print_list, print_show)
from .doctor import do_doctor, doctor_exit
from .report import print_result
from .recovery import shell_quote
from .interactive import interactive
from .parser import SETTING_VERB, _refuse_moved, build_parser


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
          source: str | None = None, *, verb: str = "") -> None:
    if target is not None:
        data = {**data, "target": str(target.resolve()), "source": source}
    data.setdefault("next", "rbtv install status --target " + _quote(target)
                    if target is not None else "rbtv install status")
    if as_json:
        print(json.dumps(data, indent=2))
    else:
        # `verb` picks the title (D9 §1); never part of the JSON contract.
        print_result({**data, "_verb": verb} if verb else data)


def _print_refused(code: str, message: str) -> None:
    """The ONE place a plain-text refusal begins: the shared title, then a
    blank line, then the `REFUSED [code] message` line every refusal path
    already prints. Every non-JSON stderr refusal — a parser validation
    error, a retired form, a target/OSError, or a command `Refuse` — calls
    this first so none of them can print `REFUSED …` bare. JSON's single
    undecorated value never goes through this — only the human-text path."""
    print(present.title("refused"), file=sys.stderr)
    print(file=sys.stderr)
    print(f"REFUSED [{code}] {message}", file=sys.stderr)


def _error_data(exc: Refuse, target: Path | None = None,
                catalog: dict | None = None) -> dict:
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
        out["next"] = ("rbtv install show " + _quote(error["suggestions"][0]["id"])
                       + (" --target " + _quote(target) if target is not None else ""))
    elif exc.code in {"name-unknown", "unit-unknown", "component-unknown"}:
        out["next"] = ("rbtv install list"
                       + (" --target " + _quote(target) if target is not None else ""))
    return out


def mutation_locked(handler):
    """Cover selection/settings reads and the operation with one target lock."""
    @wraps(handler)
    def run(args, target, catalog, shadowed, *, ask=None):
        if getattr(args, "dry_run", False):
            return handler(args, target, catalog, shadowed, ask=ask)
        with workspace_mutation_lock(target):
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
    data = build_list(catalog, state, query=args.query,
                      modules=args.module, components=args.component,
                      methods=args.method,
                      installed=bool(args.installed or args.verb == "li"),
                      search=args.verb == "search",
                      limit=limit, offset=offset)
    data.update(target=str(target.resolve()), source=getattr(args, "_why", "unknown"))
    if offset >= data["total"] and data["total"]:
        raise Refuse("offset-out-of-range",
                     f"--offset {offset} is past {data['total']} matching items. "
                     "Run `rbtv install list --offset 0 --target "
                     + _quote(target) + "`")
    command = ["rbtv install " + ("search" if args.verb == "search" else "list")]
    if args.query:
        command.append(_quote(args.query))
    for flag, values in (("--module", args.module), ("--component", args.component),
                         ("--type", args.method)):
        command.extend(f"{flag} {_quote(value)}" for value in values)
    if args.installed or args.verb == "li":
        command.append("--installed")
    command.append("--target " + _quote(target))
    has_more = offset + data["returned"] < data["total"]
    if has_more:
        command.extend((f"--limit {limit}", f"--offset {offset + data['returned']}"))
    elif not data["total"]:
        command = ["rbtv install list --target " + _quote(target)]
    elif data["scope"] == "items" and data["returned"] == 1:
        command = ["rbtv install show " + _quote(data["items"][0]["id"])
                   + " --target " + _quote(target)]
    else:
        command = ["rbtv install show " + _quote(data["query"] or "MODULE")
                   + " --target " + _quote(target)]
    data["next"] = " ".join(command)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        # Presentation-only bookkeeping (never part of the JSON contract):
        # which title/next-label branch to render.
        print_list({**data, "searching": args.verb == "search",
                   "installed_only": bool(args.installed or args.verb == "li"),
                   "has_more": has_more})
    return 0


def cmd_ls(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    return cmd_list(args, target, catalog, shadowed, ask=ask)


def cmd_search(args, target: Path, catalog: dict, shadowed: list,
               *, ask=None) -> int:
    if not args.query:
        raise Refuse("query-required", "search needs words to match against item names and descriptions")
    return cmd_list(args, target, catalog, shadowed, ask=ask)


def cmd_li(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    return cmd_list(args, target, catalog, shadowed, ask=ask)


def cmd_show(args, target: Path, catalog: dict, shadowed: list,
             *, ask=None) -> int:
    del ask, shadowed
    state = read_state(target)
    known_modules = {part["module"] for part in iter_catalog_parts(catalog)}
    named_module = ("_hub" if args.name == "hub" else args.name)
    if named_module in known_modules:
        if args.method:
            raise Refuse("type-mismatch", "--type requires an item name; list "
                         + args.name + " --type " + args.method[0])
        view = build_list(catalog, state, query=args.name, limit=100)
        comp = next((c for c in catalog.values()
                     if c.get("module") == named_module), None)
        description = _short_description(comp.get("module_description", "")) if comp else ""
        selection = {"scope": "module", "id": args.name,
                     "description": description,
                     "components": view["items"],
                     "installed_items": sum(r["installed_items"] for r in view["items"]),
                     "source_items": sum(r["source_items"] for r in view["items"])}
        # A real component drilled into (screen 21's pattern), never the
        # module itself again — `list` was a dead end that never advanced
        # the reader toward an actual item.
        next_cmd = (f"rbtv install show {view['items'][0]['id']} --target {_quote(target)}"
                   if view["items"] else
                   f"rbtv install list {args.name} --target {_quote(target)}")
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
            "selection": build_show(selected, catalog, state)}
    parts = data["selection"]["units"]
    if selected["kind"] == "part":
        # Approved screens 20/55: an installed item's next step is a health
        # check, never a removal suggestion just because it happens to be
        # installed. An uninstalled item's next step is the setup that
        # would install it.
        data["next"] = (f"rbtv install doctor --target {_quote(target)}"
                        if parts[0]["installed"] else
                        f"rbtv install add {selected['id']} --target {_quote(target)}")
    else:
        # Screen 21: a component's next step drills into one of its real
        # included items, never a generic re-listing of itself.
        data["next"] = (f"rbtv install show {parts[0]['key']} --target {_quote(target)}"
                        if parts else
                        f"rbtv install list {selected['id']} --target {_quote(target)}")
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_show(data)
    return 0


def cmd_status(args, target: Path, catalog: dict, shadowed: list,
               *, ask=None) -> int:
    del ask, shadowed
    installed = do_list(target, catalog)
    comps = installed["components"]
    count = sum(len(rec.get("units") or {}) for rec in comps.values())
    modules = sorted({("hub" if (comp.get("module") or cid.split("/")[0]) == "_hub"
                       else comp.get("module") or cid.split("/")[0])
                      for cid, comp in catalog.items()})
    settings = installed["settings"]
    data = {"ok": True, "target": str(target.resolve()),
            "target_source": ("explicit" if getattr(args, "_why", None) == "--target"
                              else getattr(args, "_why", "unknown")),
            "installation": {"configured": settings["recorded"],
                             "harnesses": settings["harnesses"] or [],
                             "guidance": settings["artifact"],
                             "guidance_excludes": settings["guidance_excludes"],
                             "installed_components": len(comps),
                             "installed_items": count,
                             "health": "not_checked"},
            "source_catalog": {"modules": len(modules),
                               "items": len(iter_catalog_parts(catalog))},
            "next": f"rbtv install doctor --target {_quote(target)}"}
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        why = getattr(args, "_why", None)
        print(present.title("status"))
        print()
        print(f"Target: {data['target']} ({present.target_source_label(why)})")
        if settings["recorded"]:
            harnesses = ", ".join(
                f"{h} ({present.HARNESS_MEANING.get(h, h)})"
                for h in settings["harnesses"])
            print("Saved receiving tools: " + harnesses)
            print("Maintained guidance: " + (settings["artifact"] or "none"))
            print("Guidance folders excluded from copying: "
                  + (", ".join(settings["guidance_excludes"]) or "none"))
            print()
            print("Recorded installation in this target")
            print(f"  Components with selected items: {len(comps)}")
            print(f"  Items: {count}")
            print(f"  Saved record: {STATE_REL}")
        else:
            print("Installation: no saved configuration or selected items")
            print()
            print("First use: choose receiving tools and a maintained guidance file.")
            print("  " + "; ".join(f"{h} = {present.HARNESS_MEANING[h]}"
                                    for h in HARNESSES))
            print("  CLAUDE.md or AGENTS.md must exist in this target; "
                  "none disables copying.")
        print()
        print("Local source catalog on this machine")
        print(f"  {len(modules)} modules, {data['source_catalog']['items']} items; "
              "source availability does not mean installed here.")
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
                "this workspace already targets " + ", ".join(booked)
                + "; change it with `rbtv install configure --harness "
                + _quote(raw) + " --target " + _quote(target)
                + "` before adding components",
                str(target / STATE_REL))
    if booked is None:
        if raw is None:
            raise Refuse(
                "harness-required",
                "first install on this workspace: pass --harness with a "
                "comma-separated subset of " + ", ".join(HARNESSES)
                + ". It is recorded once for the whole workspace; every later "
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
                "this workspace already uses guidance "
                + str(state.get("guidance_basis") or BASIS_NONE)
                + "; change it with `rbtv install configure --guidance "
                + _quote(raw) + " --target " + _quote(target) + "`",
                str(target / STATE_REL))
    if not booked and raw is None:
        raise Refuse(
            "artifact-required",
            "first install on this workspace: pass --guidance with "
            + " or ".join((*GUIDANCE_NAMES, BASIS_NONE))
            + " — the root guidance file YOU author, from which the others are "
              f"generated. `{BASIS_NONE}` means author nothing and generate "
              "nothing. Recorded once; thereafter "
              f"`{SETTING_VERB['guidance']}`")
    return raw


def _replan_all(target: Path, catalog: dict, harnesses: list[str],
                dry_run: bool, *, guidance_basis: str | None = None,
                guidance_excludes: list[str] | None = None,
                scope: str = "all") -> dict:
    """D16 — re-plan EVERY booked component under a changed workspace setting.
    `apply` removes what the old book held and the new plan does not, so a
    dropped harness really loses its files. A component whose folder vanished
    upstream is left in the book untouched: `plan_files` still refuses the run
    with `component-vanished`, the same refusal `add` gives."""
    records = read_state(target).get("components") or {}
    picked = [cid for cid in sorted(records) if cid in catalog]
    return do_install(target, catalog, picked, harnesses, dry_run,
                      guidance_basis=guidance_basis,
                      guidance_excludes=guidance_excludes, scope=scope)


def _require_recorded(target: Path, state: dict) -> list[str]:
    booked = book_harnesses(state)
    if booked is None:
        raise Refuse(
            "workspace-unrecorded",
            "this workspace has no recorded settings yet — nothing has been "
            "installed here. The first add needs both --harness and "
            "--guidance; run `rbtv install list` to choose an item",
            str(target / STATE_REL))
    return booked


def cmd_harness(args, target: Path, catalog: dict, shadowed: list,
                *, ask=None) -> int:
    del ask, shadowed, catalog, target
    _refuse_moved("harness", list(getattr(args, "moved", None) or []))
    return 1  # unreachable: _refuse_moved always raises


def cmd_artifact(args, target: Path, catalog: dict, shadowed: list,
                 *, ask=None) -> int:
    del ask, shadowed, catalog, target
    _refuse_moved("artifact", list(getattr(args, "moved", None) or []))
    return 1  # unreachable: _refuse_moved always raises


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
            "that would leave this workspace targeting no harness at all. "
            "Removing every harness is an uninstall — `rbtv install rm -A`",
            str(target / STATE_REL))
    if new == current:
        _emit({"ok": True, "changed": False, "dry_run": bool(args.dry_run),
               "message": f"this workspace already targets {', '.join(new)}"},
              bool(args.json), target, getattr(args, "_why", "unknown"),
              verb="configure")
        return 0
    data = _replan_all(target, catalog, new,
                       bool(getattr(args, "dry_run", False)))
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="configure")
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
              verb="configure")
        return 0
    data = _replan_all(target, catalog, harnesses,
                       bool(getattr(args, "dry_run", False)),
                       guidance_basis=value)
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="configure")
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
              verb="configure")
        return 0
    data = _replan_all(target, catalog, harnesses,
                       bool(getattr(args, "dry_run", False)),
                       guidance_excludes=new)
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="configure")
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
            f"`{verb} {head}` changes a WORKSPACE SETTING and takes no "
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
        raise Refuse("noun-retired", "artifact is now guidance. Run `rbtv install "
                     + verb + " guidance exclude FOLDER` to change excluded folders")

    known = "harness, guidance exclude"
    raise Refuse(
        "noun-unknown",
        f"`{head}` names no workspace setting. Known: {known}. "
        "To choose COMPONENTS, use the selector flags (-c/-m/-x/-A) with no "
        "noun — run `rbtv install " + verb + " --help`")


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
                         "and --guidance; for example: rbtv install configure "
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
        _emit(data, bool(args.json), target, getattr(args, "_why", "unknown"),
              verb="configure")
        return 0
    raise Refuse("noun-missing", "configure needs --harness, --guidance, or both")


@mutation_locked
def cmd_add(args, target: Path, catalog: dict, shadowed: list,
            *, ask=None) -> int:
    del ask, shadowed
    noun = list(getattr(args, "noun", None) or [])
    if noun and noun[0] in ("harness", "guidance", "artifact"):
        return _settings_form(args, target, catalog, "add", noun)
    if not (_has_selectors(args) or noun):
        raise SystemExit(2)
    args.names = noun
    keys = resolve_selection(args, catalog, None)
    picked, parts = _split_part_keys(keys)
    state = read_state(target)
    if book_harnesses(state) is None and (
            getattr(args, "harness", None) is None
            or getattr(args, "artifact", None) is None):
        raise Refuse(
            "setup-required",
            "first add needs both --harness (which AI tools receive items) "
            "and --guidance (CLAUDE.md, AGENTS.md, or none). Example: "
            "rbtv install add " + parts[0]
            + " --harness codex --guidance none --target " + _quote(target))
    harnesses = _gate_add_harness(target, state, getattr(args, "harness", None))
    basis = _gate_add_artifact(target, state, getattr(args, "artifact", None))
    data = do_install(
        target, catalog, picked, harnesses,
        bool(getattr(args, "dry_run", False)),
        guidance_basis=basis,
        parts=parts)
    data["selected_items"] = parts
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="add")
    return 0


@mutation_locked
def cmd_rm(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    del shadowed, ask
    noun = list(getattr(args, "noun", None) or [])
    if noun and noun[0] in ("harness", "guidance", "artifact"):
        return _settings_form(args, target, catalog, "rm", noun)
    if not (_has_selectors(args) or noun):
        raise SystemExit(2)
    args.names = noun
    book = read_state(target).get("components")
    keys = resolve_selection(args, catalog, book)
    dry = bool(getattr(args, "dry_run", False))
    path_release = bool(args.all and getattr(args, "_why", None) == "--target"
                        and not (target / STATE_REL).is_file())
    preview_links = (release_workspace_links(bin_dir(), target, dry=True)
                     if path_release else {})
    shared_count = len(set(preview_links.get("released") or [])
                       | set(preview_links.get("unlinked") or [])
                       | set(preview_links.get("kept_shared") or []))
    if not keys and not shared_count:
        _emit({"ok": True, "uninstalled": [], "dry_run": dry,
               "message": "no installed items matched this request"},
              bool(args.json), target, getattr(args, "_why", "unknown"),
              verb="remove")
        return 0
    broad = bool(args.all or args.module or args.method or _has_negative(args))
    if broad and not (dry or getattr(args, "yes", False)):
        flags = ["--all"] if args.all else []
        flags += [f"--module {_quote(m)}" for m in args.module]
        flags += [f"--component {_quote(c)}" for c in args.component]
        flags += [f"--type {_quote(m)}" for m in args.method]
        flags += [f"--exclude-module {_quote(m)}" for m in args.exclude_module]
        flags += [f"--exclude-component {_quote(c)}" for c in args.exclude_component]
        flags += [f"--exclude-type {_quote(m)}" for m in args.exclude_method]
        retry = "rbtv install remove " + " ".join(
            [_quote(name) for name in noun] + flags
            + ["--yes", "--target", _quote(target)])
        preview = sorted(keys)[:20]
        exc = Refuse(
            "confirmation-required",
            f"broad removal selected {len(keys)} item(s)"
            + (f" and {shared_count} registered shared shortcut(s)" if shared_count else "")
            + "; preview: "
            + (", ".join(preview) or "(none)")
            + (f"; {len(keys)-20} more" if len(keys) > 20 else "")
            + f". Review with --dry-run, then run: {retry}")
        exc.preview = {"total": len(keys), "items": preview,
                       "next": retry}
        raise exc
    if not keys:
        report = {"path": (preview_links if dry else
                           release_workspace_links(bin_dir(), target, dry=False))}
        _emit({"ok": True, "uninstalled": [], "dry_run": dry,
               "report": report,
               "message": "released shared shortcut claims for this target"},
              bool(args.json), target, getattr(args, "_why", "unknown"),
              verb="remove")
        return 0
    picked, parts = _split_part_keys(keys)
    data = do_uninstall(target, catalog, picked, dry, parts=parts)
    data["selected_items"] = parts
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="remove")
    return 0


@mutation_locked
def cmd_update(args, target: Path, catalog: dict, shadowed: list,
               *, ask=None) -> int:
    del ask, shadowed
    state = read_state(target)
    hs = _require_recorded(target, state)
    data = _replan_all(target, catalog, hs,
                       bool(getattr(args, "dry_run", False)),
                       scope=args.scope)
    records = state.get("components") or {}
    data["recorded_items"] = len(iter_booked_units(catalog, records))
    data["source_missing"] = sorted(cid for cid in records if cid not in catalog)
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"), verb="update")
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
            print(f"{_RESULT_LABEL[c['level']]} — {c['name']}: {c['detail']}")


def _print_doctor(data: dict, *, color: bool) -> None:
    """Doctor's terminal rendering: a Check/Scope/Result table with full
    recovery text below it, the optional cleanup-audit section split out
    (D9 §5), and a next step truthful about what was actually checked. Reads
    `do_doctor`'s check records as data only — `lib/doctor.py` itself is not
    touched; this replaces its own `render_doctor` as the printed path."""
    checks = data["checks"]
    main = [c for c in checks if c["scope"] != "Other workspace"]
    audit = [c for c in checks if c["scope"] == "Other workspace"]

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
    print(f"{len(main)} checks: {counts}. {discovery} "
          "Runtime dependencies and arbitrary command execution were not tested.")
    if audit:
        print()
        print("Optional cleanup audit")
        _print_doctor_section(audit, color=color)
        n_audit_warn = sum(1 for c in audit if c["level"] != "ok")
        print()
        print(f"Optional audit: {n_audit_warn} warning(s). No cleanup was performed.")
    print()
    if n_fail:
        print("Repair: follow the FAIL recovery text above, then rerun doctor.")
    else:
        print("Next: rbtv install list --installed --target " + _quote(data["target"]))


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
    "harness": cmd_harness,
    "artifact": cmd_artifact,
    "doctor": cmd_doctor,
    "interactive": cmd_interactive,
    "selftest": cmd_selftest,
}


def main(argv: list[str] | None = None, *, ask=None) -> int:
    parser = build_parser()
    raw = list(argv) if argv is not None else sys.argv[1:]
    # A retired word is grammar only when it occupies the verb slot or an
    # option slot. A search term, selected item, or option value may have the
    # same spelling. Walk the parser's own option actions so this pre-parse
    # check does not maintain a second list of value-taking flags.
    options: dict[str, argparse.Action] = {}
    def collect(p: argparse.ArgumentParser) -> None:
        for action in p._actions:
            options.update((name, action) for name in action.option_strings)
            if isinstance(action, argparse._SubParsersAction):
                for child in action.choices.values():
                    collect(child)
    collect(parser)
    verb_index = None
    pos = 0
    while pos < len(raw):
        token = raw[pos]
        if token == "--":
            verb_index = pos + 1 if pos + 1 < len(raw) else None
            break
        if not token.startswith("-"):
            verb_index = pos
            break
        name, eq, _value = token.partition("=")
        action = parser._option_string_actions.get(name)
        pos += 1 + (bool(action and action.nargs != 0 and not eq))

    retired_verbs = {"set": ["configure"],
                     "dupe-artifacts": ["update", "guidance"]}
    retired_options = {"--kind": "--type",
                       "--exclude-kind": "--exclude-type",
                       "--artifact": "--guidance"}
    retirements: list[tuple[int, str, list[str]]] = []
    as_json = False
    value_pending = False
    options_ended = False
    for index, token in enumerate(raw):
        if value_pending:
            value_pending = False
            continue
        if token == "--":
            options_ended = True
            continue
        if options_ended:
            continue
        if index == verb_index and token in retired_verbs:
            retirements.append((index, token, retired_verbs[token]))
        name, eq, value = token.partition("=")
        if name == "--json" and token == "--json":
            as_json = True
        if name in retired_options and token.startswith("--"):
            replacement = retired_options[name] + ("=" + value if eq else "")
            retirements.append((index, name, [replacement]))
        action = options.get(name) if token.startswith("-") else None
        value_pending = bool(action and action.nargs != 0 and not eq)
    try:
        if retirements:
            index, token, replacement = retirements[0]
            replacements = {at: parts for at, _old, parts in retirements}
            if (verb_index is not None and raw[verb_index] == "set"
                    and verb_index + 1 < len(raw)):
                old_noun = raw[verb_index + 1]
                if old_noun in {"harness", "artifact", "guidance"}:
                    replacements[verb_index + 1] = [
                        "--harness" if old_noun == "harness" else "--guidance"]
            fixed = [part for at, old in enumerate(raw)
                     for part in replacements.get(at, [old])]
            retry = "rbtv install " + " ".join(_quote(part) for part in fixed)
            exc = Refuse(
                "grammar-retired",
                f"{token} is now {' '.join(replacement)}. Nothing changed.\n"
                f"Fix: {retry}")
            exc.next = retry
            raise exc
        args = parser.parse_args(raw)
    except Refuse as exc:
        if as_json:
            print(json.dumps(_error_data(exc)))
        else:
            _print_refused(exc.code, exc.message)
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
                and not _has_selectors(args)):
            parser.error(
                f"{args.verb} needs a name, --all, --module, --component "
                "or --type")
        return handler(args, target, catalog, shadowed, ask=ask)
    except Refuse as exc:
        if as_json:
            print(json.dumps(_error_data(exc, locals().get("target"),
                                         locals().get("catalog")), indent=2))
        else:
            _print_refused(exc.code, exc.message)
            if exc.path:
                print(f"  at: {exc.path}", file=sys.stderr)
            next_cmd = _error_data(exc, locals().get("target"),
                                   locals().get("catalog")).get("next")
            if next_cmd:
                print(f"next: {next_cmd}", file=sys.stderr)
        return 2 if exc.code == "usage" else 1
    except OSError as exc:
        where = str(locals().get("target", Path.cwd()))
        message = (f"file operation failed: {exc}. A preceding workspace write "
                   "may have applied; inspect the target before retrying")
        next_cmd = "rbtv install doctor --target " + _quote(where)
        if as_json:
            print(json.dumps({"ok": False, "error": {
                "code": "io-error", "message": message,
                "path": getattr(exc, "filename", None) or where,
                }, "target": where, "changed": False,
                "next": next_cmd}, indent=2))
        else:
            _print_refused("io-error", message)
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
