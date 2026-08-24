# 20260824-c-wall-report-scratch-config-shi — wall-report + scratch-config shims

kind: creation
component: server
date: 2026-08-24
commit: 7dd03133,0b08e042,be0458b9,1d0f4903
deployed: no
pin: ignite/envelope/wall-report.selftest.js

## Motivation
The envelope redesign left three leftovers: a benign-shaped wall had no template-edit report record [T2-R6] [C-6]; tools that read config files were still fed by remounting harness auth stores [T2-R11]; and the old per-seat grant probes tested deleted behavior.

## Design
New `ignite/envelope/wall-report.js` writes `{path, family-match, seat, goal}` and never posts Slack. New `ignite/envelope/shims.js` copies harness stores and stools/gtools `config.yaml` into `{goal}/scratch/config-shims/` from `admitLaunch`. `spawn.js` lost `resolveHarnessCredGrants` / `HARNESS_CRED_PATHS` rather than growing a second remount. Residual TIER-3 pierce in `private-scope.js` now refuses credential-shaped hosts. Rejected: remounting the real store under a different bind name; Slack-posting from this seat.

## How it works
`writeWallReport` classifies cache/config/temp shape from the template families and writes `coordination/template-defect.json`. `admitLaunch` calls `writeConfigShims` so launch-time copies land in goal scratch; compiled binds never list the real store path. `composePrivateScope` refuses a named opening whose host basename is `credentials`, `*.env`, `*.key`, or `*token*`.

## Consequences
Replaced the harness-cred remount surface. Retired `probe-seat-grant-classes`, `probe-seat-rw-paths`, `probe-master-cage`, `probe-cli-write-roots`, `probe-secret-add-cage`. Rewrote private-scope / exposed-cli / register-door probes onto the bind-list model. `composeCageFor` still re-runs `conflictBind` when `exposed-clis` is declared (launch custody) — authorized vault-ro/goal-rw carves look like conflicts; that sitting cannot be driven here.

## Verification
`node ignite/envelope/wall-report.selftest.js` printed `PASS wall-report` with `family-match=cache` on a `~/.cache` miss and `family-match=none` on `/usr/share/doc`. `node ignite/envelope/envelope-shims.selftest.js` printed `PASS shims` with the claude store and stools `config.yaml` copied into goal scratch and `leaked=0` against the composed bind list. `node ignite/envelope/envelope-launch.selftest.js` still printed `PASS refusal` and `PASS injection`. `grep -rn 'resolveHarnessCredGrants\|HARNESS_CRED_PATHS' ignite/ --include='*.js'` returned empty. `node --check` exited 0 on every new or edited `.js`. Deployed no.

## ATTENTION
- Do not put a real harness store or `.rbtv/config/.env` on the composed bind list — the shim is the only legal file-config door.
- `family-match != none` is a template-edit ask record, not a strike and not a Slack post; impl-slack consumes the file.
- Driving `composeCageFor` with `exposed-clis:` re-runs `conflictBind` over the compiled list and will refuse a normal vault-ro/goal-rw envelope; that check is launch custody.
- Do not remount a real harness store or .rbtv/config/.env — the scratch shim is the only file-config door.
