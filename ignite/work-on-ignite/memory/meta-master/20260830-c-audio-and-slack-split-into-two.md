# 20260830-c-audio-and-slack-split-into-two — audio and Slack split into two injected skills

kind: creation
component: meta-master
date: 2026-08-30
commit: ccae8263
deployed: no
pin: NONE
components: capabilities,team-kit,config

## Motivation

The voice flow worked end to end but was reachable only through ONE skill: the whole ElevenLabs
recipe lived as a 114-line section inside `meta/master/references/slack-message-format.md`
(`20260828-c-audio-flow-section-in-slack-me`). The owner, asked whether a skill existed that
teaches an agent the flow, rejected the framing and ruled the shape instead: working with audio
and following the Slack conventions are TWO capabilities living in TWO rbtv modules, and a
capability skill must not assume the channel — Slack is only today's channel.

Two further defects were standing on the same surface. The Slack reference's frontmatter
`description:` never mentioned audio, so `meta/master/exposure.csv` mirrored a description that
under-described the file — the DIFFER recorded in `20260826-i-master-material-contradicts-th`
§ Consequences and widened by the 08-28 addition, which filed it forward rather than fixing it.
And `capabilities/audio/audio.md` still located the key at `credentials/elevenlabs.key`, a folder
inside the capability that does not exist and never did; `audio.py:36` and `README.md` both read
the workspace key store, ruled 2026-08-23.

## Design

The split follows the MODULE boundary, because that boundary is already the real one:
`core/communication` owns the vendor conversion, `meta/master` owns the owner-facing channel.
`audio-io` therefore names no chat surface at all — not a channel id, not a workspace flag, not
an upload verb — and `slack-message-format` names no vendor. Each points at the other in one
sentence so a reader who needs both learns it needs both.

`audio-io` is a NEW file, not a `git mv` of the section: only about half the old text is
channel-neutral, and the moved half was re-headed (`Listening` / `Speaking` rather than
`Inbound` / `Outbound`, which were Slack words). Two things were ADDED that the old section had
no room for: a pointer to this component's sibling `audio-aware` skill (a transcript is garbled
input, not finished text), and a write-for-the-ear rule — speech carries no formatting, so paths,
ids and tables belong in the accompanying text message, not in the spoken reply.

The delivery mechanism is the choke point, not prose. `.rbtv/config/modules/ignite/team-kit/
interactive-exposes.json` is the INSTANCE policy list `materialize-seats.py::_interactive_expose_refs`
reads (F5; owner rulings D11 + D15, 2026-08-10); adding the second ref there gives BOTH skills to
every seat whose prompt declares `human-interactive:`, with no per-seat frontmatter edit and no way
for a future interactive seat to be born without them. Asking nine seat authors to remember a
frontmatter line was the alternative and was not considered.

The full-path command form and the caged/uncaged vantage table were carried over verbatim, per
ATTENTION 2 of `20260828-c-audio-flow-section-in-slack-me`: a bare `audio` or `stools` in this
prose is a defect, and the table exists so nobody simplifies it back.

## How it works

`core/communication/references/audio-io.md` — 111 lines, new. `core/communication/exposure.csv`
gains a sixth row, `audio-io,reference,skill,,references/audio-io.md,"…"`, and its header comment
goes FIVE ROWS -> SIX ROWS naming why the row is channel-agnostic.

`meta/master/references/slack-message-format.md` goes 213 -> 151 lines: lines 100-212 (the whole
`## Voice notes in, spoken answers out` section) replaced by `## Files in and out of Slack` —
`stools` both directions, the `--workspace` requirement, the vantage rule restated for `stools`
alone, `--thread-ts`, `--dry-run`, and the rule that the text riding with a file obeys every
message rule above it. `</reference>` remains the last line. `grep -ci 'elevenlabs|transcribe|
audio.py'` over the result: 0.

