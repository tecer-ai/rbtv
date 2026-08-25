# 20260825-i-8-stale-settings-paths-killed — 8 stale --settings paths killed every launch silently

kind: issue
component: envelope
date: 2026-08-25
commit: 973624ce
deployed: no
pin: NONE
components: chat,supervisor,runtime
register-id: G-fix-spawn-settings-0825-2146

## Observed
Every real seat/session launch on the live daemon died silently after the 2026-08-25 cutover merge (26bea77f). Owner-proven live at 21:15:59 UTC: the daemon journal logged "harness config materialized" for `_channel-master` (spawn.js:1603), then the spawn vanished — no error line, no `failed: launch-refused` stamp, no owner NACK; the bridge posted a generic dead-air notice ~10 minutes later (queueId 1632, "expected spawn never appeared"). Four probes red on the same cause: probe-caged-settings, probe-launch-auto-mode, probe-tmux-seat-live, probe-chat-live-session. Measured by the fix-spawn-settings seat (redesign-implementation plan): `ignite/envelope/spawn-profiles.yaml` carried 8 `--settings` argv rows pointing into `ignite/config/`, a directory the cutover merge deleted; the real files sat at `ignite/chat/chat-session-settings.json` and `ignite/supervisor/worker-session-settings.json`.

## Mechanism
The cutover merge moved the two settings JSONs component-first (`ignite/config/` → `ignite/chat/` and `ignite/supervisor/`) but the 8 absolute `--settings` paths hardcoded in the launch-specs argvs of `envelope/spawn-profiles.yaml` were not swept (the config file is data, not an import the AST walk could catch). Every claude-profile child process (`claude-fable-5`, `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5`; exec and resume arms) received `--settings <nonexistent path>` and died at harness startup, after the daemon's own pre-launch steps had already succeeded — hence materialized-then-silence.

## Attempts
First attempt held — checked: `git log --oneline -- ignite/envelope/spawn-profiles.yaml` shows no prior post-cutover fix attempt; the cutover merge (26bea77f) itself was the change that broke the paths, and the yaml's own ponytail comment (line ~350) already warned the argvs must be kept in step by hand.

## Fix
Commit 973624ce: repointed the 8 `--settings` rows to the files' post-cutover homes — 4 chat rows → `ignite/chat/chat-session-settings.json`, 4 worker rows → `ignite/supervisor/worker-session-settings.json`. Absolute-path style deliberately KEPT (owner ruling: the derived/relative-path root fix is a separate deferred ruling — do not fold it into the hotfix). Owner-authorized 2026-08-25, decisions.md spawn-profiles ruling (a). Nothing else in the file touched.

## Consequences
The repo config is correct, but the running daemon still serves the STALE argvs: `spawn.js#createSpawnManager` loads the config exactly once (spawn.js:1369) when `runtime/engine.js:82` builds it at boot, and with `RBTV_IGNITE_DATA_ROOT` set the daemon reads a boot-time snapshot copy (`runtime/index.js#materializeEffectiveConfig` → `~/.local/state/rbtv-ignite/.runtime-config/spawn-profiles.yaml`, written at the 17:34 boot, still carrying the 8 stale rows). A daemon restart (owner-gated) is required before launches actually recover; the deploy tree re-detach was deliberately NOT done by the fixing seat per its cached-at-boot stop rule. The silent-death defect itself is filed, not fixed: register G-fix-spawn-settings-0825-2146.

## Verification
`git diff -U0` before commit: exactly 8 `--settings` pairs changed, nothing else; both target files exist (`ls -la`); `js-yaml` load of the edited file parses (12 root keys); `grep -c "ignite/config/"` on the file returns 0. Deployed: no — commit sits on `ignite/core-daemon` in the live repo only; deploy re-detach and restart await the owner's ruling. The 4 red probes were NOT re-run by the fixing seat (they cannot go green against a daemon holding the boot-cached stale config).

## ATTENTION
- `spawn-profiles.yaml` is BOOT-CACHED twice over: `loadConfig` runs once per daemon boot (spawn.js:1369 via runtime/engine.js:82), and env overrides make the daemon snapshot the yaml to `<data-root>/.runtime-config/spawn-profiles.yaml` at boot (runtime/index.js#materializeEffectiveConfig). Editing the repo or deploy yaml changes NOTHING on a running daemon — a config fix without a restart is invisible.
- A component move (`git mv`) does not sweep data files: the 8 absolute paths in this yaml were the exact regression class the component-first migration's AST import-walk could not see. Grep the moved path in ALL yaml/json config before calling a move complete.
- A dead `--settings` path kills the child AFTER "harness config materialized" with zero daemon-side error — do not read that journal line as launch success (register G-fix-spawn-settings-0825-2146 tracks the silence itself).
