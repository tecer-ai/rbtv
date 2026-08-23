# 20260821-c-secret-add-mediated — Secret add mediated

kind: creation
component: server
date: 2026-08-21
commit: ac1c08d8,b6c64a25,92e7156c
deployed: yes
pin: server/internal-api/probes/probe-secret-add.js; server/spawn/probes/probe-secret-add-cage.js; team-kit/test_secret_add.py (UNSCHEDULED)
components: gateway,team-kit
seeded: true

## Motivation

D-6 was still open on 2026-08-21: `goal-master` sat in the same `bwrap` cage as workers, so a one-line permission edit the owner had already ruled had to be typed in an unsandboxed terminal. D48 that day picked option C (wide master cage) and amended it — the manager must also WRITE secrets append-only (owner hands a new integration key; it lands in the env file) while reading existing secrets stays denied. The mechanism was still being interviewed: mediated command vs mount, and the tension with "never paste keys into chat." D49 (owner, same interactive session) settled it: (1) mediated `secret add` — receiver out-of-cage with stamped identity, append-only, refuse a NAME that already exists, never echo the value into bus, ledger, or logs; secrets stay read-masked in every cage so "a master can write a key it can never read back"; (2) truly-everything cage for all master roles (sibling `20260821-c-truly-everything-master-cage`); (3) key delivery is a drop file whose name is agreed in the occasion — keys do not live in chat.

## Design

Two sittings the same afternoon, because the first one missed D49's "receiver (out-of-cage)."

`92e7156c` (15:58Z) landed MasterBinds first: `*-master` roles (not `console-master`) get workspace RW, secrets still private-scope masked. Then `b6c64a25` (16:49Z, seat `secret-add`) added `coordinate secret-add <NAME> --from-file <path>` inside `coord.py`: `_secret_add_authority` via the F-8 ladder (pane / `COORD_AGENT` / cgroup→roster, never `--as`), `SECRET_ADD_NAME_RE`, refuse a drop under `.rbtv/goals/`, `fcntl.flock` exclusive on the env file, `_env_file_has_name` refuse, append, unlink. The sitting chose an in-process receiver on purpose — `coord.py` is live per invocation; a new gateway intent would be inert until deploy and would key on sender tokens, not F-8. That choice was wrong against D49: the master cage (`92e7156c`, then undeployed) masks `.rbtv/config/.env`, so an in-cage append cannot land. Only the uncaged owner console worked. The sitting also shipped a help-suppressed `--env-file` / `COORD_SECRET_ENV_FILE` hatch for fixtures and told the owner to drop keys in `/tmp` — cage `bwrap` uses `--tmpfs /tmp`, so a host `/tmp` file is invisible in the cage and a cage `/tmp` file is invisible to a later daemon.

`ac1c08d8` (17:23Z, seat `secret-add-2`, labelled D49.1) kept the CLI and the client gates, closed the hatch, and moved the write to out-of-cage daemon intent `secret-add`. Rejected: relying on the mask alone (D49 already required a mediated receiver); leaving the write in `cmd_secret_add` (fails the mask); any client-chosen env path ("a caller must not redirect the append"). The only remaining override is daemon-process `RBTV_IGNITE_SECRET_ENV_FILE`, which a cage cannot set.

## How it works

Owner puts a one-line value at a workspace path the master can read — not `/tmp`, not under `.rbtv/goals/` — and names the file and the env NAME. The master runs `coordinate secret-add THE_NAME --from-file /path/in/the/workspace/agreed.txt`.

`cmd_secret_add` never reads the value. `_secret_add_authority` admits only a proven `goal-master` / `channel-master` / `console-master`, or an uncaged console (empty `actual` and no seat id); a bare `--as` that does not match the F-8 identity is refused with no `--force`. Then NAME-shape, drop-is-file, `_drop_under_goals`. Then `gateway_client.secret_add` POSTs `{name, from_file}` only.

Gateway parse admits intent `secret-add`. `handleSecretAdd` rejects any payload key other than `name` and `from_file` (including `env_file`). `authz.canSecretAdd` allows the owner, a proven master seat, or an enrolled agent token with no proven seat. `applySecretAdd` re-validates NAME and absolute `from_file`, refuses drop-under-goals and drop-is-env, resolves the file via `resolveSecretEnvFile` (`rbtv.json` `env_file` or `.rbtv/config/.env`), refuses a missing env (the owner creates it; this intent only appends), refuses an existing NAME via `envFileHasName` (no update, no delete, no read-back; drop left), reads the drop, refuses empty / multiline / NUL value, appends `NAME=value\n`, unlinks the drop. The handler logs only `{name, envFile, dropConsumed, senderId}`. Success prints `appended NAME to <env>` and whether the drop was consumed — never the value.

