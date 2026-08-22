# rbtv-cli — the ONE system-wide RBTV CLI

`rbtv` — the agent-facing disclosure + action surface. Built for core-build task 7.65.
The contract, reasoning and rejected alternatives are the registry's (`concepts/rbtv-cli.md`,
`decisions.md#d-rbtv-cli`) and are never restated here (`PRIN-11`).

```
rbtv                        level 0 — the installed modules
rbtv <module>               level 1 — that module's components, blurb-first, + its rules and action verbs
rbtv <module> <component>   level 2 — the component's entry point body + its invocable entry points

rbtv ignite daemon <verb>   start|restart|stop|kill|unit  → ignite/capabilities/daemon-operator
rbtv ignite ticker          NOT BUILT — core-build task 7.66
rbtv ignite <command>       the gateway client            → ignite/cli/ignite.js
rbtv goal <verb>            scaffold|reindex|lint|materialize → ignite/capabilities/goals-tree

rbtv doctor                 can this tool work here?
rbtv selftest               this CLI's own mechanics
```

Flags: `--json` (machine) · `--pretty` (human; **never** TTY-derived) · `--rules` (deliver rule bodies).
On the **drill** a flag may sit anywhere (`rbtv core --rules` ≡ `rbtv --rules core`) — the drill has
no per-level flags, so every dash token is a global one. After a **delegated** route, every token
passes to the delegate verbatim; a global `--json` given before the route is re-attached exactly once.

A component name carrying **two facets delivers both** — `core safe-move` is a skill (the installed
loader) and a tool (the package it loads). Handing over whichever the manifest listed first would
make the answer depend on key order.

**Exit codes** (the `sd-graph` / `rbtv-goal` / `daemon-operator` convention): `0` success · `1`
refusal or not-found · `2` usage error. A delegated call's exit code is **the delegate's**,
unchanged.

## Everything that acts, DELEGATES

This CLI contains **no second implementation** of any behaviour that already ships (`PRIN-11`).
Every action verb execs a surface that exists, and delegation is **transparent**: the delegate's
stdout, stderr and exit code are the caller's, un-reinterpreted. This CLI never wraps a delegate's
output in an envelope and never re-derives its verdict.

⚠ **`rbtv ignite daemon unit` exits 0 for any unit it could READ** — including a failed or
crash-looping one. Health is the `health` FIELD (`healthy|unstable|starting|inactive|failed`).
**Branch on `health`, never on the exit status.** An exit code reports whether the READ succeeded,
never whether the SUBJECT is healthy (leader ruling on defect `G-121`). A wrapper that re-collapsed
health into its exit status would undo that fix for every caller arriving through here — so the
selftest asserts it with a delegate that reports an unhealthy subject on a successful read.

`rbtv install` delegates to **`install2.py` at the repo root**, not to a capability tool, and that
is the point: the installer is what a workspace runs BEFORE anything from this repo is installed
there, so it can depend on nothing installed. Its own `argparse` program name has always been
`rbtv install`; this route is what makes that string true at a shell. Its two workspace settings —
`harness` (which AI coding tools get files written for them) and `artifact` (which root guidance
file the human authors) — are answered once on the first `add` and thereafter owned by their own
verbs; `add` refuses those flags afterwards rather than accepting them and doing nothing
(`install2.py` D16).

The daemon verbs' names, the survival-check and `LoadState` behaviours, and the reason `unit` is
not called `status` are the daemon-operator capability's, carried whole there. Nothing was thinned
while wrapping. **The 3s settle and 300s unstable windows are guesses routed to task 7.68** — they
are carried through untouched and re-guessed nowhere.

## Resolution order — and why the ambiguity is refused rather than resolved

`ignite` is BOTH a module and a verb namespace: the registry rules `rbtv <module> <component>` (the
drill) and `rbtv ignite <subcommand>` (the gateway client) onto the same two tokens.

1. A **bare module token is always the drill** — `rbtv ignite` lists components, never delegates.
2. At position 2, a **multi-token route** wins first (`ignite daemon`, `ignite ticker`), which is
   what keeps `rbtv ignite daemon kill` (the unit) off `rbtv ignite kill` (a gateway session).
