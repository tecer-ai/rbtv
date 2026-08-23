# 20260823-c-installer-split-into-lib-selft — installer split into lib + selftest, renamed install.py

kind: change
component: meta-installer
date: 2026-08-23
commit: e9d571a5
deployed: yes
pin: NONE

## Motivation

`meta/installer/install2.py` had reached 7,418 lines (357 KB) in one file, of which `selftest()` alone was 3,035 — a single function holding 370 assertions — and the module docstring another 372 of design decisions before the first line of code. The owner directed the split on 2026-08-23 and chose the shape in an interview: subject-split the self-check, two subfolders (`lib/` and `selftest/`), decisions in a document beside the code, and — separately — "rename install2 to install.py simply". The file's own D1 had recorded the opposite ("ONE FILE, no package… the old installer's thin-entry + `admin/install/` split still earns nothing at this size"), so the split is an explicit supersession of a recorded decision, not a drift from it.

The second half of the ask was a regression the owner had been living with: the interactive flow printed a numbered list and read comma-separated numbers, while the PREDECESSOR installer (deleted `admin/install/installer/tui.py`, last live at f33bb07b) had had an arrow-key checkbox — up/down, space to tick, `a` for all, `i` for details. The owner wanted that UI back on the modern tool, with the non-interactive surface untouched.

## Design

The production code was cut by AST-measured symbol spans, never retyped: a generator read every top-level `def`/assignment out of install2.py, wrote each into the module named by a hand-authored map, and COMPUTED each module's import block from the symbols it actually loads. That is what makes the diff trustworthy at this size — the bodies are byte-copies, and the import lists cannot drift from the code because nobody typed them.

Nineteen modules under `lib/` plus `__init__.py`, ordered so the import graph is strictly forward and there is no cycle to reason about: constants, catalog, claims, content, guidance, pathlinks, target, state, planning, apply, selection, operations, listing, doctor, report, tui, interactive, parser, commands. Two 2-node cycles existed in the original and were broken by moving the symbol to the module whose job it actually is, not by a late import: `migrate_workspace_harnesses` / `book_harnesses` / `installed_harnesses` moved from the install verbs into `state.py` (they read and mutate the book), and `_settings_view` / `_print_settings` moved from the CLI into `listing.py` (they are the head of `li`). `_part_in` and `_wanted_parts` / `rec_files` / `rec_owns_nothing` went to `state.py` for the same reason — they take a BOOK record, not a catalog record. `do_scan` went to `listing.py`. The one remaining cycle, `commands` -> `selftest` -> `lib`, is broken by a function-local import inside `cmd_selftest` and `main`, so an ordinary run never loads 3,000 lines of checks.

`discovery.py` deliberately did NOT move into `lib/`. `ignite/team-kit/materialize-seats.py::_discovery` computes `parents[2]/meta/installer` and calls `__import__("discovery")` on it — the path is a contract with another tool, so moving the file would have re-opened the `exposes-ref-dangling` split that D86 closed, for no gain.

The self-check was the harder half. Its 42 sections shared a single function frame: 17 locals cross a section boundary, and `ok` is mutated by `check()` through `nonlocal` from every section at once — a split that loses its grip on `ok` still prints PASS lines while contributing nothing to the verdict, which is a silent failure, not a loud one. `selftest/context.py` holds that frame instead: `Ctx` owns `ok`, `check`, `skip`, `tmp`, `tree`, `target`, `shadowed`, and `CARRIED` names the ten locals measured (by reaching-definition analysis, not by eye) to cross a boundary. Each section became a function whose body is a byte-copy dedented by four, wrapped by one unpack line and one `ctx.keep(locals())`. Rejected: rewriting `check(` to `ctx.check(` inside 3,000 lines of bodies, which would have made the diff unreviewable for no behavioural gain.

Section membership says what a check is ABOUT; `runner.ORDER` says when it runs. They are separate because the sections are not independent — one installs what a later one reads — and because two sections shared the printed title "H", so a split keyed on titles would have collided.

The arrow-key UI was recovered from git rather than reinvented (`git show HEAD:admin/install/installer/tui.py`), then carried forward with one design change that matters: the degradation to a numbered list happens INSIDE each widget, decided once from `sys.stdin.isatty() and sys.stdout.isatty()`. Callers therefore have exactly one path and never branch on terminal capability. The alternative — keeping the old numbered flow as a second branch in `interactive()` — was rejected as a second source for one behaviour.

## How it works

`meta/installer/install.py` puts its own directory on `sys.path` and calls `lib.commands.main()`. `lib/__init__.py` repeats that path insertion, once, so any module of the package can `import discovery` however it was reached — the entry script, the self-check, or a bare `import lib.x` from that directory. `selftest/__init__.py` does `import lib` for exactly that bootstrap.

`REPO_ROOT` is defined once, in `lib/constants.py`, and its arithmetic CHANGED with the depth: `parents[3]` (lib -> installer -> meta -> repo) where it used to be `parents[2]`. `selftest/test_layout.py` fails the run if it ever stops resolving to the repo, spelling the expectation out as literals rather than re-deriving it from `__file__`.

`rbtv install` reaches the tool through `meta/rbtv-cli/tool/lib/verbs.js`, whose `INSTALLER` constant now names `install.py`; the exposure row is `install,tool,path,rbtv install,install.py,,`, so the installer still discovers itself on the same depth-2 rule it applies to everything else. `INSTALLER_NAME` in `lib/constants.py` is the single source for the filename wherever it is written into a file: the managed-file banner, the loader note, and the `installer` key of the book. `GENERATED_MARKERS` carries BOTH spellings, so a guidance mirror minted before 2026-08-23 is still recognised and adopted.

