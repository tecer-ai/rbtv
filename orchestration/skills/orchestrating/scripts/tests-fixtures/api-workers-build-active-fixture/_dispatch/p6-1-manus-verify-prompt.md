Verify the CURRENT official API model lineup and pricing for two providers — DeepSeek and Google Gemini — against our recorded values below, using each provider's OFFICIAL documentation/pricing pages (navigate the live web yourself).

## What to do

1. Visit DeepSeek's official API documentation pricing page (start at https://api-docs.deepseek.com/ and locate the current "Models & Pricing" page).
2. Visit Google's official Gemini API documentation (start at https://ai.google.dev/gemini-api/docs/pricing and https://ai.google.dev/gemini-api/docs/models and locate the current model list + per-token prices).
3. For EACH recorded row below, find the closest current official equivalent and report: our recorded value → the current live value → a verdict.
4. Also list any CURRENT flagship chat/reasoning text models (per provider) that our table has NO row for (name + price), so we know what is missing.

## Our recorded values to verify (these are 2026 estimates that were never confirmed against live pages)

| Provider | Recorded model id | Recorded price (input/output per 1M tokens) | Recorded context |
|----------|-------------------|---------------------------------------------|------------------|
| DeepSeek | deepseek-v4-pro | $0.435 / $0.87 | 1M tokens |
| DeepSeek | deepseek-v4-flash | $0.14 / $0.28 | 1M tokens |
| Gemini | Gemini 3.5 Flash | $1.50 / $9.00 | (not recorded) |
| Gemini | Gemini 3.1 Pro | $2.00 / $12.00 | (not recorded) |
| Gemini | Gemini 3.1 Flash-Lite | $0.25 / $1.50 | (not recorded) |

## Required report format — IN YOUR REPLY MESSAGE TEXT

Deliver the COMPLETE report as plain markdown text in your chat reply message. CRITICAL CONSTRAINTS:

- Do NOT create file attachments, documents, or artifacts of any kind — the full report must appear verbatim in the message body itself.
- Do NOT reply with only progress narration ("I checked the pages…") — the tables themselves must be in the message.

Report structure:

1. **Verification table** — one row per recorded row above: `provider | recorded id | recorded price | current official id (verbatim from the page) | current official price | verdict: CONFIRMED / STALE (values differ) / NOT-FOUND (no such model listed)`.
2. **Missing-from-our-table** — current flagship text models we have no row for: `provider | official model id | price (input/output per 1M) | one-line role`.
3. **Sources** — the exact URLs you read, with the date/time you accessed them.
4. **Caveats** — anything ambiguous (regional pricing, cache-hit vs cache-miss tiers, free tiers, preview models), stated briefly.

Prices: report standard pay-as-you-go USD per 1M tokens; where a provider lists cache-hit vs cache-miss input prices, report both.
