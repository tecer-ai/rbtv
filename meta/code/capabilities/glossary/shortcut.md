# Shortcut

A shortcut is a deliberate simplification in code that cuts a real corner with a known ceiling: one global lock where per-account locks would scale, a quadratic scan over a list that is small today, a naive heuristic in place of a model. It is marked in the code so that it is found again; an unmarked shortcut cannot be told from an oversight.

A shortcut is not a bug, a missing feature or a workaround for a symptom. A workaround for a symptom is a band-aid, which the coding skill's no-patches discipline removes with the fix; a feature nobody asked for is not written at all.

## The marker

Write the marker as a comment on the line above the simplified code, in the comment syntax of the language, with this text:

    shortcut: <the ceiling>; <the upgrade path or trigger>

The ceiling names the limit the simplification holds up to. The upgrade path names what replaces it and the observable condition that calls for the replacement. The semicolon separates the two, because either may contain a comma. For example, in Python:

    # shortcut: one global lock; per-account locks if throughput matters

Write the marker in the same change as the simplification. A marker with no upgrade trigger is incomplete: [The shortcut ledger](../methods/shortcut-ledger.md) flags it as `no-trigger`.

## Checks

Searching the tree for comment lines carrying `shortcut:` finds every marker and nothing else; a line of prose that mentions the word is not a marker, because it carries no comment prefix. Each marker read alone says what was simplified, how far it holds and what to do when it stops holding.
