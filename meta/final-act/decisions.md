# final-act decisions

Standing decisions about final-act. Each states the decision and its reason; the skill and the pages of `capabilities/` describe the resulting design.

## One skill for everything a close does

Handoff, loose ends, compound, archivist and work history are method pages under the `final-act` skill, not skills of their own. Reason: a close is one moment with several parts, and nested exposure forbids a second entry point per part; the description therefore names each part's situation so that a direct ask for one part still reaches the skill.

## The entry step runs on every load, including a direct ask for one part

Reason: the requests check and the hygiene check are the point of having one entry: a session that hands off without checking what was asked reports work done that was not.

## An undone request is the user's call

The requests check asks finish, hand off or drop per undone item and never finishes one on its own, however small. Reason: the user may have changed their mind, and the moment a session closes is the wrong one to spend on work nobody confirmed. A blind Sonnet seat finished one itself before this line existed.

## Triage is a method here, and loose ends files nothing before it

`triage` is a method page of final-act and carries the value bar itself; the loose-ends method sends its unfiled list through triage, owner round included, before any task is filed. Reason: a backlog is judged at a close and at any other time by one protocol, and the point of the protocol is that an agent never files on its own judgment; one page holds the bar because every caller is in this component.

## Triage has a command beside the skill's route

The `triage` command sends a human's invocation, with the backlog it names, to the triage page; the skill still routes to that page at a close and on an agent-recognized ask. The command opens the page without the skill's entry step. Reason: a human who types the command has chosen the action and the backlog, outside any close, and the requests and hygiene checks belong to a close; the method stays in one page so both routes follow one protocol.

## State hygiene is the entry step's hygiene check, not a rule

The six checks a file left for a later agent must pass are in the skill's entry step and run on every load; the full principle, with how it fails and the weak/strong pairs, is `capabilities/methods/state-hygiene.md`, opened when a check does not settle a file. No always-on rule carries them. Reason: cleaning state is what a close is for, so every agent entering final-act does it; an always-on rule repeated the checks on every turn of every agent and was the only file left in its component.

## The archivist sweeps by hand, in two modes, and never without a confirmed list

No script and no work-log: done entries are deleted or moved verbatim to a file the user names, after the user saw the list; a seat with no user sweeps nothing. Reason: the sweep is usually a handful of lines, a script would have bound the method to one task-file convention, the work-log duplicated handoff and work history, and a sweep removes lines.

## Compound collects three classes of scaffolding issue, sweeps the record by sub-agents, and implements nothing

A compound entry is one of three classes: an instruction the agent did not follow, a skill, tool, rule or agent that failed, was worked around or was missing, or a dangerous action; a slip with no lesson for the scaffolding is not one, and a correction about the work itself goes to memory or the board. The collection starts with a mechanical sweep of the session's record (the `session-sweep` tool cuts it into moments; labeler sub-agents on the mechanical class label them), then the agent's recall, then at the full tier three checker waves against the instructions in force, the decisions and requests, and the disk. The candidates go through the shared triage; the owner rules; no page, rule or prompt is edited by this method. Reason: owner decisions, 2026-10-14 and 2026-10-15. The earlier method asked for every correction, failure and pattern and proposed mechanical slips (a wrong count in a message) while missing the real entries, which surfaced only when the owner named the three classes; the agent's recall also left unfiled incidents it had told the owner about in the same thread, which a grep of the record shows. An instruction deviation counts without an effect because the skipped memory refresh of 2026-10-13 had none either and the lesson (nothing triggers it) was the same. The tiers exist because a full collection and three waves at every close costs more than most closes are worth; the full tier finds the silent deviations the sweep cannot.

## Compound entries go to the compound backlog of their scope, never to the project

An entry about an agent's own prompt, tools or skills is written in that agent's `output/final-act/compound/compound.md`; an entry about the installation or about a shipped rbtv component is written in the installation's `.rbtv/output/final-act/compound/compound.md` with its scope, and a rbtv-scoped entry reaches the rbtv repository by a *move* ruling at triage. An installation's instruction file may name another backlog. When no user can answer, entries are written marked unruled. Reason: owner decisions, 2026-10-15. The earlier default (the project's loose-ends or tasks file) filed scaffolding issues in the tracker of the matter, so one day's findings landed in four places; a loose end is about what the session worked on and a compound entry about what it worked with, and each belongs where its fixer looks. The owner chose the split by scope at write time, with the triage move as the correction for a wrong split, over one intake with a scope column. Headless entries are written because a candidate table in a final message nobody reads is the loss the method exists to prevent; the backlog header already says nothing there is a task until ruled.

## An agent whose conversation never closes runs compound on request, with the thread as the session

Such an agent (one that answers a conversation thread, with no session close) receives the `final-act` skill and runs compound when the user asks; its session is the thread. Reason: owner decision, 2026-10-15; no other trigger (a board close, a daily briefing) was chosen for now.

## The close verifies status claims with the sanity check

When the requests table carries a status the session did not observe itself, or the close releases an outward action, the entry step runs the coordinate skill's sanity check on those rows before showing the table as fact. Reason: owner decision, 2026-10-15. Three of the sanity check's angles (history sweep, live state, docs consistency) are independent versions of what the requests and hygiene checks do by self-report; the method itself stays in coordinate because its trigger is any moment the user is about to act on an output, not only a close.

## Loose ends go to the backlog the project already uses

A kept loose end is filed in the project's tasks, loose-ends or issues file; when none is known the agent asks once and never invents a file. Reason: rbtv is general and owns no task tooling, and a new file pattern would be a convention nobody asked for.

## A close with no part named proposes a set and runs it in a fixed order

Loose ends always; compound always at its default tier, the full tier proposed for a long session, one with sub-agents or one on shared surfaces; handoff when work leaves unfinished; work history and archivist on request; run as loose ends, handoff, compound, archivist, work history. Reason: one ask per close, and loose ends must decide what becomes a task before the handoff writes the state. Compound runs at every close since 2026-10-15 because its sweep finds what the agent did not notice, so "no correction received" is not evidence of nothing to compound.

## A work-history collection is git-ignored unless the user asks to commit it

The destination gets a `.gitignore` that ignores everything in it before the first file is written; the boundary step asks whether the collection is committed, and only an explicit yes omits the file. Reason: the collection holds whole session transcripts, recovered outputs and patches, filtered but private; committing them is a choice the owner makes per collection, never a side effect of closing a session.
