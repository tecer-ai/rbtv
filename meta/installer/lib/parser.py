"""The command grammar: every verb, flag and selector the command line
accepts.
"""
from __future__ import annotations

import argparse

from discovery import Refuse

from .constants import BASIS_NONE, CANONICAL_METHODS, GUIDANCE_NAMES, HARNESSES


class InstallerParser(argparse.ArgumentParser):
    """Turn argparse failures into the installer's one refusal contract."""

    def error(self, message: str) -> None:
        raise Refuse("usage", message)


SETTING_VERB = {"harness": "rbtv install set --harness <harnesses>",
                "artifact": "rbtv install set --guidance <name>"}

# D16b — the ACTION-FIRST settings grammar, in one place so the help text, the
# `verb-moved` refusal and the dispatch can never spell it three ways.
SETTINGS_EPILOG = (
    "Change saved settings:\n"
    "  rbtv install set --harness codex,claude --guidance CLAUDE.md\n"
    "  rbtv install status\n"
    "\nAdditional supported forms:\n"
    "  rbtv install add harness codex       (add one receiving AI tool)\n"
    "  rbtv install remove harness codex    (remove one receiving AI tool)\n"
    "  rbtv install add artifact exclude vendor\n"
    "  rbtv install remove artifact exclude vendor\n"
    "The last two commands exclude/include a folder when copying guidance.")

# The noun-led spelling D16b retired, mapped to what replaces it. Data, so the
# refusal is generated from the same table the help is, and a form that moves
# again cannot leave a stale sentence behind.
MOVED_FORMS = {
    ("harness", "add"): "add harness",
    ("harness", "rm"): "rm harness",
    ("artifact", "set"): "set artifact",
    ("artifact", "exclude", "add"): "add artifact exclude",
    ("artifact", "exclude", "rm"): "rm artifact exclude",
}


def _refuse_moved(head: str, tokens: list[str]) -> None:
    """D16b — the noun-led spelling is gone; say what replaces THIS command.

    It parses (the old ops land in a catch-all positional) for exactly one
    reason: an argparse usage dump tells a human that `add` is not a valid
    something, which is both true and useless. This names the new form with
    their own arguments already in it, ready to paste.
    """
    for old, new in MOVED_FORMS.items():
        if old[0] != head or list(old[1:]) != tokens[:len(old) - 1]:
            continue
        rest = " ".join(tokens[len(old) - 1:])
        raise Refuse(
            "verb-moved",
            f"`rbtv install {head} {' '.join(old[1:])}` moved — the ACTION "
            f"word now comes first, the same way it does for components "
            f"(D16b). Run: rbtv install {new} {rest}".rstrip())
    raise Refuse(
        "verb-moved",
        f"`rbtv install {head}` is gone. READ the workspace settings "
        "with `rbtv install status`. "
        "CHANGE this one with "
        + (SETTING_VERB["harness"] if head == "harness"
           else f"{SETTING_VERB['artifact']} or "
                "`rbtv install add|rm artifact exclude <dir>`"))


