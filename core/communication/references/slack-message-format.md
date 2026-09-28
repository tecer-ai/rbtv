---
id: slack-message-format
description: "Structural reference — how any owner-facing seat writes to the owner over Slack: mrkdwn syntax, phone-first message shape, the decision-ask format, the ❓ ask / 💭 note markers, and moving files in and out of Slack with `stools` (download and upload). Applied, never executed; exposed as a skill to interactive seats. Converting audio to text or text to speech is a DIFFERENT skill — `core/communication/audio-io`."
exposes-cli:
  - meta/planning/stools
---

<reference>
Form: STRUCTURAL (message shape) with a normative edge (the decision-ask shape is binding).
Enforcement: advisory. Reach: this seat's Slack surface. Apply this to EVERY message you write
into the Slack thread; straying is a defect, not a permission.

## Agent replies

For an Ignite agent turn, put each owner-facing message in RESULT_FILE `replies[].text`. Put any
file paths in that reply's `files` array. The runtime delivers the reply in the open thread.
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
| link | `<https://url|shown text>` | `[text](url)` |
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

**Converting a file is a different skill.** Turning a voice note into text, or text into speech,
belongs to `audio-io` (the `core/communication` audio capability). That split is the owner's
(2026-08-30): Slack is today's only channel, so channel logistics and audio conversion are kept
apart and neither assumes the other. If you must hear or speak, you need BOTH skills.

For manual file transfers, use the installed `stools` command, whose source is
`meta/planning/capabilities/stools-wrapper/tool/stools_wrapper.py`. Use that wrapper rather than calling
`3-resources/tools/stools/stools.py` directly; the wrapper enforces the send-identity rule below.
An Ignite agent replying in its current conversation attaches file paths through `replies[].files`.

**Every `stools` verb needs `--workspace`. Default to `--workspace ignite` (the bot) — every
example in this reference uses it.** `--workspace ignite-owner` sends as Henrique himself (the
owner's own Slack user token) and is REFUSED by the wrapper on every write verb (`send`,
`upload`, `react`, `canvas`) unless this sitting's `read-first` / `decisions.md` names a live
as-owner grant (owner ruling `d-slack-identity-a`, 2026-08-31 — e.g. this plan's own
`d-test-as-owner-via-stools`). Reads (`read`, `search`, `download`) on `ignite-owner` stay
available without a grant — `search:read` has no bot-token equivalent. A refused write exits 2
naming `as-owner-write-refused` and makes no Slack API call; `--dry-run` still previews
regardless of grant.

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
