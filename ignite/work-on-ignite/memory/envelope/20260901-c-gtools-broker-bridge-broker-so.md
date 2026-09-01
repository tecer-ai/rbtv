# 20260901-c-gtools-broker-bridge-broker-so — gtools-broker-bridge: broker socket + venv-python minter fix

kind: creation
component: envelope
date: 2026-09-01
commit: 8d353105
deployed: no
pin: ignite/envelope/probes/probe-credential-broker-lifecycle.js
components: supervisor

## Motivation
`d-gtools-broker-bridge` (owner ruling, 2026-09-01): the credential token broker
(`ignite/envelope/credential-broker.js`, wired into the launch path `e233584b`) was live but had
NO consumer — `transcript-summarizer-build`'s seats shell out to the external `gtools` CLI, whose
`auth.py` reads `token.json` from a credential directory directly, and that directory is (per
T2-R11/D19) never bound into a cage. This entry is the last unbuilt link: teach `gtools` to ask
the broker when one is advertised, and leave every uncaged/ordinary invocation unchanged. Folded
into the same seat: the judge-deploy window-5 finding that `gtools-token-minter.js` execs bare
`python3`, which has no `google` module, so the first-ever real-account mint died before touching
any account.

## Design
Two structurally separate fixes, same chain. (1) `composeCageFor` had no existing mechanism to
tell a caged seat WHERE the broker socket lives — `gateway-env` is the only precedent, and it is
opt-in per seat declaration. The broker socket needed no such gate: it is authorized by the same
`admitted.accountCredentials` array `ensureGoalBroker` already reads to decide whether a broker
exists for this goal at all, so advertising `IGNITE_CREDENTIAL_BROKER_SOCK` under that identical
condition costs nothing new and cannot fire for a seat with no declared account. (2) On the gtools
side, `auth.py#get_credentials` is the ONE choke point every one of the 11 tool scripts funnels
through via `get_service` — confirmed by grep, no second entry point exists — so the broker check
is a single early-return, not a spread change. It is placed AFTER the unknown-account check (so
that refusal is unchanged) and BEFORE any token_file access, so the broker path never touches
`credentials.json`/`token.json` even if they happen to be present (masked-to-tmpfs or not).

## How it works
- `ignite/supervisor/spawn/spawn.js#composeCageFor`: `if (admitted.accountCredentials?.length > 0)
  flags.push('--setenv', 'IGNITE_CREDENTIAL_BROKER_SOCK', brokerSocketPath(seatPath.goalDir))` —
  placed beside the existing `gateway-env` `--setenv` block, using `credential-broker.js`'s own
  exported `socketPath(goalDir)` so the advertised path can never drift from what the broker
  actually listens on.
- `ignite/envelope/gtools-token-minter.js#gtoolsPython(gtoolsRoot)`: derives
  `path.join(gtoolsRoot, '.venv', 'bin', 'python3')`, falling back to bare `python3` only if that
  path does not exist (keeps every fixture-root probe, which never imports `google`, unaffected).
  Computed once per `gtoolsTokenMinter(gtoolsRoot)` closure, not per call.
- `gtools/scripts/auth.py#get_credentials` (gtools repo, commit `fbb97bf`): reads
  `IGNITE_CREDENTIAL_BROKER_SOCK`; if set, `_mint_via_broker(account, sock)` opens one
  `AF_UNIX` connection, sends `{"op":"mint","account":...}\n`, reads one newline-delimited JSON
  response — the exact protocol `credential-broker.js#startBroker` implements — and returns a
  bare `Credentials(token=accessToken)` (no refresh_token; the broker is the thing that refreshes).
  Any connect/timeout/parse/`ok:false` outcome is `sys.exit(...)`, a loud named message, never a
  silent fallback and never a hang (`socket.settimeout(10)`).

