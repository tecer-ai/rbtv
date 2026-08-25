---
name: rbtv-team-kit
description: 'Set up, run, or join a coordinated parallel multi-agent team in tmux (the team-kit): one pane per seat, typed append-only message log, roster with verified identities, staged launches, watcher/closer seats. Use when the user wants to start a new team run, create a run package, add seats to a run, or asks how a team run works. The coordination CLI is coord.py (`coordinate` where symlinked); the protocol every run agent follows ships with this kit.'
# W6 — the DISCOVERY layer: the CLIs this skill routes to, in the `exposes:` reference
# grammar. A seat exposing this skill inherits those rows' `write-roots` without naming
# them; exposure.csv stays the one home of each CLI's declaration.
exposes-cli:
  - coordinate
---

# Team Kit

**CRITICAL — Execute these steps in order.**

1. Read `{rbtv_path}/ignite/coord/CLAUDE.md` (the kit's hard rules).
2. To START a new run or build a run package: read and follow `{rbtv_path}/ignite/coord/team-kit.md` § Starting a new run.
3. Every executing agent in a run follows `{rbtv_path}/ignite/coord/protocol.md`; the run package's own `CLAUDE.md` wins on conflict.
