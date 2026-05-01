# Caveman

## Purpose

Caveman is an opt-in communication mode that compresses Claude's chat responses to bare fragments — no articles, no filler, no full sentences. You get lower token usage (faster, cheaper) and a genuinely funny working style. What you trade away is readability for anyone who isn't you, and occasional oddness when precision matters. Most users skip it. If you run long technical sessions solo and enjoy a bit of absurdity, it's worth trying.

## Components

### `caveman` rule

**What it does:** Forces all chat prose into caveman-speak. Same technical substance, radically fewer words.

**Intensity levels:** The rule doesn't use a dial — it's either on or off — but the compression effect scales with response length. Short answers become one-liners. Long analyses become dense fragments with arrows and abbreviations instead of paragraphs.

The practical spectrum looks like this:

| Level | Style | Example |
|-------|-------|---------|
| Normal | Full sentences, connectives, polish | "Your component re-renders because you're passing an inline object as a prop. React's shallow comparison sees it as a new reference on every render. I'd recommend wrapping it in `useMemo`." |
| Caveman (lite feel) | Fragments, no articles, abbreviations | "Inline obj prop → new ref → re-render. `useMemo`." |
| Caveman (dense) | Pure fragments, arrows, max compression | "New ref each render → shallow compare fail. `useMemo` fix." |

The rule targets the "dense" end consistently. One to three lines per response unless you ask for detail.

**Auto-clarity escape:** Security warnings and irreversible action confirmations always revert to full, clear sentences regardless of mode. Caveman resumes immediately after. This is a hard exception in the rule — the agent can't compress "you are about to delete your production database" into a grunt.

**Banned constructs (always, even in caveman mode):** "Let me...", "I found...", "Here's my analysis", headers in chat, numbered lists over 3 items, summary tables, restating what you said.

**Turning it off:** Say `stop caveman` or `normal mode`.

**Scope:** Chat prose only. Code blocks and PR descriptions stay normal.

---

### `caveman-commit` rule

**What it does:** Replaces standard commit message style with parody caveman voice when caveman mode is active. Same commit structure (subject line under 72 chars, optional body), just written like a prehistoric field report.

**When to use:** Personal projects, throwaway branches, joke repos, side hacks where you want a laugh when you run `git log`. Not for shared repos, client work, or anything a teammate will triage at 2am.

**Format:**
- First line: caveman grunt or war cry from a rotating pool (`UGA UGA!!`, `*beats chest*`, `moon rise. caveman push code.`, etc.) + relevant emoji + what changed, in caveman voice
- Body (optional): files described as cave things (files = rocks, dirs = caves, configs = cave paintings, bugs = sabertooth), caveman grammar throughout, ends with a sign-off
- Co-Author line: written normally — "serious tribe business"

**Example — normal vs caveman:**

Normal:
```
fix(auth): handle null reference on login flow

Add guard clause at L42 to prevent null ref when session token
is missing. Add unit test to cover the case.
```

Caveman:
```
*beats chest* 🔥 fix auth bug that bite caveman

sabertooth in login cave — null ref on L42. caveman smash with guard clause.
add sniff-check so sabertooth not return. rock solid.

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Caveats

Don't enable on shared repos, client deliverables, or any docs another person will read cold. The auto-clarity escape handles dangerous confirmations well, but it's a rule, not a failsafe — edge cases exist. If you're doing something high-stakes, turn it off first (`normal mode`), do the thing, re-enable if you want.

## Credit

Based on [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman).