## Consequences
`gtools-token-minter.js`'s bare-`python3` exec is retired; every future `gtoolsTokenMinter` call
uses the derivation. `stopGoalBroker`/`endGoalBroker` remains unwired (pre-existing, named in
`20260901-c-wire-the-credential-broker-int.md`, not this seat's custody). The live goal's
`envelope.json` still declares the old bare-string `credentialNames` shape and was NOT migrated
(live-goal mutation, outside this seat's walls) — named in the report's READY-TO-DEPLOY block as
an ordered follow-up step, after this lands + deploys + the owner re-authenticates the three
accounts (`invalid_grant` on all three, unrelated to this fix, owner-only interactive OAuth).

## Verification
`probe-credential-broker.js` 6/6, `probe-credential-broker-lifecycle.js` 11/11,
`probe-credential-account-admission.js` 2/2, `probe-envelope-walls.js` 13/13 — all green,
assertions unchanged. `gtools selftest` (gtools repo) unaffected. Standalone bwrap-caged proof
(not committed as a probe — no test infra spans both repos in this tree): a real bwrap cage with
`gtools/credentials` masked to an empty tmpfs and the venv-bound gtools tree ro-bound gets a
working fixture token through `auth.get_credentials()` unmodified — the exact call any real
gtools script makes; the credential directory is proven absent inside that same cage
(`os.path.exists` → False, the T2-R11/D19 regression check); the same cage with the broker
stopped fails in <1s with `ERROR: credential broker unreachable at ...`, never a hang; an uncaged,
no-env-var run of the patched `auth.py` against a real account produces the byte-identical
`RefreshError: invalid_grant: Bad Request` the pristine `git show HEAD:scripts/auth.py` produces
for the same call (the CONTROL). The minter fix separately verified via
`gtoolsTokenMinter(realGtoolsRoot)('pessoal')` and the raw CLI form: the traceback moves from
`ModuleNotFoundError` at the `import auth` line to `RefreshError: invalid_grant` inside
`auth.get_credentials`, i.e. past the import, at the owner's separate, expected, out-of-scope
failure. Not deployed — `ignite/supervisor/spawn/spawn.js` is pinned to the deploy worktree.

## ATTENTION
1. `IGNITE_CREDENTIAL_BROKER_SOCK` is gated on `admitted.accountCredentials`, the SAME array
   `ensureGoalBroker` reads — if a future change ever separates "does this goal have a broker" from
   "does this seat get the env var", the two reads will drift silently. Keep them reading the same
   source.
2. `gtoolsPython()`'s fallback to bare `python3` when no venv exists at `<gtoolsRoot>/.venv/bin/
   python3` is deliberate (every fixture-root probe relies on it), but it means a REAL gtools tree
   whose venv gets deleted/moved will silently regress to the ORIGINAL `ModuleNotFoundError`
   defect with no refusal — there is no loud check that the venv exists, only a quiet fallback.
3. `auth.py#_mint_via_broker` builds `Credentials(token=...)` with no `refresh_token` — this is
   correct for a broker-backed account (the broker, not `google-auth`, owns refreshing), but any
   future caller that expects the returned `Credentials` object to self-refresh past its
   `expiresAt` will find it cannot; a long-running caged process must re-mint through the broker,
   not rely on the object it already holds.
4. The gtools-side fix lives in a SEPARATE git repository (`3-resources/tools/gtools`, branch
   `feat/gtools-cli`) from the rbtv changes — the two commits (`8d353105` rbtv, `fbb97bf` gtools)
   must both be present for the bridge to work; a deploy of the rbtv side alone advertises a
   socket gtools' auth.py (pre-fix) never looks for.
- gtoolsPython() silently falls back to bare python3 if the venv is ever missing/moved — no loud check, just the original ModuleNotFoundError regressing quietly
- the gtools-side half lives in a SEPARATE repo (3-resources/tools/gtools, commit fbb97bf) — both commits must ship together or the advertised socket has no consumer
