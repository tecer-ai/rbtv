# 20260901-c-gtools-config-yaml-bridged-to — gtools config.yaml bridged to caged seats via env var

kind: creation
component: supervisor
date: 2026-09-01
commit: 16ce9a7e
deployed: no
pin: ignite/envelope/probes/probe-gtools-config-bridge.js
components: envelope

## Motivation
`d-gtools-config-bridge` (escalation #9 remedy 2, owner ruling 2026-09-01) — extends
`20260901-c-gtools-broker-bridge-broker-so` (`envelope`, commit `8d353105`). That fix bridged the
credential BROKER (the token exchange), but `gtools`' own `load_config()` reads
`3-resources/tools/gtools/config.yaml` first, before it ever gets to authenticating — and
`config.yaml` is itself an enumerated private-scope `deny` entry (T2-R11/D19), so it read absent
in every cage and `load_config()` hard-exited. Every caged `gtools` SERVICE command died before
the broker fix could even run, account resolution failing first. Re-verified against the current
tree: `.rbtv/config/private.json` still lists `3-resources/tools/gtools/config.yaml` as a `deny`
entry (line 25); `scripts/auth.py`'s `load_config()` (pre-fix) unconditionally hard-exited when
`CONFIG_FILE` was missing, with no environment-variable route (confirmed by grep — no
`environ`/`getenv` hit anywhere in account/config handling).

## Design
Same shape as the broker socket it sits beside, not a new mechanism: `admitted.accountCredentials`
(the array `ensureGoalBroker` already reads) gates a SECOND `--setenv`, `IGNITE_GTOOLS_CONFIG`,
pointing at a materialized copy of `config.yaml` inside the goal's own `scratch/` tree — the SAME
already-RW `scratch-temp` family (`envelope-template.yaml` family 4) the broker socket lives in, so
this costs no new bind vocabulary. Rejected: piercing the private-scope mask for `config.yaml`
(`private-scope.js` TIER 3's named-grant pierce could technically do it) — that is exactly the
`exposedCliCode` grant-class mechanism `20260824-c-delete-credential-pierce-role` deleted under
T2-R11/D19 ("credentials are env-injected, never caged"); re-opening it for this case would
contradict a live, permanent ruling. Verified `config.yaml`'s own content first (account
names/emails/scopes only, no OAuth tokens/secrets) before treating a materialized COPY as safe —
copying it is not the T2-R11/D19 violation a mask pierce of the credentials directory would be.

A missing source `config.yaml` is NOT a launch refusal: `materializeGtoolsConfig` returns `null`
and the `--setenv` is skipped, logged as a warning. This was found the hard way — the first version
threw on `fs.copyFileSync` when no source existed, which crashed `probe-credential-broker.js` and
`probe-credential-broker-lifecycle.js` (their fixtures never needed a `config.yaml` before this
change existed). Fixed at the cause: an add-on for a workspace that HAS a gtools install (the real
vault always does) must not become a new hard requirement on every credentialed launch.

## How it works
`ignite/supervisor/spawn/spawn.js#composeCageFor`, inside the existing
`if (admitted.accountCredentials?.length > 0)` block (same block the `IGNITE_CREDENTIAL_BROKER_SOCK`
`--setenv` already lives in):
```
const gtoolsConfig = materializeGtoolsConfig(seatPath.goalDir, seatPath.workspaceRoot, log);
if (gtoolsConfig) flags.push('--setenv', 'IGNITE_GTOOLS_CONFIG', gtoolsConfig);
```
`materializeGtoolsConfig(goalDir, workspaceRoot, log)` copies
`<workspaceRoot>/3-resources/tools/gtools/config.yaml` to `<goalDir>/scratch/gtools-config.yaml`
(creating the dir) and returns the destination path, or `null` + a `log('warn', ...)` if the source
does not exist. Called on EVERY `composeCageFor` invocation that declares the credential — i.e.
every caged seat launch of the goal, not just the first — so a `config.yaml` edit on disk reaches
the NEXT seat launch, never permanently stale (no live-refresh within an already-running seat).

gtools side (separate repo, `3-resources/tools/gtools`, commit `1050554`):
`scripts/auth.py#load_config()` now checks `os.environ.get("IGNITE_GTOOLS_CONFIG")` first; when
set, reads that path (loud `sys.exit` naming the env var if it does not exist); unset, falls
through to the original `CONFIG_FILE` read, byte-identical. `gtools.py`'s separate `config.yaml`
reader (`accounts_of`/`doctor`, used by `gtools doctor`/`gtools accounts`) got the same override
via a shared `config_path()` helper — it read `ROOT / "config.yaml"` directly and would otherwise
have stayed broken in-cage even after the SERVICE-command path was fixed.

## Consequences
Every caged `gtools` SERVICE command (`gmail`, `drive`, `calendar`, `meet`) can now resolve an
account and reach the broker inside a cage, closing the last link `d-gtools-broker-bridge` left
open. `gtools doctor`/`gtools accounts` also work in-cage now (previously untouched by the broker
fix, since they bypass `auth.py` entirely). No change to any uncaged/ordinary invocation of gtools
anywhere. Not deployed — `ignite/supervisor/spawn/spawn.js` is pinned to the deploy worktree
(`~/.local/state/rbtv-deploy`); the live `transcript-summarizer-build` goal's caged gtools calls
will only see this once both repos deploy.

## Verification
New `ignite/envelope/probes/probe-gtools-config-bridge.js` (extends
`probe-credential-broker-lifecycle.js`'s fixture pattern: FIXTURE `/var/tmp` workspace + fixture
`scripts/auth.py` mirroring the real env-var contract + a `.rbtv/config/private.json` `deny` entry
mirroring the real `config.yaml` mask; REAL `admitLaunch`/`composeCageFor`/
`materializeGtoolsConfig`/bwrap) — 12/12 legs pass: materialization, byte-identical copy,
env-var advertisement, the T2-R11/D19 regression (original `config.yaml` proven unreadable inside
the SAME cage via `PermissionError`), a real caged process authenticating through the env-config
route, refresh-on-next-seat-launch (a mid-goal edit reaches seat B, not seat A), and a loud named
failure when the env var points at a missing path. Regression arms re-run green via
`node ignite/deploy/probe-suite.js --only probe-credential-broker --only
probe-credential-broker-lifecycle --only probe-envelope-walls --only probe-gtools-config-bridge`
(verdict=GREEN, 4/4 passed) — this run is also what caught and fixed the missing-source crash
above. Separately, at the gtools repo: manual proof of `load_config()`'s three legs (CONTROL:
env unset reads on-disk `config.yaml`, `['ignite','pessoal','tecer']`; override to a fixture path
returns `['fixture-acct']`; override to a missing path exits 1 with a named
`IGNITE_GTOOLS_CONFIG is set to ... but that file does not exist` error). `gtools selftest`: ran
before AND after at a pristine `git worktree add` of the gtools repo's prior HEAD (`fbb97bf`) with
the real `.venv` symlinked in — exits 0 in BOTH cases; the `prog rewrite lost: ''` defect the
escalation flagged did not reproduce at either revision (stale, unrelated to this change, not
chased).

