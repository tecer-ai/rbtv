"""The command grammar: every verb, flag and selector the command line
accepts.
"""
from __future__ import annotations

import argparse
import difflib

from discovery import Refuse

from . import present
from .constants import (BASIS_NONE, CANONICAL_METHODS, CATALOG_TYPES,
                        GUIDANCE_NAMES, HARNESSES)
from .recovery import shell_quote


class InstallerParser(argparse.ArgumentParser):
    """Turn argparse failures into the installer's one refusal contract."""

    def error(self, message: str) -> None:
        raise Refuse("usage", message)


SETTING_VERB = {"harness": "rbtv install configure --harness <harnesses>",
                "guidance": "rbtv install configure --guidance <name>"}

# D16b — the ACTION-FIRST settings grammar, in one place so the help text, the
# `verb-moved` refusal and the dispatch can never spell it three ways.
SETTINGS_EPILOG = (
    "Change saved settings:\n"
    "  rbtv install configure --harness codex,claude --guidance CLAUDE.md\n"
    "  rbtv install status\n"
    "\nAdditional supported forms:\n"
    "  rbtv install add harness codex       (add one receiving AI tool)\n"
    "  rbtv install remove harness codex    (remove one receiving AI tool)\n"
    "  rbtv install add guidance exclude vendor\n"
    "  rbtv install remove guidance exclude vendor\n"
    "The last two commands exclude/include a folder when copying guidance.")

