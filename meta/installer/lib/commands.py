"""One handler per verb, and the dispatch that runs them."""
from __future__ import annotations

import json
import sys
from functools import wraps
from pathlib import Path

from discovery import Refuse, scan_all

from .constants import (
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
    resolve_name,
    resolve_selection,
)
from .operations import do_install, do_uninstall
from .pathlinks import bin_dir
from .shared_links import release_workspace_links, workspace_mutation_lock
from .listing import build_list, build_show, do_list, print_list, print_show
from .doctor import do_doctor, doctor_exit, render_doctor
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
          source: str | None = None) -> None:
    if target is not None:
        data = {**data, "target": str(target.resolve()), "source": source}
    data.setdefault("next", "rbtv install status --target " + _quote(target)
                    if target is not None else "rbtv install status")
    print(json.dumps(data, indent=2)) if as_json else print_result(data)


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
                      limit=limit, offset=offset)
    data.update(target=str(target.resolve()), source=getattr(args, "_why", "unknown"))
    if offset >= data["total"] and data["total"]:
        raise Refuse("offset-out-of-range",
                     f"--offset {offset} is past {data['total']} matching items. "
                     "Run `rbtv install list --offset 0 --target "
                     + _quote(target) + "`")
    command = ["rbtv install list"]
    if args.query:
        command.append(_quote(args.query))
    for flag, values in (("--module", args.module), ("--component", args.component),
                         ("--kind", args.method)):
        command.extend(f"{flag} {_quote(value)}" for value in values)
    if args.installed or args.verb == "li":
        command.append("--installed")
    command.append("--target " + _quote(target))
    if offset + data["returned"] < data["total"]:
        command.extend((f"--limit {limit}", f"--offset {offset + data['returned']}"))
    elif not data["total"]:
        command = ["rbtv install list --target " + _quote(target)]
    else:
        command = ["rbtv install show ID --target " + _quote(target)]
    data["next"] = " ".join(command)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Target: {target.resolve()} ({data['source']}). "
              "Override with --target PATH.")
        print_list(data)
    return 0


def cmd_ls(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    return cmd_list(args, target, catalog, shadowed, ask=ask)


def cmd_li(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    return cmd_list(args, target, catalog, shadowed, ask=ask)


def cmd_show(args, target: Path, catalog: dict, shadowed: list,
             *, ask=None) -> int:
    del ask, shadowed
    state = read_state(target)
    selected = resolve_name(args.name, catalog, state.get("components"),
                            methods=set(args.method) or None)
    data = {"ok": True, "target": str(target.resolve()),
            "source": getattr(args, "_why", "unknown"),
            "selection": build_show(selected, catalog, state)}
    data["next"] = (f"rbtv install remove {selected['id']} --target {_quote(target)}"
                    if all(part["installed"] for part in data["selection"]["parts"])
                    else f"rbtv install add {selected['id']} --target {_quote(target)}")
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Target: {target.resolve()} ({data['source']}). "
              "Override with --target PATH.")
        print_show(data)
    return 0


def cmd_status(args, target: Path, catalog: dict, shadowed: list,
               *, ask=None) -> int:
    del ask, shadowed
    installed = do_list(target, catalog)
    comps = installed["components"]
    count = sum(len(rec.get("parts") or {}) for rec in comps.values())
    modules = sorted({("hub" if (comp.get("module") or cid.split("/")[0]) == "_hub"
                       else comp.get("module") or cid.split("/")[0])
                      for cid, comp in catalog.items()})
    data = {"ok": True, "target": str(target.resolve()),
            "source": getattr(args, "_why", "unknown"),
            "settings": installed["settings"],
            "installed_components": len(comps), "installed_items": count,
            "available_modules": modules,
            "installed_basis": "install record",
            "health_check": f"rbtv install doctor --target {_quote(target)}",
            "next": (f"rbtv install list --installed --target {_quote(target)}" if comps
                     else f"rbtv install list --target {_quote(target)}")}
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Target: {data['target']} ({data['source']}). "
              "Override with --target PATH.")
        settings = data["settings"]
        if settings["recorded"]:
            print("Harnesses: " + ", ".join(settings["harnesses"]))
            print("Guidance: " + (settings["artifact"] or "none"))
            print("Excluded guidance folders: "
                  + (", ".join(settings["guidance_excludes"]) or "none"))
        else:
            print("Workspace settings: none recorded yet.")
        print(f"Recorded installed: {len(comps)} components, {count} items.")
        print("Available modules: " + ", ".join(modules)
              + ". Explore one with 'rbtv install list --module NAME'.")
        print("Check installed files: " + data["health_check"])
        print("next: " + data["next"])
    return 0


