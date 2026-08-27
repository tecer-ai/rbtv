# 20260827-i-two-dangling-path-exposures-sh — Two dangling path exposures shut the CM's refresh door

kind: issue
component: meta-master
date: 2026-08-27
commit: d62a07a7
deployed: no
pin: NONE
components: planning

## Observed

`materialize-seats.py --refresh` — the ONLY door that re-renders the channel master's descriptor (`spawn.js#refreshSeatDescriptor` composes exactly this call before every launch, `ignite/supervisor/spawn/spawn.js:637-641`) — refused outright on the standing-seat home `.rbtv/goals/_channel-master/`, at every attempt, with

    materialize-seats refused (exposes-ref-dangling): seat 'channel-master' exposes
    'rbtv:ignite/rbtv-master-profile' (path) — no exposure.csv row 'rbtv-master-profile'
    under <repo>/ignite/exposure.csv

First measured by the role-action-program's `deliver-exposures` seat on 2026-08-27 (`1-projects/build-ignite/build/role-action-program/seats/deliver-exposures/evidence.md` §1c) while testing the premise that this seat has no renderer at all, and reproduced by `fix-cm-refresh` the same day before the edit (EXIT=1). It is a SECOND, different dangling reference from the `rbtv-embed-search` one `578547a9` repaired hours earlier at the same gate — that repair held (no `skill-cli-dangling` in this refusal), this one sat behind it.

Consequence as measured, not theorised: three CP-2 matrix rows stayed red on the live channel master (M3 a caged write-surface section on an uncaged seat, M24 `file-system-issue` + `file-issue` undelivered, M48 `commit` undelivered) even though all three corrections had already landed in the SOURCE prompt (`052b0042`, 2026-08-26). `impl-descriptors` and `deliver-exposures` reached the live descriptor by hand-edit instead — `deliver-exposures` had to import the materializer's own `_loader_md` and call it by hand to write the two missing skill loaders. Deployed vs HEAD: no difference — the prompt is read from the repo tree at assembly and the branch `ignite/core-daemon` carried the same two lines as the deploy worktree.

## Mechanism

`meta/master/prompts/channel-master-prompt.md`'s frontmatter declared `exposes: path: [rbtv:ignite/rbtv-master-profile, rbtv:ignite/rbtv-bindings, …]`. `_ref_target` (`ignite/planning/materialize-seats.py:4052-4063`) treats a `rbtv:`-prefixed reference as `rbtv:<path-under-the-repo>/<part>`: it joins every segment but the last onto the rbtv repo root and takes the last as the part-id. So both refs resolved to component dir `<repo>/ignite/` with part-ids `rbtv-master-profile` / `rbtv-bindings`, and the caller then required a `method=path` row of that id in `<repo>/ignite/exposure.csv` — a file that does not exist at all (`ignite/` is a module root, not a component; exposure manifests are per-component since the CMP-5 component-first migration). The rows live in `ignite/operator/exposure.csv` and the executables at `ignite/operator/{master-profile,bindings}/tool/rbtv-*`. The refs were therefore exactly one component segment short, and the gate is a hard `raise Refuse` with no override arm — correct behaviour over a wrong declaration.

Both refs were authored when the tools lived at a depth where `rbtv:ignite/<part>` was true. The `ignite/capabilities/…` → `ignite/operator/…` move relocated them and swept the code callers but not this declaration — the same second-statement failure class as `d3a4dbf0`'s (`20260827-i-dangling-embed-search-ref-bloc`) and as the six prose breakages in `20260826-i-master-material-contradicts-th`: the prompt restates a fact the layout owns, and nothing re-derives it when the layout moves. The wrong value is born on the declaration line, not in the resolver.

## Attempts

First attempt held — checked: `git log --oneline -- meta/master/prompts/channel-master-prompt.md` carries no prior repoint of these two refs; `052b0042` (the CP-1 sweep that ADDED `core/coding/commit`, `ignite/coord/file-system-issue` and `ignite/coord/file-issue` to this very frontmatter, and repointed three `ignite/capabilities/…` prose paths to `ignite/operator/…` in `master-instruments.md`) did not touch the `path:` list's two pre-existing entries — it edited the line beside them, which is why the defect survived a sweep aimed at this exact class. `578547a9` repaired the OTHER dangling ref at the same gate and its own sweep (`grep -rn 'exposes-cli:' ignite/ meta/`) was scoped to `exposes-cli:` declarations, so an `exposes: path:` ref was outside it. Two `rbtv embed-search query` passes over `memory/` (symptom, then the file path) and the grep floor over every `_issues.md`/`_creations.md` surfaced no earlier trial of this instance.

## Fix

`d62a07a7` inserts the missing component segment: `rbtv:ignite/operator/rbtv-master-profile` and `rbtv:ignite/operator/rbtv-bindings`. Both target rows were read out of `ignite/operator/exposure.csv` and both executables `ls -la`'d before the line was written.

The `rbtv:` prefix was KEPT rather than switched to the plain `module/component/part` form (`ignite/operator/rbtv-master-profile`), which resolves identically today because the vault mirror holds no `ignite/` tree. Two reasons for keeping it: it is the smaller edit, and `_scan_all` prefers the MIRROR over the repo when both define a component id, so the plain form would silently repoint these two grants at a mirror copy the day one appears — the rendered `exposed-clis:` absolute paths, which are what the occupant actually runs, would move with it. The prefix pins the resolution to the repo root by construction. The same shape and the same reasoning as `578547a9`'s `rbtv:meta/embed-search/rbtv-embed-search`.

