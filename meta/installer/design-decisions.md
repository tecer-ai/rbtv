# Installer design decisions

The one home for the decisions `install.py` was built to. Each `Dn` is cited by
name from the code that implements it; the module that owns a decision names it
in its own docstring. Delegated to the builder and recorded here — this file is
documentation, nothing reads it at runtime.

Lifted out of `install2.py`'s module docstring on 2026-08-23, when that file was
split into `lib/` and renamed `install.py`; the text below is unchanged except
where a decision was itself superseded, which is stated in the decision.

## D1 — PLACEMENT

PLACEMENT — the component is `meta/installer/`, and since 2026-08-23 the tool
inside it is a PACKAGE, not one file (owner ruling; supersedes the original
"ONE FILE, no package" of this decision — 7,418 lines in one file had stopped
being readable, and the `coding` skill's one-responsibility-per-file rule is
what the split answers).

The layout:

- `install.py` — the entry point. Puts its own directory on the import path
  and calls `lib.commands.main()`. Nothing else. Named `install.py` since
  2026-08-23; it was `install2.py` from its first commit until then, while a
  predecessor of that name still existed at the repo root.
- `lib/` — one module per responsibility, each named by the responsibility it
  holds; the import graph is strictly forward (`constants` → … → `commands`),
  so there is no import cycle to reason about. `lib/__init__.py` is what puts
  `meta/installer/` on the import path, so any module of the package can
  `import discovery` however it was reached.
- `selftest/` — the runnable check, one module per subject, driven by
  `selftest/runner.py`. Reached only by `rbtv install selftest`.
- `discovery.py` — deliberately NOT inside `lib/`. It is imported by name from
  this directory by `ignite/team-kit/materialize-seats.py`
  (`_live_import(<repo>/meta/installer, "discovery")`), so its path is a
  contract with another tool, not an internal detail.
- `design-decisions.md` — this file.
- `exposure.csv` — the component's own manifest (D2).

The owner ruling that put the component under `meta` (2026-08-22) stands:
`meta/` hosts what operates on the rbtv SYSTEM itself rather than on a user
goal's content, and installing rbtv into a workspace is exactly that; the
module's capability-only extension (2026-08-14) is what admits a component
holding no seats and no workflow. The folder is a component-first one —
`exposure.csv` at depth 2 IS the component (D2) — so this installer discovers
ITSELF the way it discovers everything else, on the same rule, with no special
case.

THE REPO ROOT IS COUNTED, AND THE COUNT MOVED. `REPO_ROOT` is defined once, in
`lib/constants.py`, as `Path(__file__).resolve().parents[3]` — lib → installer
→ meta → repo. It was `parents[2]` while the code lived one level higher. Every
tree scan and every fixture reads `REPO_ROOT`; a reader who reaches for
`Path(__file__).parent` gets a directory holding no modules and scans up empty,
which is a wrong-but-silent result, not an error. `selftest/test_layout.py`
fails the run if `REPO_ROOT` ever stops being the repo, so a future move that
forgets the count is caught by the suite rather than by a user.

## D2 — WHAT A COMPONENT IS

WHAT A COMPONENT IS — DEPTH-2 + exposure.csv (owner ruling, 2026-08-22)
— a directory at EXACTLY depth 2 of a scanned tree that contains
`exposure.csv`. Identity is `<module>/<component>` (two segments), so
depth 2 is forced by the id scheme. `component.md` is not read, not
checked, not a marker. A depth-1 manifest (the module-root files of the
old standard) is invisible here; a depth-3 file is not a component.
A malformed manifest (columns other than the seven) refuses by name —
it is never skipped. A directory without `exposure.csv` is not a
component; there is no no-manifest report. Hub units (`_hub/`) are a
separate branch (D15) and are untouched by this rule. The two
installers stayed separate: the PREDECESSOR installer — the repo-root
`install.py` entry plus its `admin/install/` package, unrelated to the
`install.py` of D1 — kept the old-standard tree.

