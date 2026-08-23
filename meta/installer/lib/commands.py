"""One handler per verb, and the dispatch that runs them."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from discovery import Refuse, scan_all

from .constants import (
    BASIS_NONE,
    GUIDANCE_NAMES,
    HARNESSES,
    REPO_ROOT,
    STATE_REL,
)
from .catalog import module_id
from .guidance import _norm_prefix
from .target import DISCOVER_CWD, DISCOVER_FLAG, discover_target
from .state import book_harnesses, read_state
from .selection import (
    _expand_nums,
    _has_negative,
    _norm_comp,
    _split_part_keys,
    part_key,
    read_index,
    resolve_selection,
    scan_fingerprint,
)
from .operations import do_install, do_uninstall
from .listing import build_ls, do_list, print_li, print_ls, write_visible_index
from .doctor import do_doctor, doctor_exit, render_doctor
from .report import print_result
from .interactive import interactive
from .parser import SETTING_VERB, _refuse_moved, build_parser


def _parse_harnesses(raw: str) -> list[str]:
    """A comma-separated `--harness` value -> the canonical, filtered list."""
    picked = [h.strip() for h in raw.split(",") if h.strip()]
    unknown = [h for h in picked if h not in HARNESSES]
    if unknown:
        raise Refuse("harness-unknown",
                     f"unknown harness(es): {', '.join(unknown)} — known: "
                     + ", ".join(HARNESSES))
    return [h for h in HARNESSES if h in picked]


def _emit(data: dict, as_json: bool) -> None:
    print(json.dumps(data, indent=2)) if as_json else print_result(data)


def _ls_filters(args, catalog: dict, target: Path) -> dict:
    comps = list(getattr(args, "component", None) or [])
    drop_c = list(getattr(args, "exclude_component", None) or [])
    fp = scan_fingerprint(catalog)
    idx = read_index(target)
    # No `is this numeric?` gate here: _expand_nums hands every non-index token
    # straight back, and a gate that has to recognise index tokens ITSELF is a
    # second copy of that rule — the copy that missed ranges when they landed.
    comps = _expand_nums(comps, "component", idx, fp)
    drop_c = _expand_nums(drop_c, "component", idx, fp)
    return dict(
        modules=list(getattr(args, "module", None) or []),
        methods=list(getattr(args, "method", None) or []),
        components=comps,
        exclude_modules=list(getattr(args, "exclude_module", None) or []),
        exclude_methods=list(getattr(args, "exclude_method", None) or []),
        exclude_components=drop_c,
    )


def _li_filter(data: dict, catalog: dict, args) -> dict:
    want_m = {module_id(m) for m in (getattr(args, "module", None) or [])}
    want_c = {_norm_comp(c) for c in (getattr(args, "component", None) or [])}
    drop_m = {module_id(m) for m in (getattr(args, "exclude_module", None) or [])}
    drop_c = {_norm_comp(c) for c in (getattr(args, "exclude_component", None) or [])}
    want_x = set(getattr(args, "method", None) or [])
    drop_x = set(getattr(args, "exclude_method", None) or [])
    if not (want_m or want_c or drop_m or drop_c or want_x or drop_x):
        return data
    kept = {}
    for cid, rec in data["components"].items():
        mod = rec.get("module") or cid.split("/")[0]
        if want_m and module_id(mod) not in want_m:
            continue
        if drop_m and module_id(mod) in drop_m:
            continue
        if want_c and cid not in want_c:
            continue
        if drop_c and cid in drop_c:
            continue
        rec = dict(rec)
        if want_x or drop_x:
            parts = {pid: p for pid, p in (rec.get("parts") or {}).items()
                     if isinstance(p, dict)
                     and (not want_x or p.get("method") in want_x)
                     and p.get("method") not in drop_x}
            rec["parts"] = parts
        kept[cid] = rec
    out = dict(data)
    out["components"] = kept
    return out


def confirm_removal(keys, *, dry_run: bool, ask=None) -> bool:
    """R7 guard: print the full resolved removal list. Dry-run never asks."""
    print("DRY RUN — would remove:" if dry_run else "will remove:")
    for k in sorted(keys):
        print(f"  {k}")
    if dry_run:
        return True
    fn = ask or input
    try:
        ans = fn("Proceed? [y/N]: ")
    except EOFError:
        ans = ""
    return str(ans).strip().lower() in ("y", "yes")


def cmd_ls(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    del ask
    state = read_state(target)
    data = build_ls(catalog, shadowed, state, **_ls_filters(args, catalog, target))
    write_visible_index(target, data["index"])
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
    else:
        print_ls(data, pretty=bool(getattr(args, "pretty", False)))
    return 0


def cmd_li(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    del ask, shadowed
    data = do_list(target, catalog)
    data = _li_filter(data, catalog, args)
    n, k = {}, 1
    for cid in data["components"]:
        n[str(k)] = {"kind": "component", "id": cid}
        k += 1
    for cid, rec in data["components"].items():
        for pid in sorted(rec.get("parts") or {}):
            n[str(k)] = {"kind": "part", "id": part_key(cid, pid)}
            k += 1
    write_visible_index(target, {"fingerprint": scan_fingerprint(catalog),
                                 "n": n})
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
    else:
        print_li(data, pretty=bool(getattr(args, "pretty", False)))
    return 0


def _gate_add_harness(target: Path, state: dict, raw: str | None) -> list[str]:
    """D16 — `--harness` is answerable exactly once, on the first `add`."""
    booked = book_harnesses(state)
    if booked is not None and raw is not None:
        raise Refuse(
            "setting-locked",
            "--harness is a workspace setting and this workspace already has "
            f"one: {', '.join(booked) or '(none)'}. `add` chooses COMPONENTS, "
            f"never harnesses — change the set with `{SETTING_VERB['harness']}`",
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
        raise Refuse(
            "setting-locked",
            "--artifact is a workspace setting and this workspace already has "
            f"one: {state.get('guidance_basis') or BASIS_NONE}. Change it with "
            f"`{SETTING_VERB['artifact']}`",
            str(target / STATE_REL))
    if not booked and raw is None:
        raise Refuse(
            "artifact-required",
            "first install on this workspace: pass --artifact with "
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
            "installed here. Run `rbtv install add` first; its --harness and "
            "--artifact flags are where the settings are chosen",
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
        print(f"no change — this workspace already targets {', '.join(new)}")
        return 0
    data = _replan_all(target, catalog, new,
                       bool(getattr(args, "dry_run", False)))
    _emit(data, bool(getattr(args, "json", False)))
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
        print(f"no change — the basis already is {value}")
        return 0
    data = _replan_all(target, catalog, harnesses,
                       bool(getattr(args, "dry_run", False)),
                       guidance_basis=value)
    _emit(data, bool(getattr(args, "json", False)))
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
        print("no change — " + (", ".join(new) or "nothing") + " excluded")
        return 0
    data = _replan_all(target, catalog, harnesses,
                       bool(getattr(args, "dry_run", False)),
                       guidance_excludes=new)
    _emit(data, bool(getattr(args, "json", False)))
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


def cmd_set(args, target: Path, catalog: dict, shadowed: list,
            *, ask=None) -> int:
    del ask, shadowed
    noun = list(getattr(args, "noun", None) or [])
    if not noun:
        raise Refuse(
            "noun-missing",
            f"`set` needs the setting to change: {SETTING_VERB['artifact']}")
    return _settings_form(args, target, catalog, "set", noun)


def cmd_add(args, target: Path, catalog: dict, shadowed: list,
            *, ask=None) -> int:
    del ask, shadowed
    noun = list(getattr(args, "noun", None) or [])
    if noun:
        return _settings_form(args, target, catalog, "add", noun)
    if not _has_selectors(args):
        raise SystemExit(2)
    args.index = read_index(target)
    keys = resolve_selection(args, catalog, None)
    picked, parts = _split_part_keys(keys)
    state = read_state(target)
    harnesses = _gate_add_harness(target, state, getattr(args, "harness", None))
    basis = _gate_add_artifact(target, state, getattr(args, "artifact", None))
    data = do_install(
        target, catalog, picked, harnesses,
        bool(getattr(args, "dry_run", False)),
        guidance_basis=basis,
        parts=parts,
        write_path=bool(getattr(args, "write_path", False)))
    _emit(data, bool(getattr(args, "json", False)))
    return 0


def cmd_rm(args, target: Path, catalog: dict, shadowed: list,
           *, ask=None) -> int:
    del shadowed
    noun = list(getattr(args, "noun", None) or [])
    if noun:
        return _settings_form(args, target, catalog, "rm", noun)
    if not _has_selectors(args):
        raise SystemExit(2)
    args.index = read_index(target)
    book = read_state(target).get("components")
    keys = resolve_selection(args, catalog, book)
    dry = bool(getattr(args, "dry_run", False))
    if _has_negative(args):
        if not confirm_removal(keys, dry_run=dry, ask=ask):
            print("cancelled")
            return 0
    picked, parts = _split_part_keys(keys)
    data = do_uninstall(target, catalog, picked, dry, parts=parts)
    _emit(data, bool(getattr(args, "json", False)))
    return 0


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
    _emit(data, bool(getattr(args, "json", False)))
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
    "ls": cmd_ls,
    "li": cmd_li,
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
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    if args.verb == "selftest":
        from selftest.runner import selftest
        return selftest()

    as_json = bool(getattr(args, "json", False))
    if getattr(args, "target", None) is None:
        target, why = discover_target(Path.cwd())
        if args.verb != "doctor":
            print(f"target: {target}  (discovered by {why}; pass --target to "
                  f"override)", file=sys.stderr)
    else:
        target = Path(args.target).expanduser()
        why = DISCOVER_FLAG
    args._why = why
    repo_tree = REPO_ROOT
    mirror_tree = target / ".rbtv" / "mirror"

    try:
        catalog, shadowed = scan_all(mirror_tree, repo_tree)
        if args.verb in (None, "interactive"):
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
        if (args.verb in ("add", "rm")
                and not getattr(args, "noun", None)
                and not _has_selectors(args)):
            parser.error(
                f"{args.verb} needs -A or -m/-c/-x for components, or a "
                f"setting: {args.verb} harness <h> · {args.verb} artifact "
                "exclude <dir>")
        return handler(args, target, catalog, shadowed, ask=ask)
    except Refuse as exc:
        if as_json:
            print(json.dumps(exc.payload(), indent=2))
        else:
            print(f"REFUSED [{exc.code}] {exc.message}", file=sys.stderr)
            if exc.path:
                print(f"  at: {exc.path}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        return int(exc.code or 0)
    except KeyboardInterrupt:
        print("\ncancelled", file=sys.stderr)
        return 1
