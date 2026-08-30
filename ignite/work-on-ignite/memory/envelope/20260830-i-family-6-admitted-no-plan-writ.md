# 20260830-i-family-6-admitted-no-plan-writ — family 6 admitted no plan write into the mirror

kind: issue
component: envelope
date: 2026-08-30
commit: c962f09f
deployed: no
pin: ignite/envelope/envelope-compiler.selftest.js

## Observed
A meet-transcript-summarizer build plan (12 seats, 10 milestones) could not be born: 7 of its 10
milestones write to the product home `.rbtv/mirror/office/meeting-summarizer/`. Every seat refused
with `E_LAUNCH_REFUSED` because the whole cage compile returned `ok:false kind:conflict` before
milestone 1's first probe. plan-reviewer measured it live: `projectFolder`/`namedRepos`/
`extraPaths:rw` naming the product home each returned `ok:false kind:conflict` against the live
`compile()`. Same for any path under `3-resources/tools/rbtv/`. Evidence:
`.rbtv/goals/meet-transcript-summarizer-planning/seats/leader/sessions/13c15f2e.../evidence-b2-product-home.md`.

## Mechanism
`envelope-template.yaml` family 6 `rbtv-and-mirror` bound the rbtv SOURCE REPO and the workspace
`.rbtv/mirror/` under one `id`, one `access: ro`. `compiler.js#authorizedCarve` (line 118 at the
time) admits an rw narrow inside a `vault-wide-read` ro wide, but had no equivalent clause keyed on
family 6 — so a plan rw path under either tree fell through every `authorizedCarve` clause,
`findConflict` returned the pair, and `compile()` refused. Because family 6 covered BOTH trees
under one id, keying a carve on the family (rather than splitting it) would have opened a plan's rw
grant into the rbtv repo too — a materially larger, security-shaped widening nobody asked for.

## Attempts
First attempt held — checked: `git log` on `envelope-template.yaml`/`compiler.js` for prior mirror-
carve work (none), and the family-8 comment in `compiler.js` (`authorizedCarve already admits an rw
narrow inside the vault-wide-read ro wide, so no carve rule is added for it`) which flags the same
class of gap for the ending-store family without generalizing the fix.

## Fix
Split family 6 into `rbtv-repo` (`{rbtv-repo}`, ro, no carve — unchanged posture) and a new `mirror`
family (`{mirror}`, ro, number 9) that gets the same carve `authorizedCarve` already gives
`vault-wide-read`. The rbtv source repo keeps no carve at all: a plan naming a write path inside it
still refuses. Renamed the family id everywhere it was read — `load-config.js`'s
`REQUIRED_FAMILY_IDS`, `compiler.js`'s two `familyById` lookups and its `unresolved` label, and the
selftest's family assertions — since a repo-wide grep found the reader set confined to
`ignite/envelope/`. `cagespec.py` was read and needed NO change: its `rbtvRoot`/`rbtvMirror` names
are a different mechanism entirely (`cage.js`'s goal-relative `SeatBinds` grant classes, listed in
`DROPPED_GRANTS` because they compose outside the goal folder by construction) — it does not
reference envelope-template family ids at all.

## Consequences
The generic deny-list credential rules (`**/*.env`, `**/*token*`, `**/*.key`, credential store
paths) are unchanged for the mirror: `isCredentialDeny` matches on the absolute path of any
`extraPaths` grant against `envelope-deny-list.yaml` regardless of family, so a credential-shaped
file under the mirror is denied exactly as one anywhere else in the workspace — nothing in this fix
touches that check. `supervisor/spawn/cage.js` and `spawn.js` import `authorizedCarve` directly from
`compiler.js` rather than re-deriving it, so they pick up the new clause with no edit of their own
(confirmed by reading both call sites; per the `work-on-ignite` wall for this fix, `ignite/
supervisor/**` was not touched). Family numbering: `mirror` is `number: 9`, appended after
`ending-store` (8) rather than renumbering 7/8 up, to keep the diff to the two families that
actually changed.

## Verification
`node ignite/envelope/envelope-compiler.selftest.js` — added `mirror-carve-admitted` (a plan
`projectFolder` grant under `{mirror}` compiles `ok:true`, innermost access `rw`, mirror root stays
`ro`) and `rbtv-repo-still-refuses` (the same grant vehicle inside the rbtv repo still refuses
`kind:conflict`) plus a `compilePlanning` mirror-family assertion. Confirmed red without the fix by
mutation-testing `authorizedCarve` twice: removing the new clause turned `mirror-carve-admitted`
red; widening the clause to also cover `rbtv-repo` turned `rbtv-repo-still-refuses` red. Ran the
full envelope selftest set (`envelope-compiler`, `envelope-launch`, `envelope-shims`, `wall-report`)
plus `cagespec.py` plus the supervisor probes that name the envelope mechanism
(`probe-envelope-walls`, `probe-ancestor-mask`, `probe-caged-settings`, `probe-seat-cage`) both
before and after: 0 fails in both runs (the gap was invisible to the pre-existing suite by
construction — no assertion had ever named a plan-write grant under the mirror). Live read-only
reproduction against the deployed workspace: `compile()` called with the meet-transcript-
summarizer-planning goal id, the real rbtv repo path, and `projectFolder:
.rbtv/mirror/office/meeting-summarizer` returns `ok:true` with the fix and `ok:false kind:conflict
family:rbtv-and-mirror` on unmodified HEAD — matching plan-reviewer's measurement exactly. Not yet
deployed: the daemon compiles the envelope at goal-launch dispatch time and must be restarted to
pick this up (`ignite-engine`'s domain, not mine to restart — three live goals are paused on it).
Already-running cages are unaffected: the cage is composed once at launch from the compiled bind
list, not re-read afterward.

## ATTENTION
1. `cagespec.py`'s `rbtvRoot`/`rbtvMirror` are NOT this mechanism — do not assume a family-id
   rename here needs a matching edit there; they are `cage.js`'s own goal-relative grant classes,
   already split, and unrelated to `envelope-template.yaml`.
2. A carve exception keyed on a shared family id opens EVERY path the family binds — before adding
   a carve to a multi-path family, check whether splitting the family is required to keep the carve
   narrow (this is exactly what family 6 needed and family 8, per its own comment, did not).
3. `supervisor/spawn/cage.js` and `spawn.js` import `authorizedCarve` as the single source of
   truth — a future edit to the carve rules never needs a matching edit there, but SHOULD grep both
   call sites to confirm that import hasn't drifted into a local copy.
4. This fix compiles clean but is uncommitted-to-runtime until `rbtv-ignite` restarts; a plan built
   against this envelope before that restart will still see the old refusal.
- cagespec.py's rbtvRoot/rbtvMirror are a different mechanism, unaffected by this split
