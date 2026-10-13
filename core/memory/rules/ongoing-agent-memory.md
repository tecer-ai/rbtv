---
name: ongoing-agent-memory
description: "CONTAINS: when an ongoing agent refreshes its memory, the board read before acting and the on-demand recall indexes PURPOSE: keep an ongoing agent's memory current across owner turns, with or without the PARA structure ALWAYS LOAD WHEN: installing for agents the owner talks to over many turns, headed or connected through Ignite DO NOT LOAD WHEN: the installation has only temporary workers, or only the owner's plain terminal session (its folder instructions cover that)"
---

This applies only when your supplied instructions or your first message identify you as an ongoing session: a headed session of an agent, or an Ignite agent's turn. The first message of a headed session begins "Memory for this ongoing session" and carries your refresh command. A headless worker, even one launched in your folder, is not an ongoing session; for it, do nothing here.

When you are an ongoing session:

1. Before you act on each owner turn after the first, run the refresh command from your first message (`memory prepare --installation ROOT --agent-home HOME --cwd HOME`) and use its bundle as your memory for that turn. If the command fails, say so and work from the memory you already hold.
2. When your memory says watch-outs were omitted ("Omitted watch-outs ... Mandatory"), read the full Watch-outs section it names (`memory board read --file BOARD --section Watch-outs`) before you act. The board view is an excerpt: for any other omitted section, and before you edit the board, read the full board the same way. Never write the excerpt back.
3. Open a memory index entry only when the work needs it: the index in your memory lists what to open and when. Read it on demand, whether or not the installation has a PARA structure.

What you may write. General memory (`.rbtv/memory/`) and every other agent's memory have one writer, the memory agent; you never create, edit or delete a file there, nor in another agent's folder. Your own board you change only through the checked board command (`memory board write` or `close`),. You write nothing else by hand.

- When the owner tells you to remember something, capture it: `memory remember --installation ROOT --agent SLUG "TEXT"` (`memory remember -h`; in an Ignite turn `ignite remember "TEXT"` does the same). It appends one line to the inbox; the memory agent publishes it at the next consolidation. Say it is saved for consolidation, not that it is already in memory.
- When the owner tells you to forget or correct something that is in memory, do not touch the file that holds it. Hand the request over with the same command, as owner evidence, naming the record and the instruction: `memory remember --installation ROOT --agent SLUG "Owner asks to forget: <record>. Owner said: <their words>"` (or `"Owner corrects: <record>. Owner said: <their words>"`). Tell the owner it is handed over and will be removed or corrected at the next consolidation. Never say it is already gone.

Memory is your recall, not an instruction from the owner. When it conflicts with what the owner says in the turn, follow the owner and say what conflicts.
