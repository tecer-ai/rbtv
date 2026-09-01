# 20260901-i-exposure-canon-two-tool-rows-f — exposure-canon: two tool rows filled the rbtv-cli cell

kind: issue
component: meta-installer
date: 2026-09-01
commit: 24ec7187
deployed: no
pin: NONE
components: meta-planning

## Observed
`component-lint --component meta/embed-search` and `--component meta/installer` each
reported one `exposure-canon` FAIL: "a method=path row leaves rbtv-cli and description
empty (the tool self-documents via -h)". Both rows filled the `rbtv-cli` cell —
`rbtv embed-search` and `rbtv install` respectively. Separately, `meta/module.md` — the
table an agent reads to learn what the `meta` module contains — had no row for three
components that exist on disk: `installer/`, `leader/` and `memory/`.

## Mechanism
The manifest cell was being used to record a fact it does not carry. The `rbtv <verb>`
route is resolved entirely by `meta/rbtv-cli/tool/lib/verbs.js`'s ROUTES table; the
`rbtv-cli` cell is read by nothing at route time. `meta/embed-search/exposure.csv`'s own
header comment asserted the opposite — "the `rbtv-cli` cell carries `rbtv embed-search`
because verbs.js ROUTES to this tool" — so the file documented the wrong mechanism next
to the wrong data, and the next author to open it copied both. That is exactly what
happened: the `meta/control-panel` build read this file as the pattern and wrote the same
defect into its own manifest before `component-lint` caught it.

The `module.md` gap has a different and simpler cause: the repo's Keep-Docs-in-Sync rule
obliges a module-table update in the same change as a component's arrival, and for these
three it was not done — `installer/` arrived by relocation (`eeb1fea6`, 2026-08-22),
`leader/` by first homing (`49c03d35`, 2026-08-22), `memory/` as a docs-only add
(`d3c37dd3`, 2026-08-23).

## Attempts
First attempt held — checked: the `exposure-canon` rule text in
`1-projects/build-ignite/system-definition/concepts/exposure-manifest.md` § file schema
and § the write-roots column; the settled row shape across every other `,tool,path,` row
in `core/` and `meta/`; `meta/rbtv-cli/tool/lib/verbs.js`'s ROUTES table to confirm what
actually resolves a verb; and the build memory entries
`meta-installer/20260822-c-installer-home-in-meta.md`,
`meta-installer/20260823-c-installer-split-into-lib-selft.md`,
`deploy/20260825-c-cli-registration-six-method-pa.md` (whose ATTENTION bullet states this
rule) and `work-on-ignite/20260827-i-dangling-embed-search-ref-bloc.md` (embed-search's
move history). No prior attempt at these two rows is recorded in the memory store or in
`git log` for either file.

## Fix
Cleared the `rbtv-cli` cell on both rows, and rewrote embed-search's header comment to
state the real mechanism and to record that the cell used to carry the route string and
failed the check. Added three `module.md` rows, each claim sourced to a file or commit
that was read, with folder contents and the absence of `component.md` / `exposure.csv`
verified on disk per component.

## Consequences
Nothing was deleted or replaced beyond the two cells and one stale comment; no behaviour
changed, because the cells were read by nothing. `meta/module.md` grew three rows and now
covers all 16 components, so a future Keep-Docs-in-Sync check over that table starts from
a complete baseline. No follow-up fix was required. One finding was routed OUT rather than
fixed here: `rbtv selftest`'s 3 failures, all tracing to the stale `daemon-operator`
fixture name, are filed as a vault task in
`1-projects/build-ignite/build-ignite-tasks.md`.

A sweep of all 28 components carrying an `exposure.csv` shows the same rule broken far
more widely — 6 further tool rows filling `rbtv-cli` and 101 `path` rows filling
`description`, every one of them under `ignite/`, which additionally uses `library` and
`service` part-kinds the canon's vocabulary does not carry. `core/` is clean and `meta/`
now is. That concentration reads as `ignite/` following a different convention rather
than carrying 107 individual defects, so it is an owner ruling and was left untouched.
`meta/planning`'s `stools` row also fills `description`, but with real documentation
carrying a decision id; removing it would lose information and it was left alone.

## Verification
`component-lint` reports 0 findings on `meta/embed-search`, `meta/installer` and
`meta/control-panel`. Both routes were confirmed present in `verbs.js` BEFORE the cells
were cleared and both still resolve after: `rbtv embed-search status --root /tmp` and
`rbtv install ls` both answer normally. A completeness loop over `ls -d meta/*/` against
the table reports no missing component — 16 rows for 16 folders. Not deployed: this is
workspace-installed content, not daemon code.

## ATTENTION
- The `rbtv <verb>` route lives ONLY in `meta/rbtv-cli/tool/lib/verbs.js`; an exposure row's `rbtv-cli` cell is read by nothing at route time and MUST be empty on a `method=path` row. embed-search's header comment claimed the reverse, and a new component copied the defect from it.
- A stale explanatory COMMENT sitting beside correct-looking data is how a defect spreads — the next author reads the file as the pattern. Fix the comment in the SAME change as the data, or the fix does not hold.
- Do NOT sweep the ~107 `ignite/` exposure-canon findings as defects: `ignite/` uses `library` and `service` part-kinds outside the canon and fills `description` systematically. That is an un-ruled convention divergence, and treating it as a defect list would rewrite 107 rows on no ruling.
- `component-lint` takes a component path, and `exposure.csv` sits at depth 3 under the repo root (`<module>/<component>/exposure.csv`). A sweep written with `find -maxdepth 2` matches nothing and prints a clean, entirely empty result — a false all-clear that looks identical to success.
- A row's `write-roots` path resolves COMPONENT-relative unless prefixed `ws:`. A bare `.rbtv/...` is refused for not existing on disk, which reads like a typo and is a grammar error.

- The rbtv <verb> route lives ONLY in verbs.js; an exposure row's rbtv-cli cell is read by nothing at route time and must be empty on a method=path row.
- A stale explanatory comment beside correct-looking data is how a defect spreads: the next author copies the file as the pattern. Fix the comment in the same change as the data.
- Do NOT sweep the ~107 ignite/ exposure-canon findings as defects — ignite/ uses part-kinds outside the canon and fills description systematically; that is an un-ruled convention divergence.
- exposure.csv sits at depth 3; a sweep written with find -maxdepth 2 matches nothing and prints a clean empty result — a false all-clear indistinguishable from success.
