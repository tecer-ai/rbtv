# Profile

`.rbtv/memory/profile.md` holds owner facts needed on nearly every turn. Ignite supplies it to every agent turn, including scheduled wakes. Topical facts belong in [Knowledge](knowledge.md), not in both places.

Keep facts brief and link their source notes. Employer and company detail belongs in an [Entity](entity.md); Who may retain a one-line role pointer. The profile has no health section: state a needed constraint here and keep its health reason in Knowledge.

Submit facts through [Inbox](inbox.md). [Memory](memory.md#record-and-maintain-information) owns writers and corrections; ordinary agents do not edit the profile.

## Record format

```markdown
# Profile — <owner>

## Who
- <identity or role fact>. (<YYYY-MM-DD> · <source>)

## Working with <owner>
- <standing preference or constraint>. (<YYYY-MM-DD> · <source>)

## Now
- <temporary fact>, until <YYYY-MM-DD>. (<YYYY-MM-DD> · <source>)
```

Use one dated fact per bullet and replace a corrected fact. Add `until <date>` only when the owner supplied an end, at the end of the fact before provenance. Follow [Memory](memory.md#record-checks) for provenance and counting. The [memory checker](../tools/ignite/memory.js) requires the three sections and at most 4,000 characters.

Check the published profile against Knowledge and Entity for duplicated detail, then inspect a supported turn’s supplied profile. Follow [Memory’s recovery route](memory.md#check-supplied-memory) for a missing or rejected copy.
