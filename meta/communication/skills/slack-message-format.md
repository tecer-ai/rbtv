---
name: slack-message-format
description: "Structural reference — how any owner-facing seat writes to the owner over Slack: mrkdwn syntax, phone-first message shape, the decision-ask format, the ❓ ask / 💭 note markers, and moving files in and out of Slack with `stools` (download and upload). Applied, never executed; exposed as a skill to interactive seats. Converting audio to text or text to speech is a DIFFERENT skill — `meta/communication/audio-io`."
---
<reference>
Form: STRUCTURAL (message shape) with a normative edge (the decision-ask shape is binding).
Enforcement: advisory. Reach: this seat's Slack surface. Apply this to EVERY message you write
into the Slack thread; straying is a defect, not a permission.

## Agent replies

For an Ignite agent turn, put each owner-facing message in RESULT_FILE `replies[].text`. Put any
file paths in that reply's `files` array. The runtime delivers the reply in the open thread.
`replies[].audio: true` makes the runtime generate and attach speech from `text`. Do not also
attach an audio file; to send a prerecorded file, use `audio: false` with its path in `files`.
Write Slack `mrkdwn` in `text`; send no delivery markers and do not post a second copy yourself.

## Slack is mrkdwn, not markdown

Slack renders its own `mrkdwn`. Markdown habits produce broken output — these are the mappings:

| You want | Write | NEVER write |
|---|---|---|
| bold | `*bold*` (single asterisks) | `**bold**` |
| italic | `_italic_` | `*italic*` |
| strikethrough | `~struck~` | `~~struck~~` |
| inline code | `` `code` `` | — |
| code block | triple backticks, NO language tag | ```` ```python ```` |
| link | `<https://url|shown text>` | `[text](../../../meta/communication/references/url)` |
| bullet list | `•` or `-` at line start | — |
| heading | `*a short bold line*` on its own | `#`, `##`, `###` |
| table | short aligned lines or a bullet list | pipe tables (they render as raw pipes) |
| quote | `>` at line start | — |
| separator between blocks | a BLANK LINE | `---`, `***`, `___` (mrkdwn has no horizontal rule — the dashes render as literal dashes) |

## Message shape — the owner reads on a phone

- Lead with the answer or the outcome in the first line. Detail below it, only what changes what
  the owner does next.
- Short messages, short paragraphs (2–3 lines), blank line between blocks. One topic per message;
  a second topic is a second message.
- Reply IN the thread the contact arrived on — never a new channel, never a new DM.
- Lists over prose for enumerations; never more than ~7 bullets — past that, summarize and offer
  the rest on ask.
- NEVER paste a file's contents into a message — not the whole file, not the "relevant part" that
  grows into the whole file. Long output (a file, a log, a table) does not go inline: state the
  one-line conclusion and the path to the artifact, and let the owner open it.
- Plain words. Expand every acronym and record id on FIRST use — never a bare `F-89` or `CMP-8`.
  No jargon the owner has not used first.

## Decision asks

A decision ask says what is being asked in one plain sentence · lettered options `a) b) c)` each
with its consequence on one line · your recommendation and its reason last. Never bury an ask
inside prose — it is its own message.

## Two markers separate what the owner must answer from what he may skip

- `❓` opens EVERY message that needs an answer from the owner — a question, options to pick, a
  ratification. Nothing else carries it: it is how the owner finds what is waiting on him.
- `💭` opens reasoning, grounding notes and progress remarks — optional reading. A note NEVER
  shares a message with an ask: appended to a question it reads as part of the question, and the
  owner answers the note instead of the ask.
- No other decoration, and the thread emoji (🧵) in particular is DROPPED — the surface is already
  a thread.

## Files in and out of Slack

Slack carries more than text: the owner sends voice notes and images, and an answer can go back
as an uploaded file. `stools` is the tool for BOTH directions, and it is the only Slack-facing
tool you need — it moves a file between Slack and disk and does nothing else with it.

**Manual conversion is a different skill.** Turning a voice note into text, or text into speech,
belongs to `audio-io` (the `meta/communication` audio capability). That split is the owner's
(2026-08-30): Slack is today's only channel, so channel logistics and audio conversion are kept
apart and neither assumes the other. Use both skills for manual transcription or audio-file
creation. Ignite's `audio: true` reply handles speech generation at delivery.

For manual file transfers, use the installed `stools` command, whose source is
`meta/communication/capabilities/tools/stools/stools_wrapper.py`. Use that wrapper rather than calling
`3-resources/tools/stools/stools.py` directly; the wrapper enforces the send-identity rule below.
An Ignite agent replying in its current conversation attaches file paths through `replies[].files`.

`--workspace` selects a configured account (`--account` is its alias). It is required
when two or more accounts are configured; the only account is the default when there is one.
This Ignite installation uses `ignite` for its bot and `ignite-owner` for the owner's account;
a configured account label alone does not verify the actual Slack identity.

Write verbs (`send`, `upload`, `react`, `canvas`) on an account configured with `writes: false`
require an active grant in `.rbtv/config/stools-as-owner-grants.yaml` covering the effective
account, verb and current working folder. A plan's `read-first` or `decisions.md` may cite the
approval, but those documents do not substitute for a matching record. Reads remain ungated.
A refused write exits 2 with `as-owner-write-refused` and does not contact Slack.

Follow the [STools Write Approval rule](../../../../stools/CLAUDE.md#write-approval). After
explicit owner approval, an agent may append exactly the approved grant, preserving existing
records and the approved folder and verbs. `stools send --help` locates the grant-format guide,
including what the matcher enforces and what it does not. A grant is not itself consent.
`--yes` skips only recipient confirmation; `--dry-run` previews without posting, may contact
Slack, and does not establish grant coverage or permission.

### Inbound — get the file onto disk

Address the message by permalink, or by channel + ts:

```
stools download --workspace ignite --permalink "<url>" --output /tmp/slack
stools download --workspace ignite --channel "#canal" --ts <ts> --output /tmp/slack
```

`--output` is the DIRECTORY the files land in. `--hours N` pulls a whole channel window instead of
one message; `--dry-run` lists what would be fetched without fetching it.

### Outbound — post a file back

```
stools upload --workspace ignite --channel "#canal" --file /tmp/answer.mp3 --thread-ts <ts> --message "..."
```

Upload is a WRITE — `--dry-run` prints the full preview first. `--message-file PATH` carries a
message the shell would mangle. `--thread-ts` puts it in the thread the request arrived on, which
is where a reply belongs.

**The text riding with the file obeys every rule above it in this reference.** `--message` is
`mrkdwn`, it leads with the outcome, and it carries `❓` or `💭` per the markers section. A file
reply exempts nothing: an upload is still a message to the owner.

Flags are documented by the CLI itself — `<path> --help` and `<path> <verb> --help` — and in
`3-resources/tools/stools/scripts/slack_download.md` and
`3-resources/tools/stools/scripts/slack_upload.md`. This reference does not restate them, because
the second copy is the one that goes stale.
</reference>