def _gate_add_harness(target: Path, state: dict, raw: str | None) -> list[str]:
    """Accept a repeated setup value when it agrees with the saved value."""
    booked = book_harnesses(state)
    if booked is not None and raw is not None:
        if _parse_harnesses(raw) != booked:
            raise Refuse(
                "setting-locked",
                "this workspace already targets " + ", ".join(booked)
                + "; change it with `rbtv install set --harness "
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
                + "; change it with `rbtv install set --guidance "
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
              f"`{SETTING_VERB['artifact']}`")
    return raw


def _replan_all(target: Path, catalog: dict, harnesses: list[str],
                dry_run: bool, *, guidance_basis: str | None = None,
                guidance_excludes: list[str] | None = None) -> dict:
    """D16 — re-plan EVERY booked component under a changed workspace setting.
    `apply` removes what the old book held and the new plan does not, so a
    dropped harness really loses its files. A component whose folder vanished
    upstream is left in the book untouched: `plan_files` still refuses the run
    with `component-vanished`, the same refusal `add` gives."""
    records = read_state(target).get("components") or {}
    picked = [cid for cid in sorted(records) if cid in catalog]
    return do_install(target, catalog, picked, harnesses, dry_run,
                      guidance_basis=guidance_basis,
                      guidance_excludes=guidance_excludes)


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
              bool(args.json), target, getattr(args, "_why", "unknown"))
        return 0
    data = _replan_all(target, catalog, new,
                       bool(getattr(args, "dry_run", False)))
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"))
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
              bool(args.json), target, getattr(args, "_why", "unknown"))
        return 0
    data = _replan_all(target, catalog, harnesses,
                       bool(getattr(args, "dry_run", False)),
                       guidance_basis=value)
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"))
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
              bool(args.json), target, getattr(args, "_why", "unknown"))
        return 0
    data = _replan_all(target, catalog, harnesses,
                       bool(getattr(args, "dry_run", False)),
                       guidance_excludes=new)
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"))
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

    if head == "artifact":
        if rest and rest[0] == "exclude":
            if verb == "set":
                raise Refuse(
                    "setting-wrong-verb",
                    "the skipped-folder list holds MANY values: "
                    "`rbtv install add|rm artifact exclude <dir>`")
            if not rest[1:]:
                raise Refuse(
                    "exclude-empty",
                    f"name the folder(s) to {verb}, relative to the install "
                    "root")
            return _apply_exclude(args, target, catalog, verb, rest[1:])
        if verb != "set":
            raise Refuse(
                "setting-wrong-verb",
                "the guidance basis holds ONE value, so choosing a new one "
                f"REPLACES the old — that is a set, not an {verb}: "
                f"{SETTING_VERB['artifact']}")
        if len(rest) != 1:
            raise Refuse(
                "artifact-unknown",
                "name exactly one basis: "
                + ", ".join((*GUIDANCE_NAMES, BASIS_NONE)))
        return _apply_artifact(args, target, catalog, rest[0])

    known = ", ".join(SETTING_VERB)
    raise Refuse(
        "noun-unknown",
        f"`{head}` names no workspace setting. Known: {known}. "
        "To choose COMPONENTS, use the selector flags (-c/-m/-x/-A) with no "
        "noun — run `rbtv install " + verb + " --help`")


@mutation_locked
def cmd_set(args, target: Path, catalog: dict, shadowed: list,
            *, ask=None) -> int:
    del ask, shadowed
    noun = list(getattr(args, "noun", None) or [])
    raw_h = getattr(args, "harness", None)
    raw_g = getattr(args, "artifact", None)
    if raw_h is not None or raw_g is not None:
        if noun:
            raise Refuse("usage", "use either 'set artifact NAME' or "
                         "'set --harness ... --guidance ...', not both")
        state = read_state(target)
        current = _require_recorded(target, state)
        wanted_h = _parse_harnesses(raw_h) if raw_h is not None else current
        if not wanted_h:
            raise Refuse("harness-unknown", "--harness selected no harness")
        wanted_g = raw_g if raw_g is not None else state.get("guidance_basis")
        if wanted_h == current and wanted_g == state.get("guidance_basis"):
            data = {"ok": True, "changed": False, "dry_run": bool(args.dry_run)}
        else:
            data = _replan_all(target, catalog, wanted_h, bool(args.dry_run),
                               guidance_basis=wanted_g)
        _emit(data, bool(args.json), target, getattr(args, "_why", "unknown"))
        return 0
    if not noun:
        raise Refuse(
            "noun-missing",
            "set needs --harness, --guidance, or the legacy 'artifact NAME' form")
    return _settings_form(args, target, catalog, "set", noun)


@mutation_locked
def cmd_add(args, target: Path, catalog: dict, shadowed: list,
            *, ask=None) -> int:
    del ask, shadowed
    noun = list(getattr(args, "noun", None) or [])
    if noun and noun[0] in ("harness", "artifact"):
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
          target, getattr(args, "_why", "unknown"))
    return 0


