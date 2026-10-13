# Sources of the shipped scores and costs

The rules for a `cost` cell of the shipped model catalog, and the record of where each cost and each unmeasured score came from. Read it when entering or reviewing a cost or a score; add to its tables in the same change as the cell.

## Costs

`cost` is the provider's standard API list price for output tokens, in US dollars per million tokens. Keep each cell by these rules:

1. Read the price on the provider's own pricing page, and record the page, the date read and every condition on the price in the table below.
2. Never enter what a subscription or a coding plan makes the model cost, and never a placeholder: a cost that is not known stays blank, which keeps the row out of price rankings. The cost of an image model stays blank too, because it is not priced per text token.
3. Where the price rises with the size of the request, the cell holds the base rate, and the table records the higher rate and where it starts.
4. A promotional price is entered while it runs, with its end date in the table. Change the cell when that date passes.
5. A price published for a named version applies to a row only when the harness's id is that version. Where the id is an alias or carries no version, enter the price and record the link as not confirmed.
6. Review a cell when its model is replaced, when an end date in the table passes, and when the owner asks.

| Model | `cost` | Conditions | Source, read 2026-10-10 |
|---|---|---|---|
| `haiku-5-5` | 0.50 | Up to 100,000 input tokens; 2.50 above. | <https://www.anthropic.com/claude/haiku> |
| `gemini-3.8-flash` | 3.75 | Introductory price through 2026-12-31; 7.50 from 2027-01-01. | <https://ai.google.dev/gemini-api/docs/pricing>; OpenCode's model list gives 3.75 for `google/gemini-3.8-flash`. |
| `gemini-3.1-pro-preview` | 12 | Up to 200,000 input tokens; 18 above. | <https://ai.google.dev/gemini-api/docs/pricing>; OpenCode's model list gives 12, and 18 above 200,000, for `google/gemini-3.1-pro-preview`. |
| `fugu-ultra` | 30 | Up to 272,000 input tokens; 45 above. Orchestration is billed in addition. | <https://console.sakana.ai/pricing>, which prices Fugu Ultra v2.0. The harness id `sakana/fugu-ultra` is an alias; OpenCode's model list gives it and `sakana/fugu-ultra-20260615` the same 30 and 45. That the alias is v2.0 is not confirmed. |
| `sakana-namazu` | 4 | None. | <https://console.sakana.ai/pricing>, which prices Namazu v1.0. The harness id `sakana/sakana-namazu` carries no version, so the link is not confirmed; OpenCode's model list gives 4 for it. |

The costs of the other rows were entered before this table was kept and have no recorded source; add a row here when one of them is next read.

## Scores without a measurement

These shipped scores were set on 2026-10-10 as provisional calibration, with no matched measurement behind them:

| Model | reasoning / coding | What supports it |
|---|---|---|
| `fugu-ultra` | 6 / 6 | The abstract of its paper, <https://huggingface.co/papers/2606.21228>, supports high capability. It gives no comparison with the other `L1` models. |
| `gemini-3.1-pro-preview` | 4 / 3 | The GLM-5.2 model card, <https://huggingface.co/zai-org/GLM-5.2>, reports Gemini's reasoning sometimes above GLM-5.2 and its coding below. That is indirect: it is not an assessment against `glm-5.3`. |
| `sakana-namazu` | 4 / 4 | No comparison was found. |
| `haiku-5-5` | 3 / 3 | No comparison was found. |
| `gemini-3.8-flash` | 3 / 3 | Taken from `gemini-3.7-flash`, the version it replaced. |
