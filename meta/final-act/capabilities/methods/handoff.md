# Handoff

The result: everything this session knows about the handed-off work lives where a fresh agent will find it: one document that agent can start from, or, for finished work, the existing docs, memories and task files brought current. The successor has nothing except that text: no memory of this session, no chat history, no idea what was tried. It takes over without repeating any research or any failed attempt.

Inputs: the user's ask to hand off, with the scope (total, or a named part) and the destination the conversation already carries. A scope the user did not state is total. A destination you do not know of is asked for in step 3. This page writes one handoff.

## 1. Set the scope

The handoff is total by default: everything this session knows about the work. It is partial only when the user explicitly asks to hand off just a part, for example a side error found while fixing something else. A partial handoff covers only that part, with the same completeness.

## 2. Bring the existing homes current

Do this in every handoff, before choosing a destination. From what this session already knows (the files it changed, read, or was pointed to by `CLAUDE.md`, an index or another file it read), check that everything describing the work reflects it: the docs of code you changed, indexes, state and plan files, READMEs, memories, task files. Update whatever is stale.

This is a check from memory and context, never a new search: a doc the session never saw is a declared gap, not something to look for.

## 3. Choose the destination

A handoff is not necessarily a new file. Take the first case that fits:

| The work | Destination |
|---|---|
| Is tracked in a file you already know of from this session (a project, a plan, a state doc, an existing handoff doc) | Update that file. Never create a new file when one exists. |
| Is quick, one-off work with no such file | The specific file the user confirms. Ask where: not knowing of a file means asking, not investigating. Never write to a destination the user has not confirmed. |
| Is finished | No handoff file. Step 2 already brought the homes current. A loose end that still has no home, or exists only in chat, first becomes a task as [Loose ends](loose-ends.md) files one. Then answer "nothing to hand off", listing every doc, memory and task file you checked and what you updated. Never give that answer without the check, and never create a file just to have one. |

A partial handoff follows the same order: a new file only when the handed-off part has no home, at a location the user confirms.

## 4. Write

When step 3 lands on a file, transfer all the knowledge about the handed-off work. Cover, where each applies:

- **Objective and scope**: what the work is, what "done" looks like, and, when partial, the exact boundary of what is handed off.
- **Current status**: precisely where things stand now, and the state everything was left in.
- **What was done**: every change made, with paths.
- **What was researched, how, and what it found**: sources, files read, commands run, conclusions drawn.
- **What was tried**: what worked, what failed, and why, so the successor repeats nothing.
- **Decisions made and their rationale**, including the options ruled out and why.
- **Open questions and declared gaps**: anything you know you do not know, stated explicitly ("unverified: X").
- **Challenges, cautions, traps**: anything that would catch a fresh agent.
- **Environment and setup specifics**: machines, tools, where credentials are (by pointer, never the values), running processes, anything armed or pending.
- **Pointers** to every relevant file, doc and resource.
- **Next steps**: what the successor does first.

The completeness test: could a fresh agent, given only this document, continue the work without asking anything and without redoing anything already done?

## 5. Close

Report where the knowledge now lives: the handoff file's path, or, when the work is finished, the "nothing to hand off" answer with the homes checked and updated.

After a total handoff, stop: the handoff is your last act on the task. After a partial handoff, say what remains yours and continue that work; never touch the handed-off part again, it belongs to the successor.

## Through every step

A handoff transfers knowledge the session already has; it does not gather any. Do no research, investigation or new reading for it. A gap in your knowledge is written down as a gap, never closed by a last-minute investigation.
