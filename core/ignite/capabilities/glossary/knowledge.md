# Knowledge

Knowledge is durable owner information read on demand from `.rbtv/memory/knowledge/`. It has five fixed files: `facts.md` for life facts, `preferences.md` for likes and working preferences, `decisions.md` for choices binding the owner beyond one project, `self.md` for the owner’s self-model, and `health.md` for facts that change how agents act.

A fact needed on nearly every turn belongs in [Profile](profile.md), not both places. Health records link the owner’s notes instead of copying them; a constraint may appear where needed, with its health reason here. Every agent may read all five kinds. Life decisions are separate from a folder’s own decision register.

Submit a fact through [Inbox](inbox.md), naming its kind. [Memory](memory.md#record-and-maintain-information) owns writers and corrections. A refused write leaves the file intact; none of the five files splits to evade its cap.

## Record format

```markdown
---
description: when <work needing this kind of knowledge>
type: <facts | preferences | decisions | self | health>
aliases: [<search words>]
---
# <Kind>

## <Subtopic>
- <fact>. (<YYYY-MM-DD> · <source>)
```

The type equals the filename stem. A decision bullet uses `<decision>. Rejected: <alternative>. Why: <reason>. Reopen when: <condition>. (<YYYY-MM-DD> · <source>)`. Self and health records link the source note with `- Vault: [<note>](<relative path>)`. A correction replaces its fact record rather than leaving conflicting versions.

Follow [Memory](memory.md#record-checks) for provenance and counting. The [dreamer checker](../tools/ignite/dreamer.js) validates metadata, dated records and the 3,000-character cap. Check the published kind and its neighboring Profile/Entity record for duplicated or misplaced facts; a valid record shape does not settle that judgment.
