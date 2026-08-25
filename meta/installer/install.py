#!/usr/bin/env python3
"""install.py — the exposure-manifest rbtv installer.

Installs components into a workspace by reading their EXPOSURE MANIFESTS
(`exposure.csv`) and realizing each row's canonical method per harness, at the
INSTALL ROOT only. Python 3 stdlib only.

    rbtv install ls                     what is available (+ shadowed)
    rbtv install li                     what is installed (from the state file)
    rbtv install add -c <module>/<component> [--target D]
    rbtv install add -m <module> [-x skill]
        FIRST add on a workspace only: --harness a,b --artifact CLAUDE.md|none
    rbtv install rm -c <id> | -m <name> | -A
    rbtv install add|rm harness a,b     which AI tools get files; files follow
    rbtv install set artifact N         N = CLAUDE.md | AGENTS.md | none
    rbtv install add|rm artifact exclude DIR   folders the mirror walk skips
        all three are READ at the head of `rbtv install li` (D16c)
    rbtv install dupe-artifacts         regenerate harness guidance from the basis
    rbtv install interactive            the human flow (also: no arguments)
    rbtv install selftest               the runnable check

    --dry-run and --json on every verb where they mean something.
    Exit codes: 0 success · 1 refusal · 2 usage.

    THE TARGET. `--target D` is explicit and always wins. Without it the
    install root is DISCOVERED by walking upward from the current directory —
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

BOUNDARY (core-build `decisions.md#d-materializer-seat-loaders`). The installer
exposes components at the INSTALL ROOT and NEVER writes under `.rbtv/goals/`.
Seat-folder exposure belongs to the materializer (`ignite/planning/
materialize-seats.py`), which is not imported here — `ignite/` must stay a
relocatable subtree (repo CLAUDE.md), so the forms below are re-implemented
against CMP-12, the one form authority.

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
    listing       the `ls` and `li` views
    doctor        the read-only health check
    report        printing what a run planned or did
    tui           the arrow-key widgets the interactive flow is built from
    interactive   the guided flow
    parser        the command grammar
    commands      one handler per verb, and the dispatch

`discovery.py` sits BESIDE this file, not in `lib/`: it is imported from this
directory by name by `ignite/planning/materialize-seats.py`, so its path is a
contract with another tool. `selftest/` holds the runnable check, one module
per subject. The decisions all of this was built to: `design-decisions.md`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.commands import main  # noqa: E402  (needs the path line above)

if __name__ == "__main__":
    raise SystemExit(main())
