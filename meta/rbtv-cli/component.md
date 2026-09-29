---
description: The ONE system-wide RBTV CLI — the agent-facing disclosure drill (modules → components → entry points) plus the action-verb router that delegates to the surfaces that already ship.
---

# rbtv-cli — the ONE system-wide RBTV CLI

`rbtv` — the agent-facing disclosure + action surface. Built for core-build task 7.65.
The contract, reasoning and rejected alternatives are the registry's (`concepts/rbtv-cli.md`,
`decisions.md#d-rbtv-cli`) and are never restated here (`PRIN-11`).

```
rbtv                        level 0 — the installed modules
rbtv <module>               level 1 — that module's components, blurb-first, + its rules and action verbs
rbtv <module> <component>   level 2 — the component's entry point body + its invocable entry points

rbtv install <verb>         add|rm|set|ls|li|doctor   → meta/installer/install.py
rbtv embed-search <verb>    index|query|status            → meta/embed-search
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

`rbtv install` delegates to **`meta/installer/install.py`** (named `install2.py` until
2026-08-23, when the file was split into `meta/installer/lib/` and took the plain name). The installer is homed in the `meta`
module because `meta/` hosts what operates on the rbtv SYSTEM itself rather than on a user goal's
content, and installing rbtv into a workspace is exactly that (owner ruling, 2026-08-22 — `core/`
was the wrong home). Its own `argparse` program name has always been `rbtv install`; this route is
what makes that string true at a shell. Its two workspace settings —
`harness` (which AI coding tools get files written for them) and `artifact` (which root guidance
file the human authors) — are answered once on the first `add` and thereafter owned by their own
verbs; `add` refuses those flags afterwards rather than accepting them and doing nothing
(installer `design-decisions.md` D16).

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

## ⚠ The drill is a STAND-IN pending CMP-5

The registry specifies the drill over `module.md`, per-component `component.md` description lines,
and exposure-manifest rows carrying an `rbtv-cli` column. **None of those exist** — measured:
`find . -name component.md -o -name module.md` over the whole repo returns zero, and no exposure
manifest carries that column. That is `G-109` (CMP-5 designed-unbuilt).

So `tool/lib/catalog.js` reads the substrate that IS live, and is a stand-in for a CMP-5 reader,
**not the settled schema**:

| Level | Ruled substrate | Read instead |
|-------|-----------------|--------------|
| 0 | `module.md` | `module.md` — read since 2026-08-24; a directory at the tree root holding one IS a module |
| 1 | `component.md` description lines | `component.md` frontmatter + capability folders + component folders. The retired installer's `admin/install/module-manifest.json` supplied a third set of rows here until 2026-08-24; it was deleted with that installer, and it never listed either of the two folder shapes anyway |
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

- **No auth of its own.** Nothing here reads a token value into argv. `doctor` reports
  `IGNITE_SENDER_TOKEN` **presence** only. The selftest asserts a token value never
  reaches stdout or stderr.
- **Only declared routes.** A verb with no current component entry is refused.

## Install

`rbtv` is a `tool,path` part, booked by the installer like other PATH tools.
On a new machine, bootstrap the installer directly from the cloned repo once:

```
python3 <rbtv_path>/meta/installer/install.py add -c meta/rbtv-cli --target <workspace> --harness claude,codex,opencode --artifact none
```

Open a new shell, then run `rbtv doctor` from any directory. The installer
books the dispatcher in the workspace and links it into `~/.rbtv/bin`; it also
puts that directory on the user PATH. `node` is the dispatcher's runtime
prerequisite (v24 on the ignite VPS).

## Mounting more on this skeleton

A new command family is **one row in `tool/lib/verbs.js` `ROUTES`** plus its delegate. `rbtv embed-search`
is an example of a top-level, non-module namespace. Adding a route
automatically puts it in `doctor`, in the disjointness assertion, and in the module's level-1
listing; nothing else needs editing. That is the property to preserve.
