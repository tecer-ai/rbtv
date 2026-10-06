# Context window

Everything the model sees in one turn: its [prompt](prompt.md), the [cognitive units](cognitive-unit.md) that reached it, the conversation, and the results of the [tools](tool.md) it ran. With no change to the model itself (no training or tuning), the context window is the only thing that makes a standard model act the way an agent needs. Every [principle](principle.md) exists to keep it well shaped.

## What a badly shaped window causes

- **Hallucination**: the model states or uses something that is not true or not supported by what it was given, filling a gap with a plausible invention.
- **Drift**: the model's behaviour moves away from its instructions or goal as a task or session goes on, because newer content outweighs the instructions.

## Why it happens

The window contains the wrong amount, or content of the wrong quality:

- **Context load** (too much): the more the window contains, the less attention each instruction gets, and what matters is buried among what does not, including text irrelevant to the task.
- **Context gap** (too little): what the task needs is not there, so the model guesses.
- **Cognitive load** (hard to use): the effort required to interpret the available instructions and decide how to follow them. Ambiguity, contradictions, unclear ordering, unnecessary choices and judgments with no stated criteria add to this effort. A short instruction can still make the agent invent a standard or reconsider a settled choice. Some judgment is necessary; instructions reduce avoidable work by supplying the default, the conditions that change it and the evidence needed to decide. [Keep it stupidly simple](../principles/keep-it-stupidly-simple.md) gives the authoring rule.
- **Context poisoning** (untrue): what is there is wrong, and the model acts on it with full confidence: stale content, a false statement, untrusted text from outside that carries its own instructions, or the model's own earlier mistake left in the window and built upon.
