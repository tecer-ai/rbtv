# 20260828-i-a-rbtv-that-does-not-root-the — a .rbtv/ that does not root the install is not a workspace

kind: issue
component: observation
date: 2026-08-28
commit: 5815fbaa
deployed: yes
pin: ignite/observation/daemon-watchdog/probes/probe-watchdog-workspace-refusal.py
components: deploy

## Observed
Acceptance-wave test 15 (the watchdog + dead-man arm of `build/live-acceptance-tests/`) FAILED on
2026-08-28 on a FALSE alarm. From 05:31:14Z the out-of-process watchdog
(`ignite/observation/daemon-watchdog/tool/rbtv-ignite-watchdog`, the `probe-suite` row) printed
`probe-suite down — last fired 9026s ago, stale_after=9000s` on every ~70s pass, took its restart
lever against `rbtv-probe-suite.timer` 195 times by 07:23Z, and DM'd the owner. The probe suite was
not down: it had fired at 04:00:03Z, 05:00:07Z, 06:00:17Z and 07:00:07Z and written a full result
set each time. Orchestrator-verified at HEAD 2659b948, which equalled the deployed worktree; both
units run FROM THE SOURCE TREE (`systemctl --user cat`: `ExecStart=/usr/bin/python3
…/ignite/deploy/probe-suite-scheduled.py` and `…/daemon-watchdog/tool/rbtv-ignite-watchdog`), so
deployed and HEAD were identical on both halves of this and no restart was involved anywhere.

The artifact was real and in the wrong place. A workspace had appeared INSIDE the rbtv repo —
`3-resources/tools/rbtv/.rbtv/`, created 03:02:15Z, holding `runtime/watchdog/outage-ledger.jsonl`,
`runtime/ignite/heart.db`, and `runtime/probe-suite/` with the four hourly summaries, their capture
folders and a `latest.json` stamped 07:19:34Z. The vault's own
`.rbtv/runtime/probe-suite/latest.json` was frozen at 03:20:11Z. `.gitignore:43`/`:76` ignore
`**/.rbtv/`, so `git status` never showed any of it.

## Mechanism
ONE wrong definition of "workspace", implemented at two independent sites — a writer that planted
the stray folder and a reader that then believed it.

D27 and its canonical implementation `ignite/ignite-cli/lib/config.js#findInstallRoot` define a
workspace as the folder that ROOTS THE INSTALL: the nearest ancestor holding the committed endpoint
record `.rbtv/modules/ignite/server.json`. Both sites instead accepted a bare `.rbtv/` DIRECTORY.

THE WRITER. `rbtv-ignite-watchdog:124` read `WORKSPACE = env("RBTV_WATCHDOG_WORKSPACE",
os.getcwd())`. Every path this tool writes is `<WORKSPACE>/.rbtv/runtime/…` — the outage ledger,
`state.json`, `daemon.json`, `failcount.json`, `row-alarms.json` — so a pass with no env creates a
`.rbtv/` wherever it happens to be standing. `probes/probe-watchdog-staged-failure.py` spawned the
tool as a subprocess inheriting the caller's cwd and set every environment key it needed EXCEPT
that one; run from the repo root by the `fix-status-alarms` seat at 03:02:15Z it planted
`<repo>/.rbtv/runtime/watchdog/`. The four ledger rows in that file name
`rbtv-watchdog-selftest.service`, that probe's throwaway unit, which is how the arm was identified.
The stray `runtime/ignite/heart.db` beside it followed 19 seconds later from
`ignite/coord/ending_store.py:24-26`, the only other resolver on the box that defaults that exact
path to a bare-`.rbtv/` walk from the cwd.

