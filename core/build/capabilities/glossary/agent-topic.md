# Agent topic

On-demand detail of one agent's [memory](memory.md), at `<agent>/memory/<slug>.md`. One file per topic. The filename is the id. A topic is a board subject's detail moved off the [board](board.md), a procedure this agent repeats, or reference facts only this agent needs. It is not a fact about the owner, and it is not a [learned rule](learned-rules.md).

The [dreamer](dreamer.md) writes it. For a subject, it moves the detail here and leaves the board entry's detail link. The file is read by following that link, or from the agent's memory index. It is never injected, and it never appears in general memory's index. Archive, never delete: a closed subject keeps its file, with a closing bullet. The file is tracked in git. An over-cap write is refused, never truncated.