Rejected: weakening the gate (it is the mechanism that made this visible at all, and `20260827-i-dangling-embed-search-ref-bloc` records what the whole-workflow door's warn-instead-of-refuse asymmetry already costs); deleting the two refs (they are the channel master's only route to re-casting its own harness/model — `rbtv-master-profile` — and to casting a workflow's seats, both live grants); and hand-editing the rendered descriptor again (the fourth such hand-edit, and the next refresh would revert it).

The other ten refs in the same file's `exposes:` block were swept against their manifests in the same pass — all ten resolve, so no sibling was left dangling.

## Consequences

The refresh door is open for this seat, and applying it delivered the three red matrix rows from the source in one act rather than by hand: the write-surface section flipped from the caged worker's two-entry list to the uncaged text (M3, the fix `179310e8` landed in the renderer but which no `_channel-master` render had ever reached), and `file-system-issue` (M24) and `commit` (M48) arrived as `<resources>` bullets plus generated loaders under both `.claude/skills/` and `.agents/skills/`. The refresh also carried four corrections no hand-edit had reached — including a residual `the master's act ends at the QUEUED JOB` clause that OQ-22(b) had struck everywhere else — so the rendered file is now closer to the source than the hand-maintained copy was.

It also OVERWROTE `deliver-exposures`' hand-written loaders and `impl-descriptors`' hand-edits, by design: the pre-apply diff was taken first and checked hunk by hunk, and every hand-edit was found already present in the source (`052b0042` amended the task file and `component.md` in the same change for exactly this reason), so nothing regressed. That check is not optional — the descriptor had been hand-maintained for three days.

Nothing was deleted or replaced in the repo; the frontmatter description is untouched, so no `exposure.csv` docs-in-sync obligation arose. NOT deployed: `meta/` is read from the repo tree at assembly and the deploy worktree was not advanced; no daemon or bridge restart, and the runtime descriptor edit is a working-tree change in the vault repo, deliberately uncommitted.

## Verification

The refusal was reproduced on the pre-fix tree and re-run after, byte-for-byte the call `spawn.js#refreshSeatDescriptor` composes (`--package .rbtv/goals/_channel-master --seat channel-master --catalog-root <repo>/meta --refresh --root --json`): EXIT=1 `exposes-ref-dangling` before, EXIT=0 after, with a plan of 1 `seat-descriptor-repass` + 2 `seat-guidance` + 16 `seat-exposure` writes and 0 taskforce rows. The dry-run's own `descriptors` payload was diffed against the file on disk BEFORE the mutating run, and the applied file came back byte-identical to that payload (`diff -q`).

On the applied descriptor: the write-surface section reads `**This seat runs UNCAGED.**`; `exposes:` carries 8 skills and 4 paths; `file-system-issue` and `commit` each appear as a `<resources>` bullet and as a generated loader in both harness folders, with all three loader targets `ls`-verified on disk; the frontmatter re-parses under `yaml.safe_load` with `claude / claude-sonnet-5 / low` intact (OQ-12(b)); and the six ruled-correction greps (`Secrets stay UNREADABLE`, `queued 10 minutes`, `10 minutes out`, `you do not file`, `ignite/capabilities/`, `teamview`) return zero hits. `component_lint.py --component meta/master` reports the identical 5 pre-existing findings before and after the edit — measured by restoring the pre-fix file, re-running, and restoring the fix (the `stools` grant on two prompts, one over-ceiling `<resources>` bullet). Deployed: NO.

## ATTENTION

- A `rbtv:` reference is `rbtv:<path-under-the-repo>/<part>` and the part-id must have an `exposure.csv` beside it. `rbtv:ignite/<part>` is NOT "the ignite module's `<part>`" — it means "a row `<part>` in `<repo>/ignite/exposure.csv`", and since the component-first migration no module root has one. Reading such a ref as `module/part` is what let two dead grants sit in a live prompt through a sweep aimed at their own defect class.
- `exposes: path:` refs are resolved at SEAT-GENERATION time and a dangling one closes `--refresh` for the WHOLE seat. Moving or re-nesting any exposed tool therefore silently freezes that seat's descriptor at its last render. `grep -rn 'exposes-cli:'` does not find these — the `path:` and `skill:` lists inside `exposes:` need their own sweep, and `578547a9`'s `exposes-cli:`-only sweep is why this one survived.
- `.rbtv/goals/_channel-master/seat.md` IS refreshable — `--refresh` works on a standing-seat home, not only a goal package, and `parseSeatPath` matches it. The belief that it has no renderer and must be hand-maintained (carried in this program's `loose-ends.md` and in `20260826-i-two-stale-rulings-note-lines-i`) was inherited, not measured, and it cost four rounds of hand-edits to a file one command re-derives.
- ALWAYS diff the dry-run's `descriptors` payload against the file on disk before a mutating `--refresh` on a descriptor that has been hand-edited. The refresh is a full re-render, not a merge: any correction that lives only in the rendered copy is silently gone. The safety here came from `052b0042` having amended the SOURCE for every hand-edit; that is not guaranteed in general.
- `_scan_all` prefers the vault mirror over the repo for a component id, so the plain `module/component/part` form of an `ignite/` ref is a latent repoint the day a mirror copy appears. Keep `rbtv:` where the grant must resolve to the repo's own executable.
- A rbtv: ref is rbtv:<path-under-the-repo>/<part> — rbtv:ignite/<part> needs a row in <repo>/ignite/exposure.csv, which no module root has since the component-first migration
