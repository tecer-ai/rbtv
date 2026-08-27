# 20260827-i-link-tools-tools-list-omitted — link-tools TOOLS list omitted three operator doors

kind: issue
component: deploy
date: 2026-08-27
commit: 8aa5bff6
deployed: yes
pin: NONE
components: operator,coord

## Observed
The role-action-program's CP-2 inventory matrix (2026-08-26, seat `inventory-cli-reachability`)
marked rows M32, M37 and M38 red: `rbtv-goal-request`, `rbtv-bindings` and `rbtv-master-profile`
did not resolve as bare names from a role seat's shell. `ls ~/.local/bin` on the ignite VPS held
symlinks for `coordinate`, `supervise`, `scaffold-seats`, `owed-answers`, `tmux-overview`,
`file-issue`, `ignite`, `rbtv` — and none of the three. The tools themselves were present and
executable at `ignite/operator/{goal-creation-request,bindings,master-profile}/tool/rbtv-*`
(mode 755, bash wrappers dated 2026-08-25), so the gap was reach, not the tool. Deployed tree and
HEAD agreed — `link-tools.py` is identical in both, so this was never deploy skew.

## Mechanism
`ignite/deploy/link-tools.py` links exactly the names hardcoded in its module-level `TOOLS` dict
and nothing else; it does not read any `exposure.csv`. The three operator doors were registered as
`method=path` rows in `ignite/operator/exposure.csv` when the operator component was built
(6dbfc16b, the six method=path rows), but nobody added them to `TOOLS`. Because `TOOLS` is the sole
input, `python3 ignite/deploy/link-tools.py` reported a clean `ok`/exit 0 across the board while
the three names stayed absent — the installer had no way to know they existed, so re-running it,
the one remedy `daemon-ops.md` prescribes for "a tool missing from PATH", could never fix it. The
three rows carry an EMPTY `rbtv-cli` column, which is what makes the omission fatal rather than
cosmetic: unlike `rbtv-goal`/`rbtv-execution`/`rbtv-ignite-daemon`/`rbtv-ignite-ticker`, they have
no `rbtv …` front-door verb, so the bare name was their only reach and they had none.

## Attempts
First attempt held — checked: `git log ignite/deploy/link-tools.py` (5 commits: 4ee035ac created
the step, 73f3a980 repointed it at component homes, 7dd08887 added `supervise`, 8caae835,
df22c29d added `file-issue`); the memory entries `coord/20260826-i-coordinate-crashes-by-installe`
(a different bare-name failure — the coordinate symlink resolved but crashed, because
`spec_from_file_location` inferred no loader from an extension-less `__file__`) and
`meta-installer/20260824-i-path-links-unusable-on-windows` (the OTHER, unrelated PATH-link
mechanism, `meta/installer/lib/pathlinks.py` into `~/.rbtv/bin`); plus two `rbtv embed-search`
queries and the grep floor over every `_issues.md`/`_creations.md`. No prior entry addressed the
scope of `TOOLS`.

## Fix
Commit 8aa5bff6 adds the three names to `TOOLS`, pointing at their component homes
(`operator/<capability>/tool/rbtv-<name>`), and restates the docstring's scope sentence. That
sentence had read "Scope is the ignite coordination kit ONLY", which stopped being true the moment
tools outside `coord/` needed bare names; it now states the actual membership rule — every ignite
`method=path` tool whose `exposure.csv` row names no `rbtv …` verb. That rule is what makes the
next omission detectable by reading a row instead of by a seat failing. Rejected: making
`link-tools.py` derive `TOOLS` by walking every `exposure.csv` — it would silently start linking
whatever any component declares, and the deliberate exclusion of the four front-door-reachable
tools has no expression in the CSV; a hardcoded list with a written rule keeps the decision
reviewable in a diff. Also rejected: creating the symlinks by hand, which is the exact failure
mode `link-tools.py` exists to end (its docstring records the hand-made links that a redeploy or a
second machine loses).

## Consequences
Nothing deleted or replaced; the six pre-existing links report `ok` and are untouched. The two
naming docs updated in the same commit — `ignite/deploy/component.md`'s PATH-links row and
`ignite/coord/team-kit.md`'s command comment — were ALSO still missing `supervise`, which 7dd08887
added to `TOOLS` without sweeping them; both lines now carry all nine names, so that older doc
drift is closed here too. The `~/.local/bin` symlinks point into the SOURCE repo, not the deploy
worktree at `~/.local/state/rbtv-deploy`, matching every existing link: an edit to an operator tool
in the source tree is live for bare-name callers immediately, with no redeploy. No daemon or bridge
restart was performed or needed — nothing that boots reads these links.

## Verification
`python3 ignite/deploy/link-tools.py --check` before the change: six `ok`, exit 0 (the false clean
bill). After adding the three: three `stale  absent -> …`, exit 1. After the write run (`linked`
x3): all nine `ok`, exit 0. From `/tmp`, `which` and `readlink ~/.local/bin/<name>` resolved each
of the three into `ignite/operator/*/tool/`, exit 0, and each answered `--help` BY BARE NAME with
its real usage block and exit 0 (`rbtv-bindings` catalog/inspect/scaffold/set/set-many,
`rbtv-master-profile` show/request/apply, `rbtv-goal-request`
validate/handle/scaffold-and-queue). `link-tools.py` has no probe of its own; `--check` is its
self-test. Deployed at the moment of the run, 2026-08-27 — the links are live on this box now.

## ATTENTION
- `TOOLS` in `link-tools.py` is a hardcoded dict that reads no `exposure.csv`, so a new
  `method=path` tool is invisible to it and the installer will report a clean `ok`/exit 0 while the
  name does not resolve. A green `--check` proves the LISTED links are sound, never that the list
  is complete.
- The membership rule is now written in the docstring: an ignite `method=path` tool belongs in
  `TOOLS` only when its `exposure.csv` row leaves the `rbtv-cli` column EMPTY. Adding a tool that
  already has an `rbtv …` verb duplicates a reach that exists and contradicts the stated rule.
- Two independent PATH-link mechanisms exist in this workspace and are routinely confused:
  `ignite/deploy/link-tools.py` (hardcoded list, targets `~/.local/bin`) and
  `meta/installer/lib/pathlinks.py` (exposure-driven, targets `~/.rbtv/bin`, has Windows shims).
  A fix in one does nothing for the other.
- The three targets are extension-less BASH wrappers, so they dodge the extension-less-loader crash
  that `coord/20260826-i-coordinate-crashes-by-installe` records for Python entry points. Any
  future Python tool linked here re-enters that trap and must load its module with an explicit
  `SourceFileLoader`.
- The links resolve to the source repo, not the deploy worktree. Editing an operator tool changes
  what bare-name callers execute immediately — there is no staging step to catch a mistake.
- TOOLS is hardcoded and reads no exposure.csv: a green --check proves the listed links are sound, never that the list is complete.
- Membership rule now in the docstring: an ignite method=path tool belongs in TOOLS only when its exposure.csv rbtv-cli column is EMPTY.
- Two unrelated PATH-link mechanisms exist: ignite/deploy/link-tools.py (~/.local/bin) and meta/installer/lib/pathlinks.py (~/.rbtv/bin). Fixing one does nothing for the other.