# The noun-led spelling D16b retired, mapped to what replaces it. Data, so the
# refusal is generated from the same table the help is, and a form that moves
# again cannot leave a stale sentence behind.
MOVED_FORMS = {
    ("harness", "add"): "add harness",
    ("harness", "rm"): "rm harness",
    ("artifact", "set"): "configure --guidance",
    ("artifact", "exclude", "add"): "add guidance exclude",
    ("artifact", "exclude", "rm"): "rm guidance exclude",
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
        rest = " ".join(shell_quote(token) for token in tokens[len(old) - 1:])
        raise Refuse(
            "verb-moved",
            f"`rbtv install {head} {' '.join(old[1:])}` moved — the ACTION "
            f"word now comes first, the same way it does for components. "
            f"Run: rbtv install {new} {rest}".rstrip())
    raise Refuse(
        "verb-moved",
        f"`rbtv install {head}` is gone. READ the workspace settings "
        "with `rbtv install status`. "
        "CHANGE this one with "
        + (SETTING_VERB["harness"] if head == "harness"
           else f"{SETTING_VERB['guidance']} or "
                "`rbtv install add|remove guidance exclude <dir>`"))


def build_parser() -> argparse.ArgumentParser:
    p = InstallerParser(prog="rbtv install", allow_abbrev=False)
    # `present.root_help()` is the ONE authored root `-h` / bare-command
    # screen (grouped by intent, approved screen 01) — argparse's own
    # subparsers listing is flat and cannot hide a retired verb's help text
    # via `help=SUPPRESS` on a subaction, so its default formatting is never
    # used for the root parser. Every per-command `-h` still uses argparse's
    # own formatter, built from each subparser's own description/epilog.
    p.format_help = present.root_help

    def title_help(sp: argparse.ArgumentParser, label: str) -> None:
        """Root help is fully custom (above); every OTHER `-h` still needs
        the shared `RBTV install — <label> help` title argparse's own
        formatter never adds — it only ever writes `usage: ...` first. This
        PREPENDS the title to argparse's own rendering rather than replacing
        it, so real usage syntax and the accepted-value tables stay exactly
        as argparse renders them; `label` always differs from root's own
        `"help"` label, so the two titles never collide."""
        base = sp.format_help
        sp.format_help = lambda: present.title(f"{label} help") + "\n\n" + base()

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
        changes = not on_verb or dest.prog.rsplit(" ", 1)[-1] in (
            "add", "remove", "rm", "configure", "update",
            "guidance", "scaffolding", "all")
        dest.add_argument(
            "--dry-run", action="store_true",
            default=(sup if on_verb else False),
            help=("preview changes without writing or removing files"
                  if changes else sup))
        dest.add_argument(
            "--details", action="store_true",
            default=(sup if on_verb else False),
            help=("list every item and file instead of counting long lists"
                  if changes else sup))

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
                    flag = option_string or f"--{self.NOUN}"
                    close = difflib.get_close_matches(part, self.VALID, n=1, cutoff=0.5)
                    hint = f" Did you mean {close[0]}?" if close else ""
                    parser.error(
                        f"{flag} {part!r} is unknown.{hint}\nAccepted {self.NOUN}s:\n"
                        + present.types_block(self.VALID))
                cur.append(part)
            setattr(namespace, self.dest, cur)

    class MethodsAction(ListAction):
        VALID = CATALOG_TYPES
        NOUN = "type"

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
            "--type", "-x", action=MethodsAction, default=[], dest="method",
            metavar="TYPE",
            help="select item types; comma-separated or repeatable: "
                 + " · ".join(CANONICAL_METHODS))
        for flag, meth in (("-xs", "skill"), ("-xr", "rule"),
                           ("-xc", "command"), ("-xa", "agent")):
            dest.add_argument(
                flag, action="append_const", const=meth, dest="method",
                help=argparse.SUPPRESS)
        dest.add_argument(
            "--exclude-type", "-nx", action=MethodsAction, default=[], dest="exclude_method",
            metavar="TYPE",
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
                 "(meta/functions#brainstorm), or whole component (meta/functions)")

    tree_flags(p, on_verb=False)
    # D16 — no global --harness/--artifact. Each setting has exactly one door:
    # the FIRST `add` (which requires it), then its own verb.
    sub = p.add_subparsers(dest="verb", metavar="COMMAND", title="commands")

    def list_flags(dest, *, installed_default: bool = False) -> None:
        dest.add_argument("query", nargs="?", default="",
                          help="exact module, component, or item name")
        dest.add_argument("--module", "-m", action=ListAction, default=[],
                          metavar="MODULE", help="filter to a module (a bundle of components)")
        dest.add_argument("--component", "-c", action=ListAction, default=[],
                          metavar="COMPONENT", help="filter to a component (related items)")
        dest.add_argument("--type", "-x", action=MethodsAction, default=[],
                          dest="method",
                          metavar="TYPE", help="filter to item types, such as skill or rule")
        dest.add_argument("--installed", action="store_true",
                          default=installed_default,
                          help="show only installed items")
        dest.add_argument("--limit", type=int, default=20,
                          help="maximum rows (default: 20)")
        dest.add_argument("--offset", type=int, default=0,
                          help="rows to skip (default: 0)")

    types_help = ("\n\nTypes (--type; comma-separated or repeatable):\n"
                 + present.types_block())

    list_help = (
        "Browse the local source catalog. No NAME shows modules; a module shows\n"
        "its components; a component shows its items; an exact item name shows\n"
        "only that item. NAME never searches descriptions — use search for\n"
        "broad discovery. Installed means recorded by this installer; use\n"
        "doctor to check the files."
        + types_help
        + "\n\nExamples:\n"
        "  rbtv install list core\n"
        "  rbtv install list core --type skill\n"
        "  rbtv install list --installed\n"
        "  rbtv install list --limit 20 --offset 20\n"
        "\nResults show the next-page command when more items match.")
    s_list = sub.add_parser(
        "list", help="browse exact module, component, or item scope", description=list_help,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    list_flags(s_list)
    s_ls = sub.add_parser("ls", description=list_help,
                         formatter_class=argparse.RawDescriptionHelpFormatter)
    list_flags(s_ls)
    s_li = sub.add_parser("li", description="Alias of list --installed.\n\n" + list_help,
                         formatter_class=argparse.RawDescriptionHelpFormatter)
    list_flags(s_li, installed_default=True)

    search_help = (
        "Search names and descriptions in the local source catalog broadly.\n"
        "Results are items with full IDs. Search does not select or install\n"
        "anything. Use list NAME when you know an exact module, component, or\n"
        "item name."
        + types_help
        + "\n\nExample: rbtv install search \"brainstorm\"")
    s_search = sub.add_parser(
        "search", help="search names and descriptions broadly",
        description=search_help, formatter_class=argparse.RawDescriptionHelpFormatter)
    list_flags(s_search)

    s_show = sub.add_parser(
        "show", help="show description, included items, and installation details",
        description=("Show the catalog description, included items or component "
                     "summaries, and\nrecorded installation details for one item, "
                     "component, or module. It\ndoes not print arbitrary source-file "
                     "contents. A short item name must be\nunique; ambiguity refuses."
                     + types_help
                     + "\n\nExamples:\n"
                     "  rbtv install show brainstorm\n"
                     "  rbtv install show meta/functions#brainstorm\n"
                     "  rbtv install show meta/functions"),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    s_show.add_argument("name", nargs="?", default="",
                        help="unique item name, full item ID, or module/component")
    s_show.add_argument("--type", "-x", action=MethodsAction, default=[],
                        dest="method",
                        metavar="TYPE", help="require this item type, such as skill")
    s_show.add_argument("--pack", action=ListAction, default=[], metavar="PACK",
                        help="show a named pack")
    s_status = sub.add_parser(
        "status", help="see the selected workspace, saved settings and installed counts",
        description="Show which workspace will be changed and its saved settings. "
                    "Use --target \"PATH\" to inspect another workspace or agent home.")

    s_add = sub.add_parser(
        "add",
        help="install items or refresh their generated files",
        description=(
            "Install named items, whole components, or a filtered selection from\n"
            "local source. Exact short names must be unique. Different filters\n"
            "narrow together; comma-separated or repeated values within one filter\n"
            "are alternatives. Exclusions leave matching items out. Nothing fetches\n"
            "a newer source version."
            + types_help
            + "\n\nFirst install in a workspace:\n"
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
            "  rbtv install add meta/functions#brainstorm --dry-run\n"
            "  rbtv install add --module core --type skill\n"
            "\nDifferent filters narrow the selection together; values within one filter\n"
            "are alternatives. For example, --module core --type skill selects only\n"
            "skills in core. Exclusions leave matching items out.\n"
            "\nChange saved settings with 'rbtv install configure --help'."))
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
    s_add.add_argument("--pack", action=ListAction, default=[], metavar="PACK",
                       help="turn this pack on; its units are added")
    selection_names(s_add)

    removal_help = (
        "Remove recorded installed items from this target. A named item or\n"
        "component needs no blanket confirmation. Broad filters (--all,\n"
        "--module, --type, or any exclusion) need --yes when they match\n"
        "installed items. Empty selections do not need confirmation. Removal\n"
        "never asks questions. Shared command shortcuts remain while another\n"
        "workspace owns them."
        + types_help
        + "\n\nRemove a named item directly:\n"
        "  rbtv install remove brainstorm\n"
        "\nPreview a larger selection, then confirm it:\n"
        "  rbtv install remove --module core --dry-run\n"
        "  rbtv install remove --module core --yes\n"
        "  rbtv install remove --all --yes")
    s_rm = sub.add_parser(
        "rm", description=removal_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False)
    selectors(s_rm)
    s_rm.add_argument("--yes", action="store_true",
                      help="confirm removal selected by module, type, all, or exclusions")
    s_rm.add_argument("--pack", action=ListAction, default=[], metavar="PACK",
                      help="turn this pack off")
    selection_names(s_rm)

    s_remove = sub.add_parser(
        "remove", help="remove installed items or components",
        description=removal_help,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    selectors(s_remove)
    s_remove.add_argument("--yes", action="store_true",
                          help="confirm removal selected by module, type, all, or exclusions")
    s_remove.add_argument("--pack", action=ListAction, default=[], metavar="PACK",
                          help="turn this pack off")
    selection_names(s_remove)

    s_set = sub.add_parser(
        "configure", help="initialize or change receiving tools and guidance settings",
        description=("Initialize a fresh target or change saved receiving tools and\n"
                     "guidance. This command selects no catalog items. Changing settings\n"
                     "regenerates files for items already selected; it does not add new\n"
                     "items. On first setup, give both --harness and --guidance. Later,\n"
                     "each supplied option replaces its saved setting; omitted settings\n"
                     "stay as they are.\n"
                     "\nExamples:\n"
                     "  rbtv install configure --harness codex,claude --guidance CLAUDE.md --dry-run\n"
                     "  rbtv install configure --harness codex,claude --guidance CLAUDE.md\n"
                     "  rbtv install configure --guidance AGENTS.md  (later change)\n"
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

    s_update = sub.add_parser(
        "update", help="regenerate selected files from local source",
        description=(
            "Regenerate the current target from RBTV source already on this "
            "machine.\nThis does not download newer RBTV, install "
            "dependencies, change its\nsource version, or select additional "
            "catalog items.\n\n"
            "Scopes split by CONTENT OWNERSHIP — guidance and scaffolding can "
            "both write\nthe SAME instruction file (e.g. AGENTS.md), each "
            "touching only the part it\nowns:\n"
            "  guidance      Copy your maintained instructions (the human "
            "text you\n"
            "                author) into each configured tool's "
            "counterpart file.\n"
            "                Leaves that file's own existing generated "
            "section exactly\n"
            "                as it is — does not rebuild it. Replaces "
            "dupe-artifacts.\n"
            "  scaffolding   Regenerate the generated instruction section "
            "in EVERY\n"
            "                configured instruction file — including a "
            "copied file like\n"
            "                AGENTS.md — plus selected skills, rules, and "
            "tool shortcuts.\n"
            "                Leaves human-authored text in those files "
            "alone; does not\n"
            "                copy or sync it from the basis.\n"
            "  all           Run scaffolding, then guidance, so both parts "
            "of every\n"
            "                configured file are current."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("Example: rbtv install update all --dry-run\n"
                "Next: rbtv install update all"))
    # D9 §9 — each scope explains its OWN effect; a single generic `update
    # -h` left guidance/scaffolding/all indistinguishable (the acceptance
    # drill's `update scope help` gap). A real subparser per scope, not a
    # `choices=` positional, is what gives each one its own `-h` text.
    update_sub = s_update.add_subparsers(dest="scope", metavar="{guidance,scaffolding,all}")
    update_sub.required = True

    def _update_scope(name: str, summary: str, body: str, example: str):
        sp = update_sub.add_parser(
            name, help=summary, description=body,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=f"Example: {example}\nNext: rbtv install doctor")
        sp.set_defaults(scope=name)
        tree_flags(sp, on_verb=True)
        return sp

    s_upd_guidance = _update_scope(
        "guidance", "copy your maintained human text to counterpart files",
        "Copy your maintained instruction file's HUMAN text (CLAUDE.md or "
        "AGENTS.md,\nwhichever you author) into each configured tool's "
        "counterpart file, stripping\nany source-specific generated content "
        "from what it copies. It leaves each\ndestination's OWN existing "
        "generated instruction section exactly as it is —\nit does NOT "
        "rebuild that section (that is update scaffolding's job, below), so "
        "a\ncounterpart file is not left fully untouched by this scope AND "
        "is not fully\nregenerated by it either. Works even with no "
        "selected source components.\nSaved guidance exclusions apply. If "
        "guidance is none, there is nothing to\ncopy. If the maintained "
        "file is missing, the command refuses and changes\nnothing. This "
        "scope does not rebuild skills, rules, or tool shortcuts.\n\n"
        "Former command: rbtv install dupe-artifacts",
        "rbtv install update guidance")
    s_upd_scaffolding = _update_scope(
        "scaffolding", "regenerate selected skills, rules, shortcuts, and every "
                       "file's generated section",
        "Regenerate files for items already selected in this target, plus "
        "the\ngenerated instruction section in EVERY configured instruction "
        "file — including\na file this workspace only ever RECEIVES as a "
        "copy, such as AGENTS.md when\nCLAUDE.md is the maintained basis. "
        "This includes selected skills, rules, and\ntool shortcuts. It "
        "preserves human-authored text in every file it touches;\nit does "
        "not copy or synchronize that text from the basis (that is update\n"
        "guidance's job, above) — so this scope and guidance can both write "
        "the SAME\nfile, each owning a different part of it. Use update all "
        "when both parts of\nevery configured file must be current.",
        "rbtv install update scaffolding")
    s_upd_all = _update_scope(
        "all", "regenerate scaffolding, then copy guidance, for every "
              "configured file",
        "Run scaffolding and guidance regeneration from local source. This\n"
        "refreshes selected installed files and the generated instruction "
        "section in\nevery configured file (scaffolding), then copies your "
        "maintained human text\ninto each counterpart file (guidance) — "
        "the two parts of the SAME file, each\nwritten by the scope that "
        "owns it. No new catalog items are selected, and no\nsaved "
        "selection expands. Validates both phases before writing: if the "
        "maintained\nguidance file is missing, refuses without partial "
        "scaffolding edits.",
        "rbtv install update all")

    # `set` and `dupe-artifacts` need no subparser: `main()` checks the verb
    # position before argparse runs, without confusing a positional name or
    # path that happens to have either spelling with a retired command.

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
    s_doc.add_argument("--cleanup-audit", action="store_true",
                       help="also inspect shortcut claims from other workspaces")
    s_selftest = sub.add_parser(
        "selftest",
        help="run installer checks in temporary workspaces",
        description="Run automated installer checks using temporary files and "
                    "isolated command shortcuts. Leaves live installations unchanged.")
    s_inter = sub.add_parser(
        "interactive", help="choose items through a guided menu",
        description="Start the guided menu. This is the only mode that asks questions. "
                    "For scripts or agents, use list, show, add and remove.")

    s_agent = sub.add_parser(
        "agent", help="install, refresh or remove an agent from its agent file",
        description=(
            "An agent is installed from its agent file into its own folder,\n"
            "<workspace>/.rbtv/agents/<agent>/: the agent file (its one source\n"
            "from then on), its launch values, settings, an ignore file for data\n"
            "tied to one machine, the files of every skill, rule, command, hook\n"
            "and MCP server its frontmatter selects, and a section in its folder\n"
            "instructions that points to the agent file. Harness, model and effort\n"
            "are chosen here and kept in launch.json, which stays the live source."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("Examples:\n"
                "  rbtv install agent add sara.md --harness claude --model sonnet-5 --effort high\n"
                "  rbtv install agent update sara\n"
                "  rbtv install agent remove sara\n"
                "Run the agent: rbtv spark sara"))
    agent_sub = s_agent.add_subparsers(dest="agent_verb",
                                       metavar="{add,update,remove}")
    agent_sub.required = True
    s_ag_add = agent_sub.add_parser(
        "add", help="install an agent from its agent file",
        description=(
            "Install the agent FILE describes. Its name comes from the file's\n"
            "frontmatter. Refuses when that agent is already installed (use\n"
            "update). --model and --effort are checked against `cast list`;\n"
            "an effort number 1-5 is stored as the model's own word for it."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("Example: rbtv install agent add sara.md --harness claude "
                "--model sonnet-5 --effort high\nNext: rbtv spark sara"))
    s_ag_add.add_argument("file", metavar="FILE", help="the agent file (agent.md)")
    s_ag_add.add_argument("--harness", required=True,
                          help="the AI tool that runs it: " + ", ".join(HARNESSES))
    s_ag_add.add_argument("--model", required=True,
                          help="a model name from `cast list`")
    s_ag_add.add_argument("--effort", required=True,
                          help="an effort word that model accepts, or 1-5")
    s_ag_update = agent_sub.add_parser(
        "update", help="regenerate an installed agent from its agent file",
        description=(
            "Re-read the agent's own agent.md and refresh everything generated\n"
            "from it: the files of the units it selects (removing those it no\n"
            "longer selects) and its folder-instructions section. Launch values,\n"
            "settings and live data are kept."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: rbtv install agent update sara")
    s_ag_update.add_argument("name", metavar="AGENT", help="the installed agent's name")
    s_ag_remove = agent_sub.add_parser(
        "remove", help="take back what the installer put in an agent's folder",
        description=(
            "Remove the units the installer placed in the agent's folder, its\n"
            "folder-instructions section, launch.json and the ignore file. The\n"
            "agent file, settings and everything the agent made stay: they are\n"
            "the agent's. The result lists what remains."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: rbtv install agent remove sara --dry-run")
    s_ag_remove.add_argument("name", metavar="AGENT", help="the installed agent's name")

    for sp, label in (
        (s_agent, "agent"), (s_ag_add, "agent add"),
        (s_ag_update, "agent update"), (s_ag_remove, "agent remove"),
        (s_list, "list"), (s_ls, "list"), (s_li, "list"),
        (s_search, "search"), (s_show, "show"), (s_status, "status"),
        (s_add, "add"), (s_rm, "remove"), (s_remove, "remove"),
        (s_set, "configure"), (s_update, "update"),
        (s_upd_guidance, "update guidance"),
        (s_upd_scaffolding, "update scaffolding"), (s_upd_all, "update all"),
        (s_doc, "doctor"), (s_selftest, "selftest"), (s_inter, "interactive"),
    ):
        title_help(sp, label)

    for s in (s_add, s_rm, s_remove, s_set, s_search,
              s_ls, s_li, s_list, s_show,
              s_status, s_doc, s_inter,
              s_h, s_art, s_ag_add, s_ag_update, s_ag_remove):
        tree_flags(s, on_verb=True)
    return p