## D3 — TREES + PRECEDENCE

TREES + PRECEDENCE — two roots, scanned together: `mirror` =
`{target}/.rbtv/mirror`, `repo` = the directory holding this file, which
is NOT overridable — the file and its tree ship together, so a flag
pointing one at another's tree only ever named a broken pair (owner
ruling, 2026-08-21). `--mirror-tree` stays. On the same id in both, the
MIRROR WINS (workspace-local staging is the newer copy by construction) and
the shadowing is reported, never silent.

## D4 — HARNESSES

HARNESSES — the three launchable ones (claude, codex, opencode). The set is
WORKSPACE-WIDE, not per component (D16). The standalone kimi CLI was
retired 2026-08-14 and
its models moved under opencode; `cast` lists only these three. Kimi
models remain reachable as opencode models. CON-2's three-harness bound
and this tool now agree. A live book that still lists `kimi` is stripped
on load (kept others, never an empty list) and persisted on the next write.

## D5 — STATE

STATE — `{target}/.rbtv/config/install.json`, recording per component: source
tree, module, component, harnesses, every whole file written, and every
shared-file CLAIM held. Uninstall removes exactly that set and nothing else.

## D6 — COLLISIONS

COLLISIONS — one rule, at two granularities. A planned WHOLE FILE that
exists on disk and is not in our book refuses the run, pre-write, zero
files. A planned KEY inside a shared config file that exists and is not in
our book refuses the same way. A path or key that IS in our book is ours to
rewrite (byte-identical → skipped; loaders are derived). This is what
"tolerate what we did not write" means operationally: we never overwrite a
stranger's file or key, and we never assume our book is the whole truth.

## D7 — SHARED FILES

SHARED FILES — `.mcp.json`, `.claude/settings.json`, `.codex/config.toml`,
`.codex/hooks.json` and `opencode.json` belong to the whole installed set
AND may already carry foreign content, so they are never written or deleted
wholesale (D12). They are recomputed from the whole installed set on every
install and uninstall; install and uninstall are the same operation on a
set, followed by one emit.

## D8 — `agents.md` AND THE GUIDANCE SURFACE

`agents.md` AND THE GUIDANCE SURFACE (rewritten 2026-08-10 to conform to
CMP-12, the ONE form authority; the registry is never edited from here) —
CMP-12's `agents.md` row IS this method's realization: a per-folder guidance
file whose NAME is keyed by harness (claude `CLAUDE.md`, codex `AGENTS.md`,
qwen `QWEN.md`, opencode `AGENTS.md`-or-`CLAUDE.md`).
There is no index file: the earlier `.agents/rbtv2-exposure.md` was an
invented artifact in no CMP-12 cell, auto-loaded by no harness, and is
RETIRED — an existing one is removed by the ordinary booked-file machinery
on the next install or uninstall. Every `agents.md` row and every forced
rule read is carried by the GENERATED guidance file (D13), inside one fenced
`rbtv2:start … rbtv2:end` block at its head. The BASIS is still never
written: whatever block the basis itself would need is REPORTED for the
human to place, and mirrors from there.

THE FORCED READ (CMP-12 § Fallback mechanics) is for the harnesses that
auto-inject no rule folder — Codex and Qwen ONLY. It is emitted into a
guidance file only when an installed harness of that set reads that file's
name, and it enumerates the paths those harnesses' rule copies were ACTUALLY
written to — a rule whose component was installed claude-only exists at
`.claude/rules/` and is never named to codex, whose MANDATORY Step 0 would
otherwise point at a file that was never created.
NEVER for claude (`.claude/rules/` auto-injects), and never for
opencode, which CMP-12 gives no separate rule type because it reads
`.claude/` natively — so opencode's `rule` realization in MATRIX is claude's
own `.claude/rules/` file, deduped by path exactly as its `skill` row
already is.

