"""The command grammar: every verb, flag and selector the command line
accepts.
"""
from __future__ import annotations

import argparse

from discovery import Refuse

from .constants import BASIS_NONE, CANONICAL_METHODS, GUIDANCE_NAMES, HARNESSES


SETTING_VERB = {"harness": "rbtv install add|rm harness <harness>",
                "artifact": "rbtv install set artifact <name>"}

# D16b — the ACTION-FIRST settings grammar, in one place so the help text, the
# `verb-moved` refusal and the dispatch can never spell it three ways.
SETTINGS_EPILOG = (
    "workspace settings (same action words, a NOUN instead of selectors):\n"
    "  rbtv install add harness codex          rbtv install rm harness codex\n"
    "  rbtv install set artifact CLAUDE.md|AGENTS.md|none\n"
    "  rbtv install add artifact exclude DIR   rbtv install rm artifact "
    "exclude DIR\n"
    "  rbtv install li                         (shows all three)")

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
        f"`rbtv install {head}` is gone (D16c). READ the workspace settings "
        "with `rbtv install li` — it heads its listing with all three. "
        "CHANGE this one with "
        + (SETTING_VERB["harness"] if head == "harness"
           else f"{SETTING_VERB['artifact']} or "
                "`rbtv install add|rm artifact exclude <dir>`"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rbtv install",
        description=(
            "Install rbtv components from exposure manifests. "
            "Unit is the exposed part; any subset may be installed."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog="exit codes: 0 success · 1 refusal · 2 usage")

    def tree_flags(dest, *, on_verb: bool) -> None:
        sup = argparse.SUPPRESS
        dest.add_argument(
            "--target", default=(sup if on_verb else None),
            help="install root (default: walk up from cwd for "
                 ".rbtv/config/install.json, then any .rbtv/, then cwd)")
        dest.add_argument(
            "--json", action="store_true",
            default=(sup if on_verb else False),
            help="machine output")
        dest.add_argument(
            "--pretty", action="store_true",
            default=(sup if on_verb else False),
            help="human colour + alignment (never TTY-derived)")
        dest.add_argument(
            "--dry-run", action="store_true",
            default=(sup if on_verb else False),
            help="plan and print; write nothing")

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
            "-A", action="store_true", dest="all",
            help="everything")
        dest.add_argument(
            "-m", action=ListAction, default=[], dest="module",
            metavar="MOD",
            help="module[,module] (repeatable, OR). name, or an ls/li "
                 "number or N-M range. -m hub = _hub")
        dest.add_argument(
            "-c", action=ListAction, default=[], dest="component",
            metavar="COMP",
            help="component[,component] (repeatable, OR). name, or an "
                 "ls/li number or N-M range")
        dest.add_argument(
            "-x", action=MethodsAction, default=[], dest="method",
            metavar="METH",
            help="method[,method] (repeatable, OR). "
                 + " · ".join(CANONICAL_METHODS))
        for flag, meth in (("-xs", "skill"), ("-xr", "rule"),
                           ("-xc", "command"), ("-xsa", "sub-agent")):
            dest.add_argument(
                flag, action="append_const", const=meth, dest="method",
                help=f"alias: -x {meth}")
        dest.add_argument(
            "-nx", action=MethodsAction, default=[], dest="exclude_method",
            metavar="METH",
            help="exclude method[,method]")
        dest.add_argument(
            "-nm", action=ListAction, default=[], dest="exclude_module",
            metavar="MOD",
            help="exclude module[,module]")
        dest.add_argument(
            "-nc", action=ListAction, default=[], dest="exclude_component",
            metavar="COMP",
            help="exclude component[,component]")

    # D16b — the SAME action word covers components and workspace settings.
    # A settings form is a bare NOUN in the positional slot, which is free
    # because components are always named behind a selector flag: nothing a
    # caller can write means both.
    def setting_noun(dest, verb: str) -> None:
        dest.add_argument(
            "noun", nargs="*", metavar="NOUN",
            help=f"settings form: `{verb} harness <h,h>` · "
                 f"`{verb} artifact exclude <dir>…`. Omit it and this verb "
                 "works on COMPONENTS through the selectors above")

    tree_flags(p, on_verb=False)
    # D16 — no global --harness/--artifact. Each setting has exactly one door:
    # the FIRST `add` (which requires it), then its own verb.
    sub = p.add_subparsers(dest="verb", metavar="VERB")

    s_add = sub.add_parser(
        "add",
        help="install / refresh (replan). refuses a locally-modified vendor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog=(
            "selectors AND across kinds, OR within a kind.\n"
            "many at once: -c web/browse,web/capture  ·  -c 3,7,9  ·  -c 2-9,14\n"
            "exclusion: -nx skill  -nm core  -nc web/browse\n"
            + SETTINGS_EPILOG))
    selectors(s_add)
    s_add.add_argument(
        "--harness", default=argparse.SUPPRESS,
        help="FIRST add on this workspace ONLY (required there): "
             "comma-separated subset of " + ",".join(HARNESSES)
             + ". Recorded workspace-wide; later `add` refuses it — change it "
               "with `rbtv install add|rm harness`")
    s_add.add_argument(
        "--artifact", default=argparse.SUPPRESS,
        choices=(*GUIDANCE_NAMES, BASIS_NONE),
        help="FIRST add on this workspace ONLY (required there): which root "
             "guidance file you author; the other is generated. none = "
             "author-nothing, generate-nothing. Later `add` refuses it — "
             "change it with `rbtv install set artifact`")
    s_add.add_argument(
        "--write-path", action="store_true",
        help="append the PATH bootstrap line to the shell startup file "
             "(fenced; teardown can remove it). never happens without this flag")
    setting_noun(s_add, "add")

    s_rm = sub.add_parser(
        "rm", help="remove. -A = every booked part. also `rm harness <h>` / "
                   "`rm artifact exclude <dir>`",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog=SETTINGS_EPILOG)
    selectors(s_rm)
    setting_noun(s_rm, "rm")

    s_set = sub.add_parser(
        "set", help="a workspace setting that holds ONE value: "
                    "`set artifact CLAUDE.md|AGENTS.md|none`",
        allow_abbrev=False)
    s_set.add_argument("noun", nargs="*", metavar="NOUN",
                       help="artifact <" + "|".join((*GUIDANCE_NAMES,
                                                     BASIS_NONE)) + ">")

    s_ls = sub.add_parser(
        "ls", help="what is AVAILABLE (absorbs scan: shadowed)")
    selectors(s_ls)
    s_li = sub.add_parser(
        "li", help="what is INSTALLED; marks partials and names parts in")
    selectors(s_li)

    s_dupe = sub.add_parser(
        "dupe-artifacts",
        help="regenerate harness guidance files from the recorded basis "
             "(change the basis with `set artifact`, never here)")

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
        help="can this tool work here: target, trees, PATH, collisions")
    sub.add_parser(
        "selftest",
        help="fixture tree + install/uninstall + new surface")
    s_inter = sub.add_parser(
        "interactive", help="the human flow (also: no arguments)")

    for s in (s_add, s_rm, s_set, s_ls, s_li, s_dupe, s_doc, s_inter,
              s_h, s_art):
        tree_flags(s, on_verb=True)
    return p
