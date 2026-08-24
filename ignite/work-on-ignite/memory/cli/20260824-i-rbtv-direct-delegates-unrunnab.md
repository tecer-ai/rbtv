# 20260824-i-rbtv-direct-delegates-unrunnab — rbtv direct delegates unrunnable on Windows

kind: issue
component: cli
date: 2026-08-24
commit: 71e07d03
deployed: no
pin: NONE
components: meta-installer

## Observed
On the Windows desktop (`C:\Users\henri\Documents\second-brain`), 2026-08-24, every `direct` route
of the `rbtv` CLI refused. `rbtv install ls` printed the delegate-execution refusal with
`cause: spawnSync ...\meta\installer\install.py EFTYPE`. The same failure mode applies to every
other `direct` route in `meta/rbtv-cli/tool/lib/verbs.js` — `goal`, `ignite daemon`,
`ignite ticker`, `run`, `teambuild`, `embed-search` — so the only routes that worked on that
machine were `ignite` (exec `node`) and the drill levels, which spawn nothing. `rbtv selftest`
reported 5 of 25 checks failing, two of them the delegation checks. HEAD and the deployed tree
agree; this is platform-specific, not drift.

## Mechanism
`delegate()` in `meta/rbtv-cli/tool/lib/delegate.js` built its spawn as
`route.exec === 'node' ? [process.execPath, [target, ...args]] : [target, args]`. The `direct`
arm passes the script file itself as the executable, which is correct only where the kernel
honours a `#!` line. Windows has no shebang layer: `CreateProcess` on a `.py` or extensionless
text file has no executable to launch and Node surfaces `EFTYPE`. Nothing in the CLI was wrong
about the route, the target, or the arguments — the assumption that a shebang is executable is
the whole defect.

## Attempts
First attempt held — checked: `meta/rbtv-cli/tool/lib/delegate.js` header comment (which states
the two exec kinds and their contract), `meta/rbtv-cli/tool/lib/verbs.js` ROUTES table and the
shebang of every target it names, `meta/rbtv-cli/component.md`, and the selftest's delegation
fixtures in `meta/rbtv-cli/tool/lib/selftest.js`. A grep of
`ignite/work-on-ignite/memory/*/_issues.md` and `*/_creations.md` for `rbtv-cli`, `delegate.js`,
`windows`, `win32`, `shebang`, `EFTYPE` and `spawn` surfaced no prior entry on this surface; the
three `spawn` hits (jobs, launch-profiles, server) are unrelated subjects.

## Fix
`delegate()` gained `winShebang(target)`, which on `win32` only reads the target's first 256
bytes, parses a `#!` line (handling both `#!/usr/bin/env X` and `#!/usr/bin/X`), and returns the
interpreter to spawn with the script as its first argument — the argv the POSIX kernel would have
built. Off `win32` it returns null and the original `direct` spawn is untouched, so POSIX
behaviour is bit-identical and the VPS is unaffected.

Two Windows specifics are resolved rather than assumed:

- `python3` is not a name on a stock Windows PATH; the launcher is `python`.
- `bash` on PATH is WSL's, whose filesystem view contains no `C:/...`; handed a Windows script
  path it exits 127 with "No such file or directory" — a failure that reads like a missing script
  rather than a wrong interpreter. Git for Windows ships a bash that does resolve those paths, so
  `winBash()` locates it from git's own install (`where git` → `…/cmd/git.exe` →
  `…/bin/bash.exe`) and falls back to plain `bash` only when that fails. Resolving through git
  rather than PATH order is deliberate: PATH order is what produced the wrong bash in the first
  place. Backslashes in the path are also escape sequences to bash, so the script path is
  forward-slashed when an interpreter is used.

Rejected: a per-route `exec: 'python'` / `exec: 'bash'` field. It would have duplicated, in the
route table, information the target file already carries in its shebang, and left every future
target one forgotten field away from the same refusal.

## Consequences
Nothing was deleted or replaced; the `node` arm and the `direct` arm on POSIX are unchanged.
`rbtv selftest` on Windows went from 5 failures to 3: "ticker namespace routes to the built
surface" and "delegation propagates a delegate exit code EXACTLY" now pass. The 3 that remain
pre-date this change and are unrelated to delegation — a health-verdict check whose fixture calls
`spawnSync(file, [])` directly and so hits the same Windows shebang gap on the TEST side, an
unresolvable-root refusal that does not name the root it resolved, and a level-2 component read
that leaks `component.md` frontmatter into the printed body. Those three are untouched here.

## Verification
`rbtv selftest` on the Windows desktop, before (5 failures, via `git stash`) and after (3), with
the two newly-passing checks named above. Live routes exercised end to end through the PATH
wrapper: `rbtv install ls` and `rbtv install li` (a `python` delegate, printing the workspace's
component inventory and its harness/artifact settings), `rbtv goal` (a `bash` delegate, printing
`rbtv-goal`'s own argparse usage), and `rbtv teambuild` (a `node` delegate, unchanged path).
Committed 71e07d03 on `ignite/core-daemon`. Not deployed — the change is inert on the VPS by
construction.

## ATTENTION
- A `direct` route's target is only self-executing where a shebang is honoured. Adding a route
  whose target is a script, and testing it only on the VPS, proves nothing about Windows — the
  refusal there is `EFTYPE` at spawn, which reads like a permissions problem and is not one.
- `bash` on Windows PATH is usually WSL's, and it fails a Windows path with exit 127, not with an
  error naming the interpreter. Exit 127 from a delegate on Windows means the wrong bash far more
  often than it means a missing script.
- The selftest's own delegation fixtures spawn `#!/bin/sh` files. One of them (`a health verdict
  is NEVER collapsed into the exit status`) calls `spawnSync` directly instead of going through
  `delegate()`, so it stays red on Windows no matter what this layer does. Do not chase that
  failure into `delegate.js` — the gap is in the test.
- `winShebang()` reads only the first 256 bytes. A target whose shebang is preceded by a BOM or
  padding will fall through to the raw spawn and refuse with `EFTYPE` again.
- A direct route's target self-executes only where a shebang is honoured; on Windows it refuses with EFTYPE, which reads like a permissions problem and is not one.
