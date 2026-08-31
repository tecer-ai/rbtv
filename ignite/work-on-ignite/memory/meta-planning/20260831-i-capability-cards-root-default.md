# 20260831-i-capability-cards-root-default — capability-cards --root default was a 5-card mirror slice

kind: issue
component: meta-planning
date: 2026-08-31
commit: f55dc3a3
deployed: no
pin: meta/planning/capabilities/capability-cards/tool/test_capability_cards.py
register-id: G-leader-0828-2010

## Observed
`capability_cards.py list`/`show` defaulted `--root` to the relative `.rbtv/mirror/`. From a seat
folder (cwd-mode) that path does not exist under the cwd and the tool dies `root path does not
exist`; from the vault root it silently resolves to a PARTIAL installer copy — 5 cards against the
~182 the rbtv repo root actually carries — with no error, "a wrong answer that looks like an
answer." Sighted repeatedly (task 158 seed evidence): `G-leader-0828-2010` (leader measured 5 vs
182 at source, 2026-08-28), `G-plan-drafter-0828-1849` (`stools-canvas-audio-elevenlabs-planning`,
same partial-mirror facet). Reproduced 2026-08-31: `capability_cards.py list` from `/tmp` ->
`root path does not exist: .rbtv/mirror`.

## Mechanism
`list_parser`/`show_parser` both declared `default=".rbtv/mirror/"` — a path relative to whatever
the process's cwd happens to be, with no relation to where the tool itself lives or where the rbtv
repo's real exposure.csv catalog is. The catalogs moved into the rbtv repo 2026-08-22 (per
`G-leader-0828-2010`'s evidence); the default was never updated to follow, and nothing in
`load_cards`/`find_components` warns that a resolved root is suspiciously small.

## Attempts
First attempt held — no prior fix found in `ignite/work-on-ignite/memory/meta-planning/` or in
`test_capability_cards.py` (every existing test passes `--root` explicitly; none exercised the
default at all, so a regression here would have gone unnoticed by the suite).

## Fix
Both defaults now read `DEFAULT_ROOT = str(Path(__file__).resolve().parents[5])` — the rbtv repo
root, derived from the tool's own on-disk position
(`<repo>/meta/planning/capabilities/capability-cards/tool/capability_cards.py`, five levels down),
computed once at import time. Rejected: hardcoding an absolute path (breaks on any other machine or
checkout location — the seed explicitly rules this out) and resolving via `rbtv.json`'s
`rbtv_path` book (the tool already IS inside the repo it would resolve to, so reading a book to
re-derive its own ancestor directory is a needless indirection for no gain in correctness).

## Consequences
No deletions. `--root` still fully overrides the default (unchanged flag semantics) — verified by
an explicit call passing a different path and confirming it, not the derived default, is what the
tool reports as missing when that path itself does not exist on disk.

## Verification
`capability_cards.py list` (no `--root`) from `/tmp` and from a seat folder: 185 cards (was: refusal
from a seat folder; a 5-card silent slice from the vault root). New pinning test
`test_default_root_is_the_rbtv_repo` in `test_capability_cards.py`: asserts `DEFAULT_ROOT` equals
the derived repo root, and that a no-arg `list --json` run from a directory carrying no
`.rbtv/mirror/` at all (tempdir) returns >100 cards. `python3 test_capability_cards.py` — PASS (all
legs, including the new one). Not deployed — a plain script, live-on-save.

## ATTENTION
- `DEFAULT_ROOT` is computed once at import (`Path(__file__).resolve().parents[5]`) — moving this
  file to a different depth under the repo without updating the `[5]` index would silently point the
  default somewhere else with no error (it would still find `component.md` files, just fewer of
  them, reproducing exactly this defect's silent-slice failure mode).
- This does not touch the OTHER facet `G-plan-drafter-0828-1849` also named: `capability-cards`
  missing from a seat's granted PATH entirely when the target lacks +x — that facet is task 161
  (`ignite/supervisor/spawn/spawn.js`), fixed separately and filed under `supervisor`.
