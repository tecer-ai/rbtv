# Inbox

The holding file for an explicit "remember X" about the owner, at `.rbtv/memory/inbox.md`. Any agent appends one line in the same turn, with `ignite remember`. Every agent sees the line at once, because the inbox is injected into every turn. The [dreamer](dreamer.md) files each line into the [profile](profile.md), [knowledge](knowledge.md), or an [entity](entity.md) and removes only the lines it filed.

Appending cannot overwrite. The inbox never refuses an append. Past 20 lines the owner is alerted. A correction of one agent's behaviour goes to that agent's [board](board.md) watch-outs, not here, unless it is also a fact about the owner, in which case it goes to both.

The agent on a turn never rewrites or deletes a line. A missing or invalid inbox is saved aside, including unfiled lines, and the last good version in git is loaded.
