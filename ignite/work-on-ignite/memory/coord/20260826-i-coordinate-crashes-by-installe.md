# 20260826-i-coordinate-crashes-by-installe — coordinate crashes by installed name (extension-less loader)

kind: issue
component: coord
date: 2026-08-26
commit: df22c29d
deployed: no
pin: NONE
components: deploy

## Observed
`~/.local/bin/coordinate --help` crashed by installed name: `AttributeError: 'NoneType' object has no attribute 'loader'` at `coord.py:66`, exit 1.
Reachable by any of the three uncaged system-role seats (goal-master, channel-master, leader), since none of them can call `coordinate` by full path — every one of their actuator calls goes through this bare name. Running the SAME file by its real path (`python3 ignite/coord/coord.py --help`) worked fine. Only the extension-less `~/.local/bin/coordinate` symlink triggered it.

## Mechanism
`spec_from_file_location` returned `None` because `__file__` had no recognizable extension.
`coord.py`'s `if __name__ == "__main__":` trampoline (landed `bc0af66f`, "the six supervision modules become real imports") re-enters the file by path — required so `save-coord.py`'s mutation gate, which runs `python3 <candidate> --help`, actually exercises the candidate rather than resolving an installed copy by name. It did `_ilu.spec_from_file_location("coord", __file__)` with no explicit `loader=`. `spec_from_file_location` infers the loader from `__file__`'s suffix; `__file__` is whatever name invoked the script, and the `coordinate` symlink in `~/.local/bin` carries no `.py` suffix. No suffix matches no loader, so the call returns `None`, and `module_from_spec(None)` raises the `AttributeError` before `coord.py`'s own `main()` ever runs.

## Attempts
First attempt held — checked: `git log -- ignite/coord/coord.py` (only `bc0af66f`, `1cbb7c76`, `7dd08887` touch this file since the split; none addresses loader inference), and `ignite/supervisor/supervise.py` (the sibling "door" seats can call by name without crashing) — it never re-enters itself at all; it does `sys.path.insert(...); import coord` and dispatches into the SAME already-imported `coord` module, so it never hits `spec_from_file_location`. That pattern doesn't apply to `coord.py` itself, since `coord.py` is the file the mutation gate needs re-executed literally, by path, not resolved through `sys.path`.

## Fix
Passed an explicit `SourceFileLoader("coord", __file__)` into `spec_from_file_location`, so the loader no longer depends on the invoking name's extension — it just reads and compiles `__file__` as Python source. Rejected: switching to `import coord` by name (defeats `save-coord.py`'s gate — every mutant would resolve the installed, unmutated kit and pass); rejected renaming/copying the symlink to carry a `.py` suffix (moves the defect to every other caller that types the bare name `coordinate`, and the daemon's own spawn profiles + every seat prompt name it bare).

## Consequences
No known regressions — the change is additive (one more keyword argument) and the by-path re-entry semantics that `save-coord.py`'s gate and the "ONE NAMESPACE, ALWAYS NAMED `coord`" invariant depend on are unchanged (still keyed on `__file__`, still installs into `sys.modules["coord"]` before `exec_module`).

## Verification
`python3 ignite/coord/coord.py selftest` → PASS, 0 failures (full run, ~4 min). Reproduced the crash pre-fix via `bash -c '~/.local/bin/coordinate --help'`; confirmed fixed post-fix on: the `~/.local/bin/coordinate` symlink directly, the bare `coordinate` name with `~/.local/bin` on PATH, and the real path — all exit 0. By-path re-entry re-verified with a hand-built mutation: copied the whole `coord/` component to a scratch dir, renamed `coord.py` to an extension-less `coordinate`, edited a docstring line — the traceback surfaced the SCRATCH copy's own line numbers, confirming the mutant's own content executes (unrelated `ModuleNotFoundError` further down is scratch-copy incompleteness, not this fix). Not deployed — this is the live repo tree; the deploy worktree (`~/.local/state/rbtv-deploy`) was not touched (out of this seat's walls).

## ATTENTION
- `spec_from_file_location(name, __file__)` with no `loader=` is an extension-sniffing call — ANY future re-entry-by-path trampoline in this kit must pass an explicit loader or it silently breaks the moment its `__file__` loses a recognizable suffix (a new symlink name, a `.pyc`-only deploy, etc).
- The by-path-not-by-name comment immediately above this code is still exactly correct and untouched — do not "simplify" this block into `import coord`; that reopens the `save-coord.py` mutation-gate hole this same block's first comment documents.
- `supervise.py`'s `import coord` pattern is NOT a template for `coord.py`'s own trampoline — they solve different problems (a thin second door vs. re-executing the tested file itself).
- spec_from_file_location needs an explicit loader= or an extension-less __file__ returns None
