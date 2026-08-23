# 20260822-c-home-leader-master-planning-ca — home-leader-master-planning-catalogs

kind: creation
component: meta-leader
date: 2026-08-22
commit: 49c03d35
deployed: yes
pin: NONE
components: meta-master-agent,meta-planning
seeded: true

## Motivation
Until 2026-08-22 15:04Z the leader, master-agent, and planning catalogs (and `meta/module.md`) existed only as 111 vault-tracked files under `.rbtv/mirror/meta/`. They were not versioned with the rbtv code they scaffold. The owner closed that split in the 14:27Z relentless interview as E11: HISTORY would live beside the code, and **meta moves from `.rbtv/mirror/meta/` into `<rbtv>/meta/` NOW** — the mirror keeps only cross-module homes (materialize/install); anything that affects only meta lives only in the repo. Owner's scope line: "meta is every harness/scaffolding layer that rbtv and ignite need to survive." E15 named the executor and the deadline: this session, with sub-agents to fix paths, **before** minting `ignite-engine`. The failure mode a leftover split would keep open is named in the vault companion (`ed9025ab1`) and the move seat: installer's `scan_all` lets the mirror **win** on a duplicate id, so a leftover copy keeps loaders and the book stale even after a repo copy exists.

## Design
`49c03d35` (2026-08-22 15:04:34Z, `feat(meta): home leader, master-agent, planning catalogs in the repo`) is purely additive — 111 files, +10423/−0, `git show --diff-filter=D` empty. It writes `meta/leader/`, `meta/master-agent/`, `meta/planning/`, and `meta/module.md` beside the already-homed `meta/installer/` (`eeb1fea6`). Cross-repo `git mv` was impossible (destination is a nested, gitignored repo), so the sitting copied, verified `diff -r`, then committed the repo side alone. Same commit rewrote in-tree `.rbtv/mirror/meta` literals inside the moved catalogs to `3-resources/tools/rbtv/meta` — not a blind copy. First attempt held — checked: `git log --before=2026-08-22T15:04:34` on those three trees is empty of prior repo commits; E1–E10 carry no earlier meta-move ruling; redesign-plan `decisions.md` has no D-id for a mirror→repo catalog move. Rejected: leaving meta split across mirror + repo (E11: "anything that affects only meta lives only in the repo"). Rejected: one commit that also retargets readers and deletes the mirror — the seat's DoD split that into three pathspec-scoped commits across two repos so each index stayed clean.

## How it works
After this commit the catalogs are read from `3-resources/tools/rbtv/meta/{leader,master-agent,planning}/` (plus `meta/module.md`). Planning moved with its capability tools (`component-lint`, `create-cli`, `delta-anchors`, `capability-cards`); those are catalog content, not a new product of this sha. This commit does **not** retarget any reader: `ignite/config/spawn-profiles.yaml` `--catalog-root` lines, `queue-request.js` `resolveCatalogRoot`, `master_profile.py`'s default, and the bindings JSON still pointed at `.rbtv/mirror/meta/` until the companions. A caller that already takes `--catalog-root` can be pointed at the new tree immediately; everyone else is still on the stale root. Live seat descriptors keep absolute paths until a later `--refresh` (explicitly out of this sitting). Catalog files are read live per invocation — no daemon restart.

## Consequences
Sixteen seconds later `919e1595` (15:04:50Z) retargets the code-side readers via `rbtv_path` — filed as `20260822-i-retarget-catalog-root`. Sixty-nine seconds later vault `ed9025ab1` (15:05:43Z) deletes the 111-file mirror copy and rewrites the eight `.rbtv/config/modules/meta/**/bindings/*.json` paths plus `.rbtv/goals/_channel-master/CLAUDE.md`. Explicitly left pending by the sitting: daemon deploy of the deploy-pinned JS/yaml (those edits live on `919e1595`, not here), an `install2` re-run that rewrites the book and harness loaders, and `--refresh` of the live seats. No later commit restores the mirror home; later touches on `meta/planning` (`2b00b593`, `d3fd4a3b` and kin) are unrelated work. E24 rewires HISTORY vs. build-memory and does not reopen E11's location.

## Verification
`49c03d35` itself adds no probe and changes no selftest — it is content at a new home. Proof of the add is the commit itself: 111 files, zero deletions, first history on those repo paths. Proof the move is not this sha alone is the two companions landing inside 90 seconds with matching deletes/retargets. Deployed yes at commit time (15:04:34Z) because these files are read live per invocation; D6's "deploying = committing" binds the daemon JS, which this commit does not touch. Pin NONE — there is no probe path that asserts the catalogs' home.

## ATTENTION
- `49c03d35` only **adds** the repo copy. Readers still pointed at `.rbtv/mirror/meta/` until `919e1595`; the mirror copy itself stayed until vault `ed9025ab1`. Treating this sha as "the move is done" leaves loaders on the stale tree.
- `install2` `scan_all` prefers the mirror on a duplicate id. Adding a repo home and leaving the mirror copy as a backup does not complete a meta move — the leftover wins and the book stays stale. Delete the mirror copy in the same sitting (`ed9025ab1` pattern).
- Live seat descriptors keep absolute paths until `--refresh`. After a catalog move the live seats keep working against the old path; do not read a live `seat.md` as proof of where the catalog now lives.
