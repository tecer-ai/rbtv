#!/usr/bin/env python3
"""install.py — the rbtv installer.

Installs units into a workspace by reading each component's `<component>.json`
and the folder that exposes each unit, and realizing that method per harness, at the
INSTALL ROOT only. Python 3 stdlib only.

    rbtv install status                target, settings and installed counts
    rbtv install list [NAME]           browse modules, components or exact items
    rbtv install search QUERY          search items broadly
    rbtv install list --installed      inspect recorded installed items
    rbtv install show NAME             resolve a name and inspect details
    rbtv install add NAME...           install or refresh selected items
        First add: --harness codex --guidance CLAUDE.md|AGENTS.md|none
        Identical setup flags may be repeated on later adds.
    rbtv install add --module core     select a whole module
    rbtv install remove NAME...        remove selected items
    rbtv install remove --all --yes    explicitly confirm broad removal
    rbtv install configure --harness codex --guidance none
    rbtv install update guidance       copy maintained instructions
    rbtv install update scaffolding    refresh selected installed files
    rbtv install update all            do both updates
    rbtv install doctor               read-only health and recovery checks
    rbtv install interactive           explicitly start the guided flow
    rbtv install selftest              run isolated regression checks

    No arguments prints help. ls/li/rm and explicit selector flags remain
    compatible aliases. See --help for the complete command grammar.

    --dry-run and --json on every verb where they mean something.
    Exit codes: 0 success · 1 refusal · 2 usage.

    THE TARGET. `--target D` is explicit and always wins. Without it the
    existing IGNITE_AGENT_HOME is used when set; invalid values refuse.
    Otherwise the install root is discovered from the current directory —
    first ancestor holding `.rbtv/config/install.json`, else first ancestor
    holding a `.rbtv/` directory, else the cwd (D24). So a run from anywhere
    inside the workspace finds the workspace, and a run from inside this repo
    finds nothing to install only when the repo really is outside one.

THE NAME. This file was `install2.py` from its first commit until 2026-08-23,
because a DIFFERENT installer held the name `install.py` — the repo-root entry
plus its `admin/install/` package, which served the old flat-module standard.
This tool never read or wrote that one's state file (`rbtv.json` at the target
root); its own book is `{target}/.rbtv/config/install.json`. It tolerates files
at the install root it did not write — see D6 and D12 — and it sees only
new-standard component folders (D2).

BOUNDARY. The installer exposes components at the INSTALL ROOT and NEVER
writes under `.rbtv/goals/`. It does not import the Ignite 0.1 seat
materializer. The forms below are re-implemented against CMP-12, the one form
authority.

WHERE THE CODE IS. This file is the entry and holds no logic. One module per
responsibility under `lib/`, in import order — each may import only from the
ones above it, so there is no cycle:

    constants     every literal: names, paths, banners, harnesses, the matrix
    catalog       reading one discovered component record and its parts
    claims        one key or one fenced block inside a shared config file
    content       rendering the body of every file written, recognising ours
    guidance      the root guidance mirror (D13)
    pathlinks     the `~/.rbtv/bin` shortcuts and the shell PATH line
    target        finding the install root when no --target was given
    state         the install book: read, migrate, write, query
    planning      chosen components -> the exact files and claims of a run
    apply         writing that set to disk, and removing what the book records
    selection     what the human typed -> the component and part keys it names
    operations    performing one install or one uninstall
    listing       available/installed item views and item details
    doctor        the read-only health check
    report        printing what a run planned or did
    tui           the arrow-key widgets the interactive flow is built from
    interactive   the guided flow
    parser        the command grammar
    commands      one handler per verb, and the dispatch

`discovery.py` sits BESIDE this file, not in `lib/`: this directory is on
`sys.path` and the package imports it by bare name. `selftest/` holds the runnable check, one module
per subject. The decisions all of this was built to: `design-decisions.md`.
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