## Consequences

Replaced the in-process append in `cmd_secret_add` (`b6c64a25`): the flock, `_env_file_has_name`, `--env-file` hatch, and the happy-path / duplicate-NAME selftest arms that asserted on env contents. `test_secret_add.py` shrank 200→152 lines; what remains is client gates only. No later commit has reopened `secret-add.js`, `canSecretAdd`, or `cmd_secret_add`.

Same sitting recorded G-123: live seats often have no proven `sender.seat`, so the daemon admits `kind: agent` with no seat (the same approximation as `register-job`). A worker who bypasses `coord.py` and speaks the shared agent token can append. F-8 still blocks the CLI; when a seat IS proven, workers are refused daemon-side. D60 sent G-123 to investigation; it is not closed here.

D56 later named `secret-add` the only install path for an owner-posted secret. D68 reused the D49.1 pattern (caged request, uncaged daemon write, stamped identity) for the deploy intent. `92e7156c`'s new `ro-mask` verb is not this write path; its next-day spawn-kill (`6b55b1c4`, D53/#576) lives on the sibling cage entry.

## Verification

`b6c64a25`: fixture happy path plus four refusal arms (existing NAME, worker, uncorroborated `--as`, drop-under-goals) and a red-proof (mutated `_env_file_has_name` on a copy appended a duplicate); `coord.py selftest` and `test_secret_add.py` PASS. Deploy not owed — live Python, no JS.

`ac1c08d8`: `probe-secret-add-cage.js` 8/8 — caged dummy `TEST_SECRET_ADD2_CAGE` lands, drop gone, value absent from output; in-cage `echo >> env` does not land (`host_has_direct=false`); worker / `--as` / goals-drop / duplicate-NAME refusals quoted; dummy value absent from stdout, stderr, daemon logs, and `coordination/`. `probe-secret-add.js` 15/15 — in-process parse+dispatch+authz on a scratch env under `os.tmpdir()` (never the live `.env`); owner / agent / master allowed, worker / bridge refused; `env_file` payload field refused at the gateway door. `probe-intent-drift.js` INTENTS lockstep size 12. `coord.py selftest` (hatch-closed + worker + `--as` + goals-drop). `test_secret_add.py` PASS. Red-proof: mutated `envFileHasName` on a copy, `dup_count=2`, copy discarded.

Deployed 2026-08-21 18:14:37Z at `ac1c08d8` (`fix-inventory.csv` D49). Until that deploy a caged master talking to the live daemon got `UNKNOWN_INTENT`.

## ATTENTION

- `team-kit/test_secret_add.py` is a standalone pytest file `probe-suite.js` does not discover (same unscheduled-standalone pattern as D43/D45/F-8). The scheduled JS probes pin daemon parse/authz/cage landing, not the Python client gates; touching `_secret_add_authority` or the hatch-closed parser and running only the suite is a false pass.
- The write lived in `cmd_secret_add` for ~34 minutes (`b6c64a25` 16:49Z → `ac1c08d8` 17:23Z) and failed the `.env` mask. Putting the append back in the caged process, or adding any other in-cage write of a private-scope path, repeats that miss.
- `--env-file` / `COORD_SECRET_ENV_FILE` was a fixture hatch in `b6c64a25` and was closed in `ac1c08d8` ("a caller must not redirect the append"). The only remaining override is daemon-process `RBTV_IGNITE_SECRET_ENV_FILE`, which a cage cannot set and which the production unit must not export.
- The drop file must be a workspace path the master can read. Host `/tmp` is invisible inside the cage (`bwrap --tmpfs /tmp`); a cage `/tmp` file is invisible to the daemon. `.rbtv/goals/` is refused on both sides — live goal ledgers are not a mailbox.
- `canSecretAdd` admits an enrolled agent token with no proven seat (G-123). "Only a master can add a secret" is enforced by `_secret_add_authority`, not fully by the daemon. Tightening the client without tightening the receiver, or assuming the two gates match, leaves the wire open.
