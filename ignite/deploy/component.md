---
description: Read before changing how ignite is deployed or probed — the systemd units, the probe-suite runner and its scheduled twin, and the PATH-link tool.
---

# deploy

Deployment and whole-tree verification. Law is
`1-projects/build-ignite/redesign/specs/spec-component-map.md` §1 under [D22], [T4-R11]:
the map's `deploy` row is a 1:1 keep — this folder was already the deploy component and
was not reshaped by the component-first move.

It owns how the code is *installed and observed running*. It owns no daemon behaviour: the
process itself is `runtime/`, the out-of-process watchdog is `observation/`.

## What lives here

| Part | File | What it is |
|---|---|---|
| systemd units | `rbtv-ignite.service`, `rbtv-chat-bridge.service`, `rbtv-probe-suite.service`, `rbtv-probe-suite.timer` | The unit files the cutover installs; `ExecStart` names `runtime/index.js` and `chat/index.js` since the component-first move |
| probe-suite runner | `probe-suite.js` | Runs every component's probes and reports the tree's verdict |
| scheduled probe suite | `probe-suite-scheduled.py` | The timer-fired payload around the runner — internal-daemon, never an agent's command |
| PATH links | `link-tools.py` | Puts the kit's bare-name commands (`coordinate`, `scaffold-seats`, `owed-answers`, `tmux-overview`, `file-issue`) on PATH, idempotently, from their component homes |
| network + probe records | `network/`, `p3-*.js`, `*.out`, `*.log` | The containment probes and their recorded outputs |

## Exposure

The first-party CLIs here each carry a `method=path` row on `exposure.csv` beside this
file — `link-tools`, `probe-suite`, `probe-suite-scheduled`, landed per
`spec-component-map` §7.3 (`d-exposure-method-path`). The installer PATH-links those
rows into the shared bin dir; nothing here is a second copy of a binary. `rbtv-cli` and
`description` are empty on each, because a `method=path` row leaves the tool to
self-document via `-h`.

Audience (§7.1, transcribed in `ignite/ignite-cli/cli-audience-map.md`): `link-tools`
and `probe-suite` are owner-console; `probe-suite-scheduled` is internal-daemon — it is
fired by the timer and is never a router-skill target.

## Deploy model — last commit, never the live tree (owner-ruled D6, 2026-08-19)

**History.** On 2026-08-17 the owner ruled the daemon ran from the working copy, with no
deploy gate, "and by owner ruling … none is built". That ruling is superseded.

**Now (D6, 2026-08-19):** single daemon instance, running from the last COMMIT, never the live
working tree. Deploying = committing. No staging. A restart mid-edit deploys nothing half-finished.

The installed units' `ExecStart` and `RBTV_IGNITE_CONFIG_PATH` point at a detached git worktree
(`$XDG_STATE_HOME/rbtv-deploy`, default `~/.local/state/rbtv-deploy`). `RBTV_IGNITE_SRC` still names
the live repo — it is the per-invocation tree (the coordination kit, `coord.py`), not the booted one.

| Surface | Verdict |
|---|---|
| Daemon JS require-closure (`runtime/`, `supervisor/`, `state-store/`, `supervisor/launch-profiles/`, everything `runtime/index.js` requires) | **PINNED** — what `ExecStart` resolves |
| `envelope/spawn-profiles.yaml` (boot-read by the daemon) | **PINNED** via `RBTV_IGNITE_CONFIG_PATH` |
| `chat/` (the chat-bridge unit) | **PINNED** — same worktree, same commit |
| `coord/coord.py` + the kit's scripts | **LIVE TREE** — re-read on every invocation; path composed from `RBTV_IGNITE_SRC` |
| `runtime/jobs/*.py` (spawned per firing) | **LIVE TREE** — argv in `envelope/spawn-profiles.yaml` still name the live repo |
| attached execution (`rbtv run`) | **LIVE TREE by design** — it runs what the console holds |
| probes, `deploy/probe-suite.js`, hand-run scripts | **LIVE TREE** — per-invocation, from the repo |

**Deploy verb:** `rbtv ignite daemon deploy` (also `rbtv-ignite-daemon deploy`). Refuses a missing
or dirty deploy tree; checks the worktree out detached to the branch tip; ensures
`ignite/node_modules`; restarts the unit. `RBTV_IGNITE_UNIT=rbtv-chat-bridge.service … deploy`
re-pins the bridge onto the same refreshed tree.

**What the daemon booted:** `.rbtv/runtime/daemon-code.json` (`root` is under the deploy tree;
`code.digest` hashes the loaded bytes). The watchdog's `daemon_code_state` re-hashes those files
under the marker's carried `root`. **STALE CODE** means "the deploy tree moved and the unit has not
restarted", not "somebody saved a file".

## Installation model

