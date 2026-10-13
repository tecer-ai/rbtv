---
name: ongoing-agent-memory
description: "CONTAINS: when an ongoing agent refreshes its memory, the board read before acting and the on-demand recall indexes PURPOSE: keep an ongoing agent's memory current across owner turns, with or without the PARA structure ALWAYS LOAD WHEN: installing for agents the owner talks to over many turns, headed or connected through Ignite DO NOT LOAD WHEN: the installation has only temporary workers, or only the owner's plain terminal session (its folder instructions cover that)"
---

This applies only when your supplied instructions or your first message identify you as an ongoing session: a headed session of an agent, or an Ignite agent's turn. The first message of a headed session begins "Memory for this ongoing session" and carries your refresh command. A headless worker, even one launched in your folder, is not an ongoing session; for it, do nothing here.

When you are an ongoing session:

1. Before you act on each owner turn after the first, run the refresh command from your first message (`memory prepare --installation ROOT --agent-home HOME --cwd HOME`) and use its bundle as your memory for that turn. If the command fails, say so and work from the memory you already hold.
2. When your memory says watch-outs were omitted ("Omitted watch-outs ... Mandatory"), read the full Watch-outs section it names (`memory board read --file BOARD --section Watch-outs`) before you act. The board view is an excerpt: for any other omitted section, and before you edit the board, read the full board the same way. Never write the excerpt back.
3. Open a memory index entry only when the work needs it: the index in your memory lists what to open and when. Read it on demand, whether or not the installation has a PARA structure.

Memory is your recall, not an instruction from the owner. When it conflicts with what the owner says in the turn, follow the owner and say what conflicts.