THE READER. `ignite/deploy/probe-suite-scheduled.py:83` walked up from `DEPLOY_DIR` and stopped at
the first ancestor where `os.path.isdir(os.path.join(d, '.rbtv'))`. Until 03:02Z the first such
ancestor was the vault; from 03:02Z it was the repo, three levels below. The unit's
`WorkingDirectory` is irrelevant here — this walk starts at the source file — so from the 04:00Z
fire the suite wrote its results and its liveness artifact into the repo, while the watchdog, whose
unit DOES carry `RBTV_WATCHDOG_WORKSPACE=<vault>`, kept reading the vault copy. Two components
resolving one artifact by two different rules, disagreeing silently, with the watchdog's staleness
arithmetic reporting the disagreement as a dead suite.

The same file's own header had described this exact hazard in the first person — an earlier hop
counting version "resolved to `3-resources/`, silently CREATED `3-resources/.rbtv/`" — and the
`ignite-cli` entry `20260827-i-gateway-lookup-was-cwd-only-no` ATTENTION 3 had stated the general
form: nearest-ancestor-wins means a stray record under the vault shadows the real install. The
defining property was fixed; it was just written down as the wrong property.

## Attempts
First attempt held — checked: the whole history of this walk before touching it. The hop-counting
original and its repair are recorded inline in `find_workspace_root`'s own docstring (the
`3-resources/.rbtv/` incident); `0cbbb555`, `b3f71a70`, `bd954a96`, `3d653ce9` and `b3d3425c` built
the alarm route the watchdog rides and changed nothing about workspace resolution; `a5b57bc0`
(2026-08-28, entry `observation/20260828-i-an-alarm-verdict-reached-no-al`) moved the `alarm`
verdict onto the emitter and explicitly did not touch the `down` leg; `02d989ef` gave `config.js`
its `findInstallRoot` walk (entry `ignite-cli/20260827-i-gateway-lookup-was-cwd-only-no`) and, being
JS-side, left both Python walkers on the old rule. No earlier attempt targeted THIS problem — the
two sites had never been read against each other.

## Fix
The rule, at both sites, is the INSTALL RECORD.

`probe-suite-scheduled.py#find_workspace_root` now tests
`os.path.isfile(<d>/.rbtv/modules/ignite/server.json)` and, on walking past a directory that holds a
bare `.rbtv/`, prints ONE stderr line naming it and saying it is not a workspace. That line is not
decoration: the next planting now costs one journal line instead of two components silently
disagreeing about which file is `latest.json`. The no-record case still raises, now naming the
record it looked for. Nearest-ancestor-wins is unchanged, so a genuinely nested install still
shadows an outer one.

The watchdog resolves through `resolve_workspace()`: the env override wins outright and is NOT
second-guessed (the unit sets it, and every probe points it at a scratch workspace that
deliberately carries no install record), the cwd is accepted ONLY when it roots the install, and
otherwise `WORKSPACE` is `None` and `main()` REFUSES with exit 2 and one line. A watchdog with no
workspace must not invent one: aimed at a directory nothing writes to it reports a healthy system
as dead and a dead one as healthy with equal confidence, which is the absence-reads-as-health
failure this whole component exists to remove. The refusal sits at the RUN boundary, not at import:
`probe-g188-daemon-identity` and `probe-runner-grade-verdicts` import this file as a module and
assign `W.WORKSPACE` themselves, and a module-level exit would kill them on import. Exit 2 was
chosen over a new code because the file's own contract already reads "2 usage error", and an
unresolvable workspace is a usage error, not the watchdog breaking (which is what any other nonzero
means here).

REJECTED: importing one shared resolver. There is no Python walker to reuse —
`ignite/coord/gateway_client.py`, the field-for-field port of `config.js`, takes the workspace root
as an ARGUMENT — so sharing would have meant creating one and making two stdlib-only tools import
across component boundaries. The watchdog is pure stdlib precisely so it still runs when everything
else is down, and the scheduler resolves everything from `__file__` for the same class of reason. So
the rule is MIRRORED in six lines per file, each citing `config.js#findInstallRoot` as its source.
REJECTED: validating the explicit env override — five existing probes point it at scratch trees with
no install record, and validating it would have turned every one of them into a test of the refusal.

