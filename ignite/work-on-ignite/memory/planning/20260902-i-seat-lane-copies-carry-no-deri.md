# 20260902-i-seat-lane-copies-carry-no-deri — seat-lane copies carry no DERIVED warning in-file

kind: issue
component: planning
date: 2026-09-02
commit: 2d44f7658592b40583e3701439a42bd0d3b63187
deployed: yes
pin: ignite/planning/probes/probe-goal-local-lane-warning.py

## Observed
`shutil.copyfile`, used by `materialize-seats.py` (the tool that assembles a goal's seats) to copy
prompt/task files into `planning/current/seat-lane/` (a derived, disposable working copy), gave an
agent opening a goal-local prompt/task in that derived lane no signal that edits made there are
discarded on the next materialize run. Measured 2026-08-23 on goal `ignite-engine`: a ruled fix was
applied inside the derived copy and silently evaporated on the next materialize
(`decisions.md#p-seat-lane-is-derived-the-three-surfaces-are-unfixed`). Re-measured directly against
the archived source (`.rbtv/goals/_archive/ignite-engine/planning/current/seats/`) during this fix's
own build: the two affected seats, `proposal-record-smith` and `triage-rehearser`, were still
carrying the stale, already-rejected wording, unchanged since 2026-08-23 — an earlier "all clear"
message on that goal's chat channel had been checked against the wrong (discarded) copy.

## Mechanism
Copied prompt/task markdown files carried no marker distinguishing them from their source. An agent
that opened the copy inside `seat-lane/` had no way to tell, from the file itself, that it was a
disposable regenerated copy rather than the editable source — so edits landed there, felt
successful, and vanished with no error at the next materialize. `seats.csv` and the workflow table
`goal-local.csv` (two generated CSV files) could not carry the same kind of in-file warning: a text
header line in a CSV would be read back by `csv.reader` as a data row, silently corrupting the
table.

## Attempts
First attempt held — checked: the root `DERIVED.md` marker plus `refuse_if_derived` write-door
refusal (already landed, commit `b9bfd814`, `coord/20260825-c-derived-tree-marker-and-write.md`).
That mechanism refuses a WRITE into the derived tree at the door, but names the tree's root, not the
specific file an agent has open — it does not close the file-level signal gap task 127 named. This
fix is additive to it, not a duplicate.

## Fix
`_copy_with_derived_warning` stamps an unmissable warning as the first body line of every copied
prompt/task file, immediately after the closing `---` of its YAML frontmatter (never before it,
which would corrupt `_goal_local_frontmatter`'s parsing). `component.md`'s body also now carries the
same warning, not only its frontmatter description field. `seats.csv` and `goal-local.csv`, which
cannot carry an in-file text warning without corrupting the table, each get a `README.md` sidecar
dropped in the same folder instead, stating the warning and naming the real source — named
explicitly rather than left a silent gap. Adds `probe-goal-local-lane-warning.py` (scheduled-suite
discoverable) pinning the warning's presence across both copied-file types and both CSV sidecars.

## Consequences
Does not change the discard behaviour itself — an edit made inside the derived copy still vanishes
on the next materialize; that is expected, since the actual fix for the discard mechanism is the
separate write-refusal lock (`b9bfd814`). The two seats measured stale at the source (`proposal-
record-smith`, `triage-rehearser`) were confirmed still wrong as of this fix's build, but were not
corrected — this fix has no permission to edit that archived content; it is reported as evidence
only. Closed the originating defect report `G-leader-0823-1442` with a note explaining exactly what
was and wasn't fixed.

## Verification
Red-first, on a scratch test copy: hand-edited a copied file, re-ran the copy step — before the fix,
no warning existed and the edit vanished with no error at all. After the fix: the warning was
present in the file BEFORE the edit was made, and the edit still vanished after re-running the copy
step, proving the discard behaviour is unchanged (as expected) while the warning now survives every
regeneration. `probe-goal-local-lane-warning.py`: 5/7 checks failed with the fix removed, all 7 pass
with it applied; confirmed auto-discovered by the scheduled check suite (live run: PASS). The file's
own internal self-check ran 343 checks clean, then hit an unrelated pre-existing crash (a database-
location lookup failing in a different, unrelated check about seat staffing) — confirmed identical
on unmodified code before this change, not caused by this fix. Not deployed.

## ATTENTION
1. This closes only the FILE-LEVEL signal gap (an agent opening a derived copy now sees a warning in
   the file itself). The WRITE-REFUSAL mechanism at the tree root (`b9bfd814`,
   `refuse_if_derived`) is separate and unchanged by this fix — both are needed; neither
   supersedes the other. 2. `seats.csv`/`goal-local.csv` deliberately do NOT carry an in-file
   warning (a header line would corrupt the table as a `csv.reader` data row) — they get a
   `README.md` sidecar instead. Do not "fix" this by adding a warning row to the CSV. 3. The pre-
   existing crash in the file's own selftest (staff-seat section, a database-location lookup
   against a temp folder) still blocks a clean full-suite PASS, independent of this fix —
   reproduced identically on unmodified code, not fixed here. 4. `proposal-record-smith` and
   `triage-rehearser`'s actual source wording under `.rbtv/goals/_archive/ignite-engine/` is
   still wrong as of this fix — whoever has permission to edit that archived content still needs
   to correct it.
- coord/20260825-c-derived-tree-marker covers only the tree-root marker