The guided flow now asks: the workspace path (typed, with a suggested default and a validator that re-asks on a bad path instead of refusing the run), the components (a ticklist grouped by module id, pre-ticked from the book, `i` showing each component's parts and methods), the AI tools (a ticklist, only when the book has not recorded them — D16), the root guidance file (a single-choice picker, likewise once), then a dry-run report and a confirmation. Components that cannot be installed are named ABOVE the picker rather than greyed out inside it, because a greyed row cannot say why.

## Consequences

`prompt_basis()` and its four self-check arms are DELETED. They existed because a mistyped basis filename used to throw away the target, the component picks and the harness picks (task 7.623(b)); the basis is now chosen from a list, so there is no typo to retry and the function was reachable only from its own test. The risk it covered — a fumbled answer costing the whole run — is now covered at the new mechanism: `select_one` re-asks up to three times on a bad number in typed mode. `resolve_basis` is untouched and still refuses a bad `--artifact` on the first try, with an arm holding that.

`_parse_harnesses` moved from `interactive.py` to `commands.py`: with the harness ticklist the guided flow no longer parses a comma-separated string, and its only remaining callers are the two D16b settings forms.

Driving the real arrow-key path under a forked pty exposed a live defect carried in from the predecessor: `_term_cols()` returned `os.get_terminal_size().columns` unguarded, and a pty whose window size was never set reports 0 rather than raising. The redraw divides by that width, so the picker died with `ZeroDivisionError` before drawing a single row — reachable in a detached multiplexer pane and on CI runners, not only under a test harness. Fixed at the one place the value is born, with `DEFAULT_COLS` as the floor.

Three files carrying edits this change requires were left OUT of commit e9d571a5 because they sit inside another session's uncommitted work: `meta/rbtv-cli/tool/lib/verbs.js` (the `INSTALLER` path), `meta/rbtv-cli/component.md`, and the repo `CLAUDE.md`. One foreign hunk rode along inside `meta/installer/exposure.csv` — a peer's `core/` -> `meta/` rbtv-cli path correction in a comment — and is disclosed in the commit message.

Found and NOT fixed, because the split did not create them: `AGGREGATE_METHODS` (`lib/constants.py`) and `print_scan` (`lib/report.py`) were already defined-but-never-referenced in install2.py, and `do_scan` is reached only from the self-check. The repo-root `install.py` entry raises a traceback because `admin/install/installer` is deleted in the working tree, and `rbtv` refuses every verb because `admin/install/module-manifest.json` is gone with it.

## Verification

`rbtv install selftest` is 384 PASS / 0 FAIL at e9d571a5. The decisive evidence is a diff, not a count: the 370 pre-split checks were captured to a baseline BEFORE the first edit, and the split suite's output is byte-identical to it once the two new layout arms are excluded — same checks, same order, same shared state, same text. Fourteen new arms cover the guided flow driven end to end without a terminal (install, the D16 second run that does not re-ask, cancelling at the confirmation, pre-ticked rows), the widget fallbacks, the zero-width terminal, the retained pre-rename banner, and `REPO_ROOT`.

Every new arm was mutation-proved red before being trusted: removing the pre-tick reddens 2, rewording the harness question reddens 1, `parents[3]` -> `parents[2]` reddens 2, removing the width floor reddens 2. The first attempt at the width arm reported ZERO failures under mutation because the suite CRASHED rather than failed — the arm now reports a caught `ZeroDivisionError` as a FAIL detail, so a grep for `[FAIL]` cannot read a dead run as a clean one. The arrow-key path itself has no automated arm (it needs a pty, and the installer supports Windows); it was driven by hand under `pty.fork()` — down, `i` for detail, space, enter, and an up-arrow in the single-choice picker all behaved, returning the expected indices.

Deployed yes on commit: `install.py` is live-tree Python invoked per `rbtv install` run, not daemon code awaiting a deploy. `ls`, `li`, `doctor`, `--json` and a dry-run `add` were each run against the live vault workspace after the split.

## ATTENTION

- `REPO_ROOT` moved from `parents[2]` to `parents[3]` because `lib/constants.py` sits one level deeper than `install2.py` did. Any new module placed at a different depth that re-derives the repo root gets a directory holding no modules and returns an EMPTY catalog with no error — a wrong-but-silent result. Read `REPO_ROOT` from `lib.constants`; never compute it.
- `selftest` sections are ORDERED, not independent: `runner.ORDER` is the suite, and a section moved within it reads state a different section left. Adding a local that a later section must see requires adding its name to `CARRIED` in `selftest/context.py` — an unlisted name silently arrives as `None` instead of raising.
- `discovery.py` must stay directly in `meta/installer/`. `ignite/team-kit/materialize-seats.py` imports it by bare name from that directory; moving it into `lib/` breaks the materializer with no failure visible from the installer's own suite.
- `GENERATED_MARKERS` holds two spellings of the generated-mirror banner on purpose. Dropping `"GENERATED by install2.py"` orphans every guidance mirror minted before 2026-08-23 — they stop being adopted and start refusing the run as foreign files.
- A widget must never be given a terminal width that came from anywhere but `_term_cols()`. A pty with no window size reports 0 columns, and the redraw divides by it.