def build_parser() -> argparse.ArgumentParser:
    p = InstallerParser(
        prog="rbtv install",
        description=(
            "Find, install and remove skills, rules and tools.\n"
            "Humans and agents use the same commands; add --json for structured output.\n"
            "Only 'interactive' asks questions.\n"
            "\nStart here:\n"
            "  rbtv install status\n"
            "  rbtv install list brainstorm\n"
            "  rbtv install show brainstorm\n"
            "  rbtv install add brainstorm --harness codex --guidance none\n"
            "  rbtv install list --installed\n"
            "  rbtv install remove brainstorm\n"
            "\nThe add example chooses Codex and no guidance-file copying.\n"
            "Use --target \"PATH\" to manage another workspace or agent home."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog=("More help: rbtv install COMMAND --help\n"
                "Shortcuts still accepted: ls = list; li = list --installed; rm = remove.\n"
                "Exit codes: 0 success; 1 refused or failed; 2 invalid command arguments."))

    def tree_flags(dest, *, on_verb: bool) -> None:
        sup = argparse.SUPPRESS
        dest.add_argument(
            "--target", default=(sup if on_verb else None),
            help="workspace or agent-home folder; overrides IGNITE_AGENT_HOME "
                 "and discovery from the current folder")
        dest.add_argument(
            "--json", action="store_true",
            default=(sup if on_verb else False),
            help="return structured JSON for scripts and agents")
        dest.add_argument(
            "--pretty", action="store_true",
            default=(sup if on_verb else False),
            help=("use colour in doctor output" if not on_verb
                  or dest.prog.endswith(" doctor") else sup))
        dest.add_argument(
            "--dry-run", action="store_true",
            default=(sup if on_verb else False),
            help=("preview changes without writing or removing files" if not on_verb
                  or dest.prog.rsplit(" ", 1)[-1] in
                  ("add", "remove", "rm", "set", "dupe-artifacts") else sup))

    class ListAction(argparse.Action):
        """One selector token per comma, appended across repeats.

        `-c a,b` and `-c a -c b` produce the same list, so a caller removing
        or installing many parts writes ONE command instead of one per part.
        Repeat-only was the shape before, and it made a ten-component `rm`
        ten invocations. Safe because no module, component or method id
        carries a comma — `-x` has split this way since it shipped, and this
        only widens the same rule to the other four selectors.
        """

        VALID: tuple = ()
        NOUN = "value"

        def __call__(self, parser, namespace, values, option_string=None):
            cur = getattr(namespace, self.dest) or []
            for part in str(values).split(","):
                part = part.strip()
                if not part:
                    continue
                if self.VALID and part not in self.VALID:
                    parser.error(
                        f"unknown {self.NOUN} {part!r} (want "
                        + " · ".join(self.VALID) + ")")
                cur.append(part)
            setattr(namespace, self.dest, cur)

    class MethodsAction(ListAction):
        VALID = CANONICAL_METHODS
        NOUN = "method"

    def selectors(dest) -> None:
        dest.add_argument(
            "--all", "-A", action="store_true", dest="all",
            help="select all available items for add, or all installed items for remove")
        dest.add_argument(
            "--module", "-m", action=ListAction, default=[], dest="module",
            metavar="MODULE",
            help="select a module (a bundle of components); comma-separated or repeatable")
        dest.add_argument(
            "--component", "-c", action=ListAction, default=[], dest="component",
            metavar="COMPONENT",
            help="select a component (a group of related items); accepts full item IDs too")
        dest.add_argument(
            "--kind", "-x", action=MethodsAction, default=[], dest="method",
            metavar="KIND",
            help="select item types; comma-separated or repeatable: "
                 + " · ".join(CANONICAL_METHODS))
        for flag, meth in (("-xs", "skill"), ("-xr", "rule"),
                           ("-xc", "command"), ("-xsa", "sub-agent")):
            dest.add_argument(
                flag, action="append_const", const=meth, dest="method",
                help=argparse.SUPPRESS)
        dest.add_argument(
            "--exclude-kind", "-nx", action=MethodsAction, default=[], dest="exclude_method",
            metavar="KIND",
            help="leave these item types out of the selection")
        dest.add_argument(
            "--exclude-module", "-nm", action=ListAction, default=[], dest="exclude_module",
            metavar="MODULE",
            help="leave these modules out of the selection")
        dest.add_argument(
            "--exclude-component", "-nc", action=ListAction, default=[], dest="exclude_component",
            metavar="COMPONENT",
            help="leave these components out of the selection")

    def selection_names(dest) -> None:
        dest.add_argument(
            "noun", nargs="*", metavar="NAME",
            help="item name (brainstorm), full item ID "
                 "(core/functions#brainstorm), or whole component (core/functions)")

    tree_flags(p, on_verb=False)
    # D16 — no global --harness/--artifact. Each setting has exactly one door:
    # the FIRST `add` (which requires it), then its own verb.
    sub = p.add_subparsers(dest="verb", metavar="COMMAND", title="commands")

    def list_flags(dest, *, installed_default: bool = False) -> None:
        dest.add_argument("query", nargs="?", default="",
                          help="words to search in names and descriptions")
        dest.add_argument("--module", "-m", action=ListAction, default=[],
                          metavar="MODULE", help="filter to a module (a bundle of components)")
        dest.add_argument("--component", "-c", action=ListAction, default=[],
                          metavar="COMPONENT", help="filter to a component (related items)")
        dest.add_argument("--kind", "-x", action=MethodsAction, default=[],
                          dest="method",
                          metavar="KIND", help="filter to item types, such as skill or rule")
        dest.add_argument("--installed", action="store_true",
                          default=installed_default,
                          help="show only installed items")
        dest.add_argument("--limit", type=int, default=20,
                          help="maximum rows (default: 20)")
        dest.add_argument("--offset", type=int, default=0,
                          help="rows to skip (default: 0)")

    list_help = (
        "Search item names and descriptions. Copy an item's full ID into show, add or remove.\n"
        "Installed means recorded by this installer; use doctor to check the files.\n"
        "\nExamples:\n"
        "  rbtv install list\n"
        "  rbtv install list \"browser automation\"\n"
        "  rbtv install list --installed\n"
        "  rbtv install list --module core --kind skill\n"
        "  rbtv install list --limit 20 --offset 20\n"
        "\nResults show the next-page command when more items match.")
    s_list = sub.add_parser(
        "list", help="find available or installed items", description=list_help,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    list_flags(s_list)
    s_ls = sub.add_parser("ls", description=list_help,
                         formatter_class=argparse.RawDescriptionHelpFormatter)
    list_flags(s_ls)
    s_li = sub.add_parser("li", description="Alias of list --installed.\n\n" + list_help,
                         formatter_class=argparse.RawDescriptionHelpFormatter)
    list_flags(s_li, installed_default=True)

    s_show = sub.add_parser(
        "show", help="inspect an item before installing or removing it",
        description=("Show one item's description, source and recorded installation state.\n"
                     "Ambiguous names return choices; use the full ID to choose one.\n"
                     "\nExamples:\n"
                     "  rbtv install show brainstorm\n"
                     "  rbtv install show core/functions#brainstorm\n"
                     "  rbtv install show core/functions"),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    s_show.add_argument("name", help="unique item name, full item ID, or module/component")
    s_show.add_argument("--kind", "-x", action=MethodsAction, default=[],
                        dest="method",
                        metavar="KIND", help="require this item type, such as skill")
    s_status = sub.add_parser(
        "status", help="see the selected workspace, saved settings and installed counts",
        description="Show which workspace will be changed and its saved settings. "
                    "Use --target \"PATH\" to inspect another workspace or agent home.")

    s_add = sub.add_parser(
        "add",
        help="install items or refresh their generated files",
        description=(
            "Install one or more named items. Ambiguous names refuse with choices.\n"
            "\nFirst install in a workspace:\n"
            "  rbtv install add brainstorm --harness codex --guidance none\n"
            "\n--harness chooses which AI tools receive files.\n"
            "--guidance chooses the instruction file you maintain; the installer\n"
            "generates the other tool's copy. Use none to disable that copying.\n"
            "These settings are saved. Later adds can omit them or repeat the same values."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog=(
            "Examples after setup:\n"
            "  rbtv install add brainstorm challenging\n"
            "  rbtv install add core/functions#brainstorm --dry-run\n"
            "  rbtv install add --module core --kind skill\n"
            "\nDifferent filters narrow the selection together; values within one filter\n"
            "are alternatives. For example, --module core --kind skill selects only\n"
            "skills in core. Exclusions leave matching items out.\n"
            "\nChange saved settings with 'rbtv install set --help'."))
    selectors(s_add)
    s_add.add_argument(
        "--harness", default=argparse.SUPPRESS,
        help="AI tools receiving files; required on first add: "
             + ",".join(HARNESSES) + " (comma-separated)")
    s_add.add_argument(
        "--guidance", dest="artifact",
        default=argparse.SUPPRESS,
        choices=(*GUIDANCE_NAMES, BASIS_NONE),
        help="instruction file you maintain, or none to disable copying; required on first add")
    s_add.add_argument("--artifact", dest="artifact",
                       default=argparse.SUPPRESS,
                       choices=(*GUIDANCE_NAMES, BASIS_NONE),
                       help=argparse.SUPPRESS)
    selection_names(s_add)

    removal_help = (
        "Remove installed items from the selected workspace.\n"
        "\nRemove a named item directly:\n"
        "  rbtv install remove brainstorm\n"
        "\nPreview a larger selection, then confirm it:\n"
        "  rbtv install remove --module core --dry-run\n"
        "  rbtv install remove --module core --yes\n"
        "  rbtv install remove --all --yes\n"
        "\n--yes is required when matching installed items using --all, --module,\n"
        "--kind, or any --exclude-* option. It is not required for --dry-run,\n"
        "a selection using only names/--component, or an empty selection.\n"
        "Removal never prompts.\n"
        "Shared command shortcuts stay until their last workspace removes them.")
    s_rm = sub.add_parser(
        "rm", description=removal_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False)
    selectors(s_rm)
    s_rm.add_argument("--yes", action="store_true",
                      help="confirm removal selected by module, kind, all, or exclusions")
    selection_names(s_rm)

    s_remove = sub.add_parser(
        "remove", help="remove installed items or components",
        description=removal_help,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    selectors(s_remove)
    s_remove.add_argument("--yes", action="store_true",
                          help="confirm removal selected by module, kind, all, or exclusions")
    selection_names(s_remove)

    s_set = sub.add_parser(
        "set", help="change the receiving AI tools or instruction-file settings",
        description=("Change settings for a workspace that already has an installation.\n"
                     "The installer updates existing installed files to match.\n"
                     "\nExamples:\n"
                     "  rbtv install set --harness codex,claude --dry-run\n"
                     "  rbtv install set --harness codex,claude\n"
                     "  rbtv install set --guidance CLAUDE.md\n"
                     "\n--harness replaces the complete list of receiving AI tools.\n"
                     "--guidance names the instruction file you maintain; none disables copying."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=SETTINGS_EPILOG,
        allow_abbrev=False)
    s_set.add_argument("noun", nargs="*", metavar="NOUN",
                       help=argparse.SUPPRESS)
    s_set.add_argument("--harness", help="replace the list of AI tools: " + ",".join(HARNESSES))
    s_set.add_argument("--guidance", dest="artifact",
                       choices=(*GUIDANCE_NAMES, BASIS_NONE),
                       help="choose the instruction file to copy from, or none")
    s_set.add_argument("--artifact", dest="artifact",
                       choices=(*GUIDANCE_NAMES, BASIS_NONE),
                       help=argparse.SUPPRESS)

    s_dupe = sub.add_parser(
        "dupe-artifacts",
        help="refresh generated instruction files using saved settings",
        description="Refresh generated instruction files. To change which instruction "
                    "file you maintain, use 'rbtv install set --guidance NAME'.")

    # D16c — HIDDEN, and hidden is the point: no `help=` keyword means
    # argparse never lists them, so the menu carries only verbs that DO
    # something. They still parse, purely so every retired spelling —
    # `harness`, `harness add`, `artifact set` — lands on a refusal that
    # names where it went, rather than on `invalid choice: 'harness'`.
    s_h = sub.add_parser("harness", allow_abbrev=False)
    s_h.add_argument("moved", nargs="*", help=argparse.SUPPRESS)

    s_art = sub.add_parser("artifact", allow_abbrev=False)
    s_art.add_argument("moved", nargs="*", help=argparse.SUPPRESS)

    s_doc = sub.add_parser(
        "doctor",
        help="check installation health and show recovery steps",
        description="Check the workspace, installed files and shared command shortcuts. "
                    "Reports problems and recovery steps; changes no files.")
    sub.add_parser(
        "selftest",
        help="run installer checks in temporary workspaces",
        description="Run automated installer checks using temporary files and "
                    "isolated command shortcuts. Leaves live installations unchanged.")
    s_inter = sub.add_parser(
        "interactive", help="choose items through a guided menu",
        description="Start the guided menu. This is the only mode that asks questions. "
                    "For scripts or agents, use list, show, add and remove.")

    for s in (s_add, s_rm, s_remove, s_set, s_ls, s_li, s_list, s_show,
              s_status, s_dupe, s_doc, s_inter,
              s_h, s_art):
        tree_flags(s, on_verb=True)
    return p
