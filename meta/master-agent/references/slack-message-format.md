---
id: slack-message-format
description: "Structural reference — how any owner-facing seat writes to the owner over Slack: mrkdwn syntax, phone-first message shape, the decision-ask format, and the ❓ ask / 💭 note markers. Applied, never executed; gathered by channel-surfaces (resources composed-of reference) and exposed as a skill to interactive seats."
---

<reference>
Form: STRUCTURAL (message shape) with a normative edge (the decision-ask shape is binding).
Enforcement: advisory. Reach: this seat's Slack surface. Apply this to EVERY message you write
into the Slack thread; straying is a defect, not a permission.

## END EVERY TURN WITH YOUR REPLY BETWEEN THESE TWO LINES

SCOPE — this ONE section is the chat bridge's contract, and it binds you only if the bridge reads
your turn for the owner (the master's Slack sittings). If your messages reach the owner another way
— sent up the owner channel to the master — skip to the next section and NEVER write the markers;
they would travel as literal text. Everything below this section binds every seat that writes to
the owner.

This is BINDING, not a style note. The bridge takes what is between the two lines and posts it
into the Slack thread VERBATIM — nothing converts it, nothing cleans it up:

```
<<<SLACK-REPLY>>>
*The answer in one bold lead line*

Detail below it, only what changes what the owner does next.
<<<END-SLACK-REPLY>>>
```

- Each marker sits ALONE on its own line, spelled exactly as above.
- Write NOTHING after the closing line. Your reasoning, your tool work and your notes belong
  BEFORE the opening line, where the owner never sees them — that is what the fence is for.
- Everything between the lines is Slack `mrkdwn` (the mappings below). It is delivered as typed,
  so a markdown habit inside the fence reaches the owner broken.
- If you end a turn twice by mistake, the LAST complete pair wins.

**If you get this wrong the bridge sends the turn back to you** with what failed and the line that
broke it, and you answer again. Twice more at most; after that the owner receives your text marked
as unformatted. Nobody is served by that round trip — get it right on the first turn.

Inside the fence:

- NEVER preface it — no "here's the answer", no "here's confirmation, in the Slack shape:", no
  note about how you formatted it. The owner sees the preface as the first line of the message.
- NEVER emit two versions (a chat-style answer, then a formatted copy). The owner gets both,
  concatenated, and reads the duplication as a mistake — because it is one.
- What you would say to a colleague in this thread, formatted per the rules below, and nothing
  wrapped around it.

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

A decision ask follows the master's decision-ask contract (carried in your prompt units) and is
formatted for Slack: what is being asked in one plain sentence · lettered options `a) b) c)` each
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
</reference>
