"""CLI dispatch for safe-move consult/act."""

import argparse
import json
import sys

from safe_move.act import ActError, format_action_log, run_act
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
        "--generated",
        metavar="<glob>",
        action="append",
        default=[],
        help="Glob marking generated files (regenerate, don't patch). Repeatable.",
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
            generated=args.generated,
        )
    except (ConsultError, ScopeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

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
            generated=args.generated,
            apply=args.apply,
        )
    except (ActError, ConsultError, MoveError, ScopeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(format_action_log(result))
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
