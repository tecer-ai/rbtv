<!--
Shape of one entity file. Copy the skeleton into the instance. Do not copy this comment.
The dreamer writes the instance. type is person, org, place, or device. places are geography only.
-->

## Skeleton

```markdown
---
description: when <the work that needs this entity — who/what it is>
type: <person | org | place | device>
aliases: [<other names>, <nicknames>, <misheard spellings>]
---
# <Name>

- <relation to the owner / what it is>. (<YYYY-MM-DD> · <agent>/<thread link>)
- <a fact an agent needs>. (<YYYY-MM-DD> · <agent>/<thread link>)
- Vault: [<path of the vault note or folder holding the content>](<relative link>)
- Glossary: [row "<Name>"](<relative link to the installation's name glossary>)   (people and orgs only)
```

## Example (fictional — never copy)

```markdown
---
description: when handling Sam's taxes or studio accounts — Lea Moreau, Sam's accountant since 2026-10-01
type: person
aliases: [Lea, Léa, Moreau, accountant, "Leah Moro"]
---
# Lea Moreau

- Sam's accountant for the studio and personal taxes, replacing [paul-girard](paul-girard.md). (2026-10-01 · master/[t-2204](https://example.slack.com/archives/C0000/p2204))
- Works at [moreau-conseil](../orgs/moreau-conseil.md). (2026-10-02 · master/[t-2230](https://example.slack.com/archives/C0000/p2230))
- Prefers email to calls. (2026-10-02 · master/[t-2230](https://example.slack.com/archives/C0000/p2230))
- On parental leave — reach her colleague [nina-roux](nina-roux.md) instead, until 2026-11-30. (2026-10-02 · master/[t-2230](https://example.slack.com/archives/C0000/p2230))
- Vault: [2-areas/finance/](../../../../2-areas/finance/)
- Glossary: [row "Lea Moreau"](<relative link to the installation's name glossary>)
```