## ATTENTION
1. `materializeGtoolsConfig` degrades to "no copy, no env var" when the source `config.yaml` is
   missing (see Design) — it does NOT refuse the launch. A goal that genuinely needs the config
   bridged but whose workspace has no `3-resources/tools/gtools/config.yaml` gets silent-to-rbtv,
   loud-to-gtools failure (gtools' own masked-absent hard exit fires instead) — there is no rbtv-side
   signal distinguishing "nothing to bridge" from "config genuinely missing" beyond the `log('warn', ...)`
   line.
2. `IGNITE_GTOOLS_CONFIG` is gated on the SAME `admitted.accountCredentials` array
   `IGNITE_CREDENTIAL_BROKER_SOCK` already uses (same drift risk `20260901-c-gtools-broker-bridge-broker-so`'s
   ATTENTION #1 already names for the broker var) — if a future change ever separates these two
   env vars' gating, keep them reading the same source or they will drift silently.
3. The gtools-side fix lives in a SEPARATE git repository (`3-resources/tools/gtools`, branch
   `feat/gtools-cli`, commit `1050554`) from the rbtv change (`16ce9a7e`) — both must be present
   for the bridge to work; deploying the rbtv side alone advertises a path gtools' pre-fix
   `load_config()` never looks for (harmless — falls through to its unchanged on-disk read, still
   masked-absent in-cage, so the ORIGINAL escalation #9 symptom persists until gtools also ships).
4. `gtools.py`'s `doctor`/`accounts_of` now read `config_path()` (env-override-aware) but every
   OTHER hardcoded `ROOT`-relative read in that file (script paths, venv path) is untouched by
   design — only the `config.yaml` read needed the cage bridge.
- materializeGtoolsConfig degrades to no-copy-no-env-var on a missing source, never refuses the launch — a genuinely-missing config still fails, but only at gtools' own hard exit, not visibly on the rbtv side
- IGNITE_GTOOLS_CONFIG shares its gate (admitted.accountCredentials) with IGNITE_CREDENTIAL_BROKER_SOCK — keep them reading the same source
- gtools-side fix is a SEPARATE repo commit (1050554, feat/gtools-cli) — both must ship together