## D13 — THE GUIDANCE MIRROR

THE GUIDANCE MIRROR (owner ruling 9, 2026-08-10; harness-keyed per CMP-12
2026-08-10) — the BASIS is the guidance file the human authors (`CLAUDE.md`
or `AGENTS.md`), NEVER written by this installer. The mirror targets are
derived, never hardcoded:

    targets = { CMP-12 guidance filename of each INSTALLED harness }
              − { the basis }

so a claude-only install with basis `CLAUDE.md` writes NO mirror at all
(empty set → nothing rendered, nothing booked), and several harnesses that
share a filename (codex + opencode both read `AGENTS.md`) get ONE
file. "Installed harnesses" is the union of the `harnesses` recorded for
every component in our own book — the same set uninstall shrinks.

The basis is answered once — on the first `add` via `--artifact`, or in
`interactive` — persisted as `guidance_basis`, and thereafter owned by
`rbtv install set artifact` (D16). It is never re-asked and never
defaulted: since D16 the first `add` REQUIRES an explicit answer, because
unset silently meant "generate nothing". A basis value outside the known
guidance names refuses. Each generated mirror is a
normal installer-owned file — booked, collision-gated (a mirror file that
exists and is not in our book, e.g. one the old installer's `model_mirror`
renders, refuses the run pre-write) and removed on full uninstall.

WHEN THE TARGET SET GOES EMPTY (a basis flip that leaves every installed
harness reading the basis), yesterday's generated file is today's authored
one: it is kept, never booked, and its stale `GENERATED — DO NOT EDIT`
banner and fenced block are cleaned off IN PLACE — the one write this
installer makes to a basis name, guarded by the machine-readable banner, so
a hand-authored file is never touched. Leaving the banner would tell the
human their own file must not be edited.

