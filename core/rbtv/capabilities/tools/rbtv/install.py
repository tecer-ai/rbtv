#!/usr/bin/env python3
"""install.py — the rbtv command.

Installs files into an installation by reading each component's `<component>.json`
and the folder that exposes each file, and realizing that method per harness, at the
INSTALLATION ROOT only. Python 3 stdlib only.

    rbtv status                target, saved settings and recorded selections
    rbtv list [NAME]           browse modules, components or exact files
    rbtv search QUERY          search names and descriptions broadly
    rbtv show NAME             resolve a name and inspect details
    rbtv add NAME...           install or refresh selected files
        First add: --harness codex --guidance CLAUDE.md|AGENTS.md|none
        Identical setup flags may be repeated on later adds.
    rbtv add --module core     select a whole module
    rbtv remove NAME...        remove selected files
    rbtv remove --all --yes    explicitly confirm broad removal
    rbtv configure --harness codex --guidance none
    rbtv update guidance       copy maintained instructions
    rbtv update scaffolding    refresh selected installed files
    rbtv update all            do both updates
    rbtv providers list        provider accounts: logins, saved names, usage
    rbtv doctor               read-only health and recovery checks
    rbtv interactive           explicitly start the guided flow
    rbtv selftest              run isolated regression checks

    No arguments prints help. ls/li/rm and explicit selector flags remain
    compatible aliases. See --help for the complete command grammar.

    --dry-run and --json on every verb where they mean something.
    Exit codes: 0 success · 1 refusal · 2 usage.

    THE TARGET. `--target D` is explicit and always wins. Without it the
    existing RBTV_AGENT_HOME is used when set; invalid values refuse.
    Otherwise the install root is discovered from the current directory —
    first ancestor holding `.rbtv/config/install.json`, else first ancestor
    holding a `.rbtv/` directory, else the cwd (D24). So a run from anywhere
    inside the installation finds the installation, and a run from inside this repo
    finds nothing to install only when the repo really is outside one.

BOUNDARY. The installer exposes components at the INSTALL ROOT and NEVER
writes under `.rbtv/goals/`. It does not import the Ignite 0.1 seat
materializer. The forms below are re-implemented against CMP-12, the one form
authority.

WHERE THE CODE IS. This file is the entry and holds no logic. One module per
responsibility under `lib/`, in import order — each may import only from the
ones above it, so there is no cycle:

    constants     every literal: names, paths, banners, harnesses, the matrix
    frontmatter   reading the `---` block at the top of a source file
    fsio          the one way a file's content is replaced
    locks         bounded cross-platform locks for mutations
    files_key     the keys `files` and `selected` of a record, read from one that says `units`
    catalog       reading one discovered component record and its parts
    claims        one key or one fenced block inside a shared config file
    link_paths    a link from the repository root or `.rbtv/`, made absolute
    schema        checking a record against one of the JSON Schemas in `templates/`
    recovery      the recovery wording refusals share
    content       rendering the body of every file written, recognising ours
    guidance      the root guidance mirror (D13)
    target        finding the install root when no --target was given
    pathlinks     the `~/.rbtv/bin` shortcuts and the shell PATH line
    shared_links  which installation owns a shortcut, and one mutation at a time
    selection     what the human typed -> the component and part keys it names
    state         the install book: read, migrate, write, query
    present       terminal vocabulary: the --type table, the `.rbtv/` folders, titles, tables
    help_pages    the `-h` page of every command path
    subagents     an agent written as a harness-native sub-agent: its --on values
    planning      chosen components -> the exact files and claims of a run
    apply         writing that set to disk, and removing what the book records
    operations    performing one install or one uninstall
    agents        one agent's folder: add, configure, update, remove
    listing       available/installed file views and file details
    doctor        the read-only health check
    report        printing what a run planned or did
    tui           the arrow-key widgets the interactive flow is built from
    providers     the supported providers, an installation's saved logins, their verbs
    usage         plan usage of provider accounts: readers, parsers, both views, its verb
    interactive   the guided flow
    parser        the command grammar
    commands      one handler per verb, and the dispatch

`discovery.py` sits BESIDE this file, not in `lib/`: this directory is on
`sys.path` and the package imports it by bare name. `selftest/` holds the runnable check, one module
per subject. The decisions all of this was built to: `documentation/design-decisions.md`.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _configure_unicode_output() -> None:
    """Avoid Windows legacy-console crashes on installer diagnostics."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


_configure_unicode_output()

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.commands import main  # noqa: E402  (needs the path line above)

if __name__ == "__main__":
    raise SystemExit(main())
