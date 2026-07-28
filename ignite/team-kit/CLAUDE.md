# team-kit/ — rules for agents in this folder

Shared, run-agnostic multi-agent team mechanics (index: `team-kit.md`). Component of the **ignite**
module — the kit's tmux seats are the interactive twin of the daemon's session substrate. Entry
point: the `rbtv-team-kit` skill (thin loader → `team-kit.md`). Promoted 2026-07-26 from the
second-brain campaign workspace (`1-projects/rbtv-sb-merge-refactor/build/team-kit/`) after three
proving runs; the run records live in that vault under
`1-projects/rbtv-sb-merge-refactor/build/prototypes/team-runs/`.

## Hard rules

- **`system-design.md` is designer-only.** It carries the kit's design rationale for agents
  DESIGNING or EVOLVING this system. Run agents (leader, workers, observers, judges) MUST NOT
  read it — it is not among any briefing's pre-reads and adds no execution context. Designers:
  read it FIRST, and keep it updated in the same change as any design change (its own header
  states the maintenance contract).

- **No run state lives here — ever.** `coord.py` writes all state into the RUN PACKAGE passed via
  `--package` (`{package}/coordination/`). A `workers.md`/`messages.md`/`groups.md` appearing in
  this folder is a defect: find the caller that omitted `--package` and fix it.
- **This folder is run-agnostic.** Nothing here may name, special-case, or depend on a specific
  run, roster, or target project. Run-specific rules belong in that run package's `CLAUDE.md`;
  run-specific briefings in its `workers/`.
- **NEVER save `coord.py` by hand — `python3 save-coord.py --candidate NEW.py` is the save path.**
  Write the candidate BESIDE `coord.py`, then let the gate install it: it imports the candidate as
  a module and builds its full parser (the two failures `ast.parse` passes), carries the live
  file's mode, replaces atomically, and asserts the result is EXECUTABLE and byte-identical to what
  it gated. `coord.py` is re-read by every seat on every invocation and has no fallback, so a bad
  save takes the whole room's messaging down at module import — including every recovery path,
  which all run through this file. Hand-rolling `shutil.copyfile` + `os.replace` is how it has gone
  down twice: `copyfile` does not carry permissions, so the live file lands at `0644` and every
  bare `coordinate` returns "Permission denied" (2026-07-27 22:41; the interpreter path,
  `python3 coord.py …`, still works and is the recovery route). The gate is `save-coord.py`; its
  proof is `probes/probe-save-gate.py`.
- **`coord.py` changes MUST pass the self-test before use:** `python3 coord.py selftest` (exit 0),
  run from INSIDE this folder — it aborts on missing sibling assets elsewhere. The save gate is
  deliberately not the done gate: it does not run the self-test, so run it yourself after saving.
  The same rule applies to `watch.py` (`python3 watch.py --selftest`). Extend the self-test in the
  same change that adds or alters a mechanic — an untested mechanic is how the previous tooling
  shipped six latent defects.
- **Protocol changes are evidence-gated.** `protocol.md` rules — and equally those in its two
  role-scoped siblings `briefing-authoring.md` and `roles.md`, split out of it 2026-07-28 so a seat
  stops loading another role's content — carry a pointer to the measured
  failure they were earned from — a P-number (a numbered proposal from a proving run) or an `S§n`
  section reference (a run-1 strategic finding that was never numbered as a proposal). Both resolve
  into the proving runs' observer files, preserved in the origin vault under
  `1-projects/rbtv-sb-merge-refactor/build/prototypes/team-runs/`. Amend a rule WITH its evidence
  pointer, or not at all.
- **Backward compatibility:** existing run packages invoke this kit by absolute path. Renaming or
  moving files here requires repairing every consumer package's `CLAUDE.md`/briefings in the same
  change.

## Known instance couplings — generalize before master (owner-gated)

Carried VERBATIM at promotion (2026-07-26) per the repo's "never generalize silently" rule.
Before this kit ships beyond the `ignite/core-daemon` branch, the owner rules on each:

| Where | Coupling |
|-------|----------|
| `coord.py:38` | `VAULT_ROOT = "/home/henri/ht-wkdir/second-brain"` — hardcoded spawn-cwd fallback; should resolve from the run package / workspace root at runtime |
| `coord.py` selftest fixtures | Real captured pane text carries the origin vault's absolute paths (production-regime fixtures — anonymize or keep as-is by ruling) |
| `team-kit.md` / `system-design.md` | Provenance mentions of the origin vault's run packages (descriptive history, arguably fine) |
| `tmux-overview` / `overview-compact.py` / `provider-usage.py` | Superseded by the promoted `teamview` CLI (`orchestration/cli/teamview/`) — decide drop vs keep for the `panel` strip |

## Starting or joining a run

Follow `team-kit.md` § Starting a new run. Every executing agent follows `protocol.md`; the run
package's `CLAUDE.md` wins on conflict.
