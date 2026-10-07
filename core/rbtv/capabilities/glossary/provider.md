# Provider

A provider is the AI lab account system whose models a [harness](harness.md) runs and whose plan or balance a launch spends. rbtv names eight: `claude`, `codex`, `zai`, `deepseek`, `kimi`, `google`, `sakana` and `xai`. A provider is not a harness: `claude` and `codex` are each reached through the harness of the same name, and the other six through OpenCode.

Name the provider when the question is whose login or key is used, whether this machine holds it, or how much of a plan is left. Name the harness when the question is how instructions and tools reach the agent. Name the model, through cast, when choosing what to launch; only cast lists models.

## Login and saved login

A provider's login is either an account sign-in made with the harness or an API key. A key is found in its key variable or in the harness's store.

A saved login is a named copy of the files that make up one account's login, kept in one installation. Only a provider with an account sign-in that rbtv can copy whole has saved logins: `claude` and `codex`. The live login is the one the harness uses now. A saved login whose account id equals the live login's is the live name.

## Work with providers

Read and change provider accounts only through `rbtv providers`; follow [Provider accounts](../providers.md) for the verbs, the refusals that protect a saved login, and where saved logins live. Do not copy or edit a harness's credential files by hand, and never write a key or token into a prompt, a report or a record.

The supported providers are data in `core/cast/capabilities/tools/cast/providers.json`. To add or change one, follow the last section of Provider accounts.

## Checks

`rbtv providers list --supported` shows every provider with its lab, harness and login method. `rbtv providers list` shows whether this machine holds each login, and for `claude` and `codex` each saved name with `*` on the live one.
