# typesafe decisions

Standing decisions about the `typesafe` component. Each states the decision and its reason; [the tool's page](capabilities/tools/typesafe/typesafe.md) and `typesafe --help` describe the resulting design.

## The command uses the provider's words

State, question, instructions and criteria name the same things in the command, its help and its flags as in the provider's API. Reason: an agent that reads the provider's documentation and an agent that reads the command's help must not have to translate between two vocabularies; an earlier version said "content" and "given" for two parts of the state and was renamed.

The yes/no question type is the exception: the verb is `yesno`, and help states once that the provider calls the type `noul`. Reason: every reviewer who met `noul` without the explanation could not tell what it meant.

## One JSON request is the general form

`ask` takes one JSON request in the provider's shape, and help and the tool's listing line name it as the form for an agent. Reason: the request is already JSON at the provider, so an agent learns one shape, the documented one, and a field the provider adds needs no change to the command.

`yesno`, `choice` and `score` stay as one-question forms that build the same request. Reason: a scheduled job that gates on one answer needs one line, with no request file written first.

## A file pointer is the command's one addition to the request

An object holding only `$file` stands for the text of the file it names, anywhere in a request. Reason: several whole files in the state, and a file that only one question's instructions carry, become one mechanism with no flag per case. The `$` marks it as a directive, so a real record with a `file` field is never read as a pointer.

## The state arrives on standard input or in the request

A short verb reads its state from standard input; `--state NAME=FILE` adds whole files as named parts. A request that carries its own state refuses every other source of state. Reason: one source per run keeps what was judged unambiguous, and standard input keeps every verb usable in a pipe.

## Thresholds, tiers and sorting are computed in the command

`--at-least`, `--expect`, `--tiers`, `--list-tier` and `--sort` work on the numbers the service returned; the service is not told about them. Tiers are numbered, never named, and the caller gives the thresholds, from highest to lowest. Reason: what counts as "pass", and how many groups there are, changes case by case, such as records that go through, records for a second check and records for a person; a fixed set of names or cut-offs would fit one case.

`--tiers` and `--at-least` cannot be given together. Reason: one way to bucket an answer per run.

## Nothing is hidden by a fixed number

A choice lists every option in text output, and `--top N` limits the list when the caller asks. Reason: a fixed cut-off (the first version dropped options under 0.01) hides data by a number nobody chose; `--json` always carries every option either way.

## The exit status carries the judgment only when asked

Without a threshold the command exits 0 whenever the service answered. With `--at-least`, `--expect` or `--list-tier` it exits 0 when at least one item qualified and 3 when every item was answered and none did. A failed service call exits 1 and a refusal before any call exits 2. Reason: a script must be able to branch on the answer without parsing output, and must never mistake a failed call for a "no".

When some items failed and another qualified, the run exits 0 and names the failed items on standard error. Reason: the help promises exit 0 when any item qualifies, and one unreadable file must not silence a gate that another item opened.

## The key is read from the installation's environment file

The process environment's `TYPESAFE_API_KEY` comes first, then that line of the installation's environment file. The component keeps no key file of its own. Reason: an installation keeps every key in its one environment file.

## The program uses only the standard library

The program calls the two endpoints with Python's standard library and does not depend on the provider's SDK. Reason: the service has two operations, and a tool with no package to install runs wherever Python does. The retry policy follows the provider's stated rule for 429 and 529 answers.

## The typesafe-ai skill is the provider's text

`skills/typesafe-ai.md` is the provider's own agent skill under its licence, kept in this component with its `LICENSE` file. The command's page links to it for how to design questions and does not restate it.
