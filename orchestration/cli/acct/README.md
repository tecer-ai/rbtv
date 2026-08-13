# `acct` — AI provider accounts: switch logins, read plan limits

One command for every AI provider account on the box. Two jobs:

1. **Switch** the harness between accounts of one provider **without re-logging-in**, so agents
   keep calling the plain `claude` / `codex` / `kimi` binary. No wrapper command, no
   `CLAUDE_CONFIG_DIR`, no per-account harness.
2. **Read** each account's plan limits — the used % and the renew time of every window the
   provider exposes — as plain text, or as a live bar dashboard (`--posh`).

The use case for (1) is plan-limit rotation across several accounts whose weekly windows reset
on different days: burn one, `use` the next, keep working. (2) is how you decide which.

An orchestration-module CLI: `python3`, stdlib only, no install step beyond a symlink.

```bash
acct                              # EVERY provider, parked or not (* = active slot)
acct claude ls                    # one provider
acct claude add work              # snapshot the CURRENT login into a slot
acct claude use work              # activate a slot
acct claude rm work --force       # delete a slot (costs that account a re-login)

acct usage                        # plan limits for every account with readable usage
acct claude usage all             # every claude account
acct claude usage rbtv            # one account
acct usage --posh                 # live bars, countdowns, repaints every second
acct usage --json                 # machine-readable

acct providers                    # every usage source and endpoint, per provider
acct doctor                       # what is logged in, what can switch, what can be read
acct selftest                     # must exit 0 after ANY edit here
```

Renamed from `claude-acct` (2026-08-07) when the provider argument and the usage mode landed.

## Install

```bash
ln -s "$(pwd)/orchestration/cli/acct/acct.py" ~/.local/bin/acct
```

Run from the rbtv repo root. The CLI resolves its workspace by walking up from its own real path
to the nearest `rbtv.json`, so the symlink works from any cwd; `RBTV_WORKSPACE` overrides.

## Which providers can do what

Switching needs a credential store the tool can lift whole. Usage needs an endpoint or a local
file that reports it. Those are different sets, and the difference is a property of the
providers, not a gap here.

| Provider | Switch | Usage | Notes |
|---|---|---|---|
| claude | ✅ | ✅ per account | The only provider with a PER-ACCOUNT usage endpoint — so the only one where `usage all` is genuinely multi-account |
| codex | ✅ | ✅ one row | Usage is a local parse of `~/.codex/sessions` rollout files, which are per-MACHINE — it describes whichever account last ran, never a parked slot |
| kimi | ✅ | console only | Subscription login exposes no usage endpoint. An opt-in `sk-kimi` key (kimi.com/code/console) or a Moonshot platform key does |
| zai | — | ✅ | One key in opencode's shared `auth.json`; nothing to switch between |
| deepseek | — | ✅ balance | Pay-as-you-go: a money balance, no windows |
| google, sakana | — | console only | No usage endpoint exists (verified 2026-07-24) |
| xai | — | console only | Grok subscription login exposes no usage endpoint (2026-08-13). Its `auth.json` entry is `type: oauth` (`access`/`refresh`/`expires`, **no** `key`) — presence is read off `access`, so a login is not mistaken for `no credential` |

Adding a switchable provider is one row in the `PROVIDERS` table: the files (or JSON keys) that
make up a login, plus how to read an account id out of them.

`acct ls` prints a line for every provider in both columns, whether or not anything is parked —
`logged in, no slot saved`, `not logged in`, and the usage-only group each say themselves. That
is deliberate: a provider that printed nothing because it merely had no slot yet was
indistinguishable from one the tool does not support.

## Adding an account

There are no tokens to copy by hand:

```bash
claude /login          # authenticate the account normally
acct claude add work   # captures whatever is now live
```

## What a slot is

A slot is a snapshot of the credential locations that make up ONE login, at
`{workspace}/.rbtv/config/acct/<provider>/<name>.json`, mode `600` — the CMP-1-ruled credential
home (moved there from `.rbtv/env/{provider}-accts/` on 2026-08-07).

⚠ **`.rbtv/config/` is NOT gitignored wholesale** — its siblings (`.env`, the chat-bridge config)
are listed file by file. `.rbtv/config/acct/` carries its own DIRECTORY rule in the workspace
`.gitignore`, and that one line is all that keeps real refresh tokens out of a commit. It covers
the whole tree so a provider folder created later is ignored the moment it exists. Relocating
these files means moving that rule in the same change — never afterwards.

A location is either a whole FILE or ONE KEY of a JSON file. Claude needs both, and that is why
the distinction exists: everything else in `~/.claude.json` (project history, settings) must
survive a switch untouched.

| Provider | Locations |
|---|---|
| claude | `~/.claude/.credentials.json` (whole file) + `~/.claude.json` → `oauthAccount` key |
| codex | `~/.codex/auth.json` |
| kimi | `~/.kimi/credentials/kimi-code.json` |

## Four design points, each paid for by a bug

**Slots are files, not a static `.env`.** Tokens rotate: a Claude access token lasts ~8h and the
CLI rewrites the credential file on every refresh, rolling the refresh token forward to a ~4-week
horizon. A token pasted into an env file is stale within a day. `use` therefore writes the *live*
credentials back into the outgoing slot before swapping the new one in.

**The active slot is derived, never recorded.** An earlier version kept a `.current` marker file;
it drifted out of sync with the real credential store within an hour of existing. The account id
inside the live credentials already answers "which account is live" — so `active()` matches that
id against the slots and there is no second source of truth to go wrong. Per provider that id is
`oauthAccount.accountUuid` (claude), `tokens.account_id` (codex), or the access token's JWT `sub`
(kimi).

**Two refusals guard the one irreversible act.** A slot is usually the *only* surviving copy of an
account's refresh token, so `use` refuses when the live login matches no slot (it would be
overwritten and lost), and `rm` refuses without `--force`. Both cost a fresh login to undo.

**An expired token is REPORTED, never rendered as an empty window set.** See below.

## What it does NOT do

**It never refreshes a token.** The harness owns its own token chain; `acct` reads and moves
credentials, it does not renew them. The consequence is visible and deliberate: a claude slot
parked for more than ~8h has an expired access token, and `acct claude usage all` reports that
account as `token expired` with the fix line, rather than silently omitting it or showing a 0%
bar. An account reading 0% because nobody could read it is exactly the misreading that would
cost a wrong rotation.

To read a stale slot's usage: `acct claude use <name>`, run one session (the harness refreshes),
then read it again.

**Switching is between sessions.** A running harness holds its token in memory: it will not pick
up a swap, and on its next refresh it writes its own token back over the slot just activated.
Switch, then start new sessions. Mid-run switching is not achievable from outside the process.

**Keys and tokens are never printed** — not in `ls`, `doctor`, `usage`, or an error. Fetch
failures carry the exception class name only, never the request. Each credential is sent only to
its own provider's documented endpoint; `acct providers` lists every one.
