# 20260831-i-apply-swallowed-a-dead-re-rend — apply swallowed a dead re-render

kind: issue
component: operator
date: 2026-08-31
commit: c7673276
deployed: no
pin: ignite/operator/master-profile/probes/probe-master-profile.py
components: planning

## Observed

On 2026-08-30 and 2026-08-31 the channel master's `rbtv-master-profile apply` recorded `outcome: ACCEPTED` while `repass.rc` was 2 (`can't open file …/ignite/coord/materialize-seats.py`). Evidence: `.rbtv/goals/_channel-master/settings-requests/master-profile/done/20260830T163948113543Z.outcome.json` and `20260831T134853346303Z.outcome.json`. The binding sheet already held `opencode` / `xai/grok-4.6` / `medium`; `_channel-master/seat.md` still said `claude` / `claude-sonnet-5` / `low`. Every later `sessions.csv` row launched sonnet-5. The sitting that ran `rbtv-master-profile show` reported the sheet as itself. Repo HEAD and the live tree agreed on the stale `MATERIALIZE` path; the renderer had moved to `ignite/planning/materialize-seats.py` in the Python-kit component split.

## Mechanism

Launch reads `seat.md` frontmatter only (`spawn.js#launchSpecForSeat` → `catalog.js#specForSeatCast`). The sheet reaches that file only via `materialize-seats.py --bindings`. `master_profile.py` still composed `MATERIALIZE` as `TEAM_KIT / "materialize-seats.py"` with `TEAM_KIT` at `ignite/coord`. `_repass` returned the subprocess rc as data. `apply` settled `ACCEPTED` and posted the owner bus note *before* the re-render, then stored the rc without flipping `ok` or the outcome. The D37 per-spawn refresh cannot heal this: it runs without `--bindings`, and `--refresh` recovers the triple from the descriptor itself.

## Attempts

First attempt held — checked: `git log --oneline -- ignite/operator/master-profile/tool/master_profile.py` for a post-move retarget of `MATERIALIZE` (none); memory `server/20260820-i-spawn-refresh-before-launch.md` (D37 refresh-before-launch, no `--bindings`); `team-kit/20260825-c-the-python-kit-goes-component.md` (materialize-seats.py → planning/, consumers not swept); `meta-leader/20260822-i-retarget-catalog-root.md` (DEFAULT_CATALOG_ROOT, not the renderer path).

## Fix

Point `MATERIALIZE` at `ignite/planning/materialize-seats.py`. Keep report-before-re-render (probe check 9) but *settle after* `_repass`: rc≠0 flips the in-memory outcome to `FAILED`, sets `ok` false, wakes a second owner-facing note, and `_settle` lands the record in `refused/` rather than `done/`. Rejected: a log line on rc 2 (the owner still sees ACCEPTED). Rejected: making spawn read the sheet (D2: launch reads `seat.md` only). `show`'s `where` text and `_report_body` now state sheet-vs-live. `open_binding`'s chat-bridge/`harnessOf(profile)` claim is inverted from D2 and was corrected in place.

## Consequences

A dead renderer can no longer look like a landed switch. Identity answers that treated the sheet as the sitting are now labelled as staged. `--refresh` of `_channel-master` (granted one-off) also rewrote that seat's exposure loaders and CLAUDE.md/AGENTS.md, not only frontmatter — expected of `--refresh` (task 7.796), not a hand edit of the body. Recast is a sibling creation in the same commit.

## Verification

Red: fixture apply with `MATERIALIZE` at the missing coord/ path → `ok=True`, `repass.rc=2`, `outcome=ACCEPTED`. After: same fixture → `ok=False`, `FAILED` in `refused/`. `python3 ignite/operator/master-profile/probes/probe-master-profile.py` PASS including checks 12 and 12b. One-off `materialize-seats.py --bindings … --refresh` left `seat.md` `harness: opencode` / `model: xai/grok-4.6` / `effort: medium`, matching the sheet. `rbtv-master-profile show` `from:` names the sheet as staged, not the sitting. Deployed: no.

## ATTENTION

- `apply` must settle *after* `_repass`. Settling ACCEPTED first is how a missing renderer looked like a landed cast.
- D37 `refreshSeatDescriptor` has no `--bindings`. It will freeze a stale triple forever if `apply`'s `--bindings` re-render has not already landed.
- `show` reads the binding sheet. Launch reads `seat.md`. Telling a sitting to treat `show` as its live identity is the false-model bug.
- apply must settle after _repass or a missing renderer records ACCEPTED
- D37 refresh has no --bindings and will freeze a stale seat.md triple
- show reads the sheet; launch reads seat.md — they are not the same identity
