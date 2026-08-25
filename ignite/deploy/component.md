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
| PATH links | `link-tools.py` | Puts the kit's bare-name commands (`coordinate`, `scaffold-seats`, `owed-answers`, `tmux-overview`) on PATH, idempotently, from their component homes |
| network + probe records | `network/`, `p3-*.js`, `*.out`, `*.log` | The containment probes and their recorded outputs |

## Exposure

The first-party CLIs here (`link-tools.py`, `probe-suite.js`, `probe-suite-scheduled.py`)
have no `method=path` rows yet — `spec-component-map` §7.3 assigns those to
**impl-cli-skills**, together with the installer PATH links. `exposure.csv` beside this
file carries the header and waits for them.
