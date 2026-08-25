# 20260825-c-cli-registration-six-method-pa — CLI registration: six method=path rows + the audience map

kind: creation
component: deploy
date: 2026-08-25
commit: 6dbfc16b
deployed: no
pin: NONE
components: bridges,team-kit,cli

## Motivation
The CLI census taken for the core redesign (`authoring/cli-landscape/q1-inventory.md`,
2026-08-24, 44 rows) found the shell-invocable surface half-registered: six first-party
CLIs had no `exposure.csv` row anywhere ("discoverable via: nothing"), five more were
declared `method=path` yet absent from the shared bin dir, and five census cells carried
no audience at all. `spec-component-map` §7.1/§7.3 settled the cut; this entry lands the
registration half of it. `d-exposure-method-path` already required a `method=path` row
per first-party CLI — the tree simply did not satisfy it.

## Design
Three separate things, deliberately not merged.

The audience labels became ONE new document, `ignite/ignite-cli/cli-audience-map.md`,
rather than a cell on each component's `component.md`. The question it answers ("who is
this tool for, and is there anything I cannot reach?") is asked across the whole tree at
once; scattering it across fourteen components makes it unanswerable without reading all
fourteen. It lives on `ignite-cli` because §7.2 makes the front door the routing home.
It is a MAP, never a grant — the section "What this table is not" says so, because a
label that reads like an authorization is the way this file becomes wrong.

The six missing rows went onto their OWNING components (`deploy` ×3, `chat` ×1,
`coord` ×2), never onto a central manifest. §7.3 forbids the central file explicitly and
the per-component placement is what installer discovery actually walks. `nudge.py` got a
row because §7.3 made it conditional on surviving the observer deletion and it did — the
file and its two probes are still on the tree.

The five PATH-gap tools needed NO edit, and finding that out was the work. Their rows
already resolve; the cause of the census gap was the manifest HOME, not the row.

## How it works
Each new row is `<part-id>,tool,path,,<entry-point>,,` — `rbtv-cli` and `description`
empty, because `component_lint.py`'s `exposure-canon` check fails a `method=path` row
that fills either (the tool self-documents via `-h`). The part-id doubles as the PATH
name the installer symlinks, so it must be unique across every manifest in both trees;
`plan_path_links` in `meta/installer/lib/pathlinks.py` is the function that enforces
that, raising `path-name-collision` for a repeat and `entry-point-missing` for a row
whose file is gone.

`mirror-driver` is inventory for a tool whose real invocation is `python -m driver.cli`
from `coord/mirror/`; the row records that it exists, and `coord/component.md` records
the invocation, because the description cell cannot carry it.

On the five PATH-gap tools: `rbtv-bindings`, `rbtv-master-profile`, `rbtv-goal-request`,
`rbtv-seat-identity` and `rbtv-ignite-watchdog` were declared on the module-root
`ignite/exposure.csv`. Installer discovery treats a directory at DEPTH 2 holding an
`exposure.csv` as the component, so a depth-1 module-root manifest is never walked and
those rows were never linked — which is exactly why `coord/` (then `team-kit/`) and
`work-on-ignite/`, the only two components that already had their own manifests, DID
have their names in the bin dir. The same cause was recorded for team-kit in
`component-first-migration` (da69c086, 0563266b). The component-first move gave each of
the five a depth-2 home, so the declaration is now what the installer walks.

## Consequences
`ignite/deploy/exposure.csv` stops being a header with a deliberate "no rows yet" note
and becomes a real manifest, which also turns its `component-lint --check exposure-canon`
run from exit 1 ("discovered 0 manifest rows") to exit 0. Nothing was deleted and no
binary was copied. Five components (`chat`, `coord`, `operator`, `runtime`,
`observation`) still fail `exposure-canon` on rows this work did not author — the
part-kinds `library` and `service` are outside the checker's canon, and several
`method=path` rows carry descriptions; those pre-existing counts are unchanged by these
edits (chat 32 before and after, coord 1 before and after).

## Verification
`plan_path_links` run over all eleven rows (the six new plus the five PATH-gap ones):
eleven rows, eleven unique names, every destination `is_file()`, no collision and no
missing entry-point. The same function over all 120 `method=path` rows in both trees:
120 rows, 120 unique names, no destination missing. `rbtv install add -c deploy|chat|coord
--dry-run --json` returned `ok: true` with the new rows present as `path_rows`, and the
shared bin dir was left untouched (checked by mtime before and after). `component-lint
--check exposure-canon` exits 0 on `deploy` and reports the identical pre-existing
finding counts on `chat` and `coord`. Probe suite run chunked over all 205 discovered
probes: 190 pass, 12 fail, 3 inoperative, every chunk `SUITE-COMPLETE`; none of the
fifteen non-green probes reads an `exposure.csv`, and the three probes that do
(`probe-register-job.js`, `probe-remove-job.js`, `probe-ancestor-mask.js`) pass. Not
deployed — this is branch `ignite/core-redesign` in the redesign worktree, and the
cutover seat owns the deploy.

## ATTENTION
- The installer links every `method=path` row by its part-id regardless of `part-kind`,
  so a new row silently claims a PATH name; a duplicate anywhere in either tree aborts
  the WHOLE install run with `path-name-collision`, not just that component.
- A `method=path` row that fills `rbtv-cli` or `description` fails `exposure-canon`.
  Documentation for such a tool goes in the component's `component.md`, never the row.
- Four of the six newly registered entry-points are not executable
  (`probe-suite.js`, `goal-channel-cli.js`, `mirror/driver/cli.py`, `nudge.py`) and two
  of those have no shebang. The row is inventory and the lint grades this INFO by design,
  but the symlink the installer creates is not a runnable bare-name command until that
  is settled.
- `install.py selftest` FAILS from the redesign worktree at the `U-live` arm and PASSES
  from the live repo: the live install book still names `ignite/team-kit`, which the
  component-first move renamed to `ignite/coord`. It is a book-vs-tree disagreement that
  the cutover resolves, not a defect in either manifest.
- the installer links a method=path row by part-id regardless of part-kind; a duplicate name anywhere in either tree aborts the whole install run