The frontmatter `description:` and the `meta/master/exposure.csv` row were rewritten with the
SAME string and diffed against each other: MATCH. `capabilities/audio/audio.md:38` now reads
`<workspace>/.user/config/env/elevenlabs.key` and names the superseded ruling by anchor.

## Consequences

Committed as `ccae8263` in the rbtv repo. NOT deployed — the mirror under
`~/.local/state/rbtv-deploy/` still serves the old `slack-message-format.md` and has no
`audio-io.md` at all, so a reader served from the mirror sees neither half of the split. Deploy is
a separate act and was not performed.

Live seats do not gain the skill until their NEXT materialization: the injection happens at
`materialize-seats.py` time, not at launch, so every seat folder materialized before this commit
still carries only `slack-message-format` — and that copy is the OLD 213-line text with the audio
section still in it. Two versions of the recipe are therefore reachable in the tree until those
seats are refreshed; a stale seat folder is not evidence the split did not land.

`.rbtv/config/modules/ignite/team-kit/interactive-exposes.json` lives in the WORKSPACE, not the
rbtv repo, so it is outside commit `ccae8263` and travels with the workspace instead.

## Verification

The injection was proven end to end, not argued: `materialize-seats.py --dry-run --refresh
--seat plan-designer --catalog-root meta/planning --package …-planning` lists
`.claude/skills/audio-io/SKILL.md` and `.agents/skills/audio-io/SKILL.md` beside the
slack-message-format pair, on a seat whose `human-interactive:` marker is its prompt's, not a
hand-set flag. `_ref_target` was also called directly on both refs from a loaded module instance:
both resolve (`core/communication` | `audio-io`).

Pre-state was pinned before the mutation: `md5sum slack-message-format.md` returned
`f2b349213b912be9d1ebf4945cfd1fa5`, the exact post-md5 recorded by
`20260828-c-audio-flow-section-in-slack-me` § Verification — proof this edit started from that
entry's known end state and not from some other revision. The section replacement asserted on
line content (`lines[99]` opens the section, `lines[212]` is `</reference>`) before writing, and
was applied tmp + `replace`. The key-path fix asserted its exact anchor string was present before
substituting.

Both descriptions were compared by `diff` of the extracted strings, not by eye.

## ATTENTION

1. **`git diff` for anything under `3-resources/tools/rbtv/` MUST be run with `git -C
   3-resources/tools/rbtv`.** From the vault root it exits 0 and writes ZERO BYTES — that tree is
   a separate repository the vault's `.gitignore` ignores. Carried forward from
   `20260828-c-audio-flow-section-in-slack-me` ATTENTION 1, and it still bites.

2. **A bare `audio` or `stools` in either skill is a defect.** The bare name works ONLY inside a
   cage whose seat declared that CLI in `exposed-clis`, and exits 127 from every uncaged chair
   including the console. Both files keep the `python3 <full path>` form and the vantage table.

3. **Both skills restate facts the two CLIs own, and nothing re-derives them.** When `audio.py` or
   `stools.py` changes a flag, an exit code or a path, THESE TWO FILES are callers that must be
   swept — grep `capabilities/audio/audio.py` under `core/` and `stools/stools.py` under `meta/`.
   Splitting one document into two DOUBLED the number of places a CLI change must reach; that is
   the accepted cost of the module boundary, not an oversight.

4. **The delivery list is workspace config, not repo content.** Anything reasoning about which
   skills an interactive seat receives must read `.rbtv/config/modules/ignite/team-kit/
   interactive-exposes.json`, not the rbtv repo. An install without that file injects NOTHING and
   renders byte-identically to before — by design.

5. **Undeployed at the time of writing.** Do not tell anyone either skill is "live for every
   seat". The true sentence is "committed to the source of truth; the deploy mirror is stale and
   already-materialized seat folders carry the pre-split text".
- the delivery list is workspace config (.rbtv/config/modules/ignite/team-kit/interactive-exposes.json), not repo content; a CLI flag change must now be swept into TWO files
