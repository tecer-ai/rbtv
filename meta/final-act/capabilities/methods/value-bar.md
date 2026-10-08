# Value bar

The value bar decides whether an entry earns a place on a backlog: a task, a loose end, an issue. Every entry kept is the owner's attention spent later, so the burden of proof is on keeping. Truth is not value: a correct observation about a path nobody has hit is below the bar.

Apply it to one entry at a time, with its full body read, and classify:

| Verdict | Condition |
|---|---|
| keep | The entry names a cost paid now or on a known date: an observable defect (not one that could fire on an unhit path), an owed teardown (something left running, dirty or armed), content that actively misleads the next agent (a pointer to the wrong place, a stale instruction that already misled someone, not mere staleness), or a dependency of other kept work |
| drop | Latent edge cases nobody has hit, speculative hardening ("could break if"), hygiene whose absence has caused no wrong conclusion, polish, re-verification of what was verified once. When the cost sentence needs "may", "might", "in principle" or "someday", the entry is below the bar |
| fold | A duplicate or sibling of a keeper: merge its context into the keeper, then remove it |
| move | Real value that belongs in another home, because it must outlive this backlog or another owner's list is where it acts: carry its full context there and leave a pointer, not a copy |
| owner-decision | A decision only the owner can make, on which something real waits. A question nobody needs answered is below the bar |

Check staleness cheaply: look for the one fact that would kill the entry (the event it was gated on happened; later work already fixed it). Do not re-investigate the world to rule on an entry.

An entry that is kept, moved or folded must work cold: a fresh agent acts from its text alone, with what it is, where, why the cost is paid, what was tried, and the state things were left in.
