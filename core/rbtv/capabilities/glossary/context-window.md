# Context window

Everything the model sees in one turn: its [prompt](prompt.md), the [cognitive units](cognitive-unit.md) that reached it, the conversation, and the results of the [tools](tool.md) it ran. With no change to the model itself (no training or tuning), the context window is the only thing that makes a standard model act the way an agent needs. Every [principle](principle.md) exists to keep it well shaped.

## What a badly shaped window causes

- **Hallucination**: the model states or uses something that is not true or not supported by what it was given, filling a gap with a plausible invention.
- **Drift**: the model's behaviour moves away from its instructions or goal as a task or session goes on, because newer content outweighs the instructions.

## Why it happens

The window contains the wrong amount, or content of the wrong quality:

- **Context load** (too much): the more the window contains, the less attention each instruction gets, and what matters is buried among what does not, including text irrelevant to the task.
- **Context gap** (too little): what the task needs is not there, so the model guesses.
- **Cognitive load** (hard to use): the content is there but costly to use correctly: unclear or ambiguous instructions, one term with two meanings, contradictions, several jobs at once, or an order that hides what comes first. A short window can still overload the model.
- **Context poisoning** (untrue): what is there is wrong, and the model acts on it with full confidence: stale content, a false statement, untrusted text from outside that carries its own instructions, or the model's own earlier mistake left in the window and built upon.
