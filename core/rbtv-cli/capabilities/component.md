# rbtv-cli — the ONE system-wide RBTV CLI

`rbtv` — the agent-facing disclosure + action surface. Built for core-build task 7.65.
The contract, reasoning and rejected alternatives are the registry's (`concepts/rbtv-cli.md`,
`decisions.md#d-rbtv-cli`) and are never restated here (`PRIN-11`).

```
rbtv                        level 0 — the installed modules
rbtv <module>               level 1 — that module's components, blurb-first, + its rules and action verbs
rbtv <module> <component>   level 2 — the component's entry point body + its invocable entry points

rbtv install <verb>         status|list|search|show|configure|add|remove|update|doctor → core/installer/capabilities/tools/rbtv-install/install.py
rbtv control-panel <verb>   update|status                 → meta/control-panel

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

**Exit codes**: `0` success · `1`
refusal or not-found · `2` usage error. A delegated call's exit code is **the delegate's**,
unchanged.

## Everything that acts, DELEGATES

This CLI contains **no second implementation** of any behaviour that already ships (`PRIN-11`).
Every action verb execs a surface that exists, and delegation is **transparent**: the delegate's
stdout, stderr and exit code are the caller's, un-reinterpreted. This CLI never wraps a delegate's
output in an envelope and never re-derives its verdict.

A delegated call's exit code is the delegate's. The selftest asserts that with a
delegate that reports an unhealthy subject on a successful read — health is never
re-collapsed into the exit status.

`rbtv install` delegates to **`core/installer/capabilities/tools/rbtv-install/install.py`**, the `core/installer` component's program. Its own `argparse` program name has always been `rbtv install`; this route is
what makes that string true at a shell. Its two workspace settings —
`harness` (which AI coding tools get files written for them) and `guidance` (which root guidance
file the human authors) — can be set by `configure` before the first `add`, or supplied together on
that first `add`. Later changes use `configure`; omitted settings retain their saved values.
See installer `design-decisions.md` for the persisted-setting rationale and current command names.

The Ignite 0.1 verb families — `ignite daemon`, `ignite ticker`, the gateway client,
`goal`, `run` — are not routed. Their delegates are 0.1 and are deleted with it.

## Resolution order — and why the ambiguity is refused rather than resolved

1. A **bare module token is always the drill** — `rbtv ignite` lists components, never delegates.
2. At position 2, a **multi-token route** wins first, if one exists.
3. Then a **component**, then a **module-level verb**.
4. A token that is **both is REFUSED**, never silently resolved — guessing which one the caller
   meant is how the wrong thing runs.

`selftest` **asserts** that component names and verb names stay disjoint under every module, so (4)
is a tripwire for a future collision rather than a path anyone is expected to reach. It holds today
by accident of naming; a capability later called `status` or `inspect` breaks it, and the assertion
is what makes that arrive as a test failure instead of an outage.

## The drill reads the tree

The drill reads `<module>/<module>.json` and `<component>/<component>.json` (each record's
description), per-component `capabilities/component.md` where one exists, and each unit from the
folder that exposes it (`skills/`, `rules/`, `commands/`, `agents/`, `hooks/`, `mcp-servers/`,
`capabilities/tools/<tool>/`, `folder-instructions/`). `rbtv install list`, `search`, and `show`
list those units.

So `tool/lib/catalog.js` reads the substrate that IS live, straight off the tree:

| Level | Ruled substrate | Read instead |
|-------|-----------------|--------------|
| 0 | `<module>/<module>.json` | `<module>/<module>.json` — a directory at the tree root holding one IS a module |
| 1 | `<component>/<component>.json` description | `<component>.json` plus `capabilities/component.md` when present. The retired installer's `admin/install/module-manifest.json` supplied a third set of rows here until 2026-08-24; it was deleted with that installer, and it never listed either of the two folder shapes anyway |
| 2 | the unit file in its exposure folder | the folder the unit sits in; a tool's `<tool>.json` names its `entry` |

`catalog.js` lists; it does not validate. The installer refuses a file that breaks its schema.

**One deliberate divergence from the ruled behaviour, stated rather than silent:** the registry says
entering a scope "delivers that scope's rules in the tool result". `core` alone carries 11 rules, so
delivering every body unconditionally would make the cheap scan step the most expensive output the
CLI produces. Rules ride the result as **names + descriptions + paths always**, and **bodies under
`--rules`**. If that trade is wrong, it is one function (`level1`) to change.

## What it never does

- **No auth of its own.** Nothing here reads a token value into argv. `doctor` reports
  `IGNITE_SENDER_TOKEN` **presence** only. The selftest asserts a token value never
  reaches stdout or stderr.
- **Only declared routes.** A verb with no current component entry is refused.

## Install

`rbtv` is a `tool,path` part, booked by the installer like other PATH tools.
On a new machine, bootstrap the installer directly from the cloned repo once:

```
python3 <rbtv_path>/core/installer/capabilities/tools/rbtv-install/install.py add core/rbtv-cli --target <workspace> --harness claude,codex,opencode --guidance none
```

Open a new shell, then run `rbtv doctor` from any directory. The installer
books the dispatcher in the workspace and links it into `~/.rbtv/bin`; it also
puts that directory on the user PATH. `node` is the dispatcher's runtime
prerequisite (v24 on the ignite VPS).

## Mounting more on this skeleton

A new command family is **one row in `tool/lib/verbs.js` `ROUTES`** plus its delegate. `rbtv control-panel`
is an example of a top-level, non-module namespace. Adding a route
automatically puts it in `doctor`, in the disjointness assertion, and in the module's level-1
listing; nothing else needs editing. That is the property to preserve.
