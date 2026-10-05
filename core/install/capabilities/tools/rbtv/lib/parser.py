"""The command grammar: every verb, flag and selector the command line
accepts. The help text of each verb lives in `help_pages.py`; this file
says only what the grammar accepts.
"""
from __future__ import annotations

import argparse
import difflib

from discovery import Refuse

from . import present
from .constants import BASIS_NONE, CATALOG_TYPES, GUIDANCE_NAMES, HARNESSES, VERSION
from .help_pages import PAGES
from .subagents import ON_FORM


class InstallerParser(argparse.ArgumentParser):
    """Turn argparse failures into the installer's one refusal contract."""

    def error(self, message: str) -> None:
        # The parser that failed names its own command: `rbtv update -h` for
        # `rbtv update`, `rbtv -h` for an unknown verb.
        exc = Refuse("usage", message)
        exc.next = f"{self.prog} -h"
        raise exc


SETTING_VERB = {"harness": "rbtv configure --harness <harnesses>",
                "guidance": "rbtv configure --guidance <name>"}


def build_parser() -> argparse.ArgumentParser:
    p = InstallerParser(prog="rbtv", allow_abbrev=False)
    # Every `-h` prints the approved page for its command path (help_pages.py).
    # argparse still parses the grammar; the page says what it accepts.
    p.format_help = lambda: PAGES["root"]
    p.add_argument("--version", action="version", version=VERSION)

    def page(sp: argparse.ArgumentParser, key: str) -> None:
        sp.format_help = lambda: PAGES[key]

    def tree_flags(dest, *, on_verb: bool) -> None:
        """The flags every verb shares. A read verb accepts --dry-run and
        --details too and changes nothing, as it always has."""
        sup = argparse.SUPPRESS
        dest.add_argument("--target", default=(sup if on_verb else None))
        dest.add_argument("--json", action="store_true",
                          default=(sup if on_verb else False))
        dest.add_argument("--pretty", action="store_true",
                          default=(sup if on_verb else False))
        dest.add_argument("--dry-run", action="store_true",
                          default=(sup if on_verb else False))
        dest.add_argument("--details", action="store_true",
                          default=(sup if on_verb else False))

    class ListAction(argparse.Action):
        """One selector token per comma, appended across repeats.

        `-c a,b` and `-c a -c b` produce the same list, so a caller removing
        or installing many parts writes ONE command instead of one per part.
        Safe because no module, component or type id carries a comma.
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
        dest.add_argument("--all", "-A", action="store_true", dest="all")
        dest.add_argument("--module", "-m", action=ListAction, default=[], dest="module",
                          metavar="MODULE")
        dest.add_argument("--component", "-c", action=ListAction, default=[],
                          dest="component", metavar="COMPONENT")
        dest.add_argument("--type", "-x", action=MethodsAction, default=[], dest="method",
                          metavar="TYPE")
        dest.add_argument("--exclude-type", action=MethodsAction, default=[],
                          dest="exclude_method", metavar="TYPE")
        dest.add_argument("--exclude-module", action=ListAction, default=[],
                          dest="exclude_module", metavar="MODULE")
        dest.add_argument("--exclude-component", action=ListAction, default=[],
                          dest="exclude_component", metavar="COMPONENT")

    # Verbs are registered in the order the refusal for an unknown verb lists
    # them (approved screen 102).
    tree_flags(p, on_verb=False)
    sub = p.add_subparsers(dest="verb", metavar="COMMAND")

    def list_flags(dest, *, installed_default: bool = False) -> None:
        dest.add_argument("--module", "-m", action=ListAction, default=[], metavar="MODULE")
        dest.add_argument("--component", "-c", action=ListAction, default=[],
                          metavar="COMPONENT")
        dest.add_argument("--type", "-x", action=MethodsAction, default=[],
                          dest="method", metavar="TYPE")
        dest.add_argument("--installed", action="store_true", default=installed_default)
        dest.add_argument("--limit", type=int, default=20)
        dest.add_argument("--offset", type=int, default=0)
        dest.add_argument("--full", action="store_true")
        tree_flags(dest, on_verb=True)

    s_list = sub.add_parser("list")
    list_flags(s_list)
    s_list.add_argument("query", nargs="?", default="", metavar="NAME")
    page(s_list, "list")
    s_ls = sub.add_parser("ls")
    list_flags(s_ls)
    s_ls.add_argument("query", nargs="?", default="", metavar="NAME")
    page(s_ls, "list")
    s_li = sub.add_parser("li")
    list_flags(s_li, installed_default=True)
    s_li.add_argument("query", nargs="?", default="", metavar="NAME")
    page(s_li, "list")

    s_search = sub.add_parser("search")
    list_flags(s_search)
    s_search.add_argument("query", nargs="?", default="", metavar="WORDS")
    page(s_search, "search")

    s_show = sub.add_parser("show")
    s_show.add_argument("name", nargs="?", default="", metavar="NAME")
    s_show.add_argument("--type", "-x", action=MethodsAction, default=[],
                        dest="method", metavar="TYPE")
    s_show.add_argument("--pack", action=ListAction, default=[], metavar="PACK")
    s_show.add_argument("--full", action="store_true")
    tree_flags(s_show, on_verb=True)
    page(s_show, "show")

    s_status = sub.add_parser("status")
    tree_flags(s_status, on_verb=True)
    page(s_status, "status")

    s_add = sub.add_parser("add")
    selectors(s_add)
    s_add.add_argument("--pack", action=ListAction, default=[], metavar="PACK")
    s_add.add_argument("--on", action="append", default=[], metavar=ON_FORM)
    s_add.add_argument("--harness", default=argparse.SUPPRESS)
    s_add.add_argument("--guidance", dest="artifact", default=argparse.SUPPRESS,
                       choices=(*GUIDANCE_NAMES, BASIS_NONE))
    s_add.add_argument("noun", nargs="*", metavar="NAME")
    tree_flags(s_add, on_verb=True)
    page(s_add, "add")

    s_rm = sub.add_parser("rm", allow_abbrev=False)
    selectors(s_rm)
    s_rm.add_argument("--yes", action="store_true")
    s_rm.add_argument("--pack", action=ListAction, default=[], metavar="PACK")
    s_rm.add_argument("noun", nargs="*", metavar="NAME")
    tree_flags(s_rm, on_verb=True)
    page(s_rm, "remove")

    s_remove = sub.add_parser("remove")
    selectors(s_remove)
    s_remove.add_argument("--pack", action=ListAction, default=[], metavar="PACK")
    s_remove.add_argument("--yes", action="store_true")
    s_remove.add_argument("noun", nargs="*", metavar="NAME")
    tree_flags(s_remove, on_verb=True)
    page(s_remove, "remove")

    s_set = sub.add_parser("configure")
    s_set.add_argument("noun", nargs="*", metavar="NOUN", help=argparse.SUPPRESS)
    s_set.add_argument("--harness")
    s_set.add_argument("--guidance", dest="artifact", choices=(*GUIDANCE_NAMES, BASIS_NONE))
    tree_flags(s_set, on_verb=True)
    page(s_set, "configure")

    s_update = sub.add_parser("update")
    # The shared flags stand here too, so `update --target DIR` with no scope
    # is the same refusal as `update` alone, not a scope of DIR.
    tree_flags(s_update, on_verb=True)
    update_sub = s_update.add_subparsers(dest="scope", metavar="{guidance,scaffolding,all}")
    update_sub.required = True
    page(s_update, "update")
    for name in ("guidance", "scaffolding", "all"):
        sp = update_sub.add_parser(name)
        sp.set_defaults(scope=name)
        tree_flags(sp, on_verb=True)
        page(sp, f"update {name}")

    s_doc = sub.add_parser("doctor")
    s_doc.add_argument("--cleanup-audit", action="store_true")
    tree_flags(s_doc, on_verb=True)
    page(s_doc, "doctor")

    s_inter = sub.add_parser("interactive")
    s_inter.add_argument("--target", default=argparse.SUPPRESS)
    page(s_inter, "interactive")

    s_selftest = sub.add_parser("selftest")
    page(s_selftest, "selftest")

    s_agent = sub.add_parser("agent")
    agent_sub = s_agent.add_subparsers(dest="agent_verb", metavar="COMMAND")
    agent_sub.required = True
    page(s_agent, "agent")
    s_ag_add = agent_sub.add_parser("add")
    s_ag_add.add_argument("agent", metavar="AGENT")
    s_ag_add.add_argument("name", nargs="*", metavar="NAME")
    s_ag_add.add_argument("--pack", action=ListAction, default=[], metavar="PACK")
    s_ag_add.add_argument("--harness", choices=HARNESSES)
    s_ag_add.add_argument("--model")
    s_ag_add.add_argument("--effort")
    s_ag_add.add_argument("--on", action="append", default=[], metavar=ON_FORM)
    page(s_ag_add, "agent add")
    s_ag_remove = agent_sub.add_parser("remove")
    s_ag_remove.add_argument("agent", metavar="AGENT")
    s_ag_remove.add_argument("name", nargs="*", metavar="NAME")
    s_ag_remove.add_argument("--pack", action=ListAction, default=[], metavar="PACK")
    s_ag_remove.add_argument("--all", action="store_true")
    s_ag_remove.add_argument("--yes", action="store_true")
    page(s_ag_remove, "agent remove")
    s_ag_configure = agent_sub.add_parser("configure")
    s_ag_configure.add_argument("agent", metavar="AGENT")
    s_ag_configure.add_argument("--harness", choices=HARNESSES)
    s_ag_configure.add_argument("--model")
    s_ag_configure.add_argument("--effort")
    s_ag_configure.add_argument("--voice")
    page(s_ag_configure, "agent configure")
    s_ag_update = agent_sub.add_parser("update")
    s_ag_update.add_argument("agent", metavar="AGENT")
    # The scope is checked by cmd_agent, which words the refusal (screens 238, 239).
    s_ag_update.add_argument("scope", nargs="?")
    page(s_ag_update, "agent update")
    s_ag_list = agent_sub.add_parser("list")
    s_ag_list.add_argument("agent", nargs="?", metavar="AGENT")
    page(s_ag_list, "agent list")
    for s in (s_ag_add, s_ag_update, s_ag_remove, s_ag_configure):
        s.add_argument("--json", action="store_true")
        s.add_argument("--dry-run", action="store_true")
        s.add_argument("--details", action="store_true")
    s_ag_list.add_argument("--json", action="store_true")
    s_ag_list.add_argument("--full", action="store_true")
    return p
