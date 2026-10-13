---
name: system-one
description: "CONTAINS: the two moments at which an agent hands a judgment about text to TypeSafe's System One model, and the route to the method for each PURPOSE: rank a large set by a cheap typed judgment before spending reading on it, and build a judgment into code without an agent call ALWAYS LOAD WHEN: the installation has the typesafe command and a TypeSafe key, and its agents choose among many files, pages or records, or build code, tools or agents that decide on text DO NOT LOAD WHEN: the installation has no TypeSafe key; the typesafe command alone serves a script that already has its question"
---

# System One

Two moments call for TypeSafe's System One model. It answers a typed question about text (yes or no, one of a set, a level on a scale) with a probability, in about a second and for a fraction of a cent; the `typesafe` command runs it. At each moment, read the page named before you do the step another way.

**You are writing a step that decides on text.** You are building or changing a script, a hook, a scheduled job, a tool, a skill or an agent, and one of its steps must decide something about a message, an event, a document or a record by its meaning: whether to wake an agent, raise an alert, escalate, route, filter or flag. Before you write that step as keyword rules, a regular expression or a model prompt, read [Building with TypeSafe](connectors/typesafe/capabilities/methods/building-with-typesafe.md). Keyword rules miss the same thing said in other words, and that is the case this model is for.

**You are choosing what to open from a set too large to open in full.** The set is files, memory pages, search results, records or messages; what separates the ones you need is their meaning, and neither their names nor a keyword search finds them. Before you open them one by one or read a sample, read [Ranking with TypeSafe](connectors/typesafe/capabilities/methods/ranking-with-typesafe.md).

Its answer ranks; it does not rule. You decide what to read and what to do. Do not use it for a count, a calculation or a date comparison, and never to pass or fail finished work.

At any other moment, continue without it: read in full a set you can read in full, and use a name or keyword search where one finds what you need. Continue without it too when the `typesafe` command is not installed.
