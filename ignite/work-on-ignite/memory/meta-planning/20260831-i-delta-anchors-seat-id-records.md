# 20260831-i-delta-anchors-seat-id-records — delta-anchors: seat-id records, no hardcode, eol-safe

kind: issue
component: meta-planning
date: 2026-08-31
commit: 9cc6b1e4
deployed: not-applicable — repo-side capability tool, no daemon deploy
pin: meta/planning/capabilities/delta-anchors/tool/test_delta_anchors.py

## Observed

`delta-anchors` (`meta/planning/capabilities/delta-anchors/tool/delta_anchors.py`) is the tool an
applier uses to land an authoring seat's `## delta` edits into target files and record what it
applied. Three defects lived in `run_apply`, two on one line (`meta/planning/capabilities/delta-
anchors/tool/delta_anchors.py:152` pre-fix): the applied-record filename was
`applied-deltas-round-<n>.json`, keyed on round alone with no seat identity, so when more than one
seat returned edits in the same round the second `apply` silently overwrote the first seat's
record; the output folder was hardcoded to `<goal>/planning/current/`, a singleton that gets
archived and replaced wholesale at every milestone promotion, orphaning the record from a later
reader (e.g. a milestone re-check against already-archived deltas); and targets were read/written
in default Python text mode, which silently converts every CRLF line ending to LF on write, so a
CRLF target came back entirely LF and a reviewer's `git diff` showed the whole file changed, not
just the edited span. Measured live: `meet-transcript-summarizer`'s archived goal folder
(`.rbtv/goals/_archive/meet-transcript-summarizer/planning/current/`) holds delta files from
THREE seats for round 1 (`plan-4-plan-assembler`, `plan-4-plan-resource-definer`,
`plan-4-plan-task-definer`) but only ONE `applied-deltas-round-1.json`, alongside a hand-made
`deltas-COMBINED-APPLY-round-1.md` — a person manually concatenating three seats' deltas so a
single `apply` call would produce a single record. Filed at the ignite-engine register: `G-leader-
0823-0020`, `G-plan-4-plan-assembler-0823-0007-2`, `G-plan-4-plan-assembler-0823-0007` (build-
ignite task 130).

## Mechanism

`run_apply` derived the record's round number from the delta filename (`round-(\d+)` on the
basename) but discarded the rest of the filename, so the seat id the author already encoded in
`deltas-<seat-id>-round-<n>.md` never reached the output name — two seats' distinct filenames
collapsed to the same `applied-deltas-round-<n>.json`. The output directory was computed as
`os.path.join(goal, "planning", "current", ...)` independent of where the delta file (or its
targets) actually lived, so it always pointed at whatever `planning/current/` currently meant
under the live goal, not at the material the record actually describes. And every target `open()`
call used Python's default text mode, which performs universal-newline translation on read
(CRLF→LF) and never re-translates on write, so `open(full, "w", encoding="utf-8").write(text)`
always wrote LF regardless of the file's original convention.

## Attempts

First attempt held — checked: `git log --oneline -- meta/planning/capabilities/delta-anchors/`
(one prior commit, `49c03d35`, the tool's original authoring commit; no later attempt at any of
these three defects) and the `ignite/work-on-ignite/memory/meta-planning/` index (no prior entry
for `delta-anchors`/`delta_anchors`). The hand-concatenated `deltas-COMBINED-APPLY-round-1.md` in
meet's archived goal folder is the *workaround*, not a code fix — a person routing around defect 1
by hand rather than the tool being repaired.

## Fix

Three changes, same read/write path: (1) `run_apply` now parses BOTH the seat id and the round
number out of the delta filename (`(.+)-round-(\d+)` on the basename, stripping a leading
`deltas-`) and names the record `applied-deltas-<seat-id>-round-<n>.json`, so two seats in the same
round produce two records instead of one silently overwriting the other. (2) The record is written
in `os.path.dirname(delta_path)` — beside the delta file itself — instead of a hardcoded
`<goal>/planning/current/`; since delta files conventionally live in `planning/current/` this is a
no-op for the common case, but it means a later re-check against an already-archived milestone's
delta file writes its record beside that archived material, not into whatever `planning/current/`
currently means for a different, live milestone. (3) A new `_eol_of()` helper sniffs the target's
dominant line ending (CRLF vs LF) straight from its bytes before any edit; the final write converts
the in-memory `\n`-normalized text back to that ending and writes with `newline=""` so Python does
no further translation — an untouched line round-trips byte-identical. Rejected: making the
consumer of `applied-deltas-*.json` tolerant of a missing/collided record instead of fixing the
producer — that would have papered over the same collision the next time two seats land in one
round. Rejected: normalizing all targets to LF on write — that is the defect, not a fix, and would
still make every CRLF file's diff opaque.

## Consequences

No public interface removed; the output filename shape changed
(`applied-deltas-round-<n>.json` → `applied-deltas-<seat-id>-round-<n>.json`, at a location that
now follows the delta file instead of a fixed goal-relative path) — any downstream reader that
globbed the old fixed name/location needs to glob `applied-deltas-*-round-*.json` relative to the
delta file's own directory instead. None found in this repo (grepped `applied-deltas-round` and
`planning/current/applied-deltas`: no hits outside this tool and its own test file). The historical
workaround (`deltas-COMBINED-APPLY-round-1.md` and the single collided
`applied-deltas-round-1.json` under `.rbtv/goals/_archive/meet-transcript-summarizer/planning/
current/`) was deliberately left in place: that goal folder is archived/finished, and mutating it
to synthesize the three individual records it never got would fabricate history rather than
reconstruct it — the fix prevents recurrence going forward; it does not retroactively repair a
closed goal.

## Verification

`test_delta_anchors.py` (14 arms, 0 failed): three new arms pin the three defects —
`G4_multi_seat_same_round_two_records`, `G5_record_beside_delta_not_hardcoded_current`,
`G6_crlf_target_keeps_crlf_and_touches_only_the_edited_span` (plus `G6b_lf_target_stays_lf` as the
LF control). Each was proven red-first in isolation: a scratch `git worktree` with only ONE fix
hunk reverted at a time reproduced the matching arm failing (`G4` against the filename-only
revert, `G5` against the folder-only revert, `G6` against the eol-only revert), then passing again
once that hunk was restored, with the other two arms holding throughout. Not deployed — this is a
repo-side capability tool with no daemon deploy leg.

## ATTENTION

- The record's output PATH now follows the delta file's own directory, not a fixed
  `<goal>/planning/current/` — a caller that globs for `applied-deltas-*.json` at a hardcoded
  location will miss records for delta files authored anywhere else (e.g. an archived milestone).
- The filename now REQUIRES a seat id before `-round-<n>` (`(.+)-round-(\d+)` on the basename); a
  delta file named exactly `round-<n>.md` with nothing before it still parses (empty seat id
  segment) but produces an odd `applied-deltas--round-<n>.json` — author delta files as
  `deltas-<seat-id>-round-<n>.md` per the capability card, not as a bare `round-<n>.md`.
- `_eol_of()` sniffs CRLF vs LF from the file's CURRENT bytes on disk, read fresh at write time,
  after all targets have already been read into memory for matching — do not reorder the write
  loop to run before every target's edits are computed, or the sniff would race a target being
  edited by more than one delta in the same apply.
- record path now follows the delta file's own directory, not a hardcoded goal/planning/current/ — a hardcoded glob for applied-deltas-*.json will miss records elsewhere
- delta filenames must be deltas-<seat-id>-round-<n>.md — the seat id is parsed out of the basename before -round-<n>
