# 20260827-c-composedetachedsession-one-det — composeDetachedSession: one detached-session opener

kind: creation
component: supervisor
date: 2026-08-27
commit: 9cdb472e
deployed: no
pin: ignite/supervisor/probes/probe-lane-room-open.js
components: runtime

## Motivation
Two callers needed the identical tmux argv: `runtime/cockpit.js` (the boot cockpit) and the
new `supervisor/lane-watch.js#openGoalRoom` (the daemon lane's first-room open). The vector
lived inline in `cockpit.js`, written there deliberately rather than through
`buildScopeArgv` — that one emits `--quiet`, no `--collect`, takes seat caps this call has
none of, and names its unit `rbtv-seat-*`. A second copy was the obvious move and the wrong
one: the part a copy silently drops is the `systemd-run --user --scope --collect` wrapper,
and dropping it is not cosmetic — an unwrapped `new-session` forks the tmux SERVER into the
calling process's cgroup, so from `rbtv-ignite.service` (`KillMode=control-group`) the next
restart reaps every pane on the box (measured 2026-08-14, server pid 241103).

## How it works
`composeDetachedSession({ sessionName, windowName = null, cwd, scopeUnit })` returns
`['systemd-run','--user','--scope','--collect','--unit='+scopeUnit,'--','tmux','new-session',
'-d','-s',sessionName, ...(windowName ? ['-n',windowName] : []), '-c',cwd,'-P','-F',
'#{pane_id} #{pane_pid}']`. It validates both names through this file's own `assertTmuxName`
(a tmux name carrying `:` or `.` re-targets another pane) and refuses a missing `cwd` or
`scopeUnit` with `E_BAD_REQUEST`. It is PURE — it returns the vector and never runs it, the
stance every composer in `spawn/tmux.js` takes, which is what makes both callers testable on
a box with no tmux at all.

NO COMMAND FOLLOWS `-c`, and that absence is the feature: tmux starts the configured default
shell, so the session's only pane cannot exit on its own. A session whose one pane runs a
command dies when the command does.

`windowName` is OPTIONAL, and the two callers differ deliberately. The cockpit names its
window (`cockpit`) as half of its distinctness guarantee against a goal room. A GOAL room
passes nothing, so a room the daemon opened carries tmux's own default window name and is
byte-indistinguishable from one a human opened with `tmux new-session -s <goal>` (checked
against the live rooms 2026-08-27: `goal-memory-management` and `ignite-engine` both show
window 0 named `bash`, the cockpit shows `cockpit`).

The scope unit is minted per attempt by each caller under its own prefix
(`rbtv-tmux-cockpit-<uuid>`, `rbtv-tmux-room-<uuid>`) — never a fixed name, because
`--collect` only reaps a scope once its processes are gone, so a constant would collide on
the re-create path.

## Design
Placed in `supervisor/spawn/tmux.js` rather than a new module or an export from
`cockpit.js`: that file already owns tmux argv composition and the name guard, and
`cockpit.js` is "the BOOT COCKPIT" — a poor home for a generic opener a third caller might
one day want. `composeSeatSpawn` was NOT widened for this: it composes a `new-window` in an
EXISTING room, always bwrap-wraps a harness argv (throwing `E_FS_SANDBOX_UNAVAILABLE` before
any tmux argv exists), and its whole subject is a pane WITH a command — the opposite of a
session whose pane is defined by having none.

Rejected alternative: reuse `runtime/jobs/recover-room.py`. It creates the session, but it
requires `--seat` and launches a recovery harness into the pane it just proved; the lane
needs the room ONLY, because `seedGoal` then launches every seat through the ordinary door.

## Consequences
`cockpit.js`'s inline `newSessionArgv` array is DELETED and replaced by one call; its direct
`assertTmuxName` import went with it (the guard is now reached through this function, and the
module header's note was updated to say so). No behaviour changed on that side — the composed
vector is byte-identical and `probe-cockpit` is unchanged and green. The order of two refusals
inside `composeCockpitSpawn` did move: `masterDir` and `teamviewArgv` are now checked before the
names. No caller and no probe arm depends on that order (`probe-cockpit`'s name-guard arm supplies
both other fields), and it is recorded here so a future reader does not read it as a regression.
Nothing was deleted anywhere else, and no follow-up fix was needed.

## Verification
`runtime/probes/probe-cockpit.js` 40/40 PASS after the extraction, including its
composition-layer arms and the naming-guard arm (a session name carrying a tmux target
separator is still REFUSED, now from inside `composeDetachedSession`). The cockpit's
`newSessionArgv` was compared directly before and after and is byte-identical.
`supervisor/spawn/probes/probe-tmux-seat.js` exit 0. The new
`supervisor/probes/probe-lane-room-open.js` asserts the lane's composed vector field by
field (systemd-run first, `--collect` present, `tmux new-session` after the `--`, `-d`
present, `-c` = the goal folder, NO `-n`, unit matching `rbtv-tmux-room-<uuid>`) and then
really executes it against a private tmux server.

## ATTENTION
1. Never drop the `systemd-run --user --scope --collect` wrapper, and never replace it with
   `buildScopeArgv`. The wrapper is what keeps the forked tmux server out of the caller's
   cgroup; `buildScopeArgv` emits different flags and a `rbtv-seat-*` unit name.
2. `windowName` defaults to `null` ON PURPOSE. Adding a default name would make every
   daemon-opened goal room distinguishable from a human-opened one, which is a property the
   lane's opener relies on.
3. There must be no third `tmux new-session` composer under `ignite/` outside probes. If a
   caller needs one, it calls this function.
- never drop the systemd-run --scope wrapper: an unwrapped new-session forks the tmux server into the caller's cgroup
