<!--
Shape of one agent topic. Copy the skeleton into the instance. Do not copy this comment.
The dreamer writes the instance. type is subject, procedure, or reference. Archive, do not delete.
-->

## Skeleton

```markdown
---
description: when <the task or situation that needs this topic>
type: <subject | procedure | reference>
aliases: [<search words>]
---
# <Topic title>

Threads: [<short label>](<URL>) · [<short label>](<URL>) | none        (subject only)

- <one fact, step or state>. (<YYYY-MM-DD> · <agent>/<thread link>)
- Closed <YYYY-MM-DD> — <outcome>. (<YYYY-MM-DD> · <agent>/<thread link>)        (subject, when closed)
```

## Example (fictional — never copy)

```markdown
---
description: when working on Sam's Lisbon trip 2026-10-05 to 2026-10-12 — bookings, constraints, open items
type: subject
aliases: [lisbon, portugal, trip, train, hotel, travel]
---
# Lisbon trip 2026-10-05

Threads: [bookings](https://example.slack.com/archives/C0000/p0377) · [co-working](https://example.slack.com/archives/C0000/p0390)

- Train Lyon → Lisbon via Barcelona booked, seat 42 window, ref ABC123. (2026-10-01 · concierge/[t-0377](https://example.slack.com/archives/C0000/p0377))
- Hotel in Alfama, 7 nights; free cancellation up to 2026-10-03. (2026-10-01 · concierge/[t-0377](https://example.slack.com/archives/C0000/p0377))
- Sam wants a quiet co-working space for 2026-10-07 and 2026-10-08 — two options sent. (2026-10-02 · concierge/[t-0390](https://example.slack.com/archives/C0000/p0390))
```

Procedure example (fictional — never copy):

```markdown
---
description: when filing Sam's monthly expense export
type: procedure
aliases: [expenses, export, monthly]
---
# Monthly expense export

1. Export the CSV from the bank; save under 2-areas/finance/receipts/. (2026-09-05 · concierge/[t-0330](https://example.slack.com/archives/C0000/p0330))
2. Rename to YYYY-MM-expenses.csv before sending. (2026-09-05 · concierge/[t-0330](https://example.slack.com/archives/C0000/p0330))
```

Reference example (fictional — never copy):

```markdown
---
description: when entering the Lyon studio — door code and wifi
type: reference
aliases: [studio, door code, wifi, lyon]
---
# Lyon studio access

- Door code 4471; changes quarterly — confirm with the studio manager first. (2026-09-05 · concierge/[t-0330](https://example.slack.com/archives/C0000/p0330))
- Studio wifi `atelier-guest`; password on the router label. (2026-09-05 · concierge/[t-0330](https://example.slack.com/archives/C0000/p0330))
```
