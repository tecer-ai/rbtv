# Robotville Server Environment Template

> **Purpose:** Provide the approved VPS-side template for Nanobot Slack, allowlist, and LLM credentials without committing secrets to git.

---

## Scope

- Applies to the live VPS only.
- Secrets stay in `/etc/robotville/nanobot-gateway.env` with restricted permissions.
- Repository files must never contain real tokens or API keys.

---

## File Locations

| Artifact | Path | Owner/Mode |
|---|---|---|
| Runtime env file | `/etc/robotville/nanobot-gateway.env` | `root:nanobot`, `0640` |
| Nanobot config | `/srv/nanobot/.nanobot/config.json` | `nanobot:nanobot`, `0640` |

---

## Environment Template (VPS)

Put this content in `/etc/robotville/nanobot-gateway.env` and replace placeholders.

```bash
# Slack Socket Mode credentials
NANOBOT_SLACK_BOT_TOKEN=xoxb-REPLACE_ME
NANOBOT_SLACK_APP_TOKEN=xapp-REPLACE_ME

# Comma-separated Slack user IDs for DM allowlist (maps to dm.allow_from)
# Example: U01234567,U08999999
# Only used when dm.policy is "allowlist" in config.json
NANOBOT_ALLOW_FROM=U_REPLACE_ME

# LLM provider selection
# Supported in this template: openrouter | anthropic | openai | deepseek
NANOBOT_PROVIDER=openrouter
NANOBOT_MODEL=anthropic/claude-opus-4-5

# Provider credentials
NANOBOT_OPENROUTER_API_KEY=sk-or-REPLACE_ME
NANOBOT_ANTHROPIC_API_KEY=sk-ant-OPTIONAL_IF_UNUSED
NANOBOT_OPENAI_API_KEY=sk-OPTIONAL_IF_UNUSED
NANOBOT_DEEPSEEK_API_KEY=sk-OPTIONAL_IF_UNUSED
```

---

## Nanobot Config Template (VPS)

Write `/srv/nanobot/.nanobot/config.json` with the selected provider and Slack settings.

> **Important:** HKUDS Nanobot uses `dm.allow_from` (not top-level `allowFrom`). A top-level `allowFrom` is ignored. For DMs, set `dm.policy: "allowlist"` and `dm.allow_from` with Slack user IDs.

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "REPLACE_AT_RUNTIME"
    },
    "anthropic": {
      "apiKey": "REPLACE_AT_RUNTIME"
    },
    "openai": {
      "apiKey": "REPLACE_AT_RUNTIME"
    },
    "deepseek": {
      "apiKey": "REPLACE_AT_RUNTIME"
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5"
    }
  },
  "channels": {
    "slack": {
      "enabled": true,
      "bot_token": "xoxb-REPLACE_ME",
      "app_token": "xapp-REPLACE_ME",
      "group_policy": "mention",
      "dm": {
        "enabled": true,
        "policy": "allowlist",
        "allow_from": ["U_REPLACE_ME"]
      }
    }
  }
}
```

- For open DMs (no allowlist), use `"policy": "open"` and omit or empty `allow_from`.
- In channels with `group_policy: "mention"`, users must @mention the bot.

---

## Secure Apply Procedure (VPS)

1. Edit env file:
   - `sudoedit /etc/robotville/nanobot-gateway.env`
2. Keep permissions strict:
   - `sudo chown root:nanobot /etc/robotville/nanobot-gateway.env`
   - `sudo chmod 640 /etc/robotville/nanobot-gateway.env`
3. Render/update `/srv/nanobot/.nanobot/config.json` with real values from env.
4. Keep config file restricted:
   - `sudo chown -R nanobot:nanobot /srv/nanobot/.nanobot`
   - `sudo chmod 640 /srv/nanobot/.nanobot/config.json`
5. Ensure nanobot user HOME and NANOBOT_GATEWAY_CMD:
   - Add `HOME=/srv/nanobot` and `NANOBOT_GATEWAY_CMD='nanobot gateway'` to env file if using systemd.
6. Validate configuration as service user:
   - `sudo -u nanobot env HOME=/srv/nanobot /usr/local/bin/nanobot status`
7. Start gateway only after all required values are populated:
   - `sudo -u nanobot env HOME=/srv/nanobot /usr/local/bin/nanobot gateway`

---

## Validation Checklist

- `NANOBOT_SLACK_BOT_TOKEN` starts with `xoxb-`.
- `NANOBOT_SLACK_APP_TOKEN` starts with `xapp-`.
- `NANOBOT_ALLOW_FROM` contains real Slack user IDs (if using DM allowlist).
- `NANOBOT_GATEWAY_CMD` is set (e.g. `nanobot gateway`).
- Selected provider key is present for `NANOBOT_PROVIDER`.
- No real secret exists in any file under `H:\repos\BMAD`.

**If the bot does not answer on Slack**, see `slack-troubleshooting-checklist.md`.
