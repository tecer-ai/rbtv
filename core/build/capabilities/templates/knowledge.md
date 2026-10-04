<!--
Shape of one knowledge file. Copy the skeleton into the instance. Do not copy this comment.
The dreamer writes the instance. Kinds: facts, preferences, decisions, self, health.
facts, preferences, and decisions start as one file and split into a folder when over their cap.
-->

## Skeleton

```markdown
---
description: when <the owner's <kind> could change the answer — <subtopic words>>
type: <facts | preferences | decisions | self | health>
aliases: [<subtopic words>, <synonyms>]
---
# <Kind>

## <Subtopic>
- <one fact>. (<YYYY-MM-DD> · <agent>/<thread link>)
- <decisions only:> <decision>. Rejected: <alternative>. Why: <reason>. Reopen when: <condition>. (<YYYY-MM-DD> · <agent>/<thread link>)
- <self / health only:> Vault: [<path of the note that holds the content>](<relative link>)
```

## Example (fictional — never copy)

```markdown
---
description: when choosing food, travel, tools or communication for Sam
type: preferences
aliases: [food, dining, restaurants, lunch, travel, trains, flights, tools, apps, email, messages]
---
# Preferences

## Food
- Vegetarian since 2026-09-01. (2026-10-01 · master/[t-2209](https://example.slack.com/archives/C0000/p2209))
- Likes Lebanese and Ethiopian food. (2026-10-01 · master/[t-2209](https://example.slack.com/archives/C0000/p2209))

## Travel
- Prefers trains under 5 hours to flying. (2026-06-02 · concierge/[t-0201](https://example.slack.com/archives/C0000/p0201))
- Takes a window seat on flights. (2026-06-02 · concierge/[t-0201](https://example.slack.com/archives/C0000/p0201))

## Communication
- Short messages, one question at a time. (2026-04-11 · master/[t-1310](https://example.slack.com/archives/C0000/p1310))
```

Example decision bullet (decisions.md): `- Keeps savings in index funds only. Rejected: single stocks. Why: no time to follow companies. Reopen when: the studio is sold. (2026-02-14 · master/[t-0950](https://example.slack.com/archives/C0000/p0950))`