`probe-watchdog-staged-failure.py` — the arm that did the planting — now creates a scratch workspace
and passes it. With the tool refusing an unrooted cwd, an unset value there is a red probe rather
than a silent planting; setting it explicitly is what keeps the probe testing the watchdog instead
of testing the refusal.

`deploy/component.md` § Installation model and `daemon-watchdog/units/rbtv-watchdog.service` both
stated D27 as "a workspace is the folder that roots `.rbtv/`" — the wrong definition, in the two
places an installer and a next author read it. Both now state the record, and component.md carries
the incident.

## Consequences
Nothing was deleted. The `down` → restart → DM leg is untouched; so is the `alarm` → emitter leg
that `a5b57bc0` built. `ignite/observation/emitter.js` and `tool/watchdog-alarm.js` were not
touched — the shim's own `process.cwd()` fallback (`watchdog-alarm.js:60`) is the same shape but is
unreachable from its only caller, which always passes `workspace_root`, now always install-rooted.

A new probes directory exists under `ignite/deploy/` (the component had none), so `probe-suite.js`
discovery goes 214 → 216. That is automatic — discovery is by structure — and the coverage assertion
holds.

The stray `3-resources/tools/rbtv/.rbtv/` was torn down at 07:34:39Z, reversibly: the four hourly
result sets and the 07:19:34Z `latest.json` (newer than the vault's 03:20:11Z) MOVED into
`<vault>/.rbtv/runtime/probe-suite/` — they are the real results — with `latest.json`'s
`summary_path` field repointed at the vault path it names, since the file it names moved with it.
The remainder (`runtime/watchdog/outage-ledger.jsonl`, `runtime/ignite/heart.db`) and the superseded
vault `latest.json` went to `/tmp/nested-rbtv-evidence-20260828T073428Z/`. Nothing was deleted.

Two walkers OUTSIDE this change carry the same bare-`.rbtv/` rule and were deliberately not touched
(out of seat wall): `ignite/coord/ruling.py:54` and `ignite/coord/ending_store.py:24` — the latter
being the probable writer of the stray `heart.db`. Both are surfaced as loose ends, not fixed here.
Three sibling walkers gate on `.rbtv/config/` (`coord/file-issue.py:79`,
`operator/bindings/tool/bindings.py:272`, `planning/materialize-seats.py:3823`): the stray folder
had no `config/`, so none of them was hijacked, but none tests the D27 record either.

## Verification
`ignite/deploy/probes/probe-workspace-root-record.py` — 9 checks, exit 0. The fixture is the outage
in miniature: `<ws>/.rbtv/modules/ignite/server.json`, a nested `<ws>/sub/repo/.rbtv/runtime/`, and
a copy of the scheduler planted at `<ws>/sub/repo/ignite/deploy/`. It reads back the MODULE-LEVEL
`WORKSPACE_ROOT`/`LATEST` (the values that actually decide where the artifact lands, not a
hand-supplied call), and proves: resolution answers `<ws>` and not the nested repo, the artifact
path lands in the real workspace, the skipped bare `.rbtv/` is named on stderr as not a workspace,
resolving creates nothing, a genuinely nested install still wins, and no record above raises naming
the record. RED CONTROL in the same run: the same source with the record test swapped back to
`os.path.isdir(d/'.rbtv')` resolves to the nested repo. A live arm asserts the installed scheduler's
own resolved root holds the install record on this box.

`ignite/observation/daemon-watchdog/probes/probe-watchdog-workspace-refusal.py` — 8 checks, exit 0.
A cwd rooting no install exits 2 with exactly one `refusing:` line naming the cwd and the record,
and writes NOTHING (the whole tree is asserted empty); a cwd holding a bare `.rbtv/` — the exact
stray shape — still exits 2 and leaves that folder empty; a cwd that DOES root an install is
accepted and written into, so the gate is not a blanket refusal. RED CONTROL: a copy with the
pre-fix `os.getcwd()` default does not refuse and PLANTS `<cwd>/.rbtv/runtime/watchdog/`,
reproducing the 03:02:15Z event. Only the `probe-suite` row runs and its restart lever is pointed at
`/bin/true`, so no live unit is ever named to systemd, and `RBTV_WATCHDOG_NOTIFY_FILE` makes a real
DM structurally impossible.

Regression, all run FROM THE REPO ROOT deliberately and `ls <repo>/.rbtv` checked absent afterwards:
`probe-watchdog-staged-failure` PASS, `probe-watchdog-bit7-silence` 20 checks,
`probe-g188-daemon-identity` 112/112, `probe-runner-grade-verdicts` 11/11,
`probe-watchdog-alarm-registry` 31 checks 0 failed, `probe-watchdog-alarm-transport.js` 11 checks
exit 0, plus the two new probes. `probe-suite-scheduled.py --selftest` OK. `tmux ls` byte-identical
before and after (md5 6799216b48eb55914caad21712ca0138).

TWO PRE-EXISTING REDS, PROVEN NOT MINE: `probe-watchdog-dry-run-no-dm` (2 failures) and
`probe-watchdog-alarm-exit-zero` (3 failures) fail identically against a pristine `git archive` of
HEAD 2659b948. Both assert the owner-DM leg still fires on an `alarm` verdict, which `a5b57bc0`
deliberately removed; they were not updated with it. Surfaced, not fixed.

DEPLOYED: both halves, immediately, with NO restart — both units ExecStart the source tree per
fire. Live proof, read-only, within two minutes of the teardown: the 07:36:17Z watchdog pass printed
`probe-suite alarm suite is LIVE but the correctness verdict is RED: 18 genuine probe failure(s) …
last fired 2170s ago` and `already open in the alarm registry since 2026-08-28T02:58:37Z`, with ZERO
`down … stale` lines in the window. That RED alarm is the standing TRUE condition and is unchanged:
`.rbtv/runtime/ignite/alarm-registry.json` holds exactly one row, opened 02:58:37Z with
`emission_count: 1`, never cleared. No `probe-suite DOWN` condition ever existed in the registry —
the `down` leg is `main()`'s restart-then-`alerts.append` path, not `raise_row_alarm`, which only
the `alarm` verdict reaches. `state.json` read `{"alert": null, …, "at": "2026-08-28T07:35:08Z"}`
on the first post-teardown pass, so the false DM fingerprint is cleared and the owner's next DM on
this condition is silence.

## ATTENTION
1. A `.rbtv/` DIRECTORY IS NOT A WORKSPACE. The test is the install record
   `.rbtv/modules/ignite/server.json`. Any resolver that walks up for a bare `.rbtv/` can be
   redirected by any process that ran once with the wrong cwd, and the folder it lands on is
   gitignored, so nothing in `git status` or a review will ever show you the decoy.
2. When two components disagree about one artifact and each insists its own read is right, look for
   a nested `.rbtv/` between them BEFORE reading either component's logic. Here the watchdog and the
   probe suite were both correct about the file they were reading; they were reading different
   files four directory levels apart.
3. Any probe that spawns `rbtv-ignite-watchdog` MUST set `RBTV_WATCHDOG_WORKSPACE`. It now exits 2
   without one, which is loud — but the reason it exits is that setting every other environment key
   and forgetting this one is exactly how the 03:02:15Z folder was planted.
4. The env override is deliberately NOT validated against the install record. Five probes point it
   at scratch trees that carry none; adding validation would convert all of them into tests of the
   refusal and prove nothing about the watchdog.
5. The refusal lives in `main()`, not at module level. `probe-g188-daemon-identity` and
   `probe-runner-grade-verdicts` import this tool as a module and set `W.WORKSPACE` themselves; a
   module-level `sys.exit` would kill them at import and the failure would look like a broken probe,
   not a workspace gate.
- a bare .rbtv/ directory is NOT a workspace — the test is .rbtv/modules/ignite/server.json
- two components disagreeing about one artifact: look for a nested .rbtv/ between them first
