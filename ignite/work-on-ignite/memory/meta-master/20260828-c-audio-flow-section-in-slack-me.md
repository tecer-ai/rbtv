# 20260828-c-audio-flow-section-in-slack-me — the voice-note flow written into slack-message-format.md

kind: creation
component: meta-master
date: 2026-08-28
commit: NONE — uncommitted working-tree change in the rbtv repo
deployed: no
pin: NONE
components: capabilities

## Motivation

Clause 3 of goal `stools-canvas-audio-elevenlabs-close` ("the audio flow written into the live Slack
conventions reference, so agents discover it in both directions") had no landing place: an
owner-facing seat holding `slack-message-format` as a skill could read the whole reference and learn
nothing about the voice notes the owner actually sends, or about replying in speech. Both CLIs
existed and worked; neither was discoverable from the one document that seat reads before writing to
the owner. The section was AUTHORED by that goal's `conventions-writer` seat (caged, read-only under
`3-resources/tools/rbtv/`), and applied by the goal's leader chair as a relay act — the seat could
not write the file, and the leader does not write another seat's product, so the text landed
byte-for-byte with nothing re-typed or re-worded.

## Design

One `##` section appended as the LAST section INSIDE the `<reference>` fence, with four `###`
sub-parts (inbound, outbound, language, what a caged seat can and cannot do). Flat bullets were
rejected by the author and the rejection sustained by the chair: flat, this would be the longest and
least scannable block in a file that is read under time pressure. The doc used only `##` before, so
the nesting is a deliberate first — it conflicts with nothing and the file has no depth rule.

The load-bearing design choice is that **every command is printed as `python3 <full workspace path>
<verb>`, never as a bare `audio` or `stools`.** That follows a ruling made in the same goal
(`.rbtv/goals/stools-canvas-audio-elevenlabs-close/decisions.md`, 2026-08-28 21:53, sited at
`planning/evidence/m6/leader-ruling-audio-recipe.md`): CLI reach is a PER-SEAT GRANT on a different
axis from the cage. `~/.rbtv-bin/<name>` is a SYMLINK materialized INSIDE a sandbox from that seat's
own `exposed-clis` (`spawn.js:1008`, `RBTV_BIN_DIRNAME = '.rbtv-bin'`); it does not exist on the real
filesystem, so a bare `audio` WORKS for a caged seat that declared it and exits 127 for an undeclared
caged seat AND for every uncaged chair. Uncaged means unmasked, not better-equipped. The section
states both halves as a two-row table rather than picking one, because a reference cannot know its
reader's cage — and the full-path form is the only one correct in both vantages.

What was deliberately NOT written: the constraint that a shim for this CLI must stay a symlink
(`audio.py` computes `ROOT = Path(__file__).resolve().parent`, so a physical copy reads a DIFFERENT
`config.json`). That is guidance for whoever installs a shim, not for a seat writing Slack messages;
restating it here would put a fact the installer path owns into prose nothing re-derives — the exact
failure class `20260826-i-master-material-contradicts-th` and `81d04a1c` were both written about.
Ruled and recorded as `p-m6-section-scope` in that goal's decisions.md.

Also deliberately NOT written: per-flag documentation. The section closes by pointing at
`<path> --help`, `<path> <verb> --help`, `scripts/slack_download.md`, `scripts/slack_upload.md` and
the audio `README.md`, and says in its own words that it does not restate them "because the second
copy is the one that goes stale". That sentence is the component's own recurring lesson written into
the artefact.

## How it works

`3-resources/tools/rbtv/meta/master/references/slack-message-format.md` goes 99 -> 213 lines. Line 99
is blank, line 100 opens `## Voice notes in, spoken answers out`, and `</reference>` remains the last
line. Pure addition: 114 insertions, ZERO deletions, nothing reordered.

