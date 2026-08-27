# 20260827-i-gateway-lookup-was-cwd-only-no — gateway lookup was cwd-only: no seat could reach the daemon

kind: issue
component: ignite-cli
date: 2026-08-27
commit: 02d989ef
deployed: no
pin: ignite-cli/probes/probe-cli-server-json.js
components: deploy,coord,chat

## Observed
From a real daemon-spawned channel-master sitting (session `0d4bc9e9`, 2026-08-26, `cwd-mode: seat-folder` so cwd was `/home/henri/ht-wkdir/second-brain/.rbtv/goals/_channel-master/`), both `ignite status` and `rbtv ignite status` exited 2 with `USAGE ERROR: no gateway address configured. Set IGNITE_GATEWAY_ADDR, or run ignite from a workspace where <cwd>/.rbtv/modules/ignite/server.json names an installed server`. The same probe measured that the record DOES exist three levels up at `/home/henri/ht-wkdir/second-brain/.rbtv/modules/ignite/server.json`, and that `IGNITE_GATEWAY_ADDR` was unset in the spawned environment (the daemon's spawn argv carries only `COORD_AGENT` and `PATH`). The bare name resolved fine (`command -v ignite` -> `~/.local/bin/ignite`); the ACT did not. Recorded as CP-2 rows M39 (the status act) and M40 (the standing-warning read, which is the same act by another name — `standing_warnings` came back `None`). Deployed and HEAD were identical here: the client CLI is symlinked straight at the repo working tree, so there was no worktree/HEAD skew hiding the defect.

## Mechanism
`ignite/ignite-cli/lib/config.js` `resolveWorkspaceRoot()` was `path.resolve(process.env.RBTV_IGNITE_WORKSPACE_ROOT || process.cwd())` — one line, no search. `resolveGatewayAddr()` fed that straight into `serverJsonPath()` and `readServerJson()`, both of which join `.rbtv/modules/ignite/server.json` onto whatever it returned. So the endpoint record was only ever looked for at exactly one path: `<cwd>/.rbtv/modules/ignite/server.json`. D27 (`ignite/deploy/component.md` § Installation model) defines a workspace as "the folder that roots `.rbtv/`" — every folder nested inside that root is INSIDE the workspace — but the resolver implemented "workspace" as "cwd", which makes every nested folder wrongly outside it. Since a seat's cwd is its own seat folder by design and the daemon sets no `IGNITE_GATEWAY_ADDR`, both of the CLI's two resolution routes were dead for every seat simultaneously, and the failure was total rather than intermittent.

## Attempts
First attempt held. Checked before building: `git log --follow` on `ignite/ignite-cli/lib/config.js`; the `work-on-ignite` memory for `cli`, `coord`, `gateway` and a grep floor over every `_issues.md`/`_creations.md` (nothing had ever touched gateway-address resolution); `ignite/deploy/component.md` § Installation model for D27 itself, which describes the record's scope but nowhere rules that the lookup is cwd-only — so no ruling barred the walk. The nearest prior art is in the SAME file: the sender-token half (`readEnvFileToken`, owner-directed 2026-08-07) already walks up from cwd, with a comment stating the walk is "what makes this work from a SEAT FOLDER". The address half was simply never given the same treatment, and the token walk was written for the identical caged case.

## Fix
`resolveWorkspaceRoot()` now starts at the explicit `RBTV_IGNITE_WORKSPACE_ROOT` override, else the cwd, and calls a new `findInstallRoot(start)` that walks up to the NEAREST ancestor holding `.rbtv/modules/ignite/server.json`; when no ancestor holds one the start dir is returned unchanged so the not-installed error paths keep naming a concrete path. Nearest wins, so a nested workspace shadows an outer one — the same rule git uses for its own root. `IGNITE_GATEWAY_ADDR` keeps its precedence: `resolveGatewayAddr()` returns before the search when it is set.

The walk was put in `resolveWorkspaceRoot()` rather than in `resolveGatewayAddr()` because that function's NAME is the contract being violated — it claims to return the workspace root and returned the cwd — and because every other reader in the file (`serverJsonPath`, `readServerJson`, `resolveToken`) then inherits the correct root instead of each growing its own loop.

REJECTED: stamping `IGNITE_GATEWAY_ADDR` onto the daemon's spawn environment. It would fix only daemon-spawned seats and leave a console user in any subfolder still refused, and it adds a second resolution mechanism next to the one D27 already names. Ruled out by the orchestrator before the work started, and the walk-up is strictly more general.

Two sibling sites carry the same error string and were deliberately NOT changed, because neither is cwd-only and neither exhibits the defect: `ignite/coord/gateway_client.py` takes `workspace_root` as an explicit argument and its only callers (`coord/messages.py`) pass `coord.py`'s fixed `VAULT_ROOT` constant, and `ignite/chat/index.js` resolves `gatewayAddr` from the bridge's config file / env (`chat/config.js`) and never consults `server.json` at all. Copying the walk into either would be a second mechanism guarding nothing.

## Consequences
The usage error's text changed: it now says the resolver walks up from `<startDir>` looking for `.rbtv/modules/ignite/server.json`, and distinguishes "no ancestor holds one" from "a record was found but names no installed server". Anything grepping for the old exact sentence will miss.

`resolveToken()` calls `readEnvFileToken(resolveWorkspaceRoot())`, so the token walk now starts at the install root instead of the raw cwd. Harmless in every real and fixture case — the token file lives at the same workspace root, and when no install record exists at all the start dir is returned unchanged, which is exactly the old behaviour (this is the case `probe-cli-server-json`'s caged-leg check exercises, and it still passes).

Behaviour genuinely widened: a caller standing anywhere under an installed workspace now reaches that workspace's daemon where it used to get a local refusal. That is the point of the fix, but it means an ad-hoc script run from inside the vault that previously failed closed will now talk to the LIVE daemon. Probes are unaffected because every one of them sets `RBTV_IGNITE_WORKSPACE_ROOT` (or an explicit `IGNITE_GATEWAY_ADDR`) at a throwaway root under `/tmp`.

Docs moved in the same change: `ignite/ignite-cli/README.md` § Auth / config and the D27 paragraph in `ignite/deploy/component.md` both now state the walk-up and the nearest-wins rule.

## Verification
Commit `02d989ef` on `ignite/core-daemon`.

Discriminating before/after from the seat folder, both `IGNITE_GATEWAY_ADDR` and `RBTV_IGNITE_WORKSPACE_ROOT` unset (the override was inherited by the verifying session and confounded a first attempt at this check — it must be unset or the walk is never exercised): `git show HEAD:...config.js` in a temp dir REFUSES with the original error naming `<seat-folder>/.rbtv/modules/ignite/server.json`, while the fixed file resolves `ignite-alfa.tailf44c73.ts.net:7431`.

End to end from `/home/henri/ht-wkdir/second-brain/.rbtv/goals/_channel-master`, both vars unset: `ignite status --json` -> exit 0, `ok=True pid=2256302 standing_warnings=[] queue_depth=3`; `rbtv ignite status --json` -> the same. Control from `/tmp` (outside any workspace), both routes: exit 2 with the new usage text, `no ancestor holds one`.

`node deploy/probe-suite.js --dir ignite-cli` -> discovered 12, attempted 12, passed 12, failed 0, `SUITE-COMPLETE verdict=GREEN exit=0`. Probe enumeration via `--list | xargs grep -l` confirmed `probe-cli-server-json.js` is the only probe touching this resolver (the two other hits name `supervisor/spawn/config.js`'s unrelated same-named function).

NOT deployed at filing time: the deploy worktree at `/home/henri/.local/state/rbtv-deploy` has not been advanced and the unit was not restarted. That does not gate this fix reaching callers — `~/.local/bin/ignite` is a symlink to the repo working tree, so the client CLI is already the fixed one; only the daemon runs from the worktree, and nothing daemon-side changed.

## ATTENTION
1. `RBTV_IGNITE_WORKSPACE_ROOT` is present in a daemon-spawned session's environment on this box, pointing at the vault root. Any check of cwd-based resolution that does not `env -u` it is vacuous — it passes identically with and without the walk. This confounded the first verification pass here.
2. The token half of this same file has walked up since 2026-08-07 and the address half did not. When touching one half of `config.js`, read the other: they solve the same "a caller runs deep inside a workspace with no environment" problem and drifted apart for three weeks unnoticed.
3. Nearest-ancestor-wins means a `.rbtv/modules/ignite/server.json` created anywhere under the vault silently shadows the real workspace install for every caller below it. A throwaway fixture written outside `/tmp` becomes a redirect, not a no-op.
4. The three sites sharing the string "no gateway address configured" are NOT three copies of one resolver — only the JS CLI one reads cwd. Grepping the error message finds all three; assuming all three need the same fix adds dead code to two of them.
5. `~/.local/bin/ignite` symlinks into the repo working tree, not the deploy worktree. An edit to `ignite/ignite-cli/` is live for every caller the moment it is saved, with no restart and no deploy step — so "not deployed" is true of the daemon and false of the CLI.
- RBTV_IGNITE_WORKSPACE_ROOT is set in daemon-spawned sessions — env -u it or a cwd-resolution check is vacuous
