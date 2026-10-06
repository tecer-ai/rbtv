# Weekly timeline

A weekly timeline records the events that still matter after a week ends, at `.rbtv/memory/timeline/weekly/<YYYY-Www>.md`. It uses the ISO week number and is read on demand. The dreamer derives it from [Daily timelines](timeline-daily.md), keeping the detail there.

Link the owner’s weekly periodic note without copying it. Each event links its source day; the source day must contain thread evidence supported by the run’s owner messages. Follow [Memory](memory.md#record-and-maintain-information) for writers and corrections. Durable facts belong in their own memory records as well as the history that mentions them.

## Record format

```markdown
---
description: when asked what happened in <YYYY-Www>
---
# <YYYY-Www>

Periodic note: [<weekly note>](<relative path>)

- <event that still matters> — [<YYYY-MM-DD>](../daily/<YYYY-MM-DD>.md)
```

Keep the event’s daily link in that exact relative form. Resolve the periodic-note link from the weekly file’s folder. The [dreamer checker](../tools/ignite/dreamer.js) accepts week numbers 01–53 and at most 25 lines; [Memory](memory.md#record-checks) defines the count and refusal behavior. Check that the selected week actually contains the cited days; acceptance of the filename pattern does not establish that.

Review the published week against its source days: retain consequential events and working links without repeating each day’s episodes or the owner’s note.