The flow it documents, both directions, all of it re-measured against the deployed CLIs before the
apply: `stools download` (`--workspace` REQUIRED, choices `{ignite,ignite-owner}`; `--permalink` or
`--channel`+`--ts`; `--output` is the folder) puts the note on disk; `audio.py transcribe <file>`
(file POSITIONAL, no language flag) returns `.text` in one JSON object on stdout. Outbound:
`audio.py tts` (`--text | --file` mutually exclusive, one required, `--file -` reads stdin; `--out`
required and its EXTENSION picks the format from `.mp3/.ogg/.opus`; `--voice` defaults to the
account's first voice) writes the file, and `stools upload --thread-ts` posts it. Language is a
config key read by both verbs (`config.json`, default `pt`), changed only by the `language` verb —
no flag exists on either verb. Refusals: `EXIT_REFUSED = 2` for a local refusal (usage, missing key,
bad input), `EXIT_FAILED = 1` when the remote call failed or returned nothing usable, both read from
`audio.py:79-80`.

The last sub-part records the standing limitation: a caged seat CANNOT reach the ElevenLabs key
(`ELEVENLABS_API_KEY` unset in cages; the key store masked by the cage's `**/*.key` pattern floor, so
a cage sees a zero-length character device — a MASK, not an absent key). It tells the reader not to
misread that as a broken install, and that only the ElevenLabs half is affected: `stools download`
and `stools upload` still work in-cage, so a caged seat fetches the note and posts the answer and
hands only the conversion to an uncaged chair.

## Consequences

**Repo-only, uncommitted, UNDEPLOYED.** The deploy mirror
`/home/henri/.local/state/rbtv-deploy/meta/master/references/slack-message-format.md` is still the
old 99-line file (5466 bytes, mtime 2026-08-25). Any reader served from the mirror rather than the
source tree does not see this section yet. Committing the rbtv repo and deploying are both other
acts and neither was performed.

The file's frontmatter `description:` now UNDER-DESCRIBES its own contents — it enumerates mrkdwn,
message shape, decision asks and the two markers, and never mentions audio. This was disclosed by
the author and deliberately left alone (changing it is an edit to existing text, outside the
authoring seat's scope, and it would have muddied the goal's "pure addition" observable). It is not a
NEW defect: `20260826-i-master-material-contradicts-th` § Consequences already records that the
docs-in-sync check comparing every `.md` exposure row to its file's frontmatter reports MATCH for all
three reference rows EXCEPT `slack-message-format`, which DIFFERS — "pre-existing and untouched".
This change widens that existing gap; `meta/master/exposure.csv`'s row for this file and the
frontmatter both now need the audio flow named. Filed forward, not fixed here.

## Verification

Every claim the section makes about a CLI was re-measured from the uncaged chair before the apply,
rather than taken from the authoring seat's word: all 7 workspace paths `test -e` OK; `audio.py
--help` and each of `transcribe|tts|language --help` parsed for positional/flag shape; the two exit
constants read from source; `stools --help` prints "Every verb needs --workspace" in its own words
and `--workspace` is a required argument on both `download` and `upload`. `grep -ic canvas` over the
added lines: 0.

The apply was done in one atomic write (tmp + `replace`) and verified by containment (`section in
target` -> True) and by index (line 99 blank, line 100 the heading, last line `</reference>`), not by
eye. Pre-state was recorded BEFORE the mutation — 99 lines, md5 `b5ba9a15…`, git-clean — at
`.rbtv/goals/stools-canvas-audio-elevenlabs-close/planning/evidence/m6/pre-state.log`. Post md5
`f2b34921…`. The diff is sited at that folder's `landed-diff.txt` (6928 bytes) and was produced with
`git -C 3-resources/tools/rbtv diff -- meta/master/references/slack-message-format.md`.

## ATTENTION

1. **`git diff` for anything under `3-resources/tools/rbtv/` MUST be run with `git -C
   3-resources/tools/rbtv`.** From the vault root it exits 0 and writes ZERO BYTES — that tree is a
   separate repository and the vault's `.gitignore:6` ignores it, so `git ls-files --error-unmatch`
   there answers "did not match any file(s) known to git". The goal's own acceptance observable was
   about to be graded off that empty diff, which would have "proved" zero canvas instructions added
   by containing nothing at all. A 0-byte diff from the vault is a wrong-target result, never a clean
   tree.

2. **A bare `audio` or `stools` in any prose here is a defect.** Whoever edits this section next: the
   bare name works ONLY inside a cage whose seat declared that CLI in `exposed-clis`, and exits 127
   from every uncaged chair including the console. Keep the `python3 <full path>` form. The two-row
   vantage table exists so nobody "simplifies" it back.

3. **This section restates facts `audio.py` and `stools.py` own, and nothing re-derives them.** That
   is the component's most-recorded failure class (`20260826-i-master-material-contradicts-th`,
   `1c49ffc4`, `81d04a1c`). It was accepted here because clause 3 asked for discoverability, and
   bounded by refusing to restate per-flag docs. When either CLI's flags, exit codes or paths change,
   THIS section is a caller that must be swept — grep `capabilities/audio/audio.py` and
   `stools/stools.py` under `meta/`.

4. **The frontmatter `description:` is now stale in a way a reader cannot see.** It never mentions
   audio, and `meta/master/exposure.csv` mirrors it. That row/frontmatter pair already DIFFERED
   before this change; this widened it. Do not assume the exposure row describes the file.

5. **Undeployed and uncommitted at the time of writing.** Do not tell anyone the section is "live for
   every seat" — the true sentence is "applied to the reference's source of truth". The mirror under
   `~/.local/state/rbtv-deploy/` still serves 99 lines.
