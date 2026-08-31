# 20260830-i-two-seats-missed-the-audio-ski — two seats missed the audio skill after the split

kind: issue
component: meta-master
date: 2026-08-30
commit: 8044b482
deployed: no
pin: NONE
components: config,team-kit,meta-installer

## Observed

After `ccae8263` split audio and Slack into two skills and listed both in
`.rbtv/config/modules/ignite/team-kit/interactive-exposes.json`, two seats the owner's ruling
names still did not have the audio skill. A peer master session reported both gaps by voice and
they were re-measured here rather than taken on its word — one of its two claims was materially
overstated, and the remedy it implied for the other was aimed at the wrong mechanism.

## Mechanism

Two independent causes, one per gap.

**Gap A — already-materialized seat folders.** The interactive injection runs at
`materialize-seats.py` time, not at launch, so every seat folder written before the config change
carries no `audio-io` loader. Thirty-plus folders were in that state, `_channel-master` — the
owner's AFK door — among them. The peer's report said those seats "still have only the Slack
skill, without the audio one", which is true of the LOADER SET but NOT of the text: a materialized
`SKILL.md` is a THIN LOADER (`d-materializer-seat-loaders`) that says "read
`<absolute source path>` NOW", so `_channel-master` was already reading the NEW split Slack
reference the moment `ccae8263` landed. `grep -c 'elevenlabs|transcribe'` on its
`slack-message-format/SKILL.md`: 0. The real deficit was narrower and still real — no audio-io
loader means nothing tells the seat the skill exists.

**Gap B — `console-master` carried no `human-interactive` marker.** Confirmed: of the three master
prompts, `channel-master-prompt.md` and `goal-master-prompt.md` both declare
`human-interactive: yes` and `console-master-prompt.md` declared nothing — the one master seat
with the user literally at the keyboard. But the marker is NOT what delivers a console session its
skills, and this is the part the peer's report got wrong: `materialize-seats.py` refuses
`console-master` with `bindings-missing-seat` because
`.rbtv/config/modules/meta/master/bindings/` holds only `channel-master.json` and
`goal-master.json`. A console-master session is never materialized. It takes its skills from the
WORKSPACE INSTALL, and `rbtv install ls` shows `core/communication` at "6 parts, 5 in" with
`audio-io` marked `-`: discovered, not installed.

## Attempts

The peer master session's report was NOT taken as the finding. Each of its two claims was
re-measured from this chair before any edit, and the console-master remedy it implied
(mark the seat interactive and the skills follow) was tested and found not to hold — the
materialization it depends on refuses for that seat. Nothing was fixed on the strength of the
report alone.

## Fix

Gap A: `materialize-seats.py --refresh --seat channel-master --package .rbtv/goals/_channel-master`
— the owner's AFK door now carries `audio-io` beside `slack-message-format`. The ~30 other stale
folders were left alone DELIBERATELY: they belong to live planning goals, they will pick the
loader up at their next materialization, and forcing a refresh into a running goal is a
disturbance with no matching gain.

Gap B: `console-master-prompt.md` gains `human-interactive: yes` + `fallback: block-and-queue`
(`8044b482`) — correct in itself and correct if that seat is ever materialized, but explicitly NOT
the delivery mechanism. The delivery is `rbtv install add -c communication -xs`, which was NOT
run: its dry-run writes 85 files across three harnesses and holds 5 shared-file claims, a
workspace-wide act whose blast radius exceeds the ruling, so it was put to the owner as a queued
ask instead.

## Consequences

Roughly thirty seat folders across live planning goals still carry no `audio-io` loader and were
knowingly left that way; they are not evidence the split failed. The workspace install still does
not carry `audio-io`, so a console-master session and anything else reading the workspace
`.claude/skills/` does not see the skill at all — that remains OPEN, queued to the owner. Neither
commit is deployed.

## Verification

Marker presence read from all three master prompts before and after. Gap A's narrowing was
measured, not reasoned: the loader body was `cat`-ed and the elevenlabs/transcribe grep count on
the pre-refresh `_channel-master` copy was 0. The stale-folder census came from a find over every
`.claude/skills/slack-message-format` in `.rbtv/goals` testing for a sibling `audio-io`. The
console-master materialization refusal (`bindings-missing-seat`) and the install state
(`audio-io … -`) were both produced by running the tools, not inferred from their docs.

## ATTENTION

1. **A materialized `SKILL.md` is a thin LOADER, never a copy.** "This seat has the old skill
   text" is almost always FALSE — the seat reads the live source file. What a stale seat folder
   actually lacks is the loader for a NEWLY ADDED skill, i.e. a POINTER, not content. Diagnose the
   loader set, never the text.

2. **`console-master` is not materialized and has no bindings file.** Anything reasoning about
   what that seat carries must read the workspace INSTALL (`rbtv install ls`), not
   `materialize-seats.py`. Its `human-interactive` marker is inert today.

3. **The interactive injection fires at materialize time, not at launch.** A config change to
   `interactive-exposes.json` reaches ZERO existing seat folders by itself. Every claim of the
   form "all interactive seats now have X" needs the refresh, or a statement of which folders were
   deliberately left stale.

4. **Verify a peer session's confident report.** Both claims here came from another master session
   in the same channel; one was materially overstated and one pointed at the wrong mechanism.
   Neither was fabricated — the sightings were right and the verdicts were not.
- a materialized SKILL.md is a thin LOADER not a copy; console-master has no bindings file and takes its skills from the workspace install, so its human-interactive marker is inert