@mutation_locked
def cmd_rm(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    del shadowed, ask
    noun = list(getattr(args, "noun", None) or [])
    if noun and noun[0] in ("harness", "artifact"):
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
              bool(args.json), target, getattr(args, "_why", "unknown"))
        return 0
    broad = bool(args.all or args.module or args.method or _has_negative(args))
    if broad and not (dry or getattr(args, "yes", False)):
        flags = ["--all"] if args.all else []
        flags += [f"--module {_quote(m)}" for m in args.module]
        flags += [f"--component {_quote(c)}" for c in args.component]
        flags += [f"--kind {_quote(m)}" for m in args.method]
        flags += [f"--exclude-module {_quote(m)}" for m in args.exclude_module]
        flags += [f"--exclude-component {_quote(c)}" for c in args.exclude_component]
        flags += [f"--exclude-kind {_quote(m)}" for m in args.exclude_method]
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
              bool(args.json), target, getattr(args, "_why", "unknown"))
        return 0
    picked, parts = _split_part_keys(keys)
    data = do_uninstall(target, catalog, picked, dry, parts=parts)
    data["selected_items"] = parts
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"))
    return 0


@mutation_locked
def cmd_dupe(args, target: Path, catalog: dict, shadowed: list,
             *, ask=None) -> int:
    del ask, shadowed
    state = read_state(target)
    records = state.get("components") or {}
    picked = [cid for cid in sorted(records) if cid in catalog]
    hs = _require_recorded(target, state)
    data = do_install(
        target, catalog, picked, hs,
        bool(getattr(args, "dry_run", False)))
    _emit(data, bool(getattr(args, "json", False)),
          target, getattr(args, "_why", "unknown"))
    return 0


def cmd_doctor(args, target: Path, catalog: dict, shadowed: list,
               *, ask=None) -> int:
    del ask
    why = getattr(args, "_why", DISCOVER_CWD) if args else DISCOVER_CWD
    repo_tree = REPO_ROOT
    mirror_tree = target / ".rbtv" / "mirror"
    data = do_doctor(target, why, catalog, shadowed, repo_tree, mirror_tree)
    if args and getattr(args, "json", False):
        print(json.dumps(data, indent=2))
    else:
        print(render_doctor(data["checks"],
                            pretty=bool(args and getattr(args, "pretty", False))))
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
    "ls": cmd_ls,
    "li": cmd_li,
    "show": cmd_show,
    "status": cmd_status,
    "set": cmd_set,
    "harness": cmd_harness,
    "artifact": cmd_artifact,
    "dupe-artifacts": cmd_dupe,
    "doctor": cmd_doctor,
    "interactive": cmd_interactive,
    "selftest": cmd_selftest,
}


def main(argv: list[str] | None = None, *, ask=None) -> int:
    parser = build_parser()
    raw = list(argv) if argv is not None else sys.argv[1:]
    as_json = "--json" in raw
    try:
        args = parser.parse_args(raw)
    except Refuse as exc:
        if as_json:
            print(json.dumps(exc.payload()))
        else:
            print(f"REFUSED [{exc.code}] {exc.message}", file=sys.stderr)
        return 2
    except SystemExit as exc:
        return int(exc.code or 0)

    if args.verb is None:
        parser.print_help()
        return 0
    if args.verb == "selftest":
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
                "or --kind")
        return handler(args, target, catalog, shadowed, ask=ask)
    except Refuse as exc:
        if as_json:
            payload = exc.payload()
            for extra in ("candidates", "preview"):
                if hasattr(exc, extra):
                    payload["refusal"][extra] = getattr(exc, extra)
            print(json.dumps(payload, indent=2))
        else:
            print(f"REFUSED [{exc.code}] {exc.message}", file=sys.stderr)
            if exc.path:
                print(f"  at: {exc.path}", file=sys.stderr)
        return 2 if exc.code == "usage" else 1
    except OSError as exc:
        where = str(locals().get("target", Path.cwd()))
        message = (f"file operation failed: {exc}. A preceding workspace write "
                   "may have applied; inspect the target before retrying")
        next_cmd = "rbtv install doctor --target " + _quote(where)
        if as_json:
            print(json.dumps({"ok": False, "refusal": {
                "code": "io-error", "message": message,
                "path": getattr(exc, "filename", None) or where,
                "next": next_cmd}}, indent=2))
        else:
            print(f"REFUSED [io-error] {message}\nnext: {next_cmd}",
                  file=sys.stderr)
        return 1
    except SystemExit as exc:
        return int(exc.code or 0)
    except KeyboardInterrupt:
        if as_json:
            print(json.dumps({"ok": False, "refusal": {
                "code": "interrupted",
                "message": "operation interrupted; inspect status before retrying"}}))
        else:
            print("\ninterrupted; inspect status before retrying",
                  file=sys.stderr)
        return 1