Canonical statement of the ignite install model (owner ruling D27, 2026-07-14).

- **Workspace-scoped, not machine-scoped.** A **workspace** is the folder that roots `.rbtv/` (a
  root dir is usually a git repo, or a branch of one). **"Installed" = this workspace has ONE
  server configured to run ignite for it** — installing on a host is installing in the workspace
  it serves, never "installed on one machine".
- **Install state lives at `.rbtv/modules/ignite/`** — one folder per module, holding:

  | File | Holds |
  |---|---|
  | `status.json` | installed flag · version · first-run stamp |
  | `server.json` | the **endpoint record**, a **machine-keyed map**: each machine's install lives under `machines[<hostname>]` — tailnet hostname + IP · gateway port · SSH host/user/port for the tunnel fallback · that machine's per-machine `state_root`. The file travels via git to EVERY machine (see the travel split), so a single flat value would be right on one machine and wrong on every other; the map records each machine's install instead. The CLI selects its own machine's entry when it records a server, else the one entry that does |
  | `settings.json` | current settings |
  | `settings-history.jsonl` | append-only settings history — NEVER rewritten |

  First run creates the folder and its files **idempotently**; the installed test is: a valid
  `server.json` exists.
- **The travel split is load-bearing.** `.rbtv/modules/ignite/` is **COMMITTED** — the installation
  travels with the repo, so a `git pull` on another machine carries it and that machine's agents
  find and reach the server via `server.json`. Live per-machine runtime state (the ending store,
  logs — see `state-store/component.md` § State layout) lives in the machine's own state root,
  outside the workspace; per-workspace state that stays inside `.rbtv/` but must not travel is
  **GITIGNORED**. **Credentials NEVER travel in git**: each machine's/sender's token is distributed
  out-of-band into a gitignored env surface, and SSH private keys never appear in the repo — the
  tailnet is the preferred client path; the SSH-tunnel fallback requires the connecting machine's
  public key authorized on the server, done once out-of-band
  (`deploy/network/ssh-tunnel-fallback.md`).

## Probes — every component's probes, and the ONE runner that counts them

Each component keeps its probes in a `probes/` folder beside it; a probe is a self-contained script
that writes its verdict into an adjacent `.out`. **Run them with `node deploy/probe-suite.js`** —
`--list` to enumerate, `--dir <rel>` to scope, `--only <name>` for a single probe (`--only` takes
probe NAMES, never paths — a path silently discovers zero), `--selftest` to prove the runner itself.

**⚠ ASKING WHETHER ANYTHING ALREADY GUARDS X? USE THE ENUMERATOR — never a hand-glob of `probes/`
folders.** There are more of them than you will guess, and the obvious guesses miss. The count is
deliberately not written here — a literal in this sentence contradicts the sentence, and it went
stale twice before this note replaced it.

```
node deploy/probe-suite.js --list | grep -E '\.(js|py)$' | xargs grep -l <SYMBOL>
```

`G-179`: a leader and the engineer independently hand-globbed the wrong folders, both concluded
"unguarded", and **corroborated each other into ratifying work on a defect that had been closed for
hours**. **A search of the wrong places and a search of the right places return the SAME EMPTY
RESULT** — absence is the one claim whose wrong answer is indistinguishable from its right one.
General form: **an absence claim over a tree that HAS an enumerator must go through the enumerator.**

**Run ONE probe with `--only <name>`, never `node probes/probe-x.js` (`G-163`).** Running a probe
by hand rewrites its tracked capture with pure noise — a wall time, an ephemeral port, a timestamp —
so verification itself dirties files the seat never edited. Through the runner the capture is
restored byte-identical and the fresh output is kept outside the repo.

The runner exists because nothing enumerated, executed or counted these scripts (`G-141`): two
probes were dead for seven days across two commits, and the last "green" sweep covered 21 of 82
probes while reading complete. Three rules follow, and MUST hold in anything that replaces it:
**the denominator is written before the first probe runs** · **an incomplete run exits `2`, never
`0` or `1`** — so "nothing failed" and "nothing ran" can never look alike, and zero discovered is a
refusal · **`SUITE-COMPLETE` is written last**, so a truncated run is detectable with no exit code
in hand. A verdict comes from a live child-process exit plus a capture refreshed inside that
probe's own run window — **never from the content of a committed `.out`**.

Probes write their `.out` in place, so a run always rewrites captures — but the runner restores each
one byte-identical (mtime included) and keeps the fresh output beside the summary, so **the working
tree is unchanged by default**. Regeneration is the deliberate `--write-captures`. The summary and
captures default to `<tmpdir>/rbtv-probe-suite/` — never into the repo and never into the workspace
`.rbtv/`, so a dispatch fenced against `.rbtv/**` can run the suite without breaching its own fence.
Pass `--summary <path>` to keep one verbatim.
