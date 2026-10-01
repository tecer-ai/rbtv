<!--
Shape of a board. Copy the skeleton into the instance. Do not copy this comment.
The agent writes subjects and watch-outs with ignite-agent board write. Ignite writes Timers and flags.
Close with ignite-agent board close. Caps: 90 non-empty lines outside Timers, 8 subjects, 6 watch-outs, 6 closed lines.
-->

## Skeleton

```markdown
## What matters now

### <Subject title — a noun phrase, unique on this board>
<1–3 lines: where this subject stands now and what happens next. One fact per line.>
- Threads: [short label](URL) · [short label](URL) | none
- Detail: ../memory/<slug>.md | <vault page, on project/area boards> | none
- Flags: none | answered YYYY-MM-DD | idle since YYYY-MM-DD

## Watch-outs

- <The owner's correction, as a rule the agent follows from now> (<YYYY-MM-DD> · <agent>/<thread link>)

## Timers

| Fires | Timer | For | Subject |
|---|---|---|---|
| YYYY-MM-DD HH:MM <IANA tz> | <timer name, as passed on a wake> | <what to check or do> | <subject title> |

## Recently closed

- <Subject title> — <one-line outcome> (<YYYY-MM-DD> · <agent>/<thread link>)
```

<!-- ===================== FILLED EXAMPLE (fictional agent) — example, never copy ===================== -->

```markdown
## What matters now

### Conference talk draft
Outline approved by the owner; slides 1–8 drafted, 9–14 pending.
Next: send the full draft for review by 2026-10-02.
- Threads: [outline review](https://example.slack.com/archives/C0000/p1001) · [slide cut](https://example.slack.com/archives/C0000/p1009)
- Detail: ../memory/conference-talk.md
- Flags: answered 2026-10-01

### Printer toner reorder
Supplier quoted two options; waiting for the owner to pick one.
- Threads: none
- Detail: none
- Flags: none

## Watch-outs

- Send drafts as one PDF, never as separate slide images. (2026-10-02 · janice/[outline review](https://example.slack.com/archives/C0000/p1001))

## Timers

| Fires | Timer | For | Subject |
|---|---|---|---|
| 2026-10-02 09:00 Europe/Lisbon | talk-draft-review | Check the full draft is sent; remind the owner if not | Conference talk draft |

## Recently closed

- Team lunch booking — booked for 2026-10-09, confirmation in the thread. (2026-10-01 · janice/[lunch thread](https://example.slack.com/archives/C0000/p0990))
```
