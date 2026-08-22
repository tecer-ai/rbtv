---
description: Verify and apply an authoring seat's delta file against its target files — anchors quoted verbatim, no line numbers, all-or-nothing.
---
# delta-anchors

A relaunched authoring seat returns its repairs as *deltas*. Until this capability existed, the
anchor in a delta was re-derived by hand between authoring and application: the author quoted a
region from memory or from `task-dag.md`, and the applier searched for it by eye. Measured on
`meet-transcript-summarizer` m3 round 7 — four of nine anchors did not resolve at the target file,
one of them quoting the plan draft's paraphrase as though it were the seat file's own words. No
check dimension scores that class, and by construction none can: it is a defect of the transport,
not of the document. This tool deletes the transport step.

**A delta carries no line numbers.** A line number is a pointer that re-derives, and both ends of
a span re-derive independently; the `from` block IS the anchor.

## The delta file

Written by the author at `planning/current/deltas-<seat-id>-round-<n>.md`. The round number in
that filename is what names the applied record, so it is not optional.

~~~
## delta 1
target: planning/current/seats/detection-suite-author/task.md
source: planning/current/task-dag.md
```from
<lines copied VERBATIM out of the TARGET file — never out of task-dag.md,
never out of resourced-plan.md, never out of a route-back brief or recollection>
```
```to
<the replacement lines>
```
~~~

`source:` names the artifact the same change must also land in — a seat file under
`planning/current/seats/` is a RENDERING of `task-dag.md` / `resourced-plan.md`, and a repair
applied only to the rendering is reverted the next time the source is re-seeded. Write
`source: none — <reason>` when the text really is rendering-only. No other keys. A `from` or `to`
block may not itself contain a line that is exactly ```` ``` ````.

## What `check` reports

Every finding for every delta, never first-failure.

| finding code | fires when |
|---|---|
| `target-missing` | `target:` does not resolve to a file under the goal folder (an escape out of it is refused, never followed) |
| `anchor-absent` | the `from` block does not occur verbatim in the target |
| `anchor-ambiguous` | it occurs more than once — a from-text search would land the wrong home |
| `already-applied` | the `to` text is present and the `from` text is not — a no-op, or a second application |
| `source-not-routed` | `target:` is under `planning/current/seats/` and the delta carries neither a `source:` path that exists nor an explicit `source: none — <reason>` |
| `malformed-delta` | missing `target:`, missing or unterminated either fence, empty `from`. A delta that names its region by line span instead of quoting it lands here |

**There is deliberately no line-alignment finding.** The fix design asked for one — a `from` block
whose match starts or ends mid-line, on the reasoning that such a span "silently absorbs its
neighbours". It does not: `apply` replaces the exact bytes quoted, so a mid-line anchor removes
exactly the mid-line text the author wrote and nothing more. Measured against the reconstructed
round-7 delta list, the rule fired on THREE anchors the leader's hand audit verified sound
(the D29 clause at `detection-suite-author/task.md:78-79`, the `watermark-catchup` case, the
`validate-seams` else-tail) — every one of them a phrase that legitimately wraps a line break. The
swallow hazard it was written against belongs to a SPAN-based applier, which this tool is not.
`anchor-ambiguous` is the guard that carries the real risk. `test_delta_anchors.py`'s R3 arm is the
inverse: a mid-line multi-line phrase anchor must be accepted and applied byte-exactly.

## How to run

From the goal folder (`--goal .`), or from anywhere with `--goal <goal-folder>`:

```bash
python3 3-resources/tools/rbtv/meta/planning/capabilities/delta-anchors/tool/delta_anchors.py \
  check planning/current/deltas-<seat-id>-round-<n>.md --goal .
python3 .../delta_anchors.py apply planning/current/deltas-<seat-id>-round-<n>.md --goal .
```

`apply` re-runs `check`, **refuses on any finding**, and rewrites every target or none — the
targets are built in memory and written only after the last delta resolves. It then writes
`planning/current/applied-deltas-round-<n>.json`:

```json
[{"target": "...", "source": "...", "start_line": 163, "end_line": 171,
  "section": "### Criterion 3 — the fixture set"}]
```

`section` is the nearest preceding markdown heading, and the line span is measured in the file AS
WRITTEN — the deltas of one file are applied lowest-offset first, so an earlier record's span is
never shifted by a later delta in the same file (round 7 put four deltas in one seat file). That record is what makes the next check round bounded: `prompts/checker.md` scopes a
re-check to the regions it names, and `tasks/check-clarity.md` reads each named region with its
whole enclosing section to catch a repair that landed but does not hold.

## I/O

- Input: a delta file, and `--goal` — the goal folder every `target:` and `source:` resolves under.
- Output: one `FAIL <code> delta <id> <target>: <detail>` line per finding, then a census line
  carrying the delta count and the finding count. `apply` prints what it wrote, or `REFUSED`.
- Exit codes: `0` clean · `1` findings (or a refused apply) · `2` broken preconditions (delta file
  or goal folder absent, no `## delta` section, no `round-<n>` in the filename on `apply`) — the
  same convention `component-lint` ships.

Self-test (every finding code ships a red arm, plus green/idempotence and atomicity):

```bash
python3 -B 3-resources/tools/rbtv/meta/planning/capabilities/delta-anchors/tool/test_delta_anchors.py
```
