# 20260901-c-n1-one-shot-process-sweep-at-t — N1: one-shot process sweep at the capacity gate

kind: creation
component: supervisor
date: 2026-09-01
commit: 35d3fe9e
deployed: no
pin: ignite/coord/coord_selftest.py
components: coord

## Motivation
`registry-spawn-record` (commit `8a156a0a`, memory entry `20260901-c-registry-records-at-spawn-not.md`) closed 7.555/D5 and N2 against the supervisor registry but left N1 (an unaccounted pane — no registry row, no seat.md anywhere) permanently red, documented inline as unbuildable on the registry alone: "a registry row cannot represent an identity nobody ever wrote, by construction... no future registry-only change closes it." That entry's own ATTENTION #2 named the replacement shape (a process-tree sweep at the gate, one-shot, never persisted) as new, ungranted scope. Owner ruling `d-n1-oneshot-sweep` (`redesign-continue-1` plan `decisions.md`) granted exactly that scope. **This entry supersedes that ATTENTION bullet: N1 is no longer a permanent gap.**

## Design
A registry row only exists once something writes one, so it can never answer "is there a live harness pane nobody declared at all."

Closing that needs a SECOND observation source, and the only shape two standing rulings (T4-R8's team-monitor deletion; `d-ask9-keep-the-three-protections`) leave open is one taken fresh at the exact decision moment and discarded immediately — never a schedule, never a file, never a daemon. `process.py` already carried the right primitives for this (`ps_snapshot`, `harness_pids`, both built for the G-11 checkin check) — the only new pieces are enumerating EVERY live pane (not just one seat's) and reading its cwd, then pre-filtering to panes with no descriptor anywhere so a declared seat's own pane is never double-counted alongside its registry-sourced row.

## How it works
`ignite/supervisor/process.py#unaccounted_panes(exclude_pane, resolver=None)`: one `coord.live_panes()` call minus the CALLING pane, one `ps_snapshot()`, then per remaining pane — `coord.tmux_pane_pid` -> `harness_pids` (real harness under that pane?) -> `coord.pane_cwd` -> `resolve_descriptor` (any seat.md anywhere?). A pane that resolves is skipped (already accounted by some other mechanism); only genuinely unresolvable panes come back, shaped exactly like `census()`'s existing `no-seat`/harness rule already expects (the same shape N2's cross-goal rows already use).

`ignite/coord/tmux.py#pane_cwd(pane)`: `tmux display-message -F "#{pane_current_path}"`, the one field `pane_harness_pids` never needed.

`ignite/supervisor/launch.py`'s capacity block, right after the N2 cross-goal loop and before `census()` is called: `for _cap_rogue in process.unaccounted_panes(exclude_pane=coord.detect_pane()): _cap_seats.append({...})`. `coord.detect_pane()` (the session asking the capacity question) is resolved and excluded BEFORE any pane is even queried — the self-match trap: the calling session is routinely a live harness whose own cwd resolves to nothing (`budget.py`'s own documented ambiguity, an owner console and a leak are observationally identical), and excluding the pane wholesale also removes the sweep's own `ps`/`tmux` subprocess chain for free, since those are descendants of the excluded pane's root.

## Consequences
Nothing in `budget.py#census()` changed — this only widens what feeds it, same discipline `registry-spawn-record` established for N2. `coord_selftest.py`'s N1 arm no longer drives the retired `_c3_state(...)` snapshot fixture; it stubs `live_panes`/`tmux_pane_pid`/`pane_cwd`/`process.ps_snapshot` and the suite's own `calling_pane["v"]` seam (NOT `$TMUX_PANE` — `detect_pane` is stubbed suite-wide to read that dict, never the environment; costly to discover, see ATTENTION).

## Verification
`python3 coord.py selftest` (full suite, `ENDING_STORE_DB` set to a scratch path when run outside the vault workspace): 21 -> 20 FAIL, diffed failure sets — exactly the old N1 row flips green, zero new reds (7.555/D5, N2, `dag-10 RS-4`, a6b946cc's capacity rows all unaffected across two confirmation runs). Mutation proof in a scratch `git worktree` at commit `35d3fe9e`: clean unmutated run first (20 FAIL, matching), then disabling the self-exclusion line reddened EXACTLY the new self-match-trap check and nothing else (set-diffed FAIL lists, +1/-0). LIVE proof on a real throwaway tmux session (`test-n1-rogue`, `exec -a claude sleep 300`, cwd `/tmp`, killed after) against a real scratch goal (`.rbtv/goals/test-n1-gate-sweep`, removed after) via `supervise.py launch --dry-run --tmux-target`: with the rogue pane alive, `cap1` (cap=1) is DEFERRED with "1 unaccounted pane(s) are INSIDE in_use" printed; with the rogue pane killed, `cap1` ADMITS. NOT deployed — branch `ignite/core-daemon`, commit `35d3fe9e`.

## ATTENTION
1. **`detect_pane` is stubbed suite-wide to read `calling_pane["v"]`, never `$TMUX_PANE` or real tmux** (`coord_selftest.py` line ~684) — the WHOLE selftest suite never touches real tmux for pane identity. Setting `os.environ["TMUX_PANE"]` in a fixture does nothing; mutate `calling_pane["v"]` directly. Cost a full debug cycle to find (two file-traced debug runs) because the symptom (exclude_pane always `''`) looked like a `coord.detect_pane()` logic bug rather than a wrong stub target.
2. **Running `coord.py selftest` from a `git worktree` OUTSIDE the vault aborts** at whichever check first needs the ending store, with `EndingStoreError: no workspace above ... .rbtv/modules/ignite/server.json`. Set `ENDING_STORE_DB=/tmp/<scratch>.db` explicitly — and use a FRESH path per run, since re-running against the same db file collided with a leftover `open_asks.ask_id` UNIQUE constraint from the prior run's rows.
3. `unaccounted_panes` is intentionally NOT the raw "feed every harness pane to `census()`" shape N2 uses for cross-goal rows — it pre-filters to `resolve_descriptor(cwd) is None` itself. Feeding every harness pane through unfiltered would double-count any pane that happens to be a declared seat of THIS run (the D5 in-run correction would subtract it a second time, on top of its registry-sourced row). If a future change widens this function's callers, that pre-filter is load-bearing, not incidental.
4. `doors.js`'s JS-side `markUnsupervised`/`registerCheckIn` still have no production caller (unchanged from `registry-spawn-record`'s note) — orthogonal to N1, not touched here.
- detect_pane is stubbed suite-wide via calling_pane, never TMUX_PANE
