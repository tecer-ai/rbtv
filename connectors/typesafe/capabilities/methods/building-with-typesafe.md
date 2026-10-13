# Building with TypeSafe

The result: a step of the thing you are building (code, a tool, a skill, a rule or an agent) makes its judgment about text through TypeSafe, with a threshold measured on real cases and a stated action for the uncertain ones. Inputs: what the thing must do, its existing code and stack, and where its credentials come from. If the intended behavior is missing, ask what it must do before choosing judgments. Take the key from the application's configuration or environment; never write a key into source.

TypeSafe's System One model answers typed questions about a state: text, or named parts of text. Code owns the workflow; the model supplies the judgment at the one step where fixed rules cannot. It returns typed answers and probabilities, and no generated text or reasons.

## 1. Decide whether the step fits

| The step | Fits |
|---|---|
| Decides, in code, whether an event deserves an agent turn: a message to wake for, an alert to raise, a record to escalate | Yes. This replaces an agent call with one request. |
| Routes an item to one of a fixed set of handlers, queues, agents or models | Yes |
| Selects which candidates (files, passages, tools, skills, memories) reach an agent or a larger model | Yes, as a ranking the receiver may set aside |
| Guards an action before it runs: a command, a message about to be sent, an output about to be shown | Yes, with a stated action for the uncertain cases |
| Checks one stated condition against its evidence: a claim against its source, a field against its document, a convention against a file | Yes, one condition per question |
| Turns free text into a feature a rule or a model then uses | Yes |
| Needs a count, a sum, a date comparison, or any exact value | No. Compute it in code and give the model the result. |
| Needs several steps of reasoning, or text written | No. Use an agent or a generative model. |
| Passes or fails an agent's finished work | Not on its answer alone. An outside measurement found its judgment of another model's answer too weak to use as it comes, and weakest on multi-step work. It may send work to review; a person or a reviewing agent passes it. |
| Reads images, audio, or more than 64,000 tokens in one request | No |

When the step does not fit, build it another way and stop here.

## 2. Read the provider's documentation

The provider's documentation is the source of truth for concepts, question guidance, request fields, limits and worked examples. Read the pages the step needs before writing; do not load the whole site.

- Start at the [documentation index](https://docs.typesafe.ai/llms.txt). A page is served as Markdown when `.md` is added to its path.
- If the index cannot be reached, use the links below. If no page can be reached, work from the installed `typesafe --help` and say in your result that the documentation was not read; do not invent a field or a limit.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [System One](https://docs.typesafe.ai/concepts/system-one.md), [building guide](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md) | The programming model and how to split a workflow into judgments | Design the workflow around the step | choosing the shape of the integration |
| [Use-case map](https://docs.typesafe.ai/concepts/use-case-map.md), [cookbooks](https://docs.typesafe.ai/cookbooks.md) | Application patterns and worked examples | Start from the closest built example | the step resembles a known pattern; read the closest cookbook |
| [State](https://docs.typesafe.ai/concepts/state.md), [primitives](https://docs.typesafe.ai/primitives.md) | What a state may hold and the three question types | Supply the evidence and define the answers | writing the questions; then read the page of the type chosen |
| [Confidence](https://docs.typesafe.ai/confidence.md) | Probability, confidence and their difference | Choose what happens to uncertain answers | setting a threshold or an escalation |
| [Known weak points of the current model](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md) | Where the model answers wrongly and what to do instead | Keep the step away from them | before the first test of the questions |
| [HTTP API](https://docs.typesafe.ai/api.md), [Python SDK](https://docs.typesafe.ai/sdk/python.md), [JavaScript SDK](https://docs.typesafe.ai/sdk/javascript.md) | The request and client contracts | Write the call | writing program code; read the one that matches the stack |

## 3. Choose how the step calls it

| The step lives in | Call |
|---|---|
| A shell script, a scheduled job, or an agent's own procedure | The `typesafe` command. `typesafe ask` takes one JSON request and may point at whole files; `typesafe yesno`, `choice` and `score` take one question in one line and can exit by a threshold. `typesafe --help` and each verb's help are the reference. |
| A program | The provider's HTTP API or its SDK for the program's language, from the pages in step 2 |

## 4. Design the judgments

Choose the question type by what the answer means:

| Need | Type | Distinction |
|---|---|---|
| One of a defined set | Choice | Picks one option; its distribution compares the options |
| Whether a condition holds | Noul, the yes/no type | The probability of yes; use one per label when several may apply |
| A degree along a described dimension | Score | A probability-weighted position on ordered levels |

Give each question the state it needs to be answered: the source text, identities, relationships, policies and current facts. Name the parts when there are several, and refer to a part in the question in backticks. Put the judgment in the instructions and define the possible answers in the criteria. The key of a question is for your code and is not sent to the model; put the whole meaning in the question.

Ask one narrow judgment per question. Write the exact condition: the model reads the words and not the intent. Split dimensions that are useful on their own, without breaking the relationship being judged. Describe each level of a score as a concrete situation that stands on its own.

Keep the needed answers available: include a no-match option when nothing may fit, and check that every value the model may need to select is among the candidates. The model cannot choose a value it was not given.

## 5. Compose, set thresholds and verify

Ask independent questions about one state in one request: they run together and do not see one another's answers. Make a second request only when an earlier answer is needed to fetch evidence, build a new state or decide the next options.

Decide in code what each range of the answer does, and give the uncertain range its own action. A common shape is three tiers: the top acts, the middle goes to an agent, the bottom goes to a person or is dropped. Measure the thresholds on real cases of this step with known right answers before the step acts on them; a threshold from an example or from another step is a starting value, not a result.

A probability near 0.5 on a yes/no question means the model could not tell, not a middle degree. The confidence of a choice or a score describes how concentrated the answer is, not whether the workflow is right. A typed answer guarantees the form of the answer, not its truth.

Test representative cases and the behavior that results, including the uncertain range and a failed call. For a wrong result, inspect the exact state, questions, candidates and answers, and separate missing evidence, a model error, a code error and a service failure. Record the thresholds and the cases they were measured on with the thing you built.

Derived from the TypeSafe agent skill, copyright (c) 2026 TypeSafe AI, distributed under the [MIT license](../../LICENSE).
