# TypeSafe

`typesafe` sends content to TypeSafe's System One service and returns typed answers: the probability of yes, one option from a set, or a position on ordered levels. Run `typesafe --help` and the selected verb's help for inputs, outputs and examples. The [typesafe-ai skill](../../../skills/typesafe-ai.md) covers how to design the questions; this command only carries them.

Install with `rbtv add connectors/typesafe#typesafe`. The program needs Python and no package beyond its standard library.

The service has two operations, and every verb is one of them. `ask`, `yesno`, `choice` and `score` all build one request to `POST /v1/systemone`; `models` reads `GET /v1/models`. The [provider's API reference](https://docs.typesafe.ai/api.md) defines the request and answer fields, and the command uses the provider's words for them: state, question, instructions, criteria.

`ask` is the general form and the one an agent uses: one JSON request in the provider's shape, from standard input or `--request`. The command adds one thing to that shape: an object holding only `$file` stands for the text of the file it names, anywhere in the request. Everything else is sent unchanged and `--json` prints the service's answer unchanged, so a field the provider adds needs no change here. The service validates questions; the command does not repeat that validation, and a rejected request returns the provider's own detail.

`yesno`, `choice` and `score` send a single question under the key `answer`, for a script that needs one line. Their state is standard input, whole files added with `--state`, or both; the verb's help states the part names the command gives them. Thresholds, tiers and sorting are computed here from the returned numbers; the service knows nothing of them.

The process environment's `TYPESAFE_API_KEY` takes precedence over the installation's [environment file](../../../../../core/rbtv/capabilities/glossary/environment-file.md). The installation is the first ancestor of the working folder with `.rbtv/config/install.json`. Outside an installation, only the process environment supplies the key. The command saves no settings and writes no files.

A rate-limited or overloaded answer (429, 529) is retried four times, waiting the time the service names or 1, 2, 4 and 8 seconds. Many items are sent eight at a time. One request holds at most 64,000 tokens; a larger item fails alone and the other items are still answered. The [provider's model page](https://docs.typesafe.ai/models.md) states the current limits and price.

For offline verification, run `python test_typesafe.py` from this folder. The checks run the command in temporary installations against a local HTTP stub with a synthetic key. `TYPESAFE_BASE_URL` selects the API root; it is the name the provider's own clients read. Never point a process carrying a real key at an untrusted root.
