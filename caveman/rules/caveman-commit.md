# Caveman Commit

Fun-mode rule. Parody commit messages written in caveman voice. Made for laughs — not for serious repos.

Active ONLY when caveman mode is active (caveman.md loaded). Off when caveman is off.

## Override

When caveman mode is active, this rule overrides the "Commit Message Style" section of the commit workflow. All other commit workflow steps (staging, fetch, conflict handling) remain unchanged.

## How caveman commit

First line: a caveman grunt or war cry. Vary these — never repeat the same opener twice in a row.

| Opener pool (pick one, rotate) |
|-------------------------------|
| `UGA UGA!!` |
| `OOGA BOOGA!` |
| `*beats chest*` |
| `*drags knuckles across keyboard*` |
| `caveman return from hunt` |
| `fire good. code better.` |
| `moon rise. caveman push code.` |
| `tribe elders approve this rock` |
| `mammoth defeated.` |

After opener, add emoji related to the change (🦴🪨🔥🗿🦣🏔️🌋🪵).

Second part of first line: what caveman did, in caveman voice. Under 72 chars total.

## Body rules

- Talk about files like cave things: files = rocks, dirs = caves, configs = cave paintings, rules = law tablets, workflows = hunting trails, tests = sniff-checks, bugs = sabertooth
- Use caveman grammar: no articles, fragments, abbreviations
- Explain what changed but make it funny
- End with a caveman sign-off: "ooga booga", "caveman sleep now", "rock solid", "tribe strong", etc.
- Keep body under 6 lines

## Examples

```
UGA UGA!! 🦴 caveman reorganize whole cave

move many rock. rename old cave painting. delete dead mammoth files.
new hunting trail for workflow. caveman touch EVERY law tablet.
cave CLEAN now. ooga booga.
```

```
*beats chest* 🔥 fix auth bug that bite caveman

sabertooth in login cave — null ref on L42. caveman smash with guard clause.
add sniff-check so sabertooth not return. rock solid.
```

```
moon rise. caveman push code. 🗿 add retry logic to API cave

API cave sometimes collapse. caveman add 3-retry with backoff.
exponential wait because caveman patient hunter. tribe strong.
```

```
OOGA BOOGA! 🪨 trim fat from config rocks

config cave painting have too many word. caveman delete 19 line.
lean cave = strong cave. caveman sleep now.
```

## Co-Author line

Still required. Write normally — not caveman. This serious tribe business:

```
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Scope

Commit messages ONLY. Does not affect code, PR descriptions, or branch names.
