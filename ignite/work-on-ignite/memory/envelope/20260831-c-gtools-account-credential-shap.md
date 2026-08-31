# 20260831-c-gtools-account-credential-shap — gtools-account credential shape + token broker

kind: creation
component: envelope
date: 2026-08-31
commit: 14fe57d0
deployed: no
pin: ignite/envelope/probes/probe-credential-broker.js
components: planning

## Motivation
`transcript-summarizer-build` (approved, live) declares three gtools OAuth account names
(`pessoal`, `tecer`, `ignite`) as `credentialNames`, and `admitLaunch` refused every launch —
`resolveCredentials` only ever knew how to resolve a bare string against `.rbtv/config/.env`.
Owner ruled the extension mechanism (`d-credential-account-shape`, then `d-ask17-credential-
token-broker`, against the implementing seat's own file-copy recommendation): a daemon-side
token broker, never a materialized copy of the account's login files inside a cage.

## Design
Two failure moments, designed separately (full record: `1-projects/build-ignite/build/
redesign-continue-1/cred-account-shape-design.md` §9-11, vault-side): (1) admission-time —
`credentialNames` accepts a typed `{type:'gtools-account', account}` entry alongside bare
strings; `resolveAccountCredentials` checks the account's `credentials.json`/`token.json`
files exist on disk, no network call, same "exists, non-empty" bar the bare-string case
already used — folded into the SAME `missing-credential` refusal `admitLaunch` already
produced. (2) mint-time — `credential-broker.js#startBroker` opens ONE Unix domain socket per
goal at `<goalDir>/scratch/credential-broker.sock`, inside the family-4 scratch tree every
caged seat already gets RW — zero new bind vocabulary, zero envelope/template change. A seat
asks `{"op":"mint","account":...}`, gets a fresh short-lived access token or an explicit
`{ok:false,reason}` — never a cached/stale value, never a hang. The socket's own allow-list
(this goal's declared accounts) is checked server-side even though reachability is already the
primary boundary (only this goal's own cage can see the socket at all).

Rejected explicitly, and why: reusing the live `ignite/runtime/gateway/` (its sender model is
`owner`|`agent`|`bridge` — coarse, no per-goal/per-seat identity, so a shared `agent` token
could mint for an account the calling goal never declared); a per-account rw directory bind
(forbidden outright, `T2-R11`/`D19`, proven refused with `kind:"conflict"` via the
`**/credentials/` deny-list both before and after this change — probe leg REGRESSION).

## How it works
`envelope/launch.js#admitLaunch` splits `credentialNames` into bare-string entries (unchanged
path: `resolveCredentials` + `spawn.js#injectDeclaredEnv`) and account entries
(`resolveAccountCredentials`, `envelope/credentials.js`); missing arrays from both concatenate
into one refusal. On success, `accountCredentials` (the account name list) rides in
`admitLaunch`'s return, ready for a caller to start the broker — `credential-broker.js` is NOT
yet called from `admitLaunch` or `spawn.js` (see its own header: `admitLaunch` must stay fully
synchronous, `startBroker` is inherently async). The REAL minter,
`gtools-token-minter.js#gtoolsTokenMinter(gtoolsRoot)`, shells to `gtools_mint_token.py`, which
imports gtools' own `scripts/auth.py#get_credentials` (never re-implements the OAuth refresh
handshake) and prints only `{access_token, expiry}` — the refresh_token never leaves that one
python process.

## Consequences
Nothing deleted or broken — `credentialNames`'s bare-string contract, `injectDeclaredEnv`, and
every existing caller are untouched (full selftest suite green, unchanged assertions). Follow-
up NOT done here, named as a loose end in the seat's report: wiring `startBroker`/`stopBroker`
into `spawn.js`'s actual launch sequence (a live-daemon change this sitting deliberately did
not risk), and escalating a mid-run mint failure into the daemon's own alarm/report vocabulary
(`T2-R16`) rather than only the goal-scoped `credential-broker.log` audit line this version
writes.

## Verification
`envelope-launch.selftest.js` (new cases: `resolveAccountCredentials`, `admitLaunch` with a
present/missing/mixed account entry) — green. New probe `probes/probe-credential-broker.js`,
fixture minter only (no real account, no Google, no network) — 6/6 legs green: RED (today's
admission refusal), ADMIT, GREEN (a real `bwrap`-caged python process mints a working token
over the socket), ALLOWLIST (cross-account refused despite a live reachable broker), NEGATIVE
(the real `gtools/credentials/<account>` folder absent inside the cage), REGRESSION (a
directory bind on it still refuses `kind:"conflict"`). Not deployed as of this filing — commit
`14fe57d0`, `ignite/core-daemon` branch, uncommitted-to-deploy.

## ATTENTION
1. A test that needs the in-process broker to answer a caged child process MUST use `execFile`
   (async), never `execFileSync` — the sync call blocks the Node event loop the broker's own
   socket server runs on, producing a hang that looks like a broker bug but is a test-harness
   bug (measured directly building `probe-credential-broker.js`; `cagedRunAsync`'s own comment
   carries the full symptom).
2. `startBroker`/`stopBroker` are NOT wired into any live launch path yet — do not assume a
   caged seat can reach `scratch/credential-broker.sock` in production until a follow-up change
   lands in `spawn.js`.
3. `resolveAccountCredentials` checks file EXISTENCE only, never whether the OAuth grant is
   still valid at Google — that question is answered live, once, by the broker's first mint,
   deliberately not duplicated at admission (network calls at every launch would add latency
   and a new flaky-network failure mode to every launch of every account-declaring goal).
- execFileSync blocks the event loop an in-process broker test needs; use execFile
- startBroker not wired into spawn.js's live launch path yet
