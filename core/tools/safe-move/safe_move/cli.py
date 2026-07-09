"""CLI dispatch for safe-move consult/act/show."""

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from safe_move import report, scope
from safe_move.act import ActError, run_act
from safe_move.consult import ConsultError, build_consult_result
from safe_move.move import MoveError
from safe_move.scope import ScopeError


def _add_shared_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scope-root",
        metavar="<path>",
        default=None,
        help="Override the search root (default: git top level of OLD).",
    )
    parser.add_argument(
        "--exclude",
        metavar="<glob>",
        action="append",
        default=[],
        help="Glob to skip during the scan. Repeatable.",
    )
    parser.add_argument(
        "--read-only",
        metavar="<glob>",
        action="append",
        default=[],
        help="Glob whose matches are always surfaced, never auto-edited. Repeatable.",
    )
    parser.add_argument(
        "--include-archive",
        action="store_true",
        default=False,
        help="Descend into --exclude paths instead of skipping them.",
    )
    parser.add_argument(
        "--include-nested-repos",
        action="store_true",
        default=False,
        help=(
            "Descend into nested git repositories under the scope root "
            "(default: skip them). Use to find cross-repo references."
        ),
    )
    parser.add_argument(
        "--generated",
        metavar="<glob>",
        action="append",
        default=[],
        help="Glob marking generated files (regenerate, don't patch). Repeatable.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help=(
            "Print the full result envelope as JSON on stdout and write no "
            "report file (default: write a report file and print a compact summary)."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="safe-move")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    consult = subparsers.add_parser("consult", help="Find and classify references.")
    _add_shared_options(consult)
    consult.add_argument("old", help="The file or folder being moved/renamed.")
    consult.add_argument("new", help="The destination path.")
    consult.set_defaults(func=_run_consult)

    act = subparsers.add_parser("act", help="Apply chosen references and move.")
    _add_shared_options(act)
    act.add_argument(
        "--apply",
        metavar="<id:hash>[,<id:hash>...]",
        nargs="?",
        const="",
        default="",
        required=True,
        help=(
            "Comma-separated id:hash pairs of surfaced refs to ALSO apply. "
            "Auto-class refs are applied automatically; an empty value applies "
            "the auto fixes and performs the move."
        ),
    )
    act.add_argument("old", help="The file or folder being moved/renamed.")
    act.add_argument("new", help="The destination path.")
    act.set_defaults(func=_run_act)

    show = subparsers.add_parser(
        "show", help="Slice records back out of a consult/act report file."
    )
    show.add_argument("report", help="Path to a report file written by consult/act.")
    show.add_argument(
        "--id",
        metavar="<ref-id>",
        action="append",
        default=[],
        dest="ids",
        help="Print the full record(s) with this id. Repeatable.",
    )
    show.add_argument(
        "--class",
        metavar="<class>",
        choices=["auto", "surface", "protected"],
        default=None,
        dest="ref_class",
        help="Print the full records of this class.",
    )
    show.add_argument(
        "--file",
        metavar="<glob>",
        default=None,
        dest="file_glob",
        help="Print the full records whose file matches this glob.",
    )
    show.add_argument(
        "--warnings",
        action="store_true",
        default=False,
        help="Print the warnings list as JSON.",
    )
    show.set_defaults(func=_run_show)

    return parser


def _run_consult(args: argparse.Namespace) -> int:
    try:
        result = build_consult_result(
            args.old,
            args.new,
            scope_root=args.scope_root,
            exclude=args.exclude,
            read_only=args.read_only,
            include_archive=args.include_archive,
            descend_nested_repos=args.include_nested_repos,
            generated=args.generated,
        )
    except (ConsultError, ScopeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    report_path = _write_report_safe("consult", args, result)
    print(report.format_consult_summary(result, args.old, args.new, report_path))
    if report_path is None:
        # Never lose information: with no report file, fall back to the full envelope.
        print(json.dumps(result, indent=2))
    return 0


def _run_act(args: argparse.Namespace) -> int:
    try:
        result = run_act(
            args.old,
            args.new,
            scope_root=args.scope_root,
            exclude=args.exclude,
            read_only=args.read_only,
            include_archive=args.include_archive,
            descend_nested_repos=args.include_nested_repos,
            generated=args.generated,
            apply=args.apply,
        )
    except (ActError, ConsultError, MoveError, ScopeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = dataclasses.asdict(result)
    if args.json:
        print(json.dumps(payload, indent=2))
        return result.exit_code

    report_path = _write_report_safe("act", args, payload)
    print(report.format_act_summary(result, report_path))
    if report_path is None:
        print(json.dumps(payload, indent=2))
    return result.exit_code


def _run_show(args: argparse.Namespace) -> int:
    try:
        output, code = report.run_show(
            args.report,
            ids=args.ids,
            ref_class=args.ref_class,
            file_glob=args.file_glob,
            warnings_only=args.warnings,
        )
    except report.ReportError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(output)
    return code


def _write_report_safe(kind: str, args: argparse.Namespace, payload) -> Path | None:
    """Write the report file; on failure warn and return None (caller falls back)."""
    try:
        try:
            root = scope.resolve_scope_root(args.old, args.scope_root)
        except ScopeError:
            # After ``act`` the old path is gone — resolve from the destination.
            root = scope.resolve_scope_root(args.new, args.scope_root)
        return report.write_report(kind, args.old, args.new, root, payload)
    except (OSError, ScopeError) as exc:
        print(f"warning: could not write report file: {exc}", file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
