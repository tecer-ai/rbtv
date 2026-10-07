# Provider accounts

Use `rbtv providers` to see which [provider](glossary/provider.md) logins a machine holds, to switch a harness between accounts of one provider without logging in again, and to read each account's plan usage. Use this page when running those verbs, when deciding which account to switch to, and when adding or changing a supported provider. `rbtv providers -h` and each verb's `-h` own the grammar, options and exit codes.

Run the verbs from a folder inside an installation. They take no `--target`, and a run outside an installation is refused with `installation-unknown`: saved logins belong to one installation, so an agent folder or the current folder never stands in for it.

## Read the state before changing it

`rbtv providers list` reads local files only. Each provider has a row whether or not it is logged in. For a provider whose login can be saved it shows every saved name, `*` on the live one, the account's e-mail and how long the saved login stays valid. `rbtv providers list --supported` shows what rbtv supports instead: lab, harness, login method, key variable and usage source. Models are listed by cast, not here.

`rbtv providers usage` reads plan usage. Its sources differ by provider, and the difference decides how to read a row:

| Provider | Row | Source |
|---|---|---|
| claude | One per saved name, plus the live login when it is saved under no name | The provider's usage address, read with that account's own stored token |
| codex | One | This machine's session files. They describe whichever account ran last, never a saved login that is not live |
| zai, kimi | One | The provider's usage address, read with its key |
| deepseek | One | A money balance; it has no windows |
| google, sakana, xai | One | No usage source exists; the row names the provider's console address |

A model-scoped weekly window, such as `7d fable`, is a part of the plain `7d` window. It can be used up while `7d` still has room.

rbtv never renews a token; the harness owns that. A claude login that has not been live for some hours holds an expired access token, and its row says `token expired` in place of a window. To read it, switch to that name, start one session so the harness renews the token, and read again. A row that cannot be read is reported in its place and counted in the first line; the command still exits 0.

## Save and switch a login

Only a provider with a `saved_login` entry can be saved and switched: claude and codex. Every other provider holds one login or key, with nothing to switch between.

1. Log in with the harness: `claude`, then `/login`; or `codex login`.
2. Save the live login under a name: `rbtv providers name PROVIDER ACCOUNT`.
3. Switch: `rbtv providers switch PROVIDER ACCOUNT`. Start new sessions afterwards. A running session keeps its token in memory, does not see the switch, and writes its own token back when it renews it.

A saved login is usually the only surviving copy of that account's login. Three refusals protect it:

- `switch` refuses while the live login is saved under no name, because switching would overwrite it. Save it with `name` first.
- `name` refuses a name that already holds a different account. Saving the same account again refreshes it.
- `remove-name` deletes nothing without `--yes`, and refuses the live name.

`switch` first writes the live login back under its own name. Tokens change as the harness uses them, so the copy taken at the last `name` is older than the live one.

`--dry-run` on `switch`, `name` and `remove-name` reports what would change and writes nothing.

## Where a saved login lives

`<installation>/.rbtv/config/rbtv/providers/<provider>/<account>.json`, readable by its owner only. The first write creates the folder and a `.gitignore` holding `*` inside it, so no saved login is committed from any clone or worktree. Do not delete that file or add an exception to it. See [Configuration folder](glossary/config.md) for the folder these belong to.

An account name is 1 to 40 lowercase letters, digits and hyphens, and starts with a letter or a digit.

Saved logins belong to an installation; the live login belongs to the machine. Two installations on one machine see different saved names for the same live login. Keep the saved logins of a machine in one installation.

The live files are read at their default places under the home folder. `CLAUDE_CONFIG_DIR` and `CODEX_HOME` are not followed: on a machine that sets either, `switch` and `name` act on the default files, not the ones the harness uses.

Which saved login is live is read from the account id inside the live files, never from a recorded marker.

## Keys and tokens

No key, token or request detail is printed, in a result or an error. A failed read carries the error's class name only. Each credential is sent only to the usage address of its own provider, the one `providers.json` names. A key provider's credential is looked up in this order: its key variable in the process environment, then in the installation's [environment file](glossary/environment-file.md), then the harness's store.

## Add or change a supported provider

The supported providers are one file, `core/cast/capabilities/tools/cast/providers.json`, read by both cast and rbtv. Edit it there, then run cast's route test and `rbtv selftest`.

```json
{
  "stores": {
    "<harness>": {"base_env": "<VARIABLE>", "base_default": "<folder>", "path": "<file inside it>"}
  },
  "providers": {
    "<provider>": {
      "lab": "<AI lab, for display>",
      "login": "account | api-key",
      "env_var": "<key variable; absent for an account login>",
      "harnesses": {"<harness>": {"store_key": "<entry in that harness's store>"}},
      "saved_login": {
        "files": {"<label>": {"path": "<file>", "key": "<one key of it; absent for the whole file>"}},
        "id": ["<label>", "<key path to the account id>"],
        "email": ["<label>", "<key path>"],
        "valid_until_ms": ["<label>", "<key path to an expiry in milliseconds>"]
      },
      "usage": {"source": "endpoint | local | console", "url": "<address>", "path": "<folder>"}
    }
  }
}
```

- `harnesses` names each harness that runs the provider. `store_key` is present only where the harness keeps the credential in its store. The key `api` means cast also reaches the provider directly with its key variable.
- `saved_login` is present only when the login can be saved and switched. A `files` entry with `key` moves that one key and leaves the rest of the file as it is; without `key` it moves the whole file. `id` must name a value that differs between accounts. `email` is a key path, or `{"jwt": [<key path to a token>], "claim": "<name>"}` when the e-mail is inside a token. `valid_until_ms` is optional.
- `usage.source` is `endpoint` with `url`, `local` with `path`, or `console` with `url`. `per_account: true` means the endpoint is read once per saved name with that login's own token. A new `endpoint` provider also needs its parser and its Authorization header form in `lib/usage.py` of the rbtv tool.
- Leave out account state and anything that describes one installation.