SCOPE — RECURSIVE (owner ruling d-s17-agents-md-handover-to-install2,
2026-08-10; amends A6's root-only scope). A mirror is rendered beside EVERY
basis file in the tree, each generated from THAT directory's own basis, at
parity with the old installer's `model_mirror` driver
(`orchestration/models/mirror/driver/guidance.py`). The walk skips: any
directory named in `GUIDANCE_SKIP_DIRS`; any NESTED GIT REPO (a directory
below the root holding `.git` — its guidance files belong to that repo and
are never touched); the `GUIDANCE_ALWAYS_EXCLUDED` prefixes (`.rbtv/goals`,
whose BOTH routers are scaffold-owned — a structural collision in every
workspace rbtv serves, so a driver default and not a per-workspace entry);
and whatever `rbtv install add|rm artifact exclude` records (persisted as
`guidance_excludes`; the verb edits the list as a SET — the old driver's
`--exclude` replaced it wholesale, which is why asking to skip one more
folder used to silently un-skip every other). `protect` covers EVERY directory's basis, not just the root's.
A basis that is itself somebody's generated mirror has its banner STRIPPED
before mirroring, and the strip is reported — the old driver's banner-over-
banner accumulation (task 7.623 item (a)) is a defect and is NOT ported.
Strip rather than refuse, because the ruled recovery from a deleted basis is
to repoint at the surviving GENERATED file: a refusal would break it.

ADOPTION (owner ruling, 2026-08-10, unblocking the same handover). A planned
MIRROR path that exists outside our book is ADOPTED — overwritten and booked
— when the file itself PROVES it is generated, by carrying a machine-
readable DO-NOT-EDIT banner (ours or `mirror.py`'s). Without that proof it
still refuses with `guidance-mirror-collision`. That boundary is the whole
point: the refusal protects HAND-AUTHORED guidance, and a file whose own
header says a tool wrote it is not that. Adoption is what let install2 take
the mirror over from `install.py`'s `model_mirror` on the maintainer's vault
without a human hand-deleting another tool's artifact.

A PARTIAL UNINSTALL CAN UN-MANAGE A MIRROR, briefly (task 7.623(c)).
Removing a component must NEVER be blocked by a mirror problem, so when the
replan refuses (a deleted basis, a hand-edited book) the mirror is SKIPPED
and every guidance file the book holds is held off the delete set: the file
STAYS ON DISK BUT LEAVES THE BOOK. In that window it is an unbooked file
under a mirror name, so an install carrying a DIFFERENT basis refuses
`guidance-mirror-collision` on it unless its own banner lets ADOPTION take
it. The next successful install re-books it. Correct — un-managed beats
deleted — and surprising enough to say here rather than only at the code.

THE EXPOSURE BLOCK is rendered at the ROOT only (the installer exposes
components at the install root — see BOUNDARY above), inside the fenced
`rbtv2:` block D8 describes. A nested mirror is a pure per-folder guidance
mirror: banner + that folder's basis body, nothing else. The fence is what
makes the basis FLIP safe: a generated file that later becomes the basis has
both its banner and its fenced block stripped before it is re-mirrored, so
neither can stack across runs.

## D14 — THE `.gitignore` BLOCK

THE `.gitignore` BLOCK (owner ruling, 2026-08-21) — every per-component
artifact and the state file are MACHINE-LOCAL: a loader bakes an ABSOLUTE
entry-point path (D10) and the book records an absolute target, so a
committed copy is wrong on every other machine
(`decisions.md#d-s15-installer2-artifacts-machine-local`). Until 2026-08-21
the workspace enforced that with name patterns (`.claude/skills/rbtv2-*/`);
D12 retired the prefix, and git cannot match an in-file marker — so the
installer, which is the one thing that knows exactly what it wrote, carries
the list itself. It is an ORDINARY D7/D12 shared-file claim: one fenced
`# rbtv2:start … # rbtv2:end` block in `{target}/.gitignore`, recomputed
from the whole installed set on every install and uninstall, removed with
the last component, gated by the same collision rule as every other claim.
Bounds: only when the target is a GIT REPO (nothing mints a `.gitignore`
in a workspace that has no git); the GUIDANCE MIRROR is never listed (it
carries no absolute path and is authored-adjacent content the workspace
commits — install.py's mirrors always were); and a `.gitignore` that
already carries a fence we do not own refuses, like any other claim.
A file ALREADY TRACKED by git is not covered — `.gitignore` does not
reach one, and untracking it is the workspace owner's call, not ours; the
report names any such file so the human sees it.

## D15 — `_hub/`

`_hub/` — METHOD-FIRST UNITS, NO MANIFEST (generalises the 2026-08-21
`_skills/` ruling) — `_hub/<method>/<name>` is an installable unit with no
`component.md` and no `exposure.csv`. The parent folder names the method.
A hub skill folder is still copied VERBATIM (the original D15 rule). Legacy
`_skills/<name>/` is discovered as `_hub/skills/<name>`; book keys rewrite
the same way on load (R6). `-m hub` reaches module `_hub`. pool, and a
directory-shaped path, refuse by name (R4).

INSTALL copies the folder VERBATIM (bytes, so a binary reference survives)
into `MATRIX["skill"]`'s directory for each installed harness, skipping
`.git`, `node_modules` and `__pycache__`. UNINSTALL deletes every file it
copied and prunes the emptied directories — the folder goes as a whole.

OWNERSHIP is stamped ONCE, on the copied `SKILL.md` (`_mark`); the files
beside it stay byte-identical to the source, which is the point of a
verbatim copy. `_is_ours` therefore reads a file's OWN marker first and then
the marker of any ancestor directory's `SKILL.md` — so every file under a
marked skill folder is ours, and stripping the marker from that one
`SKILL.md` releases the WHOLE folder from the book (D12's release arm),
which is the human's way of taking a vendored skill over.

## D16 — HARNESS AND ARTIFACT ARE WORKSPACE SETTINGS, SET ONCE, MANAGED BY THEIR

HARNESS AND ARTIFACT ARE WORKSPACE SETTINGS, SET ONCE, MANAGED BY THEIR
OWN VERBS (owner ruling, 2026-08-22). Both used to ride on `add`, and both
were silent when they did nothing: `--harness` DEFAULTED to all three, and
a narrower list on a later run MERGED into the record instead of narrowing
it, so a human asking for fewer harnesses got a successful run that changed
nothing. `--artifact` was worse — unset was a third state meaning "generate
no guidance at all", reachable by simply not passing the flag.

    the FIRST `add` on a workspace REQUIRES both `--harness` and
    `--artifact` (`--artifact none` is the explicit author-nothing answer)
    and records them in the book at TOP LEVEL, outside `components`;

    every LATER `add` REFUSES either flag (`setting-locked`), naming the
    verb that owns it — `add` decides which components are installed and
    nothing else;

    the ACTION-FIRST settings forms own them thereafter —
    `add|rm harness`, `set artifact`, `add|rm artifact exclude` (D16b).
    A harness change REPLANS EVERY BOOKED COMPONENT, so `rm harness
    codex` really deletes codex's files through the same book-diff
    `apply` uses for everything else — never a no-op.

Each component record still carries a `harnesses` list, now a projection of
the workspace set (every record holds the same one), because `plan_files`
reads it per record. `upgrade_book`/`read_state` migrate a pre-D16 book by
taking the UNION across its records — the widest set any component had, so
a migration never silently deletes an installed file.

## D16b — THE ACTION WORD COMES FIRST

THE ACTION WORD COMES FIRST (owner ruling, 2026-08-22, amends D16's
SPELLING only — every rule above about WHEN a setting may change is
untouched). D16 gave each setting its own noun-led verb, so the same
action was spelled two ways depending on what it acted on: `add -c
<component>` but `harness add <harness>`. Now one grammar covers both:

    rbtv install add harness codex        rbtv install rm harness codex
    rbtv install set artifact CLAUDE.md
    rbtv install add artifact exclude D   rbtv install rm artifact exclude D
    rbtv install harness                  rbtv install artifact   (show)

`set` exists rather than folding the basis into `add` because the basis
holds ONE value: choosing a new one REPLACES the old. Spelling a replace
as an "add" is the silent-overwrite shape D16 was written to kill, so the
grammar names the third action instead of lying about the second.

The noun-led spelling is GONE, not aliased — `harness add codex` refuses
with `verb-moved` naming the new form. Two spellings of one action is the
shape that drifts: one gets maintained and the other quietly rots.

## D16c — THE SETTINGS ARE READ IN `li`

THE SETTINGS ARE READ IN `li` (owner ruling, 2026-08-22, completes D16b).
With their edit forms moved to `add`/`rm`/`set`, `harness` and `artifact`
were verbs that only PRINTED three lines — menu entries a reader has to
step past to reach a verb that does something. Those three lines are a
description of THIS workspace, which is exactly what `li` reports, so
they head its listing (and ride its `--json` under `settings`).

Both verbs stay in the parser, HIDDEN and refusing. That is not an alias:
the whole point is that `rbtv install harness` — the thing a reader's
fingers already know — lands on a sentence naming where it went, instead
of on argparse's `invalid choice: 'harness'`, which names nothing.

## D9 — `path` ROWS MINT NOTHING UNDER THE INSTALL TARGET

`path` ROWS MINT NOTHING UNDER THE INSTALL TARGET
(`decisions.md#d-tool-inventory-exposure-rows`). `pool` stays inventory.
A `path` part is linked into `~/.rbtv/bin` under its part-id (human PATH);
that reverse does not write under `{target}`.

## D9b — WINDOWS PATH LINKS ARE `.cmd` SHIMS, NOT SYMLINKS

On Windows a D9 link is a generated `<part-id>.cmd` shim in `~/.rbtv/bin`
instead of a bare symlink: symlink creation needs a privilege most accounts
lack (WinError 1314), and a bare name is not executable there anyway —
Windows has no shebang layer. The shim's first line 
(`@rem rbtv-shim -> <target>`) is the D12 ownership marker AND the recorded
target; its second line spawns the interpreter the target's shebang names,
with the resolutions the cli memory entry
`20260824-i-rbtv-direct-delegates-unrunnab` settled: `python3` spawns as
`python`, and `bash` is git's own (`where git` → `../bin/bash.exe`, script
path forward-slashed), never PATH bash, which is usually WSL's and cannot
see `C:` paths. POSIX behaviour is byte-identical to before. The
`--write-path` line is likewise per-platform: PowerShell `$PROFILE` syntax
on Windows, bash/zsh on POSIX, same `# rbtv2:...` fences.

## D10 — BAKED PATHS ARE ABSOLUTE

BAKED PATHS ARE ABSOLUTE — a loader points at its entry point by resolved
absolute path (the `materialize-seats.py` precedent). Loaders are derived;
re-running the installer is how a relocated target is fixed.

## D11 — NO CATALOG ASSEMBLY

NO CATALOG ASSEMBLY — an entry-point of the form `prompts.csv#row-id` is a
catalog reference. This tool checks the FILE half exists and names the whole
reference in the guidance index; assembling catalog rows is the assembler's
and the materializer's job, not the installer's.

## D12 — OWNERSHIP IS MARKED IN THE FILE, NOT IN ITS NAME

OWNERSHIP IS MARKED IN THE FILE, NOT IN ITS NAME (owner amendment,
2026-08-21; supersedes the `rbtv2-` prefix of 2026-08-09) — a part is
realized under its OWN id (`.claude/skills/planning/SKILL.md`), and what
makes the file ours is the machine-readable `rbtv2-managed` marker its head
carries (`MANAGED_BANNER`, placed after any YAML frontmatter so a loader's
`---` block still parses). The book stays the primary record; the marker is
what lets the installer answer "may I edit this?" from the FILE, which the
book cannot do for a file the book never saw. Two consequences:

  · ADOPTION — a planned path that exists outside our book but carries the
    marker is overwritten and booked, exactly as a banner-carrying guidance
    mirror already was (D13). Without the marker it still refuses (D6):
    the collision gate protects hand-authored files, and a file whose own
    head says this tool wrote it is not one.
  · RELEASE — a booked file whose marker is GONE (a human took it over) is
    never deleted. It is dropped from the book and reported instead.

NAME COLLISION WITH THE PREDECESSOR INSTALLER — the repo-root `install.py`
entry plus its `admin/install/` package, which is NOT the `install.py` of D1.
It sweeps `.claude/{rules,commands,agents,skills}` for names starting `rbtv-`
(`admin/install/installer/generator.py::clear_previous_install`). Bare part
ids do not start with `rbtv-`, so that sweep still cannot reach our work —
and a manifest that DOES declare a `rbtv-*` part id is refused
(`part-id-reserved`) rather than minting a file the other installer would
delete behind our back.

LEGACY NAMES. Files earlier runs minted under the `rbtv2-` prefix carry no
marker (rules were verbatim copies). `LEGACY_PREFIX` keeps them recognized
as ours by the ownership test ALONE, so the first unprefixed run deletes
yesterday's prefixed files as stale instead of orphaning them. Nothing
mints that prefix any more.

Files that can carry neither a name nor a marker — the shared config files
of D7 — translate ownership to key/block ownership: a JSON file is edited at
the exact key paths the book records (`mcpServers.<name>`, `hooks.<event>`,
…) and a text file through a fenced `rbtv2:start … rbtv2:end` block;
uninstall removes exactly those keys or that block and deletes the file ONLY
when nothing at all is left in it.