3. Then a **component**, then a **module-level verb**.
4. A token that is **both is REFUSED**, never silently resolved — guessing which one the caller
   meant is how the wrong thing runs.

`selftest` **asserts** that component names and verb names stay disjoint under every module, so (4)
is a tripwire for a future collision rather than a path anyone is expected to reach. It holds today
by accident of naming; a capability later called `status` or `inspect` breaks it, and the assertion
is what makes that arrive as a test failure instead of an outage.

## ⚠ The drill is a STAND-IN pending CMP-5

The registry specifies the drill over `module.md`, per-component `component.md` description lines,
and exposure-manifest rows carrying an `rbtv-cli` column. **None of those exist** — measured:
`find . -name component.md -o -name module.md` over the whole repo returns zero, and no exposure
manifest carries that column. That is `G-109` (CMP-5 designed-unbuilt).

So `tool/lib/catalog.js` reads the substrate that IS live, and is a stand-in for a CMP-5 reader,
**not the settled schema**:

| Level | Ruled substrate | Read instead |
|-------|-----------------|--------------|
| 0 | `module.md` | `admin/install/module-manifest.json` module descriptions |
| 1 | `component.md` description lines | the manifest's per-module inventory rows (`skills`/`commands`/`rules`/`subagents`/`tools`) + capability folders |
| 2 | exposure rows where `rbtv-cli` is set | the capability-folder shape; **invocable entry points are INFERRED from the executable bit** |

**When CMP-5 lands, `catalog.js` is the file that changes; nothing above it should need to.**
The inference at level 2 over-reports (an importable module that happens to be `+x` is listed), and
the output says so on the line itself rather than leaving the reader to know it. `rbtv doctor`
reports the stand-in posture too, so it reaches anyone who never opens this file.

**One deliberate divergence from the ruled behaviour, stated rather than silent:** the registry says
entering a scope "delivers that scope's rules in the tool result". `core` alone carries 11 rules, so
delivering every body unconditionally would make the cheap scan step the most expensive output the
CLI produces. Rules ride the result as **names + descriptions + paths always**, and **bodies under
`--rules`**. If that trade is wrong, it is one function (`level1`) to change.

## What it never does

- **No auth of its own.** The drill and the daemon verbs are local; nothing here crosses the
  gateway. The delegated gateway client reads `IGNITE_SENDER_TOKEN` from the environment itself —
  this process never sees, formats or forwards its value, and `doctor` reports token **presence**
  only. The selftest asserts a token value never reaches stdout or stderr.
- **No seat gate.** Owner-ruled 2026-07-26: during development all agents on the box may run all
  daemon commands. The enforcement point is the OS (a caged worker's namespace masks the user bus).
  Master-gating is PARKED pending `CMP-13` / task 7.10. Do not add one here.
- **No `run` verb.** The attached-run embedded engine is task 7.44.
- **No `enable`/`disable`, unit-file edits, or `RBTV_IGNITE_CARRIER` writes** — install-time acts
  owned by the deploy runbook, and a carrier write would remove a containment gate.

## Install

Per-machine symlink, never synced by git — the convention `sd-graph`, `coordinate` and `ignite`
already follow on this box:

```
ln -sfn <rbtv_path>/core/capabilities/rbtv-cli/tool/rbtv ~/.local/bin/rbtv
```

`node` is the only prerequisite (v24 on the ignite VPS). Verify with `rbtv doctor` from any
directory — it names each delegate individually, because "some delegate is missing" is not
actionable.

## Mounting more on this skeleton

A new command family is **one row in `tool/lib/verbs.js` `ROUTES`** plus its delegate. `rbtv goal`
is the worked example of a top-level, non-module namespace — which is exactly the shape
`rbtv teambuild` needs (core-build task 7.55, which depends on this task). Adding a route
automatically puts it in `doctor`, in the disjointness assertion, and in the module's level-1
listing; nothing else needs editing. That is the property to preserve.
